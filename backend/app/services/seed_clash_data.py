import datetime
import uuid
import sys
import argparse
from sqlalchemy import select, delete
from app.core.database import (
    AsyncSessionLocal,
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
from app.core.security import hash_password
from app.services.clash_detector import detect_clashes_for_event

async def reset_clash_scenario_data(session):
    """
    Deletes ONLY clash-feature rows:
    - notifications
    - case_timelines
    - clash_cases
    - assessments
    - course_offerings
    - event_participants
    - events
    Leaves all core tables (users, faculty, students, parents, buses, attendance, document_embeddings, audit_logs) untouched.
    """
    print("Resetting clash-feature tables...")
    await session.execute(delete(Notification))
    await session.execute(delete(CaseTimeline))
    await session.execute(delete(ClashCase))
    await session.execute(delete(Assessment))
    await session.execute(delete(CourseOffering))
    await session.execute(delete(EventParticipant))
    await session.execute(delete(Event))
    await session.flush()
    print("Clash-feature tables reset completed.")

async def seed_clash_scenario(reset: bool = False):
    """
    Idempotent seed script for the Event-Exam Clash & Retake Rescheduling feature:
    - 1 HOD (Prof. Dave, Computer Science)
    - 2 Professors:
      * Professor Smith: Teaches Cloud Computing (CS-401) to Sections A, B, and C
      * Prof. Alan Turing: Teaches Advanced Compilers (CS-505) to Section A only
    - Students spread across Sections A, B, and C
    - Event: 'Smart Campus Hackathon 2026' overlapping Section A's midterm exams
    - Automatically detects initial clashes
    """
    async with AsyncSessionLocal() as session:
        if reset:
            await reset_clash_scenario_data(session)

        # Check if already seeded
        existing_event = (
            await session.execute(select(Event).where(Event.title == "Smart Campus Hackathon 2026"))
        ).scalar_one_or_none()
        if existing_event:
            print("Clash scenario already seeded. Skipping. Use --reset to re-seed from scratch.")
            return

        print("Seeding Event-Exam Clash scenario...")
        pwd_hash = hash_password("password123")
        now = utcnow()

        # 1. Admin
        admin = (
            await session.execute(select(User).where(User.email == "admin@campus.edu"))
        ).scalar_one_or_none()
        if not admin:
            admin = User(
                public_id=str(uuid.uuid4()),
                name="Admin Officer",
                email="admin@campus.edu",
                password_hash=pwd_hash,
                role="admin",
                created_at=now,
            )
            session.add(admin)
            await session.flush()
        else:
            admin.password_hash = pwd_hash

        # 2. HOD
        hod_user = (
            await session.execute(select(User).where(User.email == "prof.dave@campus.edu"))
        ).scalar_one_or_none()
        if not hod_user:
            hod_user = User(
                public_id=str(uuid.uuid4()),
                name="Prof. Dave (HOD)",
                email="prof.dave@campus.edu",
                password_hash=pwd_hash,
                role="faculty",
                created_at=now,
            )
            session.add(hod_user)
            await session.flush()
        else:
            hod_user.password_hash = pwd_hash

        hod_fac = (
            await session.execute(select(Faculty).where(Faculty.user_id == hod_user.id))
        ).scalar_one_or_none()
        if not hod_fac:
            hod_fac = Faculty(
                user_id=hod_user.id,
                emp_code="FAC-HOD-01",
                department="Computer Science",
                designation="Head of Department",
                annual_salary=135000.0,
            )
            session.add(hod_fac)
            await session.flush()

        # 3. Professor 1: Prof. Smith (Cloud Computing across A, B, C)
        prof1_user = (
            await session.execute(select(User).where(User.email == "smith@campus.edu"))
        ).scalar_one_or_none()
        if not prof1_user:
            prof1_user = User(
                public_id=str(uuid.uuid4()),
                name="Professor Smith",
                email="smith@campus.edu",
                password_hash=pwd_hash,
                role="faculty",
                created_at=now,
            )
            session.add(prof1_user)
            await session.flush()
        else:
            prof1_user.password_hash = pwd_hash

        prof1_fac = (
            await session.execute(select(Faculty).where(Faculty.user_id == prof1_user.id))
        ).scalar_one_or_none()
        if not prof1_fac:
            prof1_fac = Faculty(
                user_id=prof1_user.id,
                emp_code="FAC-102",
                department="Computer Science",
                designation="Associate Professor",
                annual_salary=115000.0,
            )
            session.add(prof1_fac)
            await session.flush()

        # 4. Professor 2: Prof. Alan Turing (Advanced Compilers, Section A only)
        prof2_user = (
            await session.execute(select(User).where(User.email == "turing@campus.edu"))
        ).scalar_one_or_none()
        if not prof2_user:
            prof2_user = User(
                public_id=str(uuid.uuid4()),
                name="Prof. Alan Turing",
                email="turing@campus.edu",
                password_hash=pwd_hash,
                role="faculty",
                created_at=now,
            )
            session.add(prof2_user)
            await session.flush()
        else:
            prof2_user.password_hash = pwd_hash

        prof2_fac = (
            await session.execute(select(Faculty).where(Faculty.user_id == prof2_user.id))
        ).scalar_one_or_none()
        if not prof2_fac:
            prof2_fac = Faculty(
                user_id=prof2_user.id,
                emp_code="FAC-104",
                department="Computer Science",
                designation="Assistant Professor",
                annual_salary=95000.0,
            )
            session.add(prof2_fac)
            await session.flush()

        # 5. Students: Jane Doe (A), Alex Smith (B), Maya Patel (C), Liam Chen (A)
        # Jane Doe
        jane_user = (await session.execute(select(User).where(User.email == "student@campus.edu"))).scalar_one_or_none()
        if not jane_user:
            jane_user = User(public_id=str(uuid.uuid4()), name="Jane Doe", email="student@campus.edu", password_hash=pwd_hash, role="student", created_at=now)
            session.add(jane_user)
            await session.flush()
        else:
            jane_user.password_hash = pwd_hash
        jane_stud = (await session.execute(select(Student).where(Student.user_id == jane_user.id))).scalar_one_or_none()
        if not jane_stud:
            jane_stud = Student(user_id=jane_user.id, roll_number="CS-2023-042", department="Computer Science", semester=6, section="Section A")
            session.add(jane_stud)
        else:
            jane_stud.section = "Section A"

        # Alex Smith
        alex_user = (await session.execute(select(User).where(User.email == "alex@campus.edu"))).scalar_one_or_none()
        if not alex_user:
            alex_user = User(public_id=str(uuid.uuid4()), name="Alex Smith", email="alex@campus.edu", password_hash=pwd_hash, role="student", created_at=now)
            session.add(alex_user)
            await session.flush()
        else:
            alex_user.password_hash = pwd_hash
        alex_stud = (await session.execute(select(Student).where(Student.user_id == alex_user.id))).scalar_one_or_none()
        if not alex_stud:
            alex_stud = Student(user_id=alex_user.id, roll_number="CS-2023-088", department="Computer Science", semester=6, section="Section B")
            session.add(alex_stud)
        else:
            alex_stud.section = "Section B"

        # Maya Patel (Section C)
        maya_user = (await session.execute(select(User).where(User.email == "maya@campus.edu"))).scalar_one_or_none()
        if not maya_user:
            maya_user = User(public_id=str(uuid.uuid4()), name="Maya Patel", email="maya@campus.edu", password_hash=pwd_hash, role="student", created_at=now)
            session.add(maya_user)
            await session.flush()
        else:
            maya_user.password_hash = pwd_hash
        maya_stud = (await session.execute(select(Student).where(Student.user_id == maya_user.id))).scalar_one_or_none()
        if not maya_stud:
            maya_stud = Student(user_id=maya_user.id, roll_number="CS-2023-105", department="Computer Science", semester=6, section="Section C")
            session.add(maya_stud)

        # Liam Chen (Section A)
        liam_user = (await session.execute(select(User).where(User.email == "liam@campus.edu"))).scalar_one_or_none()
        if not liam_user:
            liam_user = User(public_id=str(uuid.uuid4()), name="Liam Chen", email="liam@campus.edu", password_hash=pwd_hash, role="student", created_at=now)
            session.add(liam_user)
            await session.flush()
        else:
            liam_user.password_hash = pwd_hash
        liam_stud = (await session.execute(select(Student).where(Student.user_id == liam_user.id))).scalar_one_or_none()
        if not liam_stud:
            liam_stud = Student(user_id=liam_user.id, roll_number="CS-2023-019", department="Computer Science", semester=6, section="Section A")
            session.add(liam_stud)

        await session.flush()

        # 6. Offerings:
        # Cloud Computing (CS-401) taught by Prof. Smith to Section A, B, C
        off_cc_a = CourseOffering(
            course_code="CS-401",
            subject="Cloud Computing",
            section="Section A",
            semester=6,
            department="Computer Science",
            faculty_id=prof1_fac.id,
        )
        off_cc_b = CourseOffering(
            course_code="CS-401",
            subject="Cloud Computing",
            section="Section B",
            semester=6,
            department="Computer Science",
            faculty_id=prof1_fac.id,
        )
        off_cc_c = CourseOffering(
            course_code="CS-401",
            subject="Cloud Computing",
            section="Section C",
            semester=6,
            department="Computer Science",
            faculty_id=prof1_fac.id,
        )

        # Advanced Compilers (CS-505) taught by Prof. Turing to Section A only
        off_compilers = CourseOffering(
            course_code="CS-505",
            subject="Advanced Compilers",
            section="Section A",
            semester=6,
            department="Computer Science",
            faculty_id=prof2_fac.id,
        )

        session.add_all([off_cc_a, off_cc_b, off_cc_c, off_compilers])
        await session.flush()

        # 7. Assessments:
        # Base day = tomorrow
        base_day = now.date() + datetime.timedelta(days=1)
        exam_cc_a = Assessment(
            offering_id=off_cc_a.id,
            kind="Midterm Examination",
            start_at=datetime.datetime.combine(base_day, datetime.time(10, 0)),
            end_at=datetime.datetime.combine(base_day, datetime.time(12, 0)),
            venue="Computing Lab 101",
        )
        exam_cc_b = Assessment(
            offering_id=off_cc_b.id,
            kind="Midterm Examination",
            start_at=datetime.datetime.combine(base_day + datetime.timedelta(days=1), datetime.time(10, 0)),
            end_at=datetime.datetime.combine(base_day + datetime.timedelta(days=1), datetime.time(12, 0)),
            venue="Computing Lab 102",
        )
        exam_cc_c = Assessment(
            offering_id=off_cc_c.id,
            kind="Midterm Examination",
            start_at=datetime.datetime.combine(base_day + datetime.timedelta(days=2), datetime.time(10, 0)),
            end_at=datetime.datetime.combine(base_day + datetime.timedelta(days=2), datetime.time(12, 0)),
            venue="Computing Lab 103",
        )

        # Advanced Compilers exam on base day 14:00 - 16:00
        exam_compilers = Assessment(
            offering_id=off_compilers.id,
            kind="Midterm Examination",
            start_at=datetime.datetime.combine(base_day, datetime.time(14, 0)),
            end_at=datetime.datetime.combine(base_day, datetime.time(16, 0)),
            venue="Lecture Hall A",
        )

        session.add_all([exam_cc_a, exam_cc_b, exam_cc_c, exam_compilers])
        await session.flush()

        # 8. Event: 'Smart Campus Hackathon 2026'
        # Overlaps base_day 09:00 to 18:00
        hackathon_event = Event(
            title="Smart Campus Hackathon 2026",
            description="Inter-college 24-hour innovation hackathon & symposium",
            start_at=datetime.datetime.combine(base_day, datetime.time(9, 0)),
            end_at=datetime.datetime.combine(base_day, datetime.time(18, 0)),
            created_by=admin.id,
            created_at=now,
        )
        session.add(hackathon_event)
        await session.flush()

        # Add participants: Jane Doe and Liam Chen (both Section A)
        p1 = EventParticipant(event_id=hackathon_event.id, student_id=jane_stud.id)
        p2 = EventParticipant(event_id=hackathon_event.id, student_id=liam_stud.id)
        session.add_all([p1, p2])
        await session.flush()

        # Run automated clash detection
        cases = await detect_clashes_for_event(session, hackathon_event.id, admin.id)
        await session.commit()
        print(f"Clash scenario successfully seeded! Created {len(cases)} detected clash cases.")

if __name__ == "__main__":
    import asyncio
    parser = argparse.ArgumentParser(description="Seed Event-Exam Clash scenario data")
    parser.add_argument("--reset", action="store_true", help="Delete only clash-feature rows and re-seed from clean")
    args = parser.parse_args()
    asyncio.run(seed_clash_scenario(reset=args.reset))
