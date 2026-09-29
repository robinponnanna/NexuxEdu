import pytest
import datetime
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from app.core.database import (
    Base,
    User,
    Student,
    Faculty,
    Event,
    CourseOffering,
    Assessment,
    ClashCase,
    CaseTimeline,
    Notification,
    AuditLog,
)
from app.core.datetime_utils import utcnow
from app.core.notifications import NotificationCollector
from app.models.schemas import UserSecurityClaims
from app.services.clash_state_machine import (
    file_clash_cases_bulk,
    professor_decide_bulk,
    admin_accept_counter,
    admin_send_back,
    hod_override,
    complete_case,
)

@pytest.fixture
async def test_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

async def setup_test_hierarchy(db: AsyncSession):
    now = utcnow()

    # Users
    u_admin = User(public_id="u_adm", name="Admin", email="admin@test.com", password_hash="h", role="admin")
    u_prof1 = User(public_id="u_p1", name="Prof CS", email="p1@test.com", password_hash="h", role="faculty")
    u_prof2 = User(public_id="u_p2", name="Prof Other", email="p2@test.com", password_hash="h", role="faculty")
    u_hod = User(public_id="u_hod", name="HOD CS", email="hod@test.com", password_hash="h", role="faculty")
    u_hod_other = User(public_id="u_hod_oth", name="HOD EE", email="hodee@test.com", password_hash="h", role="faculty")
    u_stud1 = User(public_id="u_s1", name="Student 1", email="s1@test.com", password_hash="h", role="student")
    u_stud2 = User(public_id="u_s2", name="Student 2", email="s2@test.com", password_hash="h", role="student")

    db.add_all([u_admin, u_prof1, u_prof2, u_hod, u_hod_other, u_stud1, u_stud2])
    await db.flush()

    # Faculty profiles
    f_prof1 = Faculty(user_id=u_prof1.id, emp_code="FAC01", department="Computer Science", designation="Associate Professor", annual_salary=80000.0)
    f_prof2 = Faculty(user_id=u_prof2.id, emp_code="FAC02", department="Computer Science", designation="Assistant Professor", annual_salary=75000.0)
    f_hod = Faculty(user_id=u_hod.id, emp_code="HOD01", department="Computer Science", designation="Head of Department", annual_salary=110000.0)
    f_hod_other = Faculty(user_id=u_hod_other.id, emp_code="HOD02", department="Electrical Engineering", designation="Head of Department", annual_salary=110000.0)

    # Students
    s_stud1 = Student(user_id=u_stud1.id, roll_number="CS-01", department="Computer Science", semester=6, section="Section A")
    s_stud2 = Student(user_id=u_stud2.id, roll_number="CS-02", department="Computer Science", semester=6, section="Section B")

    db.add_all([f_prof1, f_prof2, f_hod, f_hod_other, s_stud1, s_stud2])
    await db.flush()

    # Offerings & Assessments
    offering = CourseOffering(
        course_code="CS-401",
        subject="Cloud Computing",
        section="Section A",
        semester=6,
        department="Computer Science",
        faculty_id=f_prof1.id,
    )
    db.add(offering)
    await db.flush()

    assessment = Assessment(
        offering_id=offering.id,
        kind="midterm",
        start_at=now + datetime.timedelta(days=1),
        end_at=now + datetime.timedelta(days=1, hours=2),
        venue="Room 101",
    )
    db.add(assessment)
    await db.flush()

    event = Event(
        title="Hackathon",
        start_at=now + datetime.timedelta(days=1),
        end_at=now + datetime.timedelta(days=1, hours=8),
        created_by=u_admin.id,
    )
    db.add(event)
    await db.flush()

    # Initial Case
    case = ClashCase(
        event_id=event.id,
        student_id=s_stud1.id,
        assessment_id=assessment.id,
        status="DETECTED",
        created_at=now,
        updated_at=now,
    )
    db.add(case)
    await db.commit()

    claims_admin = UserSecurityClaims(user_id=u_admin.id, public_id=u_admin.public_id, role="admin", email=u_admin.email, name="Admin")
    claims_prof1 = UserSecurityClaims(user_id=u_prof1.id, public_id=u_prof1.public_id, role="faculty", email=u_prof1.email, name="Prof 1", department="Computer Science", faculty_id=f_prof1.id, is_hod=False)
    claims_prof2 = UserSecurityClaims(user_id=u_prof2.id, public_id=u_prof2.public_id, role="faculty", email=u_prof2.email, name="Prof 2", department="Computer Science", faculty_id=f_prof2.id, is_hod=False)
    claims_hod = UserSecurityClaims(user_id=u_hod.id, public_id=u_hod.public_id, role="faculty", email=u_hod.email, name="HOD CS", department="Computer Science", faculty_id=f_hod.id, is_hod=True)
    claims_hod_other = UserSecurityClaims(user_id=u_hod_other.id, public_id=u_hod_other.public_id, role="faculty", email=u_hod_other.email, name="HOD EE", department="Electrical Engineering", faculty_id=f_hod_other.id, is_hod=True)
    claims_student = UserSecurityClaims(user_id=u_stud1.id, public_id=u_stud1.public_id, role="student", email=u_stud1.email, name="Student 1", student_id=s_stud1.id)

    return {
        "case": case,
        "claims_admin": claims_admin,
        "claims_prof1": claims_prof1,
        "claims_prof2": claims_prof2,
        "claims_hod": claims_hod,
        "claims_hod_other": claims_hod_other,
        "claims_student": claims_student,
    }

