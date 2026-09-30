"""
Automated Test Suite for Universal YouTube Discovery & Related Lecture System.
Tests provider hierarchy, deterministic search URLs, 30-module coverage, and RAG integration.
"""

import unittest
import asyncio
from app.core.database import AsyncSessionLocal, init_db, Subject, SubjectModule
from app.services.seed_academic_data import seed_academic_support_data
from app.services.youtube_service import (
    resolve_youtube_resource, build_academic_search_query,
    build_youtube_search_url, AcademicTopicContext
)
from app.services.academic_rag import generate_grounded_microlesson
from app.models.schemas import UserSecurityClaims, AcademicExplainRequest
from sqlalchemy import select

class TestUniversalYouTubeSuite(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        await init_db()
        await seed_academic_support_data()
        self.session = AsyncSessionLocal()

        self.student_claims = UserSecurityClaims(
            user_id=1,
            public_id="usr_student_jane",
            role="student",
            name="Jane Doe",
            email="student@nexuxedu.com",
            department="Computer Science",
            student_id=1
        )

    async def asyncTearDown(self):
        await self.session.close()

    # --- Test 1: Academic Query Builder ---
    def test_academic_search_query_builder(self):
        ctx = AcademicTopicContext(
            subject_code="CS301",
            subject_name="Operating Systems",
            module_title="Memory Management & Virtual Memory",
            topic="Translation Lookaside Buffer TLB Hit Ratio"
        )
        query = build_academic_search_query(ctx)
        self.assertIn("CS301", query)
        self.assertIn("Operating", query)
        self.assertIn("Memory", query)
        self.assertIn("TLB", query)

        url = build_youtube_search_url(query)
        self.assertTrue(url.startswith("https://www.youtube.com/results?search_query="))
        self.assertIn("CS301", url)

    # --- Test 2: Full Curriculum Coverage (30/30 Modules) ---
    async def test_all_30_modules_yield_valid_youtube_resources(self):
        """Every module across all 6 subjects must resolve a valid, non-null YouTubeResource."""
        subjs_res = await self.session.execute(select(Subject))
        subjects = subjs_res.scalars().all()
        self.assertEqual(len(subjects), 6, "Must have 6 academic subjects")

        total_modules_tested = 0
        for subj in subjects:
            mods_res = await self.session.execute(select(SubjectModule).where(SubjectModule.subject_id == subj.id))
            modules = mods_res.scalars().all()
            self.assertEqual(len(modules), 5, f"Subject {subj.code} must have 5 modules")

            for mod in modules:
                yt = await resolve_youtube_resource(
                    subject_code=subj.code,
                    subject_name=subj.name,
                    module_code=mod.co_code,
                    module_title=mod.title,
                    topic=f"{mod.title} fundamentals"
                )
                self.assertIsNotNone(yt, f"Failed resolving YouTube for {subj.code} {mod.co_code}")
                self.assertIsNotNone(yt.search_url, f"Missing search URL for {subj.code} {mod.co_code}")
                self.assertTrue(yt.search_url.startswith("https://www.youtube.com/results?search_query="))
                self.assertIsNotNone(yt.search_query)
                self.assertGreater(len(yt.search_query), 5)
                total_modules_tested += 1

        self.assertEqual(total_modules_tested, 30, "All 30 modules must be tested and valid")

    # --- Test 3: Curated Resource Resolution ---
    async def test_curated_resource_resolution(self):
        """Known core topics return embeddable videos with start/end timestamps."""
        yt_tlb = await resolve_youtube_resource(
            subject_code="CS301",
            subject_name="Operating Systems",
            module_code="CO3",
            module_title="Memory Management",
            topic="Translation Lookaside Buffer TLB"
        )
        self.assertTrue(yt_tlb.is_embeddable)
        self.assertEqual(yt_tlb.video_id, "p3q5BIzRsmU")
        self.assertEqual(yt_tlb.channel, "MIT OpenCourseWare")
        self.assertEqual(yt_tlb.start_seconds, 120)

        yt_avl = await resolve_youtube_resource(
            subject_code="CS304",
            subject_name="Design and Analysis of Algorithms",
            module_code="CO3",
            module_title="Greedy Strategies & Balanced Trees",
            topic="AVL Tree Rotations LL RR"
        )
        self.assertTrue(yt_avl.is_embeddable)
        self.assertEqual(yt_avl.video_id, "jDM6_TnYIqE")
        self.assertEqual(yt_avl.channel, "Abdul Bari")

    # --- Test 4: Dynamic Fallback for Unseeded Module ---
    async def test_dynamic_fallback_for_unseeded_module(self):
        """Unseeded custom topic produces guaranteed rich search fallback without throwing."""
        yt_custom = await resolve_youtube_resource(
            subject_code="CS305",
            subject_name="Software Engineering & Architecture",
            module_code="CO4",
            module_title="Software Testing & Quality Assurance",
            topic="Cyclomatic Complexity & Boundary Value Analysis",
            highlighted_text="Equivalence partitioning and basis path testing"
        )
        self.assertIsNotNone(yt_custom)
        self.assertIsNotNone(yt_custom.search_url)
        self.assertIn("CS305", yt_custom.search_query)
        self.assertIn("Testing", yt_custom.search_query)
        self.assertFalse(yt_custom.is_embeddable)
        self.assertEqual(yt_custom.channel, "YouTube Academic Search")

    # --- Test 5: Dynamic RAG Integration Returns YouTube Resource ---
    async def test_dynamic_rag_includes_youtube_resource(self):
        """POST /learning/explain on dynamic unseeded module returns populated YouTube resource."""
        # Query CS305 (Software Engineering) which has no pre-seeded micro-lesson
        req = AcademicExplainRequest(
            subject_id=5, # CS305
            co_code="CO1",
            selected_text="Agile sprint planning and Scrum story points"
        )
        resp = await generate_grounded_microlesson(
            session=self.session,
            student_id=self.student_claims.student_id,
            req=req,
            claims=self.student_claims
        )
        self.assertEqual(resp.status, "success")
        self.assertIsNotNone(resp.lesson.youtube_resource)
        self.assertIsNotNone(resp.lesson.youtube_resource.search_url)
        self.assertIsNotNone(resp.lesson.youtube_resource.search_query)


if __name__ == "__main__":
    unittest.main()
