from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
import datetime

from app.api.auth import get_current_user_claims
from app.core.database import (
    get_db_session,
    Event,
    EventParticipant,
    CourseOffering,
    Assessment,
    ClashCase,
    CaseTimeline,
    Notification,
    Student,
    Faculty,
    User,
)
from app.core.datetime_utils import utcnow, to_iso_z, parse_iso_utc
from app.core.department import normalize_department
from app.core.notifications import NotificationCollector
from app.models.schemas import (
    UserSecurityClaims,
    EventCreateRequest,
    EventResponse,
    EventDetailResponse,
    AddParticipantsRequest,
    ClashCaseResponse,
    ClashCaseDetailResponse,
    CaseTimelineResponse,
    CaseFileBulkRequest,
    CaseDecisionBulkRequest,
    CounterActionRequest,
    HODOverrideRequest,
    HODOverviewResponse,
    NotificationResponse,
)
from app.services.clash_detector import detect_clashes_for_event
from app.services.clash_state_machine import (
    file_clash_cases_bulk,
    professor_decide_bulk,
    admin_accept_counter,
    admin_send_back,
    hod_override,
    complete_case,
    STUCK_THRESHOLD_HOURS,
)

router = APIRouter(prefix="/clash", tags=["Event-Exam Clash & Retake"])

def _format_case_response(case: ClashCase) -> ClashCaseResponse:
    student_name = "Unknown Student"
    student_roll = ""
    student_dept = ""
    student_section = ""
    if "student" in case.__dict__ and case.student:
        student_roll = case.student.roll_number
        student_dept = case.student.department
        student_section = case.student.section or ""
        if "user" in case.student.__dict__ and case.student.user:
            student_name = case.student.user.name

    subject = ""
    course_code = ""
    assessment_kind = ""
    assessment_start = ""
    assessment_end = ""
    offering_section = ""
    faculty_id = None
    faculty_name = None

    if "assessment" in case.__dict__ and case.assessment:
        assessment_kind = case.assessment.kind
        assessment_start = to_iso_z(case.assessment.start_at)
        assessment_end = to_iso_z(case.assessment.end_at)
        if "offering" in case.assessment.__dict__ and case.assessment.offering:
            off = case.assessment.offering
            subject = off.subject
            course_code = off.course_code
            offering_section = off.section or ""
            faculty_id = off.faculty_id
            if "faculty" in off.__dict__ and off.faculty:
                if "user" in off.faculty.__dict__ and off.faculty.user:
                    faculty_name = off.faculty.user.name

    event_title = ""
    if "event" in case.__dict__ and case.event:
        event_title = case.event.title

    sugg_info = None
    if "suggested_retake" in case.__dict__ and case.suggested_retake:
        sugg_info = (
            f"{case.suggested_retake.kind} ({to_iso_z(case.suggested_retake.start_at)} - "
            f"{case.suggested_retake.venue or 'TBA'})"
        )

    retake_info = None
    if "retake_assessment" in case.__dict__ and case.retake_assessment:
        retake_info = (
            f"{case.retake_assessment.kind} ({to_iso_z(case.retake_assessment.start_at)} - "
            f"{case.retake_assessment.venue or 'TBA'})"
        )
    elif case.retake_at:
        retake_info = f"Custom Slot: {to_iso_z(case.retake_at)}"

    return ClashCaseResponse(
        id=case.id,
        event_id=case.event_id,
        event_title=event_title,
        student_id=case.student_id,
        student_name=student_name,
        student_roll=student_roll,
        student_section=student_section,
        student_department=student_dept,
        assessment_id=case.assessment_id,
        course_code=course_code,
        subject=subject,
        offering_section=offering_section,
        assessment_kind=assessment_kind,
        assessment_start=assessment_start,
        assessment_end=assessment_end,
        assessment_start_at=assessment_start,
        assessment_end_at=assessment_end,
        faculty_id=faculty_id,
        faculty_name=faculty_name,
        status=case.status,
        suggested_retake_assessment_id=case.suggested_retake_assessment_id,
        suggested_retake_info=sugg_info,
        retake_assessment_id=case.retake_assessment_id,
        retake_info=retake_info,
        retake_at=to_iso_z(case.retake_at) if case.retake_at else None,
        retake_note=case.retake_note,
        rejection_reason=case.rejection_reason,
        created_at=to_iso_z(case.created_at),
        updated_at=to_iso_z(case.updated_at),
    )

# --- Events Endpoints (Admin) ---

