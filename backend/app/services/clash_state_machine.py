import datetime
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload

from app.core.datetime_utils import utcnow, to_iso_z
from app.core.department import normalize_department
from app.core.notifications import NotificationCollector
from app.models.schemas import UserSecurityClaims
from app.core.database import (
    ClashCase,
    CaseTimeline,
    Assessment,
    CourseOffering,
    Student,
    Faculty,
    User,
    AuditLog,
    Notification,
    Event,
)
from app.services.clash_detector import suggest_retake_slot

STUCK_THRESHOLD_HOURS = 48

import json

def _create_audit(
    db: AsyncSession,
    actor: UserSecurityClaims,
    action: str,
    case_id: int,
    details: Dict[str, Any],
) -> AuditLog:
    entry = AuditLog(
        user_id=actor.user_id,
        role=actor.role,
        event_type=action,
        details=json.dumps({"case_id": case_id, **details}),
        timestamp=utcnow(),
    )
    db.add(entry)
    return entry

def _queue_notification(
    db: AsyncSession,
    collector: NotificationCollector,
    target_user_id: int,
    notif_type: str,
    title: str,
    body: str,
    case_id: Optional[int] = None,
    event_id: Optional[int] = None,
) -> Notification:
    notif = Notification(
        user_id=target_user_id,
        type=notif_type,
        title=title,
        body=body,
        case_id=case_id,
        event_id=event_id,
        is_read=False,
        created_at=utcnow(),
    )
    db.add(notif)
    collector.queue_publish(f"channel:user:{target_user_id}", {
        "id": None, # Will be persisted post-commit
        "type": notif_type,
        "title": title,
        "body": body,
        "case_id": case_id,
        "event_id": event_id,
        "created_at": to_iso_z(utcnow()),
    })
    return notif

async def get_hod_user_ids(db: AsyncSession, department: str) -> List[int]:
    norm_dept = normalize_department(department)
    stmt = (
        select(User.id)
        .join(Faculty, Faculty.user_id == User.id)
        .where(
            func.lower(Faculty.designation).in_(["head of department", "hod"])
        )
    )
    rows = (await db.execute(stmt)).scalars().all()
    # Filter department in python for consistency with normalize_department
    hod_users = []
    for uid in rows:
        fac = (await db.execute(select(Faculty).where(Faculty.user_id == uid))).scalar_one_or_none()
        if fac and normalize_department(fac.department) == norm_dept:
            hod_users.append(uid)
    return hod_users

async def file_clash_cases_bulk(
    db: AsyncSession,
    case_ids: List[int],
    actor: UserSecurityClaims,
    collector: NotificationCollector,
) -> List[ClashCase]:
    """
    Transition: DETECTED -> REQUEST_FILED
    Allowed: Admin only.
    Atomic all-or-nothing: Recomputes suggested retake, executes CAS,
    writes CaseTimeline, AuditLog, and Notifications.
    """
    if actor.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can file clash requests")

    if not case_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No case IDs provided")

    # Fetch all cases explicitly
    stmt = (
        select(ClashCase)
        .where(ClashCase.id.in_(case_ids))
        .options(
            selectinload(ClashCase.assessment).selectinload(Assessment.offering).selectinload(CourseOffering.faculty).selectinload(Faculty.user),
            selectinload(ClashCase.student).selectinload(Student.user),
            selectinload(ClashCase.event),
        )
    )
    cases = (await db.execute(stmt)).scalars().all()

    if len(cases) != len(set(case_ids)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or more cases were not found")

    # Validate all are in DETECTED status (atomic check)
    for c in cases:
        if c.status != "DETECTED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Case {c.id} is in status '{c.status}', expected 'DETECTED'",
            )

    now = utcnow()
    updated_cases = []

    for c in cases:
        # Recompute suggested retake
        new_sugg = await suggest_retake_slot(db, c.student, c.assessment, c.event)
        new_sugg_id = new_sugg.id if new_sugg else None

        # CAS update
        stmt_cas = (
            update(ClashCase)
            .where(ClashCase.id == c.id, ClashCase.status == "DETECTED")
            .values(
                status="REQUEST_FILED",
                suggested_retake_assessment_id=new_sugg_id,
                filed_by=actor.user_id,
                filed_at=now,
                updated_at=now,
            )
        )
        res = await db.execute(stmt_cas)
        if res.rowcount != 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Concurrent conflict: Case {c.id} could not be updated",
            )

        # Timeline
        timeline = CaseTimeline(
            case_id=c.id,
            actor_user_id=actor.user_id,
            actor_role="admin",
            from_status="DETECTED",
            to_status="REQUEST_FILED",
            note="Admin filed reschedule request to course faculty",
            at=now,
        )
        db.add(timeline)

        # Audit
        _create_audit(
            db, actor, "CLASH_REQUEST_FILED", c.id,
            {"from_status": "DETECTED", "to_status": "REQUEST_FILED", "suggested_retake_id": new_sugg_id}
        )

        # Notifications:
        # 1. Professor of the course
        prof_user_id = c.assessment.offering.faculty.user_id
        _queue_notification(
            db, collector, prof_user_id,
            "RESCHEDULE_REQUEST_RECEIVED",
            f"Reschedule Request: {c.assessment.offering.subject}",
            f"Admin filed an exam clash reschedule request for student {c.student.roll_number} for {c.assessment.kind}.",
            case_id=c.id, event_id=c.event_id
        )

        # 2. HOD of the department (for department awareness)
        hod_uids = await get_hod_user_ids(db, c.assessment.offering.department)
        for h_uid in hod_uids:
            _queue_notification(
                db, collector, h_uid,
                "DEPT_RESCHEDULE_FILED",
                f"Department Request: {c.assessment.offering.subject}",
                f"Reschedule request filed for {c.student.roll_number} in {c.assessment.offering.department}.",
                case_id=c.id, event_id=c.event_id
            )

        c.status = "REQUEST_FILED"
        c.suggested_retake_assessment_id = new_sugg_id
        c.filed_by = actor.user_id
        c.filed_at = now
        c.updated_at = now
        updated_cases.append(c)

    return updated_cases

