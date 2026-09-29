import pytest
import datetime
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from app.api.clash import router as clash_router
from app.core.database import (
    Base,
    User,
    Student,
    Faculty,
    CourseOffering,
    Assessment,
    get_db_session,
)
from app.core.datetime_utils import utcnow, to_iso_z
from app.models.schemas import UserSecurityClaims
from app.api.auth import get_current_user_claims

e2e_app = FastAPI()
e2e_app.include_router(clash_router, prefix="/api/v1")

@pytest.fixture
async def demo_env():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    now = utcnow()
    base_day = now.date() + datetime.timedelta(days=1)

    async with async_session() as session:
        # Users
        u_admin = User(public_id="u_admin", name="Campus Admin", email="admin@campus.edu", password_hash="h", role="admin")
        u_smith = User(public_id="u_smith", name="Professor Smith", email="smith@campus.edu", password_hash="h", role="faculty")
        u_turing = User(public_id="u_turing", name="Prof. Alan Turing", email="turing@campus.edu", password_hash="h", role="faculty")
        u_hod = User(public_id="u_hod", name="Prof. Dave (HOD)", email="prof.dave@campus.edu", password_hash="h", role="faculty")
        u_jane = User(public_id="u_jane", name="Jane Doe", email="student@campus.edu", password_hash="h", role="student")
        u_alex = User(public_id="u_alex", name="Alex Smith", email="alex@campus.edu", password_hash="h", role="student")

        session.add_all([u_admin, u_smith, u_turing, u_hod, u_jane, u_alex])
        await session.flush()

        # Faculty profiles
        f_smith = Faculty(user_id=u_smith.id, emp_code="FAC-102", department="Computer Science", designation="Associate Professor", annual_salary=115000.0)
        f_turing = Faculty(user_id=u_turing.id, emp_code="FAC-104", department="Computer Science", designation="Assistant Professor", annual_salary=95000.0)
        f_hod = Faculty(user_id=u_hod.id, emp_code="FAC-HOD", department="Computer Science", designation="Head of Department", annual_salary=135000.0)

        # Students: Jane (Section A), Alex (Section B)
        s_jane = Student(user_id=u_jane.id, roll_number="CS-2023-042", department="Computer Science", semester=6, section="Section A")
        s_alex = Student(user_id=u_alex.id, roll_number="CS-2023-088", department="Computer Science", semester=6, section="Section B")

        session.add_all([f_smith, f_turing, f_hod, s_jane, s_alex])
        await session.flush()

        # Offerings
        # Cloud Computing (Sections A & B taught by Prof. Smith)
        off_cc_a = CourseOffering(course_code="CS-401", subject="Cloud Computing", section="Section A", semester=6, department="Computer Science", faculty_id=f_smith.id)
        off_cc_b = CourseOffering(course_code="CS-401", subject="Cloud Computing", section="Section B", semester=6, department="Computer Science", faculty_id=f_smith.id)
        # Advanced Compilers (Section A only taught by Prof. Turing)
        off_comp = CourseOffering(course_code="CS-505", subject="Advanced Compilers", section="Section A", semester=6, department="Computer Science", faculty_id=f_turing.id)

        session.add_all([off_cc_a, off_cc_b, off_comp])
        await session.flush()

        # Assessments
        # Cloud Computing Section A: base_day 10:00 - 12:00
        exam_cc_a = Assessment(
            offering_id=off_cc_a.id,
            kind="Midterm Examination",
            start_at=datetime.datetime.combine(base_day, datetime.time(10, 0)),
            end_at=datetime.datetime.combine(base_day, datetime.time(12, 0)),
            venue="Lab 101",
        )
        # Cloud Computing Section B: base_day + 1 10:00 - 12:00 (Alternative slot!)
        exam_cc_b = Assessment(
            offering_id=off_cc_b.id,
            kind="Midterm Examination",
            start_at=datetime.datetime.combine(base_day + datetime.timedelta(days=1), datetime.time(10, 0)),
            end_at=datetime.datetime.combine(base_day + datetime.timedelta(days=1), datetime.time(12, 0)),
            venue="Lab 102",
        )
        # Advanced Compilers Section A: base_day 14:00 - 16:00
        exam_comp = Assessment(
            offering_id=off_comp.id,
            kind="Midterm Examination",
            start_at=datetime.datetime.combine(base_day, datetime.time(14, 0)),
            end_at=datetime.datetime.combine(base_day, datetime.time(16, 0)),
            venue="Lecture Hall A",
        )

        session.add_all([exam_cc_a, exam_cc_b, exam_comp])
        await session.commit()

        seed_data = {
            "admin_user": u_admin,
            "smith_user": u_smith,
            "turing_user": u_turing,
            "hod_user": u_hod,
            "jane_user": u_jane,
            "jane_student": s_jane,
            "f_smith": f_smith,
            "f_turing": f_turing,
            "f_hod": f_hod,
            "exam_cc_b": exam_cc_b,
            "base_day": base_day,
        }

    claims_map = {
        "admin": UserSecurityClaims(user_id=seed_data["admin_user"].id, public_id="u_admin", role="admin", email="admin@campus.edu", name="Campus Admin"),
        "smith": UserSecurityClaims(user_id=seed_data["smith_user"].id, public_id="u_smith", role="faculty", email="smith@campus.edu", name="Professor Smith", department="Computer Science", faculty_id=seed_data["f_smith"].id, is_hod=False),
        "turing": UserSecurityClaims(user_id=seed_data["turing_user"].id, public_id="u_turing", role="faculty", email="turing@campus.edu", name="Prof. Alan Turing", department="Computer Science", faculty_id=seed_data["f_turing"].id, is_hod=False),
        "hod": UserSecurityClaims(user_id=seed_data["hod_user"].id, public_id="u_hod", role="faculty", email="prof.dave@campus.edu", name="Prof. Dave (HOD)", department="Computer Science", faculty_id=seed_data["f_hod"].id, is_hod=True),
        "jane": UserSecurityClaims(user_id=seed_data["jane_user"].id, public_id="u_jane", role="student", email="student@campus.edu", name="Jane Doe", student_id=seed_data["jane_student"].id),
    }

    async def override_get_db():
        async with async_session() as session:
            yield session

    current_role_claim = [claims_map["admin"]]

    async def override_claims():
        return current_role_claim[0]

    e2e_app.dependency_overrides[get_db_session] = override_get_db
    e2e_app.dependency_overrides[get_current_user_claims] = override_claims

    yield {
        "claims_map": claims_map,
        "current_role_claim": current_role_claim,
        "seed_data": seed_data,
    }

    e2e_app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.mark.asyncio
