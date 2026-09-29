import pytest
import datetime
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, inspect

from app.core.database import (
    Base, User, Student, Faculty, Event, EventParticipant,
    CourseOffering, Assessment, ClashCase, CaseTimeline, Notification
)
from app.core.datetime_utils import utcnow, to_iso_z, parse_iso_utc
from app.core.department import normalize_department, is_hod_designation

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture
async def test_session():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.mark.asyncio
async def test_datetime_utilities():
    now = utcnow()
    assert now.tzinfo is None, "Database datetimes must be naive UTC"

    iso_str = to_iso_z(now)
    assert iso_str.endswith("Z"), "API boundary ISO string must end with Z"

    parsed = parse_iso_utc(iso_str)
    assert parsed.tzinfo is None, "Parsed ISO string must be naive UTC"
    assert parsed.year == now.year
    assert parsed.month == now.month
    assert parsed.day == now.day

@pytest.mark.asyncio
async def test_department_and_hod_helpers():
    assert normalize_department("computer science") == "Computer Science"
    assert normalize_department("  Computer Science  ") == "Computer Science"
    assert normalize_department("software engineering") == "Software Engineering"

    # Exact match tests
    assert is_hod_designation("Head of Department") is True
    assert is_hod_designation("head of department") is True
    assert is_hod_designation("HOD") is True
    assert is_hod_designation("hod") is True

    # Negative tests (loose substrings must be rejected)
    assert is_hod_designation("Associate Professor") is False
    assert is_hod_designation("Distinguished Professor") is False
    assert is_hod_designation("Assistant to HOD") is False
    assert is_hod_designation("Acting HOD Staff") is False
    assert is_hod_designation(None) is False
    assert is_hod_designation("") is False

@pytest.mark.asyncio
async def test_clash_models_and_constraints(test_session: AsyncSession):
    # 1. Create Base User, Student, Faculty
    admin_user = User(
        public_id="USR-ADM-1",
        name="Admin Sarah",
        email="admin@test.edu",
        password_hash="hashed_pw",
        role="admin"
    )
    prof_user = User(
        public_id="USR-FAC-1",
        name="Prof Babbage",
        email="babbage@test.edu",
        password_hash="hashed_pw",
        role="faculty"
    )
    student_user = User(
        public_id="USR-STU-1",
        name="Student Jane",
        email="jane@test.edu",
        password_hash="hashed_pw",
        role="student"
    )
    test_session.add_all([admin_user, prof_user, student_user])
    await test_session.flush()

    prof = Faculty(
        user_id=prof_user.id,
        emp_code="FAC-TEST-1",
        department="Computer Science",
        designation="Professor",
        annual_salary=110000.0
    )
    student = Student(
        user_id=student_user.id,
        roll_number="CS-TEST-001",
        department="Computer Science",
        semester=6,
        section="Section A"
    )
    test_session.add_all([prof, student])
    await test_session.flush()

    # 2. Create Event
    event = Event(
        title="Test Hackathon 2026",
        description="A major 24h event",
        start_at=utcnow(),
        end_at=utcnow() + datetime.timedelta(hours=8),
        created_by=admin_user.id
    )
    test_session.add(event)
    await test_session.flush()

    # 3. Add Event Participant
    participant = EventParticipant(event_id=event.id, student_id=student.id)
    test_session.add(participant)
    await test_session.flush()

    # Test EventParticipant UniqueConstraint
    dup_participant = EventParticipant(event_id=event.id, student_id=student.id)
    test_session.add(dup_participant)
    with pytest.raises(IntegrityError):
        await test_session.flush()
    await test_session.rollback()

    # 4. Course Offering & Assessment
    offering = CourseOffering(
        course_code="CS-401",
        subject="Cloud Computing",
        section="Section A",
        semester=6,
        department="Computer Science",
        faculty_id=prof.id
    )
    test_session.add(offering)
    await test_session.flush()

    # Test CourseOffering UniqueConstraint
    dup_offering = CourseOffering(
        course_code="CS-401",
        subject="Cloud Computing",
        section="Section A",
        semester=6,
        department="Computer Science",
        faculty_id=prof.id
    )
    test_session.add(dup_offering)
    with pytest.raises(IntegrityError):
        await test_session.flush()
    await test_session.rollback()

    # Re-add offering after rollback
    offering = CourseOffering(
        course_code="CS-401",
        subject="Cloud Computing",
        section="Section A",
        semester=6,
        department="Computer Science",
        faculty_id=prof.id
    )
    test_session.add(offering)
    await test_session.flush()

    assessment = Assessment(
        offering_id=offering.id,
        kind="midterm",
        start_at=utcnow() + datetime.timedelta(hours=2),
        end_at=utcnow() + datetime.timedelta(hours=4),
        venue="Hall 101"
    )
    test_session.add(assessment)
    await test_session.flush()

    # 5. Create ClashCase
    case = ClashCase(
        event_id=event.id,
        student_id=student.id,
        assessment_id=assessment.id,
        status="DETECTED"
    )
    test_session.add(case)
    await test_session.commit()
    case_id = case.id

    # Test ClashCase UniqueConstraint using nested savepoint
    dup_case = ClashCase(
        event_id=event.id,
        student_id=student.id,
        assessment_id=assessment.id,
        status="DETECTED"
    )
    test_session.add(dup_case)
    with pytest.raises(IntegrityError):
        await test_session.flush()
    await test_session.rollback()

    # 6. CaseTimeline append-only check
    reloaded_case = (await test_session.execute(select(ClashCase).where(ClashCase.id == case_id))).scalar_one()
    timeline_entry = CaseTimeline(
        case_id=reloaded_case.id,
        actor_user_id=admin_user.id,
        actor_role="admin",
        from_status=None,
        to_status="DETECTED",
        note="Initial system detection"
    )
    test_session.add(timeline_entry)
    await test_session.commit()

    # Verify timeline is retrievable
    timelines = (await test_session.execute(
        select(CaseTimeline).where(CaseTimeline.case_id == reloaded_case.id)
    )).scalars().all()
    assert len(timelines) == 1
    assert timelines[0].to_status == "DETECTED"