async def professor_decide_bulk(
    db: AsyncSession,
    case_ids: List[int],
    decision: str,
    slot_id: Optional[int],
    custom_at: Optional[datetime.datetime],
    note: Optional[str],
    rejection_reason: Optional[str],
    actor: UserSecurityClaims,
    collector: NotificationCollector,
) -> List[ClashCase]:
    """
    Transition: REQUEST_FILED -> APPROVED | COUNTER_PROPOSED | REJECTED (cascades to ESCALATED_TO_HOD)
    Allowed: Faculty teaching the course offering.
    Atomic all-or-nothing CAS execution.
    """
    if actor.role != "faculty" or not actor.faculty_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only course faculty can decide on cases")

    if not case_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No case IDs provided")

    decision = decision.strip().lower()
    if decision not in ["approve", "counter", "reject"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid decision. Must be approve, counter, or reject")

    if decision == "reject" and not rejection_reason:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="rejection_reason is mandatory when rejecting")

    if decision == "counter" and not (slot_id or custom_at):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A slot_id or custom_at is required for counter proposals")

    stmt = (
        select(ClashCase)
        .where(ClashCase.id.in_(case_ids))
        .options(
            selectinload(ClashCase.assessment).selectinload(Assessment.offering),
            selectinload(ClashCase.student).selectinload(Student.user),
            selectinload(ClashCase.event),
        )
    )
    cases = (await db.execute(stmt)).scalars().all()

    if len(cases) != len(set(case_ids)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or more cases not found")

    # Validate professor scope and status
    for c in cases:
        if c.assessment.offering.faculty_id != actor.faculty_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not instruct the offering for case {c.id}",
            )
        if c.status != "REQUEST_FILED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Case {c.id} is in status '{c.status}', expected 'REQUEST_FILED'",
            )

    now = utcnow()
    updated_cases = []

    for c in cases:
        if decision == "approve":
            chosen_slot_id = slot_id or (c.suggested_retake_assessment_id if not custom_at else None)
            chosen_custom_at = custom_at if not chosen_slot_id else None

            stmt_cas = (
                update(ClashCase)
                .where(ClashCase.id == c.id, ClashCase.status == "REQUEST_FILED")
                .values(
                    status="APPROVED",
                    retake_assessment_id=chosen_slot_id,
                    retake_at=chosen_custom_at,
                    retake_note=note,
                    decided_by=actor.user_id,
                    decided_at=now,
                    updated_at=now,
                )
            )
            res = await db.execute(stmt_cas)
            if res.rowcount != 1:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"CAS conflict on case {c.id}")

            timeline = CaseTimeline(
                case_id=c.id,
                actor_user_id=actor.user_id,
                actor_role="faculty",
                from_status="REQUEST_FILED",
                to_status="APPROVED",
                note=f"Professor approved reschedule. {note or ''}".strip(),
                at=now,
            )
            db.add(timeline)
            _create_audit(db, actor, "CLASH_APPROVED", c.id, {"from_status": "REQUEST_FILED", "to_status": "APPROVED"})

            # Notify student and admin
            _queue_notification(
                db, collector, c.student.user_id,
                "CLASH_APPROVED",
                f"Reschedule Approved: {c.assessment.offering.subject}",
                f"Your exam reschedule was approved by the professor. Note: {note or 'Slot confirmed'}",
                case_id=c.id, event_id=c.event_id
            )
            if c.filed_by:
                _queue_notification(
                    db, collector, c.filed_by,
                    "CLASH_APPROVED",
                    f"Reschedule Approved: {c.student.roll_number}",
                    f"Professor approved reschedule request for case #{c.id}.",
                    case_id=c.id, event_id=c.event_id
                )

            c.status = "APPROVED"
            c.retake_assessment_id = chosen_slot_id
            c.retake_at = chosen_custom_at
            c.retake_note = note
            c.decided_by = actor.user_id
            c.decided_at = now
            c.updated_at = now

        elif decision == "counter":
            stmt_cas = (
                update(ClashCase)
                .where(ClashCase.id == c.id, ClashCase.status == "REQUEST_FILED")
                .values(
                    status="COUNTER_PROPOSED",
                    retake_assessment_id=slot_id,
                    retake_at=custom_at,
                    retake_note=note,
                    decided_by=actor.user_id,
                    decided_at=now,
                    updated_at=now,
                )
            )
            res = await db.execute(stmt_cas)
            if res.rowcount != 1:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"CAS conflict on case {c.id}")

            timeline = CaseTimeline(
                case_id=c.id,
                actor_user_id=actor.user_id,
                actor_role="faculty",
                from_status="REQUEST_FILED",
                to_status="COUNTER_PROPOSED",
                note=f"Professor counter-proposed alternative slot: {note or ''}".strip(),
                at=now,
            )
            db.add(timeline)
            _create_audit(db, actor, "CLASH_COUNTER_PROPOSED", c.id, {"from_status": "REQUEST_FILED", "to_status": "COUNTER_PROPOSED"})

            # Notify student and admin
            _queue_notification(
                db, collector, c.student.user_id,
                "COUNTER_PROPOSED",
                f"Reschedule Counter-Proposal: {c.assessment.offering.subject}",
                f"Professor counter-proposed an alternative time for your retake.",
                case_id=c.id, event_id=c.event_id
            )
            if c.filed_by:
                _queue_notification(
                    db, collector, c.filed_by,
                    "COUNTER_PROPOSED",
                    f"Counter Proposal: Case #{c.id}",
                    f"Professor proposed counter slot for student {c.student.roll_number}.",
                    case_id=c.id, event_id=c.event_id
                )

            c.status = "COUNTER_PROPOSED"
            c.retake_assessment_id = slot_id
            c.retake_at = custom_at
            c.retake_note = note
            c.decided_by = actor.user_id
            c.decided_at = now
            c.updated_at = now

        elif decision == "reject":
            # 1. CAS to REJECTED
            stmt1 = (
                update(ClashCase)
                .where(ClashCase.id == c.id, ClashCase.status == "REQUEST_FILED")
                .values(
                    status="REJECTED",
                    rejection_reason=rejection_reason,
                    decided_by=actor.user_id,
                    decided_at=now,
                    updated_at=now,
                )
            )
            res1 = await db.execute(stmt1)
            if res1.rowcount != 1:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"CAS conflict on case {c.id}")

            # Timeline 1
            t1 = CaseTimeline(
                case_id=c.id,
                actor_user_id=actor.user_id,
                actor_role="faculty",
                from_status="REQUEST_FILED",
                to_status="REJECTED",
                note=f"Professor rejected: {rejection_reason}",
                at=now,
            )
            db.add(t1)

            # 2. Cascade immediately to ESCALATED_TO_HOD in the SAME transaction
            stmt2 = (
                update(ClashCase)
                .where(ClashCase.id == c.id, ClashCase.status == "REJECTED")
                .values(
                    status="ESCALATED_TO_HOD",
                    updated_at=now,
                )
            )
            res2 = await db.execute(stmt2)
            if res2.rowcount != 1:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"CAS escalation conflict on case {c.id}")

            # Timeline 2
            t2 = CaseTimeline(
                case_id=c.id,
                actor_user_id=actor.user_id,
                actor_role="system",
                from_status="REJECTED",
                to_status="ESCALATED_TO_HOD",
                note="Auto-escalated to Head of Department following professor rejection",
                at=now,
            )
            db.add(t2)

            _create_audit(
                db, actor, "CLASH_REJECTED_ESCALATED", c.id,
                {"from_status": "REQUEST_FILED", "intermediate": "REJECTED", "to_status": "ESCALATED_TO_HOD", "reason": rejection_reason}
            )

            # Notify HOD(s), Student, and Admin
            hod_uids = await get_hod_user_ids(db, c.assessment.offering.department)
            for h_uid in hod_uids:
                _queue_notification(
                    db, collector, h_uid,
                    "CLASH_ESCALATED_HOD",
                    f"Escalated to HOD: {c.student.roll_number} - {c.assessment.offering.subject}",
                    f"Professor rejected reschedule: '{rejection_reason}'. Case #{c.id} requires HOD review/override.",
                    case_id=c.id, event_id=c.event_id
                )
            _queue_notification(
                db, collector, c.student.user_id,
                "CLASH_ESCALATED",
                f"Reschedule Escalated to HOD: {c.assessment.offering.subject}",
                f"Your request was rejected by professor and automatically escalated to Head of Department.",
                case_id=c.id, event_id=c.event_id
            )
            if c.filed_by:
                _queue_notification(
                    db, collector, c.filed_by,
                    "CLASH_ESCALATED",
                    f"Case #{c.id} Escalated to HOD",
                    f"Professor rejected case #{c.id} with reason: {rejection_reason}. Escalated to HOD.",
                    case_id=c.id, event_id=c.event_id
                )

            c.status = "ESCALATED_TO_HOD"
            c.rejection_reason = rejection_reason
            c.decided_by = actor.user_id
            c.decided_at = now
            c.updated_at = now

        updated_cases.append(c)

    return updated_cases