@router.post("/events", response_model=EventResponse)
async def create_event(
    req: EventCreateRequest,
    claims: UserSecurityClaims = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_db_session),
):
    if claims.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can create events")

    start_dt = parse_iso_utc(req.start_at)
    end_dt = parse_iso_utc(req.end_at)
    if end_dt <= start_dt:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end_at must be after start_at")

    event = Event(
        title=req.title,
        description=req.description,
        start_at=start_dt,
        end_at=end_dt,
        created_by=claims.user_id,
        created_at=utcnow(),
    )
    db.add(event)
    await db.commit()

    return EventResponse(
        id=event.id,
        title=event.title,
        description=event.description,
        start_at=to_iso_z(event.start_at),
        end_at=to_iso_z(event.end_at),
        created_by=event.created_by,
        created_at=to_iso_z(event.created_at),
        participants_count=0,
        clashes_count=0,
    )

@router.get("/events", response_model=List[EventResponse])
async def list_events(
    claims: UserSecurityClaims = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_db_session),
):
    # Admin can view all events; students and faculty can view events list
    stmt = select(Event).order_by(Event.start_at.desc())
    events = (await db.execute(stmt)).scalars().all()

    res = []
    for ev in events:
        part_cnt = (
            await db.execute(select(func.count(EventParticipant.id)).where(EventParticipant.event_id == ev.id))
        ).scalar_one()
        clash_cnt = (
            await db.execute(select(func.count(ClashCase.id)).where(ClashCase.event_id == ev.id))
        ).scalar_one()

        res.append(
            EventResponse(
                id=ev.id,
                title=ev.title,
                description=ev.description,
                start_at=to_iso_z(ev.start_at),
                end_at=to_iso_z(ev.end_at),
                created_by=ev.created_by,
                created_at=to_iso_z(ev.created_at),
                participants_count=part_cnt,
                clashes_count=clash_cnt,
            )
        )
    return res

@router.get("/events/{event_id}", response_model=EventDetailResponse)
async def get_event_detail(
    event_id: int,
    claims: UserSecurityClaims = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_db_session),
):
    ev = await db.get(Event, event_id)
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    part_cnt = (
        await db.execute(select(func.count(EventParticipant.id)).where(EventParticipant.event_id == ev.id))
    ).scalar_one()

    # Load clash cases for this event with relationships
    stmt = (
        select(ClashCase)
        .where(ClashCase.event_id == event_id)
        .options(
            selectinload(ClashCase.event),
            selectinload(ClashCase.student).selectinload(Student.user),
            selectinload(ClashCase.assessment).selectinload(Assessment.offering).selectinload(CourseOffering.faculty).selectinload(Faculty.user),
            selectinload(ClashCase.suggested_retake),
            selectinload(ClashCase.retake_assessment),
        )
        .order_by(ClashCase.id.asc())
    )
    cases = (await db.execute(stmt)).scalars().all()

    # Filter cases if caller is not admin
    if claims.role == "student":
        cases = [c for c in cases if c.student_id == claims.student_id]
    elif claims.role == "faculty" and not claims.is_hod:
        cases = [c for c in cases if c.assessment.offering.faculty_id == claims.faculty_id]
    elif claims.role == "faculty" and claims.is_hod:
        cases = [
            c for c in cases
            if normalize_department(c.assessment.offering.department) == normalize_department(claims.department or "")
        ]

    formatted_cases = [_format_case_response(c) for c in cases]

    return EventDetailResponse(
        id=ev.id,
        title=ev.title,
        description=ev.description,
        start_at=to_iso_z(ev.start_at),
        end_at=to_iso_z(ev.end_at),
        created_by=ev.created_by,
        created_at=to_iso_z(ev.created_at),
        participants_count=part_cnt,
        clashes_count=len(formatted_cases),
        clashes=formatted_cases,
    )

@router.post("/events/{event_id}/participants")
async def add_participants_and_detect(
    event_id: int,
    req: AddParticipantsRequest,
    claims: UserSecurityClaims = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_db_session),
):
    if claims.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can manage participants")

    ev = await db.get(Event, event_id)
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    collector = NotificationCollector()
    try:
        for sid in req.student_ids:
            # Check if participant already added
            existing = (
                await db.execute(
                    select(EventParticipant).where(
                        EventParticipant.event_id == event_id,
                        EventParticipant.student_id == sid,
                    )
                )
            ).scalar_one_or_none()
            if not existing:
                db.add(EventParticipant(event_id=event_id, student_id=sid))
        await db.flush()

        # Run clash detection for event
        cases = await detect_clashes_for_event(db, event_id, claims.user_id)
        await db.commit()
        await collector.flush()

        return {
            "message": f"Added participants and ran detection. {len(cases)} total clash cases active.",
            "event_id": event_id,
            "clashes_count": len(cases),
        }
    except Exception:
        await db.rollback()
        collector.clear()
        raise

