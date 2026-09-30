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
    await session.execute(delete(Assessment).where(Assessment.offering_id.isnot(None)))
    await session.execute(delete(CourseOffering))
    await session.execute(delete(EventParticipant))
    await session.execute(delete(Event))
    await session.flush()
    print("Clash-feature tables reset completed.")

async def seed_clash_scenario(reset: bool = False):
    """
    Rich, comprehensive idempotent seed script for the Event-Exam Clash & Retake Rescheduling feature:
    - Faculty:
      * Prof. Dave: Head of Department (Computer Science)
      * Professor Smith: Cloud Computing (CS-401, Sections A, B, C)
      * Prof. Alan Turing: Advanced Compilers (CS-505) & Machine Learning (CS-410)
      * Prof. Priya Sharma: Distributed Database Systems (CS-303, Sections A, B)
    - Students:
      * Section A: Jane Doe (student@campus.edu), Liam Chen (liam@campus.edu), Priya Rao (priya@campus.edu)
      * Section B: Alex Smith (alex@campus.edu), Emily Watson (emily@campus.edu), Rahul Verma (rahul@campus.edu)
      * Section C: Maya Patel (maya@campus.edu), Carlos Ruiz (carlos@campus.edu)
    - Events & Multi-State Scenarios:
      1. 'Smart Campus Hackathon 2026' (Active, upcoming):
         - Overlaps Section A's midterm exams
         - Auto-detects 6 initial clashes in DETECTED status, ready for live Admin bulk-filing demo.
      2. 'National Collegiate AI & Robotics Symposium' (Multi-state lifecycle):
         - Alex Smith (CS-410): ESCALATED_TO_HOD (rejected by professor due to lab capacity, awaiting HOD override)
         - Emily Watson (CS-410): COUNTER_PROPOSED (Prof. Turing suggested alternative Saturday session)
         - Rahul Verma (CS-303): APPROVED (Prof. Sharma approved retake with Section B in Auditorium East)
      3. 'ACM ICPC Regional Collegiate Contest' (Historical / Resolved):
         - Jane Doe (CS-303): APPROVED with sister-section slot, demonstrating student retake schedule view.
    - Pre-populated notifications for Admin, HOD, Faculty, and Students.
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

        print("Seeding rich Event-Exam Clash demo scenario...")
        pwd_hash = hash_password("password123")
        now = utcnow()

        # =========================================================================
        # 1. Faculty & Staff Users
        # =========================================================================
        # 1.1 Admin
        admin = (await session.execute(select(User).where(User.email == "admin@campus.edu"))).scalar_one_or_none()
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

        # 1.2 HOD: Prof. Dave
        hod_user = (await session.execute(select(User).where(User.email == "prof.dave@campus.edu"))).scalar_one_or_none()
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

        hod_fac = (await session.execute(select(Faculty).where(Faculty.user_id == hod_user.id))).scalar_one_or_none()
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

        # 1.3 Prof. Smith (Cloud Computing)
        prof_smith_user = (await session.execute(select(User).where(User.email == "smith@campus.edu"))).scalar_one_or_none()
        if not prof_smith_user:
            prof_smith_user = User(
                public_id=str(uuid.uuid4()),
                name="Professor Smith",
                email="smith@campus.edu",
                password_hash=pwd_hash,
                role="faculty",
                created_at=now,
            )
            session.add(prof_smith_user)
            await session.flush()
        else:
            prof_smith_user.password_hash = pwd_hash

        prof_smith_fac = (await session.execute(select(Faculty).where(Faculty.user_id == prof_smith_user.id))).scalar_one_or_none()
        if not prof_smith_fac:
            prof_smith_fac = Faculty(
                user_id=prof_smith_user.id,
                emp_code="FAC-102",
                department="Computer Science",
                designation="Associate Professor",
                annual_salary=115000.0,
            )
            session.add(prof_smith_fac)
            await session.flush()

        # 1.4 Prof. Alan Turing (Compilers & Machine Learning)
        prof_turing_user = (await session.execute(select(User).where(User.email == "turing@campus.edu"))).scalar_one_or_none()
        if not prof_turing_user:
            prof_turing_user = User(
                public_id=str(uuid.uuid4()),
                name="Prof. Alan Turing",
                email="turing@campus.edu",
                password_hash=pwd_hash,
                role="faculty",
                created_at=now,
            )
            session.add(prof_turing_user)
            await session.flush()
        else:
            prof_turing_user.password_hash = pwd_hash

        prof_turing_fac = (await session.execute(select(Faculty).where(Faculty.user_id == prof_turing_user.id))).scalar_one_or_none()
        if not prof_turing_fac:
            prof_turing_fac = Faculty(
                user_id=prof_turing_user.id,
                emp_code="FAC-104",
                department="Computer Science",
                designation="Assistant Professor",
                annual_salary=95000.0,
            )
            session.add(prof_turing_fac)
            await session.flush()

        # 1.5 Prof. Priya Sharma (Databases)
        prof_sharma_user = (await session.execute(select(User).where(User.email == "prof.sharma@campus.edu"))).scalar_one_or_none()
        if not prof_sharma_user:
            prof_sharma_user = User(
                public_id=str(uuid.uuid4()),
                name="Prof. Priya Sharma",
                email="prof.sharma@campus.edu",
                password_hash=pwd_hash,
                role="faculty",
                created_at=now,
            )
            session.add(prof_sharma_user)
            await session.flush()
        else:
            prof_sharma_user.password_hash = pwd_hash

        prof_sharma_fac = (await session.execute(select(Faculty).where(Faculty.user_id == prof_sharma_user.id))).scalar_one_or_none()
        if not prof_sharma_fac:
            prof_sharma_fac = Faculty(
                user_id=prof_sharma_user.id,
                emp_code="FAC-106",
                department="Computer Science",
                designation="Associate Professor",
                annual_salary=110000.0,
            )
            session.add(prof_sharma_fac)
            await session.flush()

        # =========================================================================
        # 2. Students
        # =========================================================================
        students_def = [
            # Section A
            ("student@campus.edu", "Jane Doe", "CS-2023-042", "Section A"),
            ("liam@campus.edu", "Liam Chen", "CS-2023-019", "Section A"),
            ("priya@campus.edu", "Priya Rao", "CS-2023-033", "Section A"),
            # Section B
            ("alex@campus.edu", "Alex Smith", "CS-2023-088", "Section B"),
            ("emily@campus.edu", "Emily Watson", "CS-2023-074", "Section B"),
            ("rahul@campus.edu", "Rahul Verma", "CS-2023-091", "Section B"),
            # Section C
            ("maya@campus.edu", "Maya Patel", "CS-2023-105", "Section C"),
            ("carlos@campus.edu", "Carlos Ruiz", "CS-2023-112", "Section C"),
        ]

        student_records = {}
        for email, name, roll_no, section in students_def:
            u = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
            if not u:
                u = User(
                    public_id=str(uuid.uuid4()),
                    name=name,
                    email=email,
                    password_hash=pwd_hash,
                    role="student",
                    created_at=now,
                )
                session.add(u)
                await session.flush()
            else:
                u.password_hash = pwd_hash
                u.name = name

            s = (await session.execute(select(Student).where(
                (Student.user_id == u.id) | (Student.roll_number == roll_no)
            ))).scalar_one_or_none()
            if not s:
                s = Student(
                    user_id=u.id,
                    roll_number=roll_no,
                    department="Computer Science",
                    semester=6,
                    section=section,
                )
                session.add(s)
                await session.flush()
            else:
                s.user_id = u.id
                s.roll_number = roll_no
                s.section = section
                s.department = "Computer Science"
                s.semester = 6

            student_records[email] = (u, s)

        await session.flush()

        # =========================================================================
        # 3. Course Offerings (Computer Science, Semester 6)
        # =========================================================================
        # CS-401: Cloud Computing (Sections A, B, C) by Prof. Smith
        off_cc_a = CourseOffering(course_code="CS-401", subject="Cloud Computing", section="Section A", semester=6, department="Computer Science", faculty_id=prof_smith_fac.id)
        off_cc_b = CourseOffering(course_code="CS-401", subject="Cloud Computing", section="Section B", semester=6, department="Computer Science", faculty_id=prof_smith_fac.id)
        off_cc_c = CourseOffering(course_code="CS-401", subject="Cloud Computing", section="Section C", semester=6, department="Computer Science", faculty_id=prof_smith_fac.id)

        # CS-505: Advanced Compilers (Sections A, B) by Prof. Turing
        off_compilers_a = CourseOffering(course_code="CS-505", subject="Advanced Compilers", section="Section A", semester=6, department="Computer Science", faculty_id=prof_turing_fac.id)
        off_compilers_b = CourseOffering(course_code="CS-505", subject="Advanced Compilers", section="Section B", semester=6, department="Computer Science", faculty_id=prof_turing_fac.id)

        # CS-303: Distributed Database Systems (Sections A, B) by Prof. Sharma
        off_db_a = CourseOffering(course_code="CS-303", subject="Distributed Database Systems", section="Section A", semester=6, department="Computer Science", faculty_id=prof_sharma_fac.id)
        off_db_b = CourseOffering(course_code="CS-303", subject="Distributed Database Systems", section="Section B", semester=6, department="Computer Science", faculty_id=prof_sharma_fac.id)

        # CS-410: Machine Learning & Neural Networks (Sections B, C) by Prof. Turing
        off_ml_b = CourseOffering(course_code="CS-410", subject="Machine Learning & Neural Networks", section="Section B", semester=6, department="Computer Science", faculty_id=prof_turing_fac.id)
        off_ml_c = CourseOffering(course_code="CS-410", subject="Machine Learning & Neural Networks", section="Section C", semester=6, department="Computer Science", faculty_id=prof_turing_fac.id)

        session.add_all([
            off_cc_a, off_cc_b, off_cc_c,
            off_compilers_a, off_compilers_b,
            off_db_a, off_db_b,
            off_ml_b, off_ml_c,
        ])
        await session.flush()

        # =========================================================================
        # 4. Assessments (Midterm Exam Schedules)
        # =========================================================================
        base_day = now.date() + datetime.timedelta(days=1)

        # Tomorrow (base_day):
        # - 10:00 - 12:00: Cloud Computing Section A (Computing Lab 101)
        # - 14:00 - 16:00: Advanced Compilers Section A (Lecture Hall A)
        exam_cc_a = Assessment(
            offering_id=off_cc_a.id,
            kind="Midterm Examination",
            start_at=datetime.datetime.combine(base_day, datetime.time(10, 0)),
            end_at=datetime.datetime.combine(base_day, datetime.time(12, 0)),
            venue="Computing Lab 101",
        )
        exam_compilers_a = Assessment(
            offering_id=off_compilers_a.id,
            kind="Midterm Examination",
            start_at=datetime.datetime.combine(base_day, datetime.time(14, 0)),
            end_at=datetime.datetime.combine(base_day, datetime.time(16, 0)),
            venue="Lecture Hall A",
        )

        # base_day + 1:
        # - 10:00 - 12:00: Cloud Computing Section B (Computing Lab 102) -> Sister retake for CS-401 Sec A
        # - 14:00 - 16:00: Advanced Compilers Section B (Lecture Hall B) -> Sister retake for CS-505 Sec A
        exam_cc_b = Assessment(
            offering_id=off_cc_b.id,
            kind="Midterm Examination",
            start_at=datetime.datetime.combine(base_day + datetime.timedelta(days=1), datetime.time(10, 0)),
            end_at=datetime.datetime.combine(base_day + datetime.timedelta(days=1), datetime.time(12, 0)),
            venue="Computing Lab 102",
        )
        exam_compilers_b = Assessment(
            offering_id=off_compilers_b.id,
            kind="Midterm Examination",
            start_at=datetime.datetime.combine(base_day + datetime.timedelta(days=1), datetime.time(14, 0)),
            end_at=datetime.datetime.combine(base_day + datetime.timedelta(days=1), datetime.time(16, 0)),
            venue="Lecture Hall B",
        )

        # base_day + 2:
        # - 10:00 - 12:00: Cloud Computing Section C (Computing Lab 103)
        # - 14:00 - 16:00: Distributed Database Systems Section A (Auditorium West)
        exam_cc_c = Assessment(
            offering_id=off_cc_c.id,
            kind="Midterm Examination",
            start_at=datetime.datetime.combine(base_day + datetime.timedelta(days=2), datetime.time(10, 0)),
            end_at=datetime.datetime.combine(base_day + datetime.timedelta(days=2), datetime.time(12, 0)),
            venue="Computing Lab 103",
        )
        exam_db_a = Assessment(
            offering_id=off_db_a.id,
            kind="Midterm Examination",
            start_at=datetime.datetime.combine(base_day + datetime.timedelta(days=2), datetime.time(14, 0)),
            end_at=datetime.datetime.combine(base_day + datetime.timedelta(days=2), datetime.time(16, 0)),
            venue="Auditorium West",
        )

        # base_day + 3:
        # - 10:00 - 12:00: Machine Learning Section B (Seminar Hall 2)
        # - 14:00 - 16:00: Distributed Database Systems Section B (Auditorium East) -> Sister retake for CS-303 Sec A
        exam_ml_b = Assessment(
            offering_id=off_ml_b.id,
            kind="Midterm Examination",
            start_at=datetime.datetime.combine(base_day + datetime.timedelta(days=3), datetime.time(10, 0)),
            end_at=datetime.datetime.combine(base_day + datetime.timedelta(days=3), datetime.time(12, 0)),
            venue="Seminar Hall 2",
        )
        exam_db_b = Assessment(
            offering_id=off_db_b.id,
            kind="Midterm Examination",
            start_at=datetime.datetime.combine(base_day + datetime.timedelta(days=3), datetime.time(14, 0)),
            end_at=datetime.datetime.combine(base_day + datetime.timedelta(days=3), datetime.time(16, 0)),
            venue="Auditorium East",
        )

        # base_day + 4:
        # - 14:00 - 16:00: Machine Learning Section C (Seminar Hall 3) -> Sister retake for CS-410 Sec B
        exam_ml_c = Assessment(
            offering_id=off_ml_c.id,
            kind="Midterm Examination",
            start_at=datetime.datetime.combine(base_day + datetime.timedelta(days=4), datetime.time(14, 0)),
            end_at=datetime.datetime.combine(base_day + datetime.timedelta(days=4), datetime.time(16, 0)),
            venue="Seminar Hall 3",
        )

        session.add_all([
            exam_cc_a, exam_compilers_a,
            exam_cc_b, exam_compilers_b,
            exam_cc_c, exam_db_a,
            exam_ml_b, exam_db_b,
            exam_ml_c,
        ])
        await session.flush()

        # =========================================================================
        # 5. Events & Multi-State Scenarios
        # =========================================================================

        # -------------------------------------------------------------------------
        # Event 1: 'Smart Campus Hackathon 2026'
        # Scheduled tomorrow (base_day) from 09:00 to 18:00
        # Participants: Jane Doe, Liam Chen, Priya Rao (Section A students)
        # Collides with: Cloud Computing Sec A (10:00-12:00) & Compilers Sec A (14:00-16:00)
        # All 6 clash cases will be detected and left in 'DETECTED' status for live demo filing!
        # -------------------------------------------------------------------------
        hackathon_event = Event(
            title="Smart Campus Hackathon 2026",
            description="Inter-college 24-hour innovation hackathon & technical symposium",
            start_at=datetime.datetime.combine(base_day, datetime.time(9, 0)),
            end_at=datetime.datetime.combine(base_day, datetime.time(18, 0)),
            created_by=admin.id,
            created_at=now,
        )
        session.add(hackathon_event)
        await session.flush()

        p_jane_hack = EventParticipant(event_id=hackathon_event.id, student_id=student_records["student@campus.edu"][1].id)
        p_liam_hack = EventParticipant(event_id=hackathon_event.id, student_id=student_records["liam@campus.edu"][1].id)
        p_priya_hack = EventParticipant(event_id=hackathon_event.id, student_id=student_records["priya@campus.edu"][1].id)
        session.add_all([p_jane_hack, p_liam_hack, p_priya_hack])
        await session.flush()

        # Run automated clash detection on Event 1
        hackathon_cases = await detect_clashes_for_event(session, hackathon_event.id, admin.id)
        print(f"  -> Generated {len(hackathon_cases)} DETECTED clash cases for {hackathon_event.title}")

        # -------------------------------------------------------------------------
        # Event 2: 'National Collegiate AI & Robotics Symposium'
        # Scheduled on base_day + 3 from 08:30 to 17:30
        # Participants: Alex Smith (Sec B), Emily Watson (Sec B), Rahul Verma (Sec B)
        # Collides with: Machine Learning Sec B (10:00-12:00) & Distributed DB Sec B (14:00-16:00)
        # Seeded with diverse lifecycle states:
        #   - Alex Smith (CS-410): ESCALATED_TO_HOD (Prof. Turing rejected due to room cap; HOD override demo ready!)
        #   - Emily Watson (CS-410): COUNTER_PROPOSED (Prof. Turing proposed Saturday session; Admin demo ready!)
        #   - Rahul Verma (CS-303): APPROVED (Prof. Sharma approved retake in Auditorium East)
        # -------------------------------------------------------------------------
        symposium_event = Event(
            title="National Collegiate AI & Robotics Symposium",
            description="Annual keynote exhibits, paper presentations and live drone navigation challenge",
            start_at=datetime.datetime.combine(base_day + datetime.timedelta(days=3), datetime.time(8, 30)),
            end_at=datetime.datetime.combine(base_day + datetime.timedelta(days=3), datetime.time(17, 30)),
            created_by=admin.id,
            created_at=now - datetime.timedelta(hours=6),
        )
        session.add(symposium_event)
        await session.flush()

        p_alex_sym = EventParticipant(event_id=symposium_event.id, student_id=student_records["alex@campus.edu"][1].id)
        p_emily_sym = EventParticipant(event_id=symposium_event.id, student_id=student_records["emily@campus.edu"][1].id)
        p_rahul_sym = EventParticipant(event_id=symposium_event.id, student_id=student_records["rahul@campus.edu"][1].id)
        session.add_all([p_alex_sym, p_emily_sym, p_rahul_sym])
        await session.flush()

        # Case 2.1: Alex Smith - Machine Learning Sec B (CS-410) -> ESCALATED_TO_HOD
        alex_student = student_records["alex@campus.edu"][1]
        case_alex_ml = ClashCase(
            event_id=symposium_event.id,
            student_id=alex_student.id,
            assessment_id=exam_ml_b.id,
            status="ESCALATED_TO_HOD",
            suggested_retake_assessment_id=exam_ml_c.id,
            filed_by=admin.id,
            filed_at=now - datetime.timedelta(hours=4),
            decided_by=prof_turing_user.id,
            decided_at=now - datetime.timedelta(hours=2),
            rejection_reason="Seminar Hall 3 seating capacity exhausted for sister Section C. Cannot accommodate additional retake during normal hours.",
            created_at=now - datetime.timedelta(hours=5),
            updated_at=now - datetime.timedelta(hours=2),
        )
        session.add(case_alex_ml)
        await session.flush()

        # Timelines for Case 2.1
        session.add_all([
            CaseTimeline(case_id=case_alex_ml.id, actor_user_id=None, actor_role="SYSTEM", from_status=None, to_status="DETECTED", note="Clash detected with National Collegiate AI & Robotics Symposium", at=now - datetime.timedelta(hours=5)),
            CaseTimeline(case_id=case_alex_ml.id, actor_user_id=admin.id, actor_role="admin", from_status="DETECTED", to_status="REQUEST_FILED", note="Bulk filed by Academic Office. Recommended sister slot Section C (Seminar Hall 3).", at=now - datetime.timedelta(hours=4)),
            CaseTimeline(case_id=case_alex_ml.id, actor_user_id=prof_turing_user.id, actor_role="faculty", from_status="REQUEST_FILED", to_status="REJECTED", note="Seminar Hall 3 seating capacity exhausted for sister Section C. Cannot accommodate additional retake during normal hours.", at=now - datetime.timedelta(hours=2)),
            CaseTimeline(case_id=case_alex_ml.id, actor_user_id=None, actor_role="SYSTEM", from_status="REJECTED", to_status="ESCALATED_TO_HOD", note="Automatic escalation to Head of Department for review.", at=now - datetime.timedelta(hours=2)),
        ])

        # Case 2.2: Emily Watson - Machine Learning Sec B (CS-410) -> COUNTER_PROPOSED
        emily_student = student_records["emily@campus.edu"][1]
        counter_time = datetime.datetime.combine(base_day + datetime.timedelta(days=5), datetime.time(11, 0))
        case_emily_ml = ClashCase(
            event_id=symposium_event.id,
            student_id=emily_student.id,
            assessment_id=exam_ml_b.id,
            status="COUNTER_PROPOSED",
            suggested_retake_assessment_id=exam_ml_c.id,
            retake_at=counter_time,
            retake_note="Special supervised retake in Dept Conference Room 3 on Saturday.",
            filed_by=admin.id,
            filed_at=now - datetime.timedelta(hours=4),
            decided_by=prof_turing_user.id,
            decided_at=now - datetime.timedelta(hours=1),
            rejection_reason="Sister slot conflicts with scheduled department accreditation review. Proposed Saturday special slot.",
            created_at=now - datetime.timedelta(hours=5),
            updated_at=now - datetime.timedelta(hours=1),
        )
        session.add(case_emily_ml)
        await session.flush()

        session.add_all([
            CaseTimeline(case_id=case_emily_ml.id, actor_user_id=None, actor_role="SYSTEM", from_status=None, to_status="DETECTED", note="Clash detected with National Collegiate AI & Robotics Symposium", at=now - datetime.timedelta(hours=5)),
            CaseTimeline(case_id=case_emily_ml.id, actor_user_id=admin.id, actor_role="admin", from_status="DETECTED", to_status="REQUEST_FILED", note="Filed by Academic Office requesting sister slot.", at=now - datetime.timedelta(hours=4)),
            CaseTimeline(case_id=case_emily_ml.id, actor_user_id=prof_turing_user.id, actor_role="faculty", from_status="REQUEST_FILED", to_status="COUNTER_PROPOSED", note="Counter-proposed slot: Saturday 11:00 AM @ Dept Conference Room 3.", at=now - datetime.timedelta(hours=1)),
        ])

        # Case 2.3: Rahul Verma - Distributed DB Sec B (CS-303) -> APPROVED
        rahul_student = student_records["rahul@campus.edu"][1]
        case_rahul_db = ClashCase(
            event_id=symposium_event.id,
            student_id=rahul_student.id,
            assessment_id=exam_db_b.id,
            status="APPROVED",
            suggested_retake_assessment_id=exam_db_a.id,
            retake_assessment_id=exam_db_a.id,
            retake_at=exam_db_a.start_at,
            retake_note="Approved to sit with Section A in Auditorium West.",
            filed_by=admin.id,
            filed_at=now - datetime.timedelta(hours=4),
            decided_by=prof_sharma_user.id,
            decided_at=now - datetime.timedelta(hours=2, minutes=30),
            created_at=now - datetime.timedelta(hours=5),
            updated_at=now - datetime.timedelta(hours=2, minutes=30),
        )
        session.add(case_rahul_db)
        await session.flush()

        session.add_all([
            CaseTimeline(case_id=case_rahul_db.id, actor_user_id=None, actor_role="SYSTEM", from_status=None, to_status="DETECTED", note="Clash detected with National Collegiate AI & Robotics Symposium", at=now - datetime.timedelta(hours=5)),
            CaseTimeline(case_id=case_rahul_db.id, actor_user_id=admin.id, actor_role="admin", from_status="DETECTED", to_status="REQUEST_FILED", note="Filed by Academic Office requesting Section A parallel slot.", at=now - datetime.timedelta(hours=4)),
            CaseTimeline(case_id=case_rahul_db.id, actor_user_id=prof_sharma_user.id, actor_role="faculty", from_status="REQUEST_FILED", to_status="APPROVED", note="Approved by Prof. Priya Sharma. Student will sit in Auditorium West.", at=now - datetime.timedelta(hours=2, minutes=30)),
        ])

        # -------------------------------------------------------------------------
        # Event 3: 'ACM ICPC Regional Collegiate Contest'
        # Scheduled on base_day + 2 from 08:30 to 17:30
        # Participants: Jane Doe (student@campus.edu), Maya Patel (Sec C)
        # Collides with: Distributed Database Systems Sec A (14:00-16:00)
        # Jane Doe's case is pre-APPROVED with Section B slot!
        # When Jane Doe logs into student portal, she sees:
        #   - 2 pending conflicts for tomorrow's Hackathon
        #   - 1 APPROVED rescheduled retake for ACM ICPC with venue Auditorium East!
        # -------------------------------------------------------------------------
        icpc_event = Event(
            title="ACM ICPC Regional Collegiate Contest",
            description="Premier annual inter-collegiate algorithmic programming competition",
            start_at=datetime.datetime.combine(base_day + datetime.timedelta(days=2), datetime.time(8, 30)),
            end_at=datetime.datetime.combine(base_day + datetime.timedelta(days=2), datetime.time(17, 30)),
            created_by=admin.id,
            created_at=now - datetime.timedelta(days=1),
        )
        session.add(icpc_event)
        await session.flush()

        p_jane_icpc = EventParticipant(event_id=icpc_event.id, student_id=student_records["student@campus.edu"][1].id)
        p_maya_icpc = EventParticipant(event_id=icpc_event.id, student_id=student_records["maya@campus.edu"][1].id)
        session.add_all([p_jane_icpc, p_maya_icpc])
        await session.flush()

        # Case 3.1: Jane Doe - Distributed DB Sec A (CS-303) -> APPROVED
        jane_student = student_records["student@campus.edu"][1]
        case_jane_db = ClashCase(
            event_id=icpc_event.id,
            student_id=jane_student.id,
            assessment_id=exam_db_a.id,
            status="APPROVED",
            suggested_retake_assessment_id=exam_db_b.id,
            retake_assessment_id=exam_db_b.id,
            retake_at=exam_db_b.start_at,
            retake_note="Approved to sit with Section B on following afternoon in Auditorium East.",
            filed_by=admin.id,
            filed_at=now - datetime.timedelta(hours=18),
            decided_by=prof_sharma_user.id,
            decided_at=now - datetime.timedelta(hours=12),
            created_at=now - datetime.timedelta(hours=20),
            updated_at=now - datetime.timedelta(hours=12),
        )
        session.add(case_jane_db)
        await session.flush()

        session.add_all([
            CaseTimeline(case_id=case_jane_db.id, actor_user_id=None, actor_role="SYSTEM", from_status=None, to_status="DETECTED", note="Clash detected with ACM ICPC Regional Collegiate Contest", at=now - datetime.timedelta(hours=20)),
            CaseTimeline(case_id=case_jane_db.id, actor_user_id=admin.id, actor_role="admin", from_status="DETECTED", to_status="REQUEST_FILED", note="Filed by Academic Office with sister slot recommendation.", at=now - datetime.timedelta(hours=18)),
            CaseTimeline(case_id=case_jane_db.id, actor_user_id=prof_sharma_user.id, actor_role="faculty", from_status="REQUEST_FILED", to_status="APPROVED", note="Approved by Prof. Priya Sharma. Confirmed seating in Auditorium East.", at=now - datetime.timedelta(hours=12)),
        ])

        # =========================================================================
        # 6. Notifications for all Demo Roles
        # =========================================================================
        demo_notifications = [
            # Admin
            Notification(
                user_id=admin.id,
                type="COUNTER_PROPOSED",
                title="Counter-Proposal Received",
                body="Prof. Alan Turing proposed a special Saturday slot for Emily Watson (CS-410).",
                case_id=case_emily_ml.id,
                event_id=symposium_event.id,
                is_read=False,
                created_at=now - datetime.timedelta(hours=1),
            ),
            Notification(
                user_id=admin.id,
                type="CASE_ESCALATED",
                title="Case Escalated to HOD",
                body="Alex Smith's reschedule request for CS-410 was rejected by faculty and escalated to HOD.",
                case_id=case_alex_ml.id,
                event_id=symposium_event.id,
                is_read=False,
                created_at=now - datetime.timedelta(hours=2),
            ),
            Notification(
                user_id=admin.id,
                type="CLASH_DETECTED",
                title="Clash Alerts: Smart Campus Hackathon",
                body=f"6 potential exam clashes detected for Smart Campus Hackathon 2026. Review clash matrix.",
                case_id=hackathon_cases[0].id if hackathon_cases else None,
                event_id=hackathon_event.id,
                is_read=True,
                created_at=now,
            ),
            # HOD (Prof. Dave)
            Notification(
                user_id=hod_user.id,
                type="CASE_ESCALATED",
                title="Urgent: Retake Escalated for HOD Review",
                body="Alex Smith's retake for Machine Learning & Neural Networks (CS-410) was rejected by faculty. Awaiting discretionary override.",
                case_id=case_alex_ml.id,
                event_id=symposium_event.id,
                is_read=False,
                created_at=now - datetime.timedelta(hours=2),
            ),
            # Prof. Smith
            Notification(
                user_id=prof_smith_user.id,
                type="CLASH_DETECTED",
                title="Upcoming Assessment Overlap Notice",
                body="3 students enrolled in Cloud Computing (Section A) have registered for Smart Campus Hackathon 2026.",
                event_id=hackathon_event.id,
                is_read=False,
                created_at=now,
            ),
            # Prof. Turing
            Notification(
                user_id=prof_turing_user.id,
                type="CLASH_DETECTED",
                title="Upcoming Assessment Overlap Notice",
                body="Students enrolled in Advanced Compilers (Section A) have registered for Smart Campus Hackathon 2026.",
                event_id=hackathon_event.id,
                is_read=False,
                created_at=now,
            ),
            # Student (Jane Doe)
            Notification(
                user_id=student_records["student@campus.edu"][0].id,
                type="CASE_APPROVED",
                title="Exam Retake Approved!",
                body="Your retake for Distributed Database Systems (CS-303) was approved. Date: following afternoon in Auditorium East.",
                case_id=case_jane_db.id,
                event_id=icpc_event.id,
                is_read=False,
                created_at=now - datetime.timedelta(hours=12),
            ),
            Notification(
                user_id=student_records["student@campus.edu"][0].id,
                type="CLASH_DETECTED",
                title="Exam Clash Detected",
                body="Your Cloud Computing and Advanced Compilers exams collide with Smart Campus Hackathon 2026.",
                event_id=hackathon_event.id,
                is_read=False,
                created_at=now,
            ),
        ]
        session.add_all(demo_notifications)

        await session.commit()
        print("Rich clash scenario successfully seeded!")
        print(f"  Total Events: 3")
        print(f"  Total Course Offerings: 9 across 4 courses")
        print(f"  Total Assessments: 9 scheduled midterm exams")
        print(f"  Total Clash Cases: {len(hackathon_cases) + 4} (6 DETECTED, 1 ESCALATED_TO_HOD, 1 COUNTER_PROPOSED, 2 APPROVED)")
        print(f"  Pre-populated Notifications: {len(demo_notifications)}")

if __name__ == "__main__":
    import asyncio
    parser = argparse.ArgumentParser(description="Seed rich Event-Exam Clash demo scenario data")
    parser.add_argument("--reset", action="store_true", help="Delete only clash-feature rows and re-seed from clean")
    args = parser.parse_args()
    asyncio.run(seed_clash_scenario(reset=args.reset))
