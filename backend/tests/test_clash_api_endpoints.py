import pytest
import datetime
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from fastapi import FastAPI
from app.api.clash import router as clash_router
from app.core.database import (
    Base,
    User,
    Student,
    Faculty,
    Event,
    CourseOffering,
    Assessment,
    ClashCase,
    get_db_session,
)
from app.core.datetime_utils import utcnow, to_iso_z
from app.models.schemas import UserSecurityClaims
from app.api.auth import get_current_user_claims

isolated_app = FastAPI()
isolated_app.include_router(clash_router, prefix="/api/v1")

@pytest.fixture
async def api_env():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    now = utcnow()
    async with async_session() as session:
        # Create users & seed
        u_admin = User(public_id="u_adm", name="Admin User", email="admin@nexusedu.com", password_hash="h", role="admin")
        u_prof = User(public_id="u_prof", name="Prof Test", email="prof@nexusedu.com", password_hash="h", role="faculty")
        u_hod = User(public_id="u_hod", name="HOD Test", email="hod@nexusedu.com", password_hash="h", role="faculty")
        u_stud = User(public_id="u_stud", name="Student Test", email="stud@nexusedu.com", password_hash="h", role="student")
        session.add_all([u_admin, u_prof, u_hod, u_stud])
        await session.flush()

        f_prof = Faculty(user_id=u_prof.id, emp_code="FAC_T", department="Computer Science", designation="Associate Professor", annual_salary=80000.0)
        f_hod = Faculty(user_id=u_hod.id, emp_code="HOD_T", department="Computer Science", designation="Head of Department", annual_salary=120000.0)
        s_stud = Student(user_id=u_stud.id, roll_number="CS-T01", department="Computer Science", semester=6, section="Section A")
        session.add_all([f_prof, f_hod, s_stud])
        await session.flush()

        offering = CourseOffering(
            course_code="CS-501",
            subject="Distributed Systems",
            section="Section A",
            semester=6,
            department="Computer Science",
            faculty_id=f_prof.id,
        )
        session.add(offering)
        await session.flush()

        exam = Assessment(
            offering_id=offering.id,
            kind="midterm",
            start_at=now + datetime.timedelta(days=1, hours=10),
            end_at=now + datetime.timedelta(days=1, hours=12),
            venue="Hall 1",
        )
        session.add(exam)
        await session.commit()

        seed_data = {
            "admin_user": u_admin,
            "prof_user": u_prof,
            "hod_user": u_hod,
            "student_user": u_stud,
            "student": s_stud,
            "faculty": f_prof,
            "hod_faculty": f_hod,
            "offering": offering,
            "assessment": exam,
        }

    claims_map = {
        "admin": UserSecurityClaims(user_id=seed_data["admin_user"].id, public_id="u_adm", role="admin", email="admin@nexusedu.com", name="Admin User"),
        "prof": UserSecurityClaims(user_id=seed_data["prof_user"].id, public_id="u_prof", role="faculty", email="prof@nexusedu.com", name="Prof Test", department="Computer Science", faculty_id=seed_data["faculty"].id, is_hod=False),
        "hod": UserSecurityClaims(user_id=seed_data["hod_user"].id, public_id="u_hod", role="faculty", email="hod@nexusedu.com", name="HOD Test", department="Computer Science", faculty_id=seed_data["hod_faculty"].id, is_hod=True),
        "student": UserSecurityClaims(user_id=seed_data["student_user"].id, public_id="u_stud", role="student", email="stud@nexusedu.com", name="Student Test", student_id=seed_data["student"].id),
    }

    async def override_get_db():
        async with async_session() as session:
            yield session

    current_role_claim = [claims_map["admin"]]

    async def override_claims():
        return current_role_claim[0]

    isolated_app.dependency_overrides[get_db_session] = override_get_db
    isolated_app.dependency_overrides[get_current_user_claims] = override_claims

    yield {
        "claims_map": claims_map,
        "current_role_claim": current_role_claim,
        "seed_data": seed_data,
        "engine": engine,
    }

    isolated_app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.mark.asyncio