@router.post("/events/{event_id}/detect")
async def manual_detect_clashes(
    event_id: int,
    claims: UserSecurityClaims = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_db_session),
):
    if claims.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can trigger detection")

    ev = await db.get(Event, event_id)
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    collector = NotificationCollector()
    try:
        cases = await detect_clashes_for_event(db, event_id, claims.user_id)
        await db.commit()
        await collector.flush()
        return {"event_id": event_id, "clashes_count": len(cases)}
    except Exception:
        await db.rollback()
        collector.clear()
        raise

# --- Cases Queries & Scoping ---

@router.get("/cases", response_model=List[ClashCaseResponse])
async def list_cases(
    status_filter: Optional[str] = Query(None, alias="status"),
    event_id: Optional[int] = Query(None),
    assessment_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    claims: UserSecurityClaims = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_db_session),
):
    stmt = (
        select(ClashCase)
        .options(
            selectinload(ClashCase.event),
            selectinload(ClashCase.student).selectinload(Student.user),
            selectinload(ClashCase.assessment).selectinload(Assessment.offering).selectinload(CourseOffering.faculty).selectinload(Faculty.user),
            selectinload(ClashCase.suggested_retake),
            selectinload(ClashCase.retake_assessment),
        )
        .order_by(ClashCase.updated_at.desc())
    )

    if status_filter:
        stmt = stmt.where(ClashCase.status == status_filter.strip().upper())
    if event_id:
        stmt = stmt.where(ClashCase.event_id == event_id)
    if assessment_id:
        stmt = stmt.where(ClashCase.assessment_id == assessment_id)

    # Role Scoping
    if claims.role == "student":
        stmt = stmt.where(ClashCase.student_id == claims.student_id)
    elif claims.role == "faculty":
        if claims.is_hod:
            # HOD can see all cases in their department
            norm_dept = normalize_department(claims.department or "")
            stmt = stmt.join(Assessment, ClashCase.assessment_id == Assessment.id).join(CourseOffering, Assessment.offering_id == CourseOffering.id)
            # In SQLite, department equality
            stmt = stmt.where(func.lower(CourseOffering.department) == norm_dept.lower())
        else:
            # Non-HOD faculty sees cases for offerings they teach
            stmt = stmt.join(Assessment, ClashCase.assessment_id == Assessment.id).join(CourseOffering, Assessment.offering_id == CourseOffering.id)
            stmt = stmt.where(CourseOffering.faculty_id == claims.faculty_id)
    elif claims.role == "admin":
        pass # Admin sees all
    else:
        # Parents or unknown roles
        return []

    stmt = stmt.limit(limit).offset(offset)
    cases = (await db.execute(stmt)).scalars().all()
    return [_format_case_response(c) for c in cases]

@router.get("/cases/{case_id}", response_model=ClashCaseDetailResponse)
async def get_case_detail(
    case_id: int,
    claims: UserSecurityClaims = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_db_session),
):
    stmt = (
        select(ClashCase)
        .where(ClashCase.id == case_id)
        .options(
            selectinload(ClashCase.event),
            selectinload(ClashCase.student).selectinload(Student.user),
            selectinload(ClashCase.assessment).selectinload(Assessment.offering).selectinload(CourseOffering.faculty).selectinload(Faculty.user),
            selectinload(ClashCase.suggested_retake),
            selectinload(ClashCase.retake_assessment),
            selectinload(ClashCase.timeline),
        )
    )
    case = (await db.execute(stmt)).scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    # Scope verification
    if claims.role == "student" and case.student_id != claims.student_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    elif claims.role == "faculty":
        if claims.is_hod:
            if normalize_department(case.assessment.offering.department) != normalize_department(claims.department or ""):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to cases outside department")
        else:
            if case.assessment.offering.faculty_id != claims.faculty_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to courses you do not instruct")

    base_resp = _format_case_response(case)

    # Fetch actor names for timeline
    timeline_responses = []
    for tl in sorted(case.timeline, key=lambda t: t.at):
        actor_name = None
        if tl.actor_user_id:
            u = await db.get(User, tl.actor_user_id)
            actor_name = u.name if u else None

        timeline_responses.append(
            CaseTimelineResponse(
                id=tl.id,
                case_id=tl.case_id,
                actor_user_id=tl.actor_user_id,
                actor_name=actor_name,
                actor_role=tl.actor_role,
                from_status=tl.from_status,
                to_status=tl.to_status,
                note=tl.note,
                at=to_iso_z(tl.at),
            )
        )

    resp_dict = base_resp.model_dump()
    resp_dict["timeline"] = timeline_responses
    return ClashCaseDetailResponse(**resp_dict)

