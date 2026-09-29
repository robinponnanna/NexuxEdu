import datetime
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.core.datetime_utils import utcnow
from app.core.department import normalize_department
from app.core.database import (
    Event,
    EventParticipant,
    CourseOffering,
    Assessment,
    ClashCase,
    CaseTimeline,
    Student,
    Notification,
)

def check_interval_overlap(
    start_a: datetime.datetime,
    end_at_a: datetime.datetime,
    start_b: datetime.datetime,
    end_at_b: datetime.datetime,
) -> bool:
    """
    Returns True if intervals overlap strictly:
    start_a < end_at_b AND start_b < end_at_a
    Boundary touching (e.g. end_at_a == start_b) returns False.
    """
    return start_a < end_at_b and start_b < end_at_a

async def find_student_assessments_for_event(
    db: AsyncSession,
    student: Student,
    event: Event,
) -> List[Tuple[Assessment, CourseOffering]]:
    """
    Finds all assessments for course offerings the student is enrolled in
    that strictly overlap with the given event window.
    """
    norm_dept = normalize_department(student.department)

    # Fetch offerings for the student's cohort: department and semester
    # Matching section if specified, or if offering section is empty
    stmt = (
        select(CourseOffering)
        .where(
            CourseOffering.semester == student.semester,
        )
    )
    result = await db.execute(stmt)
    offerings = result.scalars().all()

    enrolled_offerings = []
    for off in offerings:
        if normalize_department(off.department) != norm_dept:
            continue
        if off.section and student.section and off.section.strip().lower() != student.section.strip().lower():
            continue
        enrolled_offerings.append(off)

    if not enrolled_offerings:
        return []

    offering_ids = [off.id for off in enrolled_offerings]
    offering_by_id = {off.id: off for off in enrolled_offerings}

    # Fetch assessments for these offerings
    stmt_assessments = (
        select(Assessment)
        .where(Assessment.offering_id.in_(offering_ids))
    )
    res_assessments = await db.execute(stmt_assessments)
    assessments = res_assessments.scalars().all()

    clashing_pairs: List[Tuple[Assessment, CourseOffering]] = []
    for ass in assessments:
        if check_interval_overlap(event.start_at, event.end_at, ass.start_at, ass.end_at):
            clashing_pairs.append((ass, offering_by_id[ass.offering_id]))

    return clashing_pairs

async def suggest_retake_slot(
    db: AsyncSession,
    student: Student,
    assessment: Assessment,
    event: Event,
) -> Optional[Assessment]:
    """
    Suggests a retake slot (Assessment) for a given student clashing with an event:
    1. Must be for the same subject/course.
    2. Must exclude the student's current offering/section.
    3. Must NOT clash with the event window.
    4. Must NOT clash with any other assessment already scheduled for this student's courses.
    Returns earliest eligible assessment, or None.
    """
    # 1. Fetch the original offering to know the subject and faculty
    offering = await db.get(CourseOffering, assessment.offering_id)
    if not offering:
        return None

    # Find sister offerings of the same subject in the same semester / department
    norm_dept = normalize_department(offering.department)
    stmt = (
        select(CourseOffering)
        .where(
            CourseOffering.subject == offering.subject,
            CourseOffering.semester == offering.semester,
            CourseOffering.id != offering.id, # Exclude same section offering
        )
    )
    res = await db.execute(stmt)
    sister_offerings = [
        o for o in res.scalars().all()
        if normalize_department(o.department) == norm_dept
    ]
    if not sister_offerings:
        return None

    sister_offering_ids = [o.id for o in sister_offerings]

    # Find candidate assessments of the same kind
    stmt_candidates = (
        select(Assessment)
        .where(
            Assessment.offering_id.in_(sister_offering_ids),
            Assessment.kind == assessment.kind,
        )
        .order_by(Assessment.start_at.asc())
    )
    res_candidates = await db.execute(stmt_candidates)
    candidates = res_candidates.scalars().all()

    if not candidates:
        return None

    # Fetch all assessments scheduled for the student across all enrolled subjects
    # so we guarantee the student does not get double-booked
    student_cohort_stmt = (
        select(CourseOffering)
        .where(CourseOffering.semester == student.semester)
    )
    all_cohort_offerings = (await db.execute(student_cohort_stmt)).scalars().all()
    student_enrolled_ids = [
        o.id for o in all_cohort_offerings
        if normalize_department(o.department) == normalize_department(student.department)
        and (not o.section or not student.section or o.section.strip().lower() == student.section.strip().lower())
    ]
    all_student_assessments = (
        await db.execute(
            select(Assessment).where(
                Assessment.offering_id.in_(student_enrolled_ids),
                Assessment.id != assessment.id,
            )
        )
    ).scalars().all()

    # Filter candidate:
    # - Must not clash with the event
    # - Must not clash with any existing assessment for the student
    for cand in candidates:
        # Check event clash
        if check_interval_overlap(event.start_at, event.end_at, cand.start_at, cand.end_at):
            continue

        # Check clash with student's other exams
        has_student_exam_clash = any(
            check_interval_overlap(cand.start_at, cand.end_at, other.start_at, other.end_at)
            for other in all_student_assessments
        )
        if has_student_exam_clash:
            continue

        return cand

    return None