async def admin_accept_counter(
    db: AsyncSession,
    case_id: int,
    actor: UserSecurityClaims,
    collector: NotificationCollector,
) -> ClashCase:
    if actor.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin can accept counter proposals")

    stmt = (
        select(ClashCase)
        .where(ClashCase.id == case_id)
        .options(
            selectinload(ClashCase.assessment).selectinload(Assessment.offering).selectinload(CourseOffering.faculty),
            selectinload(ClashCase.student).selectinload(Student.user),
        )
    )
    case = (await db.execute(stmt)).scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    if case.status != "COUNTER_PROPOSED":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Case is in status '{case.status}', expected 'COUNTER_PROPOSED'")

    now = utcnow()
    stmt_cas = (
        update(ClashCase)
        .where(ClashCase.id == case_id, ClashCase.status == "COUNTER_PROPOSED")
        .values(
            status="APPROVED",
            decided_by=actor.user_id,
            decided_at=now,
            updated_at=now,
        )
    )
    res = await db.execute(stmt_cas)
    if res.rowcount != 1:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="CAS conflict: Case status changed concurrently")

    timeline = CaseTimeline(
        case_id=case_id,
        actor_user_id=actor.user_id,
        actor_role="admin",
        from_status="COUNTER_PROPOSED",
        to_status="APPROVED",
        note="Admin accepted professor counter-proposed slot on behalf of student",
        at=now,
    )
    db.add(timeline)
    _create_audit(db, actor, "CLASH_COUNTER_ACCEPTED", case_id, {"from_status": "COUNTER_PROPOSED", "to_status": "APPROVED"})

    # Notify student and professor
    _queue_notification(
        db, collector, case.student.user_id,
        "COUNTER_ACCEPTED",
        f"Reschedule Confirmed: {case.assessment.offering.subject}",
        "Admin accepted the counter-proposed reschedule slot on your behalf.",
        case_id=case_id, event_id=case.event_id
    )
    prof_uid = case.assessment.offering.faculty.user_id
    _queue_notification(
        db, collector, prof_uid,
        "COUNTER_ACCEPTED",
        f"Counter Slot Confirmed: Case #{case_id}",
        "Admin accepted your proposed counter slot.",
        case_id=case_id, event_id=case.event_id
    )

    case.status = "APPROVED"
    case.decided_by = actor.user_id
    case.decided_at = now
    case.updated_at = now
    return case