# --- State Transitions (Atomic CAS) ---

@router.post("/cases/file", response_model=List[ClashCaseResponse])
async def file_cases(
    req: CaseFileBulkRequest,
    claims: UserSecurityClaims = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_db_session),
):
    collector = NotificationCollector()
    try:
        updated = await file_clash_cases_bulk(db, req.case_ids, claims, collector)
        await db.commit()
        await collector.flush()
        return [_format_case_response(c) for c in updated]
    except Exception:
        await db.rollback()
        collector.clear()
        raise

@router.post("/cases/decision", response_model=List[ClashCaseResponse])
async def decide_cases(
    req: CaseDecisionBulkRequest,
    claims: UserSecurityClaims = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_db_session),
):
    collector = NotificationCollector()
    try:
        custom_dt = parse_iso_utc(req.custom_at) if req.custom_at else None
        updated = await professor_decide_bulk(
            db,
            req.case_ids,
            req.decision,
            req.slot_id,
            custom_dt,
            req.note,
            req.rejection_reason,
            claims,
            collector,
        )
        await db.commit()
        await collector.flush()
        return [_format_case_response(c) for c in updated]
    except Exception:
        await db.rollback()
        collector.clear()
        raise

@router.post("/cases/{case_id}/accept-counter", response_model=ClashCaseResponse)
async def accept_counter(
    case_id: int,
    claims: UserSecurityClaims = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_db_session),
):
    collector = NotificationCollector()
    try:
        case = await admin_accept_counter(db, case_id, claims, collector)
        await db.commit()
        await collector.flush()
        return _format_case_response(case)
    except Exception:
        await db.rollback()
        collector.clear()
        raise

@router.post("/cases/{case_id}/send-back", response_model=ClashCaseResponse)
async def send_back_counter(
    case_id: int,
    req: CounterActionRequest,
    claims: UserSecurityClaims = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_db_session),
):
    collector = NotificationCollector()
    try:
        case = await admin_send_back(db, case_id, req.note or "Admin requested alternative option", claims, collector)
        await db.commit()
        await collector.flush()
        return _format_case_response(case)
    except Exception:
        await db.rollback()
        collector.clear()
        raise

@router.post("/cases/{case_id}/override", response_model=ClashCaseResponse)
async def override_by_hod(
    case_id: int,
    req: HODOverrideRequest,
    claims: UserSecurityClaims = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_db_session),
):
    collector = NotificationCollector()
    try:
        custom_dt = parse_iso_utc(req.custom_at) if req.custom_at else None
        case = await hod_override(db, case_id, req.slot_id, custom_dt, req.note, claims, collector)
        await db.commit()
        await collector.flush()
        return _format_case_response(case)
    except Exception:
        await db.rollback()
        collector.clear()
        raise

@router.post("/cases/{case_id}/complete", response_model=ClashCaseResponse)
async def mark_complete(
    case_id: int,
    claims: UserSecurityClaims = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_db_session),
):
    collector = NotificationCollector()
    try:
        case = await complete_case(db, case_id, claims, collector)
        await db.commit()
        await collector.flush()
        return _format_case_response(case)
    except Exception:
        await db.rollback()
        collector.clear()
        raise

# --- HOD Department Overview ---

