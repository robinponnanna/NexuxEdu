import pytest
import datetime
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from app.core.database import (
    Base,
    User,
    Student,
    Faculty,
    Event,
    EventParticipant,
    CourseOffering,
    Assessment,
    ClashCase,
    CaseTimeline,
    Notification,
)
from app.core.datetime_utils import utcnow
from app.services.clash_detector import (
    check_interval_overlap,
    suggest_retake_slot,
    detect_clashes_for_event,
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

def test_interval_overlap_logic():
    base = utcnow()
    t1 = base + datetime.timedelta(hours=1)
    t2 = base + datetime.timedelta(hours=2)
    t3 = base + datetime.timedelta(hours=3)
    t4 = base + datetime.timedelta(hours=4)

    # 1. Boundary-touching: [t1, t2] and [t2, t3] -> NOT a clash
    assert check_interval_overlap(t1, t2, t2, t3) is False
    assert check_interval_overlap(t2, t3, t1, t2) is False

    # 2. Full containment: [t1, t4] contains [t2, t3] -> IS a clash
    assert check_interval_overlap(t1, t4, t2, t3) is True
    assert check_interval_overlap(t2, t3, t1, t4) is True

    # 3. Partial overlap: [t1, t3] and [t2, t4] -> IS a clash
    assert check_interval_overlap(t1, t3, t2, t4) is True
    assert check_interval_overlap(t2, t4, t1, t3) is True

    # 4. Disjoint: [t1, t2] and [t3, t4] -> NOT a clash
    assert check_interval_overlap(t1, t2, t3, t4) is False

@pytest.mark.asyncio
async def test_detection_and_retake_suggestion(test_session: AsyncSession):
    now = utcnow()

    # 1. Create Users
    admin = User(public_id="u_admin", name="Admin", email="admin@nexusedu.com", password_hash="h", role="admin")
    prof1 = User(public_id="u_prof1", name="Prof Cloud", email="prof1@nexusedu.com", password_hash="h", role="faculty")
    stud1 = User(public_id="u_s1", name="Alice", email="alice@nexusedu.com", password_hash="h", role="student")
    stud2 = User(public_id="u_s2", name="Bob", email="bob@nexusedu.com", password_hash="h", role="student")
    test_session.add_all([admin, prof1, stud1, stud2])
    await test_session.flush()

    faculty1 = Faculty(user_id=prof1.id, emp_code="FAC01", department="Computer Science", designation="Associate Professor", annual_salary=80000.0)
    test_session.add(faculty1)
    await test_session.flush()

    # Student 1: CS, Sem 6, Section A
    student1 = Student(user_id=stud1.id, roll_number="CS2026-01", department="Computer Science", semester=6, section="Section A")
    # Student 2: CS, Sem 6, Section B
    student2 = Student(user_id=stud2.id, roll_number="CS2026-02", department="Computer Science", semester=6, section="Section B")
    test_session.add_all([student1, student2])
    await test_session.flush()

    # Offerings: Cloud Computing (CS-401) for Section A and Section B
    offering_a = CourseOffering(
        course_code="CS-401",
        subject="Cloud Computing",
        section="Section A",
        semester=6,
        department="Computer Science",
        faculty_id=faculty1.id,
    )
    offering_b = CourseOffering(
        course_code="CS-401",
        subject="Cloud Computing",
        section="Section B",
        semester=6,
        department="Computer Science",
        faculty_id=faculty1.id,
    )
    test_session.add_all([offering_a, offering_b])
    await test_session.flush()

    # Assessments:
    # Section A exam: tomorrow 10:00 - 12:00
    # Section B exam: day after tomorrow 10:00 - 12:00
    exam_a = Assessment(
        offering_id=offering_a.id,
        kind="midterm",
        start_at=now + datetime.timedelta(days=1, hours=10),
        end_at=now + datetime.timedelta(days=1, hours=12),
        venue="Lab 1",
    )
    exam_b = Assessment(
        offering_id=offering_b.id,
        kind="midterm",
        start_at=now + datetime.timedelta(days=2, hours=10),
        end_at=now + datetime.timedelta(days=2, hours=12),
        venue="Lab 2",
    )
    test_session.add_all([exam_a, exam_b])
    await test_session.flush()

    # Event: Hackathon running tomorrow from 09:00 to 18:00 (overlaps with exam_a)
    event = Event(
        title="Hackathon 2026",
        start_at=now + datetime.timedelta(days=1, hours=9),
        end_at=now + datetime.timedelta(days=1, hours=18),
        created_by=admin.id,
    )
    test_session.add(event)
    await test_session.flush()

    # Add student1 (Section A) to event
    part1 = EventParticipant(event_id=event.id, student_id=student1.id)
    test_session.add(part1)
    await test_session.commit()

    # Run Clash Detection
    cases = await detect_clashes_for_event(test_session, event.id, admin.id)
    assert len(cases) == 1
    case = cases[0]
    assert case.student_id == student1.id
    assert case.assessment_id == exam_a.id
    assert case.status == "DETECTED"
    # Verify suggested retake is exam_b (Section B's exam, different day, same subject)
    assert case.suggested_retake_assessment_id == exam_b.id

    # Verify timeline row created
    timelines = (
        await test_session.execute(select(CaseTimeline).where(CaseTimeline.case_id == case.id))
    ).scalars().all()
    assert len(timelines) == 1
    assert timelines[0].to_status == "DETECTED"

    # Verify notification created
    notifs = (
        await test_session.execute(select(Notification).where(Notification.user_id == stud1.id))
    ).scalars().all()
    assert len(notifs) == 1
    assert notifs[0].type == "CLASH_DETECTED"

    # Test Idempotency: Run detection a second time
    # Manually change status to REQUEST_FILED to verify it doesn't regress to DETECTED
    case.status = "REQUEST_FILED"
    await test_session.commit()

    second_cases = await detect_clashes_for_event(test_session, event.id, admin.id)
    assert len(second_cases) == 1
    assert second_cases[0].id == case.id
    assert second_cases[0].status == "REQUEST_FILED", "Detection re-run must not regress status"

    # No duplicate timeline or duplicate case created
    all_cases = (await test_session.execute(select(ClashCase))).scalars().all()
    assert len(all_cases) == 1

@pytest.mark.asyncio
async def test_retake_suggestion_edge_cases(test_session: AsyncSession):
    now = utcnow()

    admin = User(public_id="u_adm", name="Admin", email="adm@nexusedu.com", password_hash="h", role="admin")
    prof = User(public_id="u_prf", name="Prof Single", email="prf@nexusedu.com", password_hash="h", role="faculty")
    stud = User(public_id="u_st", name="Charlie", email="charlie@nexusedu.com", password_hash="h", role="student")
    test_session.add_all([admin, prof, stud])
    await test_session.flush()

    faculty = Faculty(user_id=prof.id, emp_code="FAC02", department="Computer Science", designation="Associate Professor", annual_salary=85000.0)
    test_session.add(faculty)
    await test_session.flush()

    student = Student(user_id=stud.id, roll_number="CS2026-03", department="Computer Science", semester=6, section="Section A")
    test_session.add(student)
    await test_session.flush()

    # Course offered to single section only
    single_offering = CourseOffering(
        course_code="CS-409",
        subject="Advanced Compilers",
        section="Section A",
        semester=6,
        department="Computer Science",
        faculty_id=faculty.id,
    )
    test_session.add(single_offering)
    await test_session.flush()

    exam = Assessment(
        offering_id=single_offering.id,
        kind="midterm",
        start_at=now + datetime.timedelta(days=1, hours=10),
        end_at=now + datetime.timedelta(days=1, hours=12),
        venue="Lab 3",
    )
    test_session.add(exam)
    await test_session.flush()

    event = Event(
        title="Coding Contest",
        start_at=now + datetime.timedelta(days=1, hours=9),
        end_at=now + datetime.timedelta(days=1, hours=15),
        created_by=admin.id,
    )
    test_session.add(event)
    await test_session.commit()

    # Suggestion should be None since there is no other section
    suggestion = await suggest_retake_slot(test_session, student, exam, event)
    assert suggestion is None