async def test_api_event_and_clash_lifecycle(api_env):
    claims_map = api_env["claims_map"]
    current_role = api_env["current_role_claim"]
    seed = api_env["seed_data"]
    now = utcnow()

    transport = ASGITransport(app=isolated_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Admin creates event
        current_role[0] = claims_map["admin"]
        event_resp = await client.post(
            "/api/v1/clash/events",
            json={
                "title": "Annual Tech Symposium",
                "description": "Coding and robotics event",
                "start_at": to_iso_z(now + datetime.timedelta(days=1, hours=9)),
                "end_at": to_iso_z(now + datetime.timedelta(days=1, hours=15)),
            },
        )
        assert event_resp.status_code == 200
        event_data = event_resp.json()
        event_id = event_data["id"]

        # 2. Admin adds participant (triggers clash detection)
        part_resp = await client.post(
            f"/api/v1/clash/events/{event_id}/participants",
            json={"student_ids": [seed["student"].id]},
        )
        assert part_resp.status_code == 200
        assert part_resp.json()["clashes_count"] == 1

        # 3. Student views their clashes
        current_role[0] = claims_map["student"]
        student_cases_resp = await client.get("/api/v1/clash/cases")
        assert student_cases_resp.status_code == 200
        cases = student_cases_resp.json()
        assert len(cases) == 1
        case_id = cases[0]["id"]
        assert cases[0]["status"] == "DETECTED"

        # 4. Admin files the clash request
        current_role[0] = claims_map["admin"]
        file_resp = await client.post(
            "/api/v1/clash/cases/file",
            json={"case_ids": [case_id]},
        )
        assert file_resp.status_code == 200
        assert file_resp.json()[0]["status"] == "REQUEST_FILED"

        # 5. Professor rejects with reason -> Auto-escalates to HOD
        current_role[0] = claims_map["prof"]
        reject_resp = await client.post(
            "/api/v1/clash/cases/decision",
            json={
                "case_ids": [case_id],
                "decision": "reject",
                "rejection_reason": "No makeup exams permitted per syllabus",
            },
        )
        assert reject_resp.status_code == 200
        escalated_case = reject_resp.json()[0]
        assert escalated_case["status"] == "ESCALATED_TO_HOD"
        assert escalated_case["rejection_reason"] == "No makeup exams permitted per syllabus"

        # 6. HOD checks department overview
        current_role[0] = claims_map["hod"]
        hod_overview_resp = await client.get("/api/v1/clash/hod/overview")
        assert hod_overview_resp.status_code == 200
        overview = hod_overview_resp.json()
        assert overview["department"] == "Computer Science"
        assert len(overview["escalated_cases"]) == 1
        assert overview["counts_by_status"].get("ESCALATED_TO_HOD") == 1

        # 7. HOD overrides rejection -> APPROVED
        override_time = to_iso_z(now + datetime.timedelta(days=4, hours=10))
        override_resp = await client.post(
            f"/api/v1/clash/cases/{case_id}/override",
            json={
                "custom_at": override_time,
                "note": "Exemption granted for official college symposium",
            },
        )
        assert override_resp.status_code == 200
        approved_case = override_resp.json()
        assert approved_case["status"] == "APPROVED"
        assert approved_case["retake_at"] == override_time

        # 8. Professor or Admin marks completed
        current_role[0] = claims_map["prof"]
        comp_resp = await client.post(f"/api/v1/clash/cases/{case_id}/complete")
        assert comp_resp.status_code == 200
        assert comp_resp.json()["status"] == "COMPLETED"

        # 9. Case detail endpoint shows full timeline
        detail_resp = await client.get(f"/api/v1/clash/cases/{case_id}")
        assert detail_resp.status_code == 200
        case_detail = detail_resp.json()
        timeline = case_detail["timeline"]
        statuses = [t["to_status"] for t in timeline]
        assert "DETECTED" in statuses
        assert "REQUEST_FILED" in statuses
        assert "REJECTED" in statuses
        assert "ESCALATED_TO_HOD" in statuses
        assert "APPROVED" in statuses
        assert "COMPLETED" in statuses