async def detect_clashes_for_event(
    db: AsyncSession,
    event_id: int,
    actor_user_id: int,
) -> List[ClashCase]:
    """
    Runs clash detection for all participants in an event.
    Idempotent:
    - If a ClashCase already exists for (event_id, student_id, assessment_id),
      its existing status is NOT overwritten or regressed.
    - If new, creates ClashCase in DETECTED status, suggests retake slot if available,
      adds initial CaseTimeline entry, and generates Notification for the student.
    Returns list of all active ClashCases for this event.
    """
    event = await db.get(Event, event_id)
    if not event:
        raise ValueError(f"Event with id {event_id} not found")

    # Fetch all participants with Student record
    stmt = (
        select(EventParticipant, Student)
        .join(Student, EventParticipant.student_id == Student.id)
        .where(EventParticipant.event_id == event_id)
    )
    rows = (await db.execute(stmt)).all()

    created_or_found_cases: List[ClashCase] = []

    for _, student in rows:
        clashing_pairs = await find_student_assessments_for_event(db, student, event)
        for ass, offering in clashing_pairs:
            # Check if case exists
            existing_case_stmt = (
                select(ClashCase)
                .where(
                    ClashCase.event_id == event_id,
                    ClashCase.student_id == student.id,
                    ClashCase.assessment_id == ass.id,
                )
            )
            existing_case = (await db.execute(existing_case_stmt)).scalar_one_or_none()

            if existing_case:
                created_or_found_cases.append(existing_case)
                continue

            # Compute suggested retake
            suggested = await suggest_retake_slot(db, student, ass, event)
            suggested_id = suggested.id if suggested else None

            case = ClashCase(
                event_id=event_id,
                student_id=student.id,
                assessment_id=ass.id,
                status="DETECTED",
                suggested_retake_assessment_id=suggested_id,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            db.add(case)
            await db.flush() # Populate case.id

            timeline = CaseTimeline(
                case_id=case.id,
                actor_user_id=actor_user_id,
                actor_role="admin",
                from_status=None,
                to_status="DETECTED",
                note=f"Automated clash detected with assessment '{ass.kind}' for course '{offering.subject}'",
                at=utcnow(),
            )
            db.add(timeline)

            # Create notification for student
            notif = Notification(
                user_id=student.user_id,
                type="CLASH_DETECTED",
                title=f"Exam Clash Detected: {offering.subject}",
                body=(
                    f"Your participation in event '{event.title}' clashes with "
                    f"{offering.subject} ({ass.kind}). Rescheduling review pending."
                ),
                case_id=case.id,
                event_id=event.id,
                is_read=False,
                created_at=utcnow(),
            )
            db.add(notif)
            created_or_found_cases.append(case)

    await db.flush()
    return created_or_found_cases
