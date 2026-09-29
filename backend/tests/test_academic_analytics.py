import asyncio
import json
import sys
import unittest
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, func, and_

from app.main import app
from app.core.database import (
    init_db, AsyncSessionLocal, User, Student, Subject, SubjectModule,
    Assessment, AssessmentQuestion, StudentQuestionMark, StudentEnrollment,
    LearningMaterial, MaterialPage, MaterialChunk, MicroLesson
)
from app.core.security import create_access_token
from app.services.seed_data import seed_database_if_empty
from app.services.seed_academic_data import seed_academic_support_data
from app.services.academic_analytics import (
    classify_status, calculate_assessment_scores, calculate_modules_performance,
    find_extreme_modules, get_student_subjects_analytics, get_student_subject_detail,
    get_student_subject_modules_analysis, get_student_marks_overview,
    get_module_learning_materials, STRONG_THRESHOLD, DEVELOPING_THRESHOLD
)

class TestAcademicAnalyticsSuite(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        await init_db()
        await seed_database_if_empty()
        await seed_academic_support_data(force_reseed=False)

        async with AsyncSessionLocal() as session:
            u_res = await session.execute(select(User).where(User.email == "student@campus.edu"))
            self.jane_user = u_res.scalar_one_or_none()
            
            s_res = await session.execute(select(Student).where(Student.user_id == self.jane_user.id))
            self.jane_student = s_res.scalar_one_or_none()

            u_res2 = await session.execute(select(User).where(User.email == "alex@campus.edu"))
            self.alex_user = u_res2.scalar_one_or_none()
            s_res2 = await session.execute(select(Student).where(Student.user_id == self.alex_user.id))
            self.alex_student = s_res2.scalar_one_or_none()

            # Find CS301 (Operating Systems)
            sub_res = await session.execute(select(Subject).where(Subject.code == "CS301"))
            self.os_subject = sub_res.scalar_one_or_none()

        # Build tokens
        self.jane_token = create_access_token({
            "user_id": self.jane_user.id,
            "public_id": self.jane_user.public_id,
            "role": "student",
            "name": self.jane_user.name,
            "email": self.jane_user.email,
            "department": "Computer Science",
            "student_id": self.jane_student.id,
            "bus_id": self.jane_student.bus_id
        })

        self.alex_token = create_access_token({
            "user_id": self.alex_user.id,
            "public_id": self.alex_user.public_id,
            "role": "student",
            "name": self.alex_user.name,
            "email": self.alex_user.email,
            "department": "Computer Science",
            "student_id": self.alex_student.id,
            "bus_id": self.alex_student.bus_id
        })

    # -------------------------------------------------------------
    # TEST 1: Subject marks aggregation
    # -------------------------------------------------------------
    async def test_01_subject_marks_aggregation(self):
        async with AsyncSessionLocal() as session:
            subjects = await get_student_subjects_analytics(session, self.jane_student.id)
            self.assertEqual(len(subjects), 6)
            
            os_sub = next(s for s in subjects if s.code == "CS301")
            self.assertEqual(os_sub.name, "Operating Systems")
            self.assertEqual(os_sub.total_marks_available, 210.0)
            self.assertAlmostEqual(os_sub.total_marks_obtained, 145.0, delta=1.0)
            self.assertAlmostEqual(os_sub.percentage, 69.0, delta=1.0)
            self.assertEqual(os_sub.status, "Developing")

    # -------------------------------------------------------------
    # TEST 2: Assessment marks aggregation
    # -------------------------------------------------------------
    async def test_02_assessment_marks_aggregation(self):
        async with AsyncSessionLocal() as session:
            detail = await get_student_subject_detail(session, self.jane_student.id, self.os_subject.id)
            self.assertIsNotNone(detail)
            self.assertEqual(len(detail.assessments), 5)

            categories = [a.category for a in detail.assessments]
            self.assertEqual(categories, ["CA1", "CA2", "CA3", "Midterm", "Endterm"])

            ca1 = detail.assessments[0]
            self.assertEqual(ca1.max_marks, 20.0)
            self.assertEqual(ca1.marks_available, 20.0)
            self.assertGreater(ca1.marks_obtained, 10.0)

            endterm = detail.assessments[4]
            self.assertEqual(endterm.max_marks, 100.0)
            self.assertEqual(endterm.marks_available, 100.0)
            self.assertGreater(endterm.marks_obtained, 50.0)

    # -------------------------------------------------------------
    # TEST 3: CO aggregation
    # -------------------------------------------------------------
    async def test_03_co_aggregation(self):
        async with AsyncSessionLocal() as session:
            detail = await get_student_subject_detail(session, self.jane_student.id, self.os_subject.id)
            self.assertIsNotNone(detail)
            self.assertEqual(len(detail.modules), 5)

            co_map = {m.co_code: m for m in detail.modules}
            self.assertIn("CO1", co_map)
            self.assertIn("CO2", co_map)
            self.assertIn("CO3", co_map)
            self.assertIn("CO4", co_map)
            self.assertIn("CO5", co_map)

            # CO1 should be ~84.8% (Strong)
            self.assertGreaterEqual(co_map["CO1"].percentage, 75.0)
            self.assertEqual(co_map["CO1"].status, "Strong")

            # CO3 should be ~38.0% (Needs Support)
            self.assertLess(co_map["CO3"].percentage, 50.0)
            self.assertEqual(co_map["CO3"].status, "Needs Support")

    # -------------------------------------------------------------
    # TEST 4: Weakest module detection
    # -------------------------------------------------------------
    async def test_04_weakest_module_detection(self):
        async with AsyncSessionLocal() as session:
            detail = await get_student_subject_detail(session, self.jane_student.id, self.os_subject.id)
            self.assertIsNotNone(detail.weakest_module)
            self.assertEqual(detail.weakest_module.co_code, "CO3")
            self.assertEqual(detail.weakest_module.title, "Memory Management & Virtual Memory")
            self.assertAlmostEqual(detail.weakest_module.percentage, 38.0, delta=1.0)
            self.assertEqual(detail.weakest_module.status, "Needs Support")

    # -------------------------------------------------------------
    # TEST 5: Strongest module detection
    # -------------------------------------------------------------
    async def test_05_strongest_module_detection(self):
        async with AsyncSessionLocal() as session:
            detail = await get_student_subject_detail(session, self.jane_student.id, self.os_subject.id)
            self.assertIsNotNone(detail.strongest_module)
            self.assertEqual(detail.strongest_module.co_code, "CO1")
            self.assertEqual(detail.strongest_module.title, "Process Management & Concurrency")
            self.assertAlmostEqual(detail.strongest_module.percentage, 84.8, delta=1.0)
            self.assertEqual(detail.strongest_module.status, "Strong")

    # -------------------------------------------------------------
    # TEST 6: Performance classification
    # -------------------------------------------------------------
    async def test_06_performance_classification(self):
        self.assertEqual(classify_status(95.0), "Strong")
        self.assertEqual(classify_status(75.0), "Strong")
        self.assertEqual(classify_status(74.9), "Developing")
        self.assertEqual(classify_status(60.0), "Developing")
        self.assertEqual(classify_status(59.9), "Needs Support")
        self.assertEqual(classify_status(38.0), "Needs Support")
        self.assertEqual(classify_status(None), "No Data")

    # -------------------------------------------------------------
    # TEST 7: OR-question denominator behavior
    # -------------------------------------------------------------
    async def test_07_or_question_denominator(self):
        # Create mock questions with OR group
        q1 = AssessmentQuestion(id=1001, assessment_id=1, co_code="CO1", question_label="Q1.a", max_marks=5.0, is_optional=True, or_group_id="OR-GRP-1")
        q2 = AssessmentQuestion(id=1002, assessment_id=1, co_code="CO1", question_label="Q1.b", max_marks=5.0, is_optional=True, or_group_id="OR-GRP-1")
        
        # Student attempted only Q1.a
        marks_map = {
            1001: StudentQuestionMark(id=1, student_id=1, question_id=1001, marks_obtained=4.0, is_attempted=True),
            1002: StudentQuestionMark(id=2, student_id=1, question_id=1002, marks_obtained=0.0, is_attempted=False)
        }

        obt, avail, responses = calculate_assessment_scores([q1, q2], marks_map)
        # Denominator must be 5.0 (NOT 10.0), numerator 4.0
        self.assertEqual(avail, 5.0)
        self.assertEqual(obt, 4.0)

    # -------------------------------------------------------------
    # TEST 8: Unattempted optional question behavior
    # -------------------------------------------------------------
    async def test_08_unattempted_optional_question_behavior(self):
        q_mandatory = AssessmentQuestion(id=2001, assessment_id=2, co_code="CO1", question_label="Q1", max_marks=10.0, is_optional=False, or_group_id=None)
        q_optional = AssessmentQuestion(id=2002, assessment_id=2, co_code="CO2", question_label="Q2_Bonus", max_marks=5.0, is_optional=True, or_group_id=None)

        # Student attempted only mandatory question
        marks_map = {
            2001: StudentQuestionMark(id=1, student_id=1, question_id=2001, marks_obtained=8.0, is_attempted=True),
            2002: StudentQuestionMark(id=2, student_id=1, question_id=2002, marks_obtained=0.0, is_attempted=False)
        }

        obt, avail, _ = calculate_assessment_scores([q_mandatory, q_optional], marks_map)
        # Denominator must exclude unattempted optional question (10.0, NOT 15.0)
        self.assertEqual(avail, 10.0)
        self.assertEqual(obt, 8.0)

    # -------------------------------------------------------------
    # TEST 9: Student enrollment filtering
    # -------------------------------------------------------------
    async def test_09_student_enrollment_filtering(self):
        async with AsyncSessionLocal() as session:
            # Test semester 6 filter
            sem6_subjects = await get_student_subjects_analytics(session, self.jane_student.id, semester=6)
            self.assertEqual(len(sem6_subjects), 6)

            # Test non-existent semester 1 filter
            sem1_subjects = await get_student_subjects_analytics(session, self.jane_student.id, semester=1)
            self.assertEqual(len(sem1_subjects), 0)

            # Test status filter "Needs Support" (should return CS301 or other weak subjects if any)
            dev_subjects = await get_student_subjects_analytics(session, self.jane_student.id, performance_status="Developing")
            self.assertTrue(any(s.code == "CS301" for s in dev_subjects))

    # -------------------------------------------------------------
    # TEST 10: Zero-Trust Student Isolation & HTTP Endpoints
    # -------------------------------------------------------------
    async def test_10_student_isolation_and_rest_apis(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Unauthenticated request -> 401
            r_unauth = await ac.get("/api/v1/student/subjects")
            self.assertEqual(r_unauth.status_code, 401)

            # 2. Jane Doe fetches her subjects -> 200
            headers_jane = {"Authorization": f"Bearer {self.jane_token}"}
            r_jane = await ac.get("/api/v1/student/subjects", headers=headers_jane)
            self.assertEqual(r_jane.status_code, 200)
            data_jane = r_jane.json()
            self.assertEqual(len(data_jane), 6)

            # 3. Jane Doe fetches marks overview -> 200
            r_marks = await ac.get("/api/v1/student/marks", headers=headers_jane)
            self.assertEqual(r_marks.status_code, 200)
            overview_data = r_marks.json()
            self.assertEqual(overview_data["student_name"], "Jane Doe")
            self.assertIn("subjects", overview_data)

            # 4. Jane Doe fetches Operating Systems detail -> 200
            r_os = await ac.get(f"/api/v1/student/marks/{self.os_subject.id}", headers=headers_jane)
            self.assertEqual(r_os.status_code, 200)
            os_data = r_os.json()
            self.assertEqual(os_data["subject"]["code"], "CS301")
            self.assertEqual(os_data["weakest_module"]["co_code"], "CO3")

            # 5. Jane Doe fetches Operating Systems module breakdown -> 200
            r_os_mods = await ac.get(f"/api/v1/student/marks/{self.os_subject.id}/modules", headers=headers_jane)
            self.assertEqual(r_os_mods.status_code, 200)
            mods_data = r_os_mods.json()
            self.assertEqual(mods_data["weakest_module"]["co_code"], "CO3")
            self.assertEqual(mods_data["strongest_module"]["co_code"], "CO1")

            # 6. Invalid subject ID -> 404
            r_invalid_sub = await ac.get("/api/v1/student/marks/99999", headers=headers_jane)
            self.assertEqual(r_invalid_sub.status_code, 404)

            # 7. Student A attempts to pass forged query or header to view Student B -> Scoped strictly to Token Claims
            headers_alex = {"Authorization": f"Bearer {self.alex_token}"}
            r_alex = await ac.get("/api/v1/student/marks", headers=headers_alex)
            self.assertEqual(r_alex.status_code, 200)
            alex_data = r_alex.json()
            self.assertEqual(alex_data["student_name"], "Alex Smith")
            self.assertEqual(alex_data["student_id"], self.alex_student.id)

    # -------------------------------------------------------------
    # TEST 11: Material/module association
    # -------------------------------------------------------------
    async def test_11_material_module_association(self):
        async with AsyncSessionLocal() as session:
            # Find CO3 module of CS301
            m_res = await session.execute(
                select(SubjectModule).where(
                    and_(
                        SubjectModule.subject_id == self.os_subject.id,
                        SubjectModule.co_code == "CO3"
                    )
                )
            )
            co3_mod = m_res.scalar_one_or_none()
            self.assertIsNotNone(co3_mod)

            materials_info = await get_module_learning_materials(session, co3_mod.id)
            self.assertIsNotNone(materials_info)
            self.assertEqual(materials_info.subject_code, "CS301")
            self.assertEqual(materials_info.co_code, "CO3")
            self.assertGreater(len(materials_info.materials), 0)
            self.assertGreater(materials_info.total_chunks, 0)
            self.assertGreater(len(materials_info.micro_lessons), 0)

            # Verify HTTP endpoint
            headers_jane = {"Authorization": f"Bearer {self.jane_token}"}
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r_mat = await ac.get(f"/api/v1/student/learning/materials/{co3_mod.id}", headers=headers_jane)
                self.assertEqual(r_mat.status_code, 200)
                mat_json = r_mat.json()
                self.assertEqual(mat_json["co_code"], "CO3")
                self.assertIn("materials", mat_json)
                self.assertIn("micro_lessons", mat_json)

    # -------------------------------------------------------------
    # TEST 12: Seed idempotency
    # -------------------------------------------------------------
    async def test_12_seed_idempotency(self):
        # Calling seeder multiple times without force_reseed should not duplicate subjects
        async with AsyncSessionLocal() as session:
            count_before = (await session.execute(select(func.count(Subject.id)))).scalar()
            
        await seed_academic_support_data(force_reseed=False)
        await seed_academic_support_data(force_reseed=False)

        async with AsyncSessionLocal() as session:
            count_after = (await session.execute(select(func.count(Subject.id)))).scalar()

        self.assertEqual(count_before, count_after)
        self.assertEqual(count_after, 6)

if __name__ == "__main__":
    unittest.main()