async def test_demo_rehearsal_full_lifecycle(demo_env):
    """
    Demo Rehearsal Test:
    1. Admin creates event.
    2. Admin adds participant (Jane Doe).
    3. Clashes appear (2 clashes: Cloud Computing & Advanced Compilers).
    4. Admin files both clash requests (status -> REQUEST_FILED).
    5. Professor Smith approves Case 1 (accepts suggested retake in Section B).
    6. Professor Turing rejects Case 2 (mandatory reason -> auto-escalates to ESCALATED_TO_HOD).
    7. HOD Dave reviews department overview and overrides Case 2 (assigns custom slot).
    8. Student Jane Doe inspects My Clashes and verifies both cases are APPROVED with full timelines.
    """
    claims = demo_env["claims_map"]
    current_role = demo_env["current_role_claim"]
    seed = demo_env["seed_data"]
    base_day = seed["base_day"]

    transport = ASGITransport(app=e2e_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1: Admin creates event
        current_role[0] = claims["admin"]
        event_resp = await client.post(
            "/api/v1/clash/events",
            json={
                "title": "Smart Campus Hackathon 2026",
                "description": "24h Inter-college hackathon",
                "start_at": to_iso_z(datetime.datetime.combine(base_day, datetime.time(9, 0))),
                "end_at": to_iso_z(datetime.datetime.combine(base_day, datetime.time(18, 0))),
            },
        )
        assert event_resp.status_code == 200
        event_id = event_resp.json()["id"]

        # Step 2: Admin adds participant (Jane Doe)
        part_resp = await client.post(
            f"/api/v1/clash/events/{event_id}/participants",
            json={"student_ids": [seed["jane_student"].id]},
        )
        assert part_resp.status_code == 200
        assert part_resp.json()["clashes_count"] == 2

        # Step 3: Admin inspects the clashes that appeared
        event_detail = await client.get(f"/api/v1/clash/events/{event_id}")
        assert event_detail.status_code == 200
        clashes = event_detail.json()["clashes"]
        assert len(clashes) == 2

        # Sort by subject
        case_cc = next(c for c in clashes if c["subject"] == "Cloud Computing")
        case_comp = next(c for c in clashes if c["subject"] == "Advanced Compilers")

        assert case_cc["status"] == "DETECTED"
        assert case_cc["suggested_retake_assessment_id"] == seed["exam_cc_b"].id, "Expected Section B exam suggested as retake"

        assert case_comp["status"] == "DETECTED"
        assert case_comp["suggested_retake_assessment_id"] is None, "Expected None because single section offering"

        # Step 4: Admin files both clash requests (bulk)
        file_resp = await client.post(
            "/api/v1/clash/cases/file",
            json={"case_ids": [case_cc["id"], case_comp["id"]]},
        )
        assert file_resp.status_code == 200
        filed_cases = file_resp.json()
        assert all(c["status"] == "REQUEST_FILED" for c in filed_cases)

        # Step 5: Professor Smith approves Case 1 (accepts suggested retake slot)
        current_role[0] = claims["smith"]
        approve_resp = await client.post(
            "/api/v1/clash/cases/decision",
            json={
                "case_ids": [case_cc["id"]],
                "decision": "approve",
                "note": "Approved to take midterm with Section B on Thursday",
            },
        )
        assert approve_resp.status_code == 200
        assert approve_resp.json()[0]["status"] == "APPROVED"
        assert approve_resp.json()[0]["retake_assessment_id"] == seed["exam_cc_b"].id

        # Step 6: Professor Turing rejects Case 2 -> auto-escalates to ESCALATED_TO_HOD
        current_role[0] = claims["turing"]
        reject_resp = await client.post(
            "/api/v1/clash/cases/decision",
            json={
                "case_ids": [case_comp["id"]],
                "decision": "reject",
                "rejection_reason": "No makeup examination permitted under course guidelines",
            },
        )
        assert reject_resp.status_code == 200
        escalated_case = reject_resp.json()[0]
        assert escalated_case["status"] == "ESCALATED_TO_HOD"
        assert escalated_case["rejection_reason"] == "No makeup examination permitted under course guidelines"

        # Step 7: HOD Dave checks overview and overrides Case 2
        current_role[0] = claims["hod"]
        hod_overview = await client.get("/api/v1/clash/hod/overview")
        assert hod_overview.status_code == 200
        overview_data = hod_overview.json()
        assert len(overview_data["escalated_cases"]) == 1
        assert overview_data["escalated_cases"][0]["id"] == case_comp["id"]

        # HOD assigns custom slot override
        override_time = to_iso_z(datetime.datetime.combine(base_day + datetime.timedelta(days=3), datetime.time(11, 0)))
        override_resp = await client.post(
            f"/api/v1/clash/cases/{case_comp['id']}/override",
            json={
                "custom_at": override_time,
                "note": "Granted exception per college hackathon participation directive",
            },
        )
        assert override_resp.status_code == 200
        overridden = override_resp.json()
        assert overridden["status"] == "APPROVED"
        assert overridden["retake_at"] == override_time

        # Step 8: Student Jane Doe sees the final status of her clashes
        current_role[0] = claims["jane"]
        student_cases = await client.get("/api/v1/clash/cases")
        assert student_cases.status_code == 200
        cases_list = student_cases.json()
        assert len(cases_list) == 2
        assert all(c["status"] == "APPROVED" for c in cases_list)

        # Inspect full timeline for the HOD-overridden case
        comp_detail = await client.get(f"/api/v1/clash/cases/{case_comp['id']}")
        assert comp_detail.status_code == 200
        timeline_entries = comp_detail.json()["timeline"]
        timeline_statuses = [t["to_status"] for t in timeline_entries]
        assert timeline_statuses == ["DETECTED", "REQUEST_FILED", "REJECTED", "ESCALATED_TO_HOD", "APPROVED"]

        # Verify notifications were created for Jane Doe
        notifs_resp = await client.get("/api/v1/clash/notifications")
        assert notifs_resp.status_code == 200
        notifs = notifs_resp.json()
        assert len(notifs) >= 2