async def admin_send_back(
    db: AsyncSession,
    case_id: int,
    note: str,
    actor: UserSecurityClaims,
    collector: NotificationCollector,
) -> ClashCase:
    if actor.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin can send back counter proposals")

    stmt = (
        select(ClashCase)
        .where(ClashCase.id == case_id)
        .options(
            selectinload(ClashCase.assessment).selectinload(Assessment.offering).selectinload(CourseOffering.faculty),
            selectinload(ClashCase.student).selectinload(Student.user),
        )
    )
    case = (await db.execute(stmt)).scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    if case.status != "COUNTER_PROPOSED":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Case is in status '{case.status}', expected 'COUNTER_PROPOSED'")

    now = utcnow()
    stmt_cas = (
        update(ClashCase)
        .where(ClashCase.id == case_id, ClashCase.status == "COUNTER_PROPOSED")
        .values(
            status="REQUEST_FILED",
            retake_note=note,
            updated_at=now,
        )
    )
    res = await db.execute(stmt_cas)
    if res.rowcount != 1:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="CAS conflict: Case status changed concurrently")

    timeline = CaseTimeline(
        case_id=case_id,
        actor_user_id=actor.user_id,
        actor_role="admin",
        from_status="COUNTER_PROPOSED",
        to_status="REQUEST_FILED",
        note=f"Admin returned proposal to faculty for reconsideration: {note}",
        at=now,
    )
    db.add(timeline)
    _create_audit(db, actor, "CLASH_SENT_BACK", case_id, {"from_status": "COUNTER_PROPOSED", "to_status": "REQUEST_FILED", "note": note})

    prof_uid = case.assessment.offering.faculty.user_id
    _queue_notification(
        db, collector, prof_uid,
        "COUNTER_SENT_BACK",
        f"Proposal Returned: Case #{case_id}",
        f"Admin returned counter proposal for {case.assessment.offering.subject}: {note}",
        case_id=case_id, event_id=case.event_id
    )

    case.status = "REQUEST_FILED"
    case.retake_note = note
    case.updated_at = now
    return case