@pytest.mark.asyncio
async def test_state_machine_approval_flow(test_session: AsyncSession):
    ctx = await setup_test_hierarchy(test_session)
    case = ctx["case"]
    collector = NotificationCollector()

    # 1. Non-admin cannot file (403)
    with pytest.raises(HTTPException) as exc:
        await file_clash_cases_bulk(test_session, [case.id], ctx["claims_prof1"], collector)
    assert exc.value.status_code == 403

    # 2. Admin files (DETECTED -> REQUEST_FILED)
    updated = await file_clash_cases_bulk(test_session, [case.id], ctx["claims_admin"], collector)
    assert len(updated) == 1
    assert updated[0].status == "REQUEST_FILED"
    await test_session.commit()
    flushed = await collector.flush()
    assert flushed > 0

    # 3. Prof from different offering cannot decide (403)
    with pytest.raises(HTTPException) as exc:
        await professor_decide_bulk(test_session, [case.id], "approve", None, utcnow(), "OK", None, ctx["claims_prof2"], collector)
    assert exc.value.status_code == 403

    # 4. Prof1 approves with custom slot
    retake_time = utcnow() + datetime.timedelta(days=3)
    approved = await professor_decide_bulk(
        test_session, [case.id], "approve", None, retake_time, "Rescheduled to Friday", None, ctx["claims_prof1"], collector
    )
    assert approved[0].status == "APPROVED"
    assert approved[0].retake_at == retake_time
    await test_session.commit()

    # 5. Mark Completed
    completed = await complete_case(test_session, case.id, ctx["claims_prof1"], collector)
    assert completed.status == "COMPLETED"
    await test_session.commit()

@pytest.mark.asyncio
async def test_rejection_cascades_to_hod_and_hod_override(test_session: AsyncSession):
    ctx = await setup_test_hierarchy(test_session)
    case = ctx["case"]
    collector = NotificationCollector()

    # Admin files request
    await file_clash_cases_bulk(test_session, [case.id], ctx["claims_admin"], collector)
    await test_session.commit()

    # Professor rejects with mandatory reason
    # Must cascade immediately to ESCALATED_TO_HOD in the SAME transaction with both timeline rows
    decided = await professor_decide_bulk(
        test_session,
        [case.id],
        "reject",
        None,
        None,
        None,
        rejection_reason="No makeup exam permitted per syllabus policy",
        actor=ctx["claims_prof1"],
        collector=collector,
    )
    assert decided[0].status == "ESCALATED_TO_HOD"
    assert decided[0].rejection_reason == "No makeup exam permitted per syllabus policy"
    await test_session.commit()

    # Verify both timeline entries exist
    timelines = (
        await test_session.execute(
            select(CaseTimeline).where(CaseTimeline.case_id == case.id).order_by(CaseTimeline.id.asc())
        )
    ).scalars().all()
    statuses = [t.to_status for t in timelines]
    assert "REJECTED" in statuses
    assert "ESCALATED_TO_HOD" in statuses

    # HOD from other department CANNOT override (403)
    with pytest.raises(HTTPException) as exc:
        await hod_override(
            test_session,
            case.id,
            slot_id=None,
            custom_at=utcnow() + datetime.timedelta(days=5),
            note="Dept EE override",
            actor=ctx["claims_hod_other"],
            collector=collector,
        )
    assert exc.value.status_code == 403

    # HOD from Computer Science overrides -> APPROVED
    override_time = utcnow() + datetime.timedelta(days=5)
    overridden = await hod_override(
        test_session,
        case.id,
        slot_id=None,
        custom_at=override_time,
        note="Approved under hackathon institutional policy exemption",
        actor=ctx["claims_hod"],
        collector=collector,
    )
    assert overridden.status == "APPROVED"
    assert overridden.retake_at == override_time
    assert "[HOD Override]" in overridden.retake_note
    await test_session.commit()

@pytest.mark.asyncio
async def test_counter_proposal_and_send_back(test_session: AsyncSession):
    ctx = await setup_test_hierarchy(test_session)
    case = ctx["case"]
    collector = NotificationCollector()

    await file_clash_cases_bulk(test_session, [case.id], ctx["claims_admin"], collector)
    await test_session.commit()

    # Professor proposes counter slot
    counter_time = utcnow() + datetime.timedelta(days=4)
    countered = await professor_decide_bulk(
        test_session,
        [case.id],
        "counter",
        slot_id=None,
        custom_at=counter_time,
        note="How about Thursday 4 PM?",
        rejection_reason=None,
        actor=ctx["claims_prof1"],
        collector=collector,
    )
    assert countered[0].status == "COUNTER_PROPOSED"
    await test_session.commit()

    # Admin sends back for reconsideration
    sent_back = await admin_send_back(test_session, case.id, "Student has another lab Thursday", ctx["claims_admin"], collector)
    assert sent_back.status == "REQUEST_FILED"
    await test_session.commit()

    # Professor counters again
    counter_time_2 = utcnow() + datetime.timedelta(days=6)
    countered_2 = await professor_decide_bulk(
        test_session,
        [case.id],
        "counter",
        slot_id=None,
        custom_at=counter_time_2,
        note="Saturday 10 AM",
        rejection_reason=None,
        actor=ctx["claims_prof1"],
        collector=collector,
    )
    assert countered_2[0].status == "COUNTER_PROPOSED"
    await test_session.commit()

    # Admin accepts counter on student's behalf
    accepted = await admin_accept_counter(test_session, case.id, ctx["claims_admin"], collector)
    assert accepted.status == "APPROVED"
    await test_session.commit()
