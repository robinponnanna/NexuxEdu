import json
import uuid
import numpy as np
from sqlalchemy import select
from app.core.database import (
    AsyncSessionLocal, User, Student, Faculty, Parent, Bus, Attendance, DocumentEmbedding, AuditLog
)
from app.core.security import hash_password

# Simple semantic embedding simulator (deterministic 384-dimensional vector based on keywords/tokens)
def generate_pseudo_embedding(text: str, dim: int = 384) -> list:
    np.random.seed(abs(hash(text.lower().strip())) % (2**32))
    vec = np.random.normal(0, 1, dim)
    norm = np.linalg.norm(vec)
    return (vec / norm).tolist() if norm > 0 else vec.tolist()

async def seed_database_if_empty():
    async with AsyncSessionLocal() as session:
        # Check if users already seeded
        result = await session.execute(select(User).limit(1))
        if result.scalar_one_or_none() is not None:
            return  # Already seeded

        print("Seeding OmniCampus database with synthetic records...")

        # 1. Seed 20 Buses with waypoints and stops
        buses = []
        base_coords = [
            (28.6139, 77.2090), (28.6200, 77.2150), (28.6300, 77.2200), (28.6400, 77.2100),
            (28.6050, 77.1950), (28.5900, 77.2300), (28.5800, 77.2100), (28.5700, 77.1900),
            (28.6500, 77.2400), (28.6600, 77.2250), (28.6350, 77.1850), (28.6250, 77.1700),
            (28.6150, 77.2500), (28.6000, 77.2600), (28.5850, 77.2450), (28.5750, 77.2350),
            (28.6700, 77.2100), (28.6800, 77.2200), (28.5600, 77.1800), (28.5500, 77.1700)
        ]
        
        route_names = [
            "Route North-4 (Civic Express)", "Route South-1 (Metro Link)", "Route East-2 (Tech Corridor)",
            "Route West-3 (Hillside Express)", "Route Central-5 (Main Gate)", "Route Metro-6 (Blue Line)",
            "Route Ring-7 (Outer Belt)", "Route Valley-8 (Greenway)", "Route Cyber-9 (Innovation Hub)",
            "Route Airport-10 (Skyline Link)", "Route North-11 (Lakeview)", "Route South-12 (Heritage Line)",
            "Route East-13 (Riverside)", "Route West-14 (Forest View)", "Route City-15 (Downtown Rapid)",
            "Route Campus-16 (Inter-Hostel)", "Route North-17 (Orchard Park)", "Route South-18 (Grand Trunk)",
            "Route East-19 (Harbor Road)", "Route Central-20 (Administrative Loop)"
        ]

        for i in range(1, 21):
            bus = Bus(
                bus_number=f"BUS-{i:03d}",
                route_name=route_names[i - 1],
                driver_name=f"Driver Dave #{i}" if i == 1 else f"Captain Raj #{i}",
                driver_phone=f"+91-9876543{i:03d}",
                current_lat=None,
                current_lng=None,
                speed_kmh=0.0,
                status="Active" if i % 6 != 0 else "Congestion Delay",
                stops_json="[]",
                waypoints_json="[]"
            )
            session.add(bus)
            buses.append(bus)

        await session.flush()

        # 2. Seed Core Demo Users
        password_hash = hash_password("password123")

        # Admin
        admin_user = User(
            public_id=str(uuid.uuid4()),
            name="Sarah Connor",
            email="admin@campus.edu",
            password_hash=password_hash,
            role="admin"
        )
        session.add(admin_user)

        # Faculty (Turing & Smith)
        faculty_user_1 = User(
            public_id=str(uuid.uuid4()),
            name="Prof. Alan Turing",
            email="faculty@campus.edu",
            password_hash=password_hash,
            role="faculty"
        )
        session.add(faculty_user_1)

        faculty_user_2 = User(
            public_id=str(uuid.uuid4()),
            name="Professor Smith",
            email="smith@campus.edu",
            password_hash=password_hash,
            role="faculty"
        )
        session.add(faculty_user_2)

        faculty_user_3 = User(
            public_id=str(uuid.uuid4()),
            name="Prof. Margaret Hamilton",
            email="hamilton@campus.edu",
            password_hash=password_hash,
            role="faculty"
        )
        session.add(faculty_user_3)

        # Parent
        parent_user = User(
            public_id=str(uuid.uuid4()),
            name="Robert Doe",
            email="parent@campus.edu",
            password_hash=password_hash,
            role="parent"
        )
        session.add(parent_user)

        # Student
        student_user = User(
            public_id=str(uuid.uuid4()),
            name="Jane Doe",
            email="student@campus.edu",
            password_hash=password_hash,
            role="student"
        )
        session.add(student_user)

        # Additional Students
        student_user_alex = User(
            public_id=str(uuid.uuid4()),
            name="Alex Smith",
            email="alex@campus.edu",
            password_hash=password_hash,
            role="student"
        )
        session.add(student_user_alex)

        await session.flush()

        # 3. Create Profiles
        # Faculty profiles (with confidential annual_salary)
        fac1 = Faculty(
            user_id=faculty_user_1.id,
            emp_code="FAC-101",
            department="Computer Science",
            designation="Head of Department",
            annual_salary=125000.00
        )
        fac2 = Faculty(
            user_id=faculty_user_2.id,
            emp_code="FAC-102",
            department="Computer Science",
            designation="Associate Professor",
            annual_salary=115000.00
        )
        fac3 = Faculty(
            user_id=faculty_user_3.id,
            emp_code="FAC-103",
            department="Software Engineering",
            designation="Distinguished Professor",
            annual_salary=145000.00
        )
        session.add_all([fac1, fac2, fac3])

        # Parent profile
        parent_profile = Parent(
            user_id=parent_user.id,
            phone="+91-9876500001",
            emergency_contact="+91-9876500002"
        )
        session.add(parent_profile)
        await session.flush()

        # Student profile (Jane Doe linked to Parent Robert Doe and Bus 1)
        student_profile_jane = Student(
            user_id=student_user.id,
            parent_id=parent_profile.id,
            bus_id=buses[0].id,
            roll_number="CS-2023-042",
            department="Computer Science",
            semester=6
        )
        student_profile_alex = Student(
            user_id=student_user_alex.id,
            parent_id=None,
            bus_id=buses[1].id,
            roll_number="CS-2023-088",
            department="Computer Science",
            semester=6
        )
        session.add_all([student_profile_jane, student_profile_alex])
        await session.flush()

        # 4. Attendance Records for Jane Doe
        # Operating Systems: 35/40 (87.5%), DBMS: 37/40 (92.5%), Networks: 31/40 (77.5%), Theory of Computation: 28/40 (70.0% < 75%)
        att1 = Attendance(
            student_id=student_profile_jane.id,
            subject="Operating Systems",
            total_classes=40,
            attended_classes=35,
            attendance_pct=87.5
        )
        att2 = Attendance(
            student_id=student_profile_jane.id,
            subject="Database Management Systems",
            total_classes=40,
            attended_classes=37,
            attendance_pct=92.5
        )
        att3 = Attendance(
            student_id=student_profile_jane.id,
            subject="Computer Networks",
            total_classes=40,
            attended_classes=31,
            attendance_pct=77.5
        )
        att4 = Attendance(
            student_id=student_profile_jane.id,
            subject="Theory of Computation",
            total_classes=40,
            attended_classes=28,
            attendance_pct=70.0
        )
        session.add_all([att1, att2, att3, att4])

        # 5. Seed Institutional Policy Documents & Embeddings
        docs = [
            {
                "title": "Academic Regulations 2026 §4.2: Attendance Requirements & Examination Eligibility",
                "section": "§4.2",
                "content": (
                    "Every enrolled student must maintain a minimum attendance threshold of 75% in each registered course "
                    "to be eligible to appear for the end-semester final university examinations. Students falling between "
                    "65% and 74% due to verified medical emergencies may apply for condonation through the Dean of Academic Affairs. "
                    "Students with attendance below 65% are strictly debarred from sitting in the exam and must repeat the course."
                ),
                "allowed_roles": "student,faculty,parent,admin",
                "department": None
            },
            {
                "title": "Examination Code & Grading Policy 2026",
                "section": "§7.1",
                "content": (
                    "The grading framework follows a standard 10-point scale: A+ (90-100%), A (80-89%), B (70-79%), C (60-69%), "
                    "and F (<60%). Course evaluations are distributed as: Continuous Internal Evaluation (CIE) comprising "
                    "mid-semester exams (30%) and quizzes/assignments (20%), and Semester End Examination (SEE) weighing 50%."
                ),
                "allowed_roles": "student,faculty,parent,admin",
                "department": None
            },
            {
                "title": "SafeTransit Fleet & Student Commute Guidelines",
                "section": "§11.3",
                "content": (
                    "SafeTransit operates daily from 07:00 to 19:30 across 20 designated regional routes. Bus tracking is "
                    "streamed via real-time telemetry markers. RFID boarding confirmation alerts are dispatched to registered "
                    "parent contacts upon stop arrival. Parents receive automatic proximity notifications when the vehicle is "
                    "within 500 meters of their pickup zone."
                ),
                "allowed_roles": "student,faculty,parent,admin",
                "department": None
            },
            {
                "title": "Faculty Compensation & Research Grant Discretionary Fund Guidelines",
                "section": "§18.4",
                "content": (
                    "CONFIDENTIAL / FACULTY ONLY: Faculty annual compensation consists of base academic scale, departmental "
                    "chair stipends, and research publication incentives. Research grant disbursements are capped at $25,000 per "
                    "fiscal annum per principal investigator. This ledger is restricted to accredited faculty and administrative auditors."
                ),
                "allowed_roles": "faculty,admin",
                "department": None
            },
            {
                "title": "Computer Science Faculty Examination Solutions & Answer Keys",
                "section": "CS-KEY-2026",
                "content": (
                    "FACULTY RESTRICTED / CS DEPARTMENT: Master solution key for Operating Systems (OS-301) and DBMS (DB-302) "
                    "mid-semester papers. Question 1 (Banker's Algorithm deadlock avoidance): Safe sequence is <P1, P3, P4, P0, P2>. "
                    "Distribution to unauthorized student accounts constitutes an academic honor violation."
                ),
                "allowed_roles": "faculty,admin",
                "department": "Computer Science"
            },
            {
                "title": "Campus Administrative Security Audit & Master Root Operations",
                "section": "ADM-SEC-01",
                "content": (
                    "RESTRICTED TO SYSTEM ADMINISTRATORS: System audit logs retain security violation markers (EVENT_PRIVILEGE_PROBE) "
                    "for 365 days. Cross-tenant access verification requires active cryptographic JWT signature validation. Database "
                    "failovers execute automated checkpoint reconciliations across write-ahead logs."
                ),
                "allowed_roles": "admin",
                "department": None
            }
        ]

        for d in docs:
            embedding_vec = generate_pseudo_embedding(d["title"] + " " + d["content"])
            doc_record = DocumentEmbedding(
                title=d["title"],
                section=d["section"],
                content=d["content"],
                allowed_roles=d["allowed_roles"],
                department=d["department"],
                embedding_json=json.dumps(embedding_vec)
            )
            session.add(doc_record)

        await session.commit()
        print("Database successfully seeded with demo accounts, buses, attendance, and policies!")