async def hod_override(
    db: AsyncSession,
    case_id: int,
    slot_id: Optional[int],
    custom_at: Optional[datetime.datetime],
    note: str,
    actor: UserSecurityClaims,
    collector: NotificationCollector,
) -> ClashCase:
    """
    Transition: ESCALATED_TO_HOD -> APPROVED
    Allowed: HOD of that offering's department only.
    Mandatory note and slot assignment.
    """
    if not actor.is_hod:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Head of Department can override escalated cases")

    if not note or not note.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A justification note is mandatory for HOD overrides")

    if not (slot_id or custom_at):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Must assign a retake slot_id or custom_at")

    stmt = (
        select(ClashCase)
        .where(ClashCase.id == case_id)
        .options(
            selectinload(ClashCase.assessment).selectinload(Assessment.offering).selectinload(CourseOffering.faculty),
            selectinload(ClashCase.student).selectinload(Student.user),
        )
    )
    case = (await db.execute(stmt)).scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    if normalize_department(case.assessment.offering.department) != normalize_department(actor.department or ""):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Offering department '{case.assessment.offering.department}' does not match your HOD scope '{actor.department}'",
        )

    if case.status != "ESCALATED_TO_HOD":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Case status is '{case.status}', expected 'ESCALATED_TO_HOD'")

    now = utcnow()
    stmt_cas = (
        update(ClashCase)
        .where(ClashCase.id == case_id, ClashCase.status == "ESCALATED_TO_HOD")
        .values(
            status="APPROVED",
            retake_assessment_id=slot_id,
            retake_at=custom_at,
            retake_note=f"[HOD Override] {note}",
            decided_by=actor.user_id,
            decided_at=now,
            updated_at=now,
        )
    )
    res = await db.execute(stmt_cas)
    if res.rowcount != 1:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="CAS conflict: Case status changed concurrently")

    timeline = CaseTimeline(
        case_id=case_id,
        actor_user_id=actor.user_id,
        actor_role="faculty", # HOD acts under faculty role authority
        from_status="ESCALATED_TO_HOD",
        to_status="APPROVED",
        note=f"HOD override approved reschedule: {note}",
        at=now,
    )
    db.add(timeline)
    _create_audit(db, actor, "CLASH_HOD_OVERRIDE", case_id, {"from_status": "ESCALATED_TO_HOD", "to_status": "APPROVED", "note": note})

    # Notify student, professor, admin
    _queue_notification(
        db, collector, case.student.user_id,
        "HOD_OVERRIDE_APPROVED",
        f"HOD Approved Reschedule: {case.assessment.offering.subject}",
        f"Head of Department approved your reschedule request. Note: {note}",
        case_id=case_id, event_id=case.event_id
    )
    prof_uid = case.assessment.offering.faculty.user_id
    _queue_notification(
        db, collector, prof_uid,
        "HOD_OVERRIDE_APPROVED",
        f"HOD Override on Case #{case_id}",
        f"HOD approved reschedule for student {case.student.roll_number}. Note: {note}",
        case_id=case_id, event_id=case.event_id
    )
    if case.filed_by:
        _queue_notification(
            db, collector, case.filed_by,
            "HOD_OVERRIDE_APPROVED",
            f"HOD Override: Case #{case_id}",
            f"HOD approved case #{case_id} for student {case.student.roll_number}.",
            case_id=case_id, event_id=case.event_id
        )

    case.status = "APPROVED"
    case.retake_assessment_id = slot_id
    case.retake_at = custom_at
    case.retake_note = f"[HOD Override] {note}"
    case.decided_by = actor.user_id
    case.decided_at = now
    case.updated_at = now
    return case