@router.get("/hod/overview", response_model=HODOverviewResponse)
async def get_hod_overview(
    claims: UserSecurityClaims = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_db_session),
):
    if not claims.is_hod:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Head of Department can access this dashboard")

    dept = normalize_department(claims.department or "Computer Science")

    # Fetch all cases for this department
    stmt = (
        select(ClashCase)
        .join(Assessment, ClashCase.assessment_id == Assessment.id)
        .join(CourseOffering, Assessment.offering_id == CourseOffering.id)
        .where(func.lower(CourseOffering.department) == dept.lower())
        .options(
            selectinload(ClashCase.event),
            selectinload(ClashCase.student).selectinload(Student.user),
            selectinload(ClashCase.assessment).selectinload(Assessment.offering).selectinload(CourseOffering.faculty).selectinload(Faculty.user),
            selectinload(ClashCase.suggested_retake),
            selectinload(ClashCase.retake_assessment),
        )
    )
    all_cases = (await db.execute(stmt)).scalars().all()

    counts: Dict[str, int] = {}
    escalated_cases = []
    stuck_cases = []
    prof_pending: Dict[str, int] = {}

    now = utcnow()
    threshold = datetime.timedelta(hours=STUCK_THRESHOLD_HOURS)

    for c in all_cases:
        counts[c.status] = counts.get(c.status, 0) + 1

        if c.status == "ESCALATED_TO_HOD":
            escalated_cases.append(_format_case_response(c))

        # Check stuck cases
        if c.status in ["REQUEST_FILED", "COUNTER_PROPOSED"]:
            if (now - c.updated_at) > threshold:
                stuck_cases.append(_format_case_response(c))

        # Professor pending counts
        if c.status == "REQUEST_FILED" and c.assessment and c.assessment.offering:
            pname = (
                c.assessment.offering.faculty.user.name
                if c.assessment.offering.faculty and c.assessment.offering.faculty.user
                else f"Faculty #{c.assessment.offering.faculty_id}"
            )
            prof_pending[pname] = prof_pending.get(pname, 0) + 1

    return HODOverviewResponse(
        department=dept,
        counts_by_status=counts,
        escalated_cases=escalated_cases,
        stuck_cases=stuck_cases,
        per_professor_pending=prof_pending,
    )

# --- Reference Data Helpers ---

@router.get("/reference/students")
async def search_students(
    q: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    claims: UserSecurityClaims = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_db_session),
):
    stmt = (
        select(Student)
        .join(User, Student.user_id == User.id)
        .options(selectinload(Student.user))
    )
    if department:
        stmt = stmt.where(func.lower(Student.department) == normalize_department(department).lower())
    if q:
        like_q = f"%{q}%"
        stmt = stmt.where(or_(User.name.ilike(like_q), Student.roll_number.ilike(like_q)))

    students = (await db.execute(stmt.limit(50))).scalars().all()
    return [
        {
            "id": s.id,
            "user_id": s.user_id,
            "name": s.user.name if s.user else "",
            "roll_number": s.roll_number,
            "department": s.department,
            "semester": s.semester,
            "section": s.section,
        }
        for s in students
    ]

@router.get("/reference/offerings")
async def list_offerings(
    claims: UserSecurityClaims = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_db_session),
):
    stmt = (
        select(CourseOffering)
        .options(
            selectinload(CourseOffering.faculty).selectinload(Faculty.user),
            selectinload(CourseOffering.assessments),
        )
    )
    offerings = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": o.id,
            "course_code": o.course_code,
            "subject": o.subject,
            "section": o.section,
            "semester": o.semester,
            "department": o.department,
            "faculty_id": o.faculty_id,
            "faculty_name": o.faculty.user.name if o.faculty and o.faculty.user else "",
            "assessments": [
                {
                    "id": a.id,
                    "kind": a.kind,
                    "start_at": to_iso_z(a.start_at),
                    "end_at": to_iso_z(a.end_at),
                    "venue": a.venue,
                }
                for a in o.assessments
            ],
        }
        for o in offerings
    ]

# --- Notifications Endpoints ---

@router.get("/notifications", response_model=List[NotificationResponse])
async def get_my_notifications(
    claims: UserSecurityClaims = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_db_session),
):
    stmt = (
        select(Notification)
        .where(Notification.user_id == claims.user_id)
        .order_by(Notification.created_at.desc())
        .limit(50)
    )
    notifs = (await db.execute(stmt)).scalars().all()
    return [
        NotificationResponse(
            id=n.id,
            user_id=n.user_id,
            type=n.type,
            title=n.title,
            body=n.body,
            case_id=n.case_id,
            event_id=n.event_id,
            is_read=n.is_read,
            created_at=to_iso_z(n.created_at),
        )
        for n in notifs
    ]

@router.post("/notifications/{notif_id}/read")
async def mark_notification_read(
    notif_id: int,
    claims: UserSecurityClaims = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_db_session),
):
    notif = await db.get(Notification, notif_id)
    if not notif or notif.user_id != claims.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    notif.is_read = True
    await db.commit()
    return {"status": "success", "id": notif_id}

@router.post("/notifications/read-all")
async def mark_all_notifications_read(
    claims: UserSecurityClaims = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_db_session),
):
    stmt = (
        update(Notification)
        .where(Notification.user_id == claims.user_id, Notification.is_read == False)
        .values(is_read=True)
    )
    await db.execute(stmt)
    await db.commit()
    return {"status": "success"}