async def complete_case(
    db: AsyncSession,
    case_id: int,
    actor: UserSecurityClaims,
    collector: NotificationCollector,
) -> ClashCase:
    """
    Transition: APPROVED -> COMPLETED
    Allowed: Admin or Course Faculty.
    """
    stmt = (
        select(ClashCase)
        .where(ClashCase.id == case_id)
        .options(
            selectinload(ClashCase.assessment).selectinload(Assessment.offering).selectinload(CourseOffering.faculty),
            selectinload(ClashCase.student).selectinload(Student.user),
        )
    )
    case = (await db.execute(stmt)).scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    is_admin = actor.role == "admin"
    is_offering_prof = (actor.role == "faculty" and actor.faculty_id == case.assessment.offering.faculty_id)
    if not (is_admin or is_offering_prof):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin or course faculty can mark a case completed")

    if case.status != "APPROVED":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Case status is '{case.status}', expected 'APPROVED'")

    now = utcnow()
    stmt_cas = (
        update(ClashCase)
        .where(ClashCase.id == case_id, ClashCase.status == "APPROVED")
        .values(
            status="COMPLETED",
            updated_at=now,
        )
    )
    res = await db.execute(stmt_cas)
    if res.rowcount != 1:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="CAS conflict: Case status changed concurrently")

    timeline = CaseTimeline(
        case_id=case_id,
        actor_user_id=actor.user_id,
        actor_role=actor.role,
        from_status="APPROVED",
        to_status="COMPLETED",
        note="Retake assessment completed and recorded",
        at=now,
    )
    db.add(timeline)
    _create_audit(db, actor, "CLASH_COMPLETED", case_id, {"from_status": "APPROVED", "to_status": "COMPLETED"})

    # Notify student, admin, professor
    _queue_notification(
        db, collector, case.student.user_id,
        "CLASH_COMPLETED",
        f"Retake Completed: {case.assessment.offering.subject}",
        "Your rescheduled assessment has been marked completed.",
        case_id=case_id, event_id=case.event_id
    )
    if case.filed_by and case.filed_by != actor.user_id:
        _queue_notification(
            db, collector, case.filed_by,
            "CLASH_COMPLETED",
            f"Case #{case_id} Completed",
            f"Case #{case_id} for student {case.student.roll_number} has been completed.",
            case_id=case_id, event_id=case.event_id
        )
    prof_uid = case.assessment.offering.faculty.user_id
    if prof_uid != actor.user_id:
        _queue_notification(
            db, collector, prof_uid,
            "CLASH_COMPLETED",
            f"Case #{case_id} Completed",
            f"Case #{case_id} for {case.assessment.offering.subject} has been completed.",
            case_id=case_id, event_id=case.event_id
        )

    case.status = "COMPLETED"
    case.updated_at = now
    return case
