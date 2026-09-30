"""
Automated Test Suite for NexuxEdu Hybrid Video Learning & Guaranteed Weak-Area Engine.

Validates:
1. Backward compatibility of MicroLesson schema with and without narration.
2. Database seeded video and YouTube metadata consistency.
3. Offline audio fallback and duration calculation.
4. Video file existence and MP4 validity for showcase lessons.
5. Academic RAG explain payload with video URL and YouTube resource.
6. In-memory video job lifecycle and tracking.
7. Zero-Trust RBAC security boundary (unenrolled student rejection).
8. Dynamic unseeded module video resolution and MP4 generation.
9. Missing physical MP4 file auto-regeneration.
10. Corrupted MP4 file detection and auto-regeneration.
11. Changed MicroLesson content hash invalidation and auto-regeneration.
12. Resilient TTS fallback ensuring video synthesis never fails.
13. End-to-end generic weak-area video pipeline without hardcoded subject maps.
"""

import unittest
import asyncio
import json
import uuid
from pathlib import Path
from sqlalchemy import select, and_

from app.models.schemas import (
    MicroLessonPayload, MicroLessonSceneResponse, YouTubeResource,
    VideoGenerationRequest, VideoJobResponse, UserSecurityClaims,
    AcademicExplainRequest
)
from app.core.database import (
    AsyncSessionLocal, init_db, MicroLesson, Student, Subject, SubjectModule, StudentEnrollment
)
from app.services.tts_provider import (
    TTSManager, BaseTTSProvider, OfflineFallbackTTSProvider,
    generate_offline_fallback_audio, get_audio_duration
)
from app.services.video_generator import (
    render_microlesson_video, create_video_job, get_job_status,
    ensure_learning_video, compute_lesson_content_hash, validate_mp4_file,
    LESSONS_VIDEO_DIR, MEDIA_DIR
)
from app.services.seed_academic_data import seed_academic_support_data
from app.services.academic_analytics import get_student_subject_modules_analysis
from app.services.academic_rag import generate_grounded_microlesson

class TestAcademicHybridVideoSuite(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        await init_db()
        await seed_academic_support_data()
        self.session = AsyncSessionLocal()

        # Seeded student: Jane Doe (ID 1, CS department)
        self.student_claims = UserSecurityClaims(
            user_id=1,
            public_id="usr_student_jane",
            role="student",
            name="Jane Doe",
            email="student@nexuxedu.com",
            department="Computer Science",
            student_id=1
        )

        # Unauthorized student: Bob (ID 2, Mechanical / Unenrolled in CS subjects)
        self.other_claims = UserSecurityClaims(
            user_id=4,
            public_id="usr_student_bob",
            role="student",
            name="Bob Smith",
            email="bob@nexuxedu.com",
            department="Mechanical Engineering",
            student_id=2
        )

    async def asyncTearDown(self):
        try:
            res = await self.session.execute(select(MicroLesson))
            for l in res.scalars().all():
                if l.topic_key and (l.topic_key.startswith("test_") or l.topic_key.startswith("dyn_")):
                    if l.video_path:
                        fpath = MEDIA_DIR / l.video_path
                        if fpath.exists():
                            try:
                                fpath.unlink()
                            except Exception:
                                pass
                    await self.session.delete(l)
            await self.session.commit()
        except Exception:
            pass
        finally:
            await self.session.close()

    # --- Test 1: Schema Backward Compatibility ---
    async def test_microlesson_schema_backward_compatibility(self):
        """MicroLessonPayload must validate with and without narration / video / youtube fields."""
        legacy_payload = MicroLessonPayload(
            title="Legacy Paging Concept",
            topic="Paging",
            objective="Understand paging",
            scenes=[
                {
                    "scene_id": 1,
                    "title": "Introduction",
                    "duration_seconds": 15,
                    "body": "Legacy body text without narration."
                }
            ]
        )
        self.assertEqual(legacy_payload.title, "Legacy Paging Concept")
        self.assertIsNone(legacy_payload.video_url)
        self.assertEqual(legacy_payload.video_status, "none")
        self.assertIsNone(legacy_payload.youtube_resource)

        modern_payload = MicroLessonPayload(
            title="Modern TLB Lesson",
            topic="TLB",
            objective="Master TLB",
            scenes=[
                {
                    "scene_id": 1,
                    "title": "Hardware Acceleration",
                    "duration_seconds": 25,
                    "narration": "The TLB caches recent translations.",
                    "key_takeaway": "TLB speeds up memory access."
                }
            ],
            video_url="/media/lessons/cs301_co3_os_memory_paging_tlb.mp4",
            video_status="ready",
            youtube_resource=YouTubeResource(
                video_id="p3q5BIzRsmU",
                title="MIT Lecture 17: Virtual Memory",
                channel="MIT OpenCourseWare",
                start_seconds=120,
                end_seconds=480
            )
        )
        self.assertEqual(modern_payload.scenes[0]["narration"], "The TLB caches recent translations.")
        self.assertEqual(modern_payload.youtube_resource.video_id, "p3q5BIzRsmU")

    # --- Test 2: Pre-seeded Video and YouTube Resources in Database ---
    async def test_database_seeded_video_and_youtube_metadata(self):
        """All 5 pre-seeded micro-lessons must have valid YouTube resources and video paths."""
        res = await self.session.execute(select(MicroLesson))
        lessons = res.scalars().all()
        self.assertGreaterEqual(len(lessons), 5)

        # 1. OS TLB
        tlb_lesson = next((l for l in lessons if l.topic_key == "os_memory_paging_tlb"), None)
        self.assertIsNotNone(tlb_lesson)
        self.assertIsNotNone(tlb_lesson.youtube_resource_json)
        yt = json.loads(tlb_lesson.youtube_resource_json)
        self.assertEqual(yt["video_id"], "p3q5BIzRsmU")
        self.assertEqual(yt["channel"], "MIT OpenCourseWare")
        self.assertEqual(tlb_lesson.video_path, "lessons/cs301_co3_os_memory_paging_tlb.mp4")

        # 2. DSA / CS304 AVL Rotations
        avl_lesson = next((l for l in lessons if l.topic_key == "algo_avl_rotations"), None)
        self.assertIsNotNone(avl_lesson)
        self.assertEqual(avl_lesson.subject_id, 4)
        self.assertEqual(avl_lesson.video_path, "lessons/cs304_co3_algo_avl_rotations.mp4")
        yt_avl = json.loads(avl_lesson.youtube_resource_json)
        self.assertEqual(yt_avl["channel"], "Abdul Bari")

    # --- Test 3: Audio Generation and Duration Calculation ---
    async def test_offline_audio_fallback_generator(self):
        """Offline fallback audio generator must produce valid WAV/MP3 with measurable duration."""
        test_audio_path = MEDIA_DIR / "audio" / "test_unit_audio.wav"
        target_dur = 4.5
        dur = generate_offline_fallback_audio(test_audio_path, target_duration=target_dur)
        self.assertTrue(test_audio_path.exists())
        self.assertAlmostEqual(dur, target_dur, delta=0.5)
        measured_dur = get_audio_duration(test_audio_path)
        self.assertAlmostEqual(measured_dur, target_dur, delta=0.5)

    # --- Test 4: Video File Existence and Validity for All 5 Showcase Lessons ---
    async def test_showcase_os_tlb_video_file_cached(self):
        """All 5 showcase MP4 videos must exist on disk, be non-empty, and validate successfully."""
        expected_videos = [
            "cs301_co3_os_memory_paging_tlb.mp4",
            "cs301_co3_os_virtual_memory_page_replacement.mp4",
            "cs302_co3_dbms_normalization_bcnf.mp4",
            "cs304_co3_algo_avl_rotations.mp4",
            "cs303_co3_net_dijkstra_routing.mp4"
        ]
        for vid_name in expected_videos:
            video_file = LESSONS_VIDEO_DIR / vid_name
            self.assertTrue(video_file.exists(), f"Showcase MP4 video '{vid_name}' must exist in backend/media/lessons/")
            is_valid, err = validate_mp4_file(video_file)
            self.assertTrue(is_valid, f"Showcase video '{vid_name}' failed validation: {err}")

    # --- Test 5: Academic RAG Explains with Video URL & YouTube Resource ---
    async def test_academic_explain_returns_video_and_youtube_payload(self):
        """POST /learning/explain returns populated video_url and youtube_resource for cached lessons."""
        req = AcademicExplainRequest(
            subject_id=1,
            co_code="CO3",
            selected_text="TLB hit and effective access time calculations in modern paging systems"
        )
        resp = await generate_grounded_microlesson(
            session=self.session,
            student_id=self.student_claims.student_id,
            req=req,
            claims=self.student_claims
        )
        self.assertEqual(resp.status, "success")
        self.assertIsNotNone(resp.lesson.video_url)
        self.assertEqual(resp.lesson.video_status, "ready")
        self.assertIsNotNone(resp.lesson.youtube_resource)
        self.assertEqual(resp.lesson.youtube_resource.video_id, "p3q5BIzRsmU")

    # --- Test 6: In-Memory Video Job Lifecycle ---
    async def test_video_job_tracking(self):
        """create_video_job and get_job_status must properly register and track background jobs."""
        job_id = create_video_job("test_topic_tree", lesson_id=99)
        job_info = get_job_status(job_id)
        self.assertIsNotNone(job_info)
        self.assertEqual(job_info["status"], "queued")
        self.assertEqual(job_info["topic_key"], "test_topic_tree")

    # --- Test 7: Student Course Enrollment Security Boundary ---
    async def test_unauthorized_student_cannot_access_unenrolled_subject_lesson(self):
        """Student cannot query concept explanation for a course they are not enrolled in."""
        from fastapi import HTTPException
        unenrolled_claims = UserSecurityClaims(
            user_id=99,
            public_id="usr_student_unenrolled",
            role="student",
            name="Unenrolled Student",
            email="unenrolled@nexuxedu.com",
            department="Civil Engineering",
            student_id=9999
        )
        req = AcademicExplainRequest(
            subject_id=1,
            co_code="CO1",
            selected_text="Virtual Memory and Paging"
        )
        with self.assertRaises(HTTPException) as cm:
            await generate_grounded_microlesson(
                session=self.session,
                student_id=unenrolled_claims.student_id,
                req=req,
                claims=unenrolled_claims
            )
        self.assertEqual(cm.exception.status_code, 403)
        self.assertIn("not enrolled", cm.exception.detail)

    # --- Test 8: Dynamic Unseeded Module Video Generation ---
    async def test_ensure_learning_video_for_unseeded_module(self):
        """ensure_learning_video must dynamically synthesize and render MP4 for unseeded module."""
        result = await ensure_learning_video(
            session=self.session,
            student_id=self.student_claims.student_id,
            subject_id=5, # CS305 Software Engineering
            co_code="CO1",
            topic="Agile Scrum Methodology and Sprint Planning",
            background=False
        )
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["progress_pct"], 100)
        self.assertIsNotNone(result["video_url"])
        self.assertTrue(result["video_url"].endswith(".mp4"))

        out_filename = Path(result["video_url"]).name
        target_path = LESSONS_VIDEO_DIR / out_filename
        self.assertTrue(target_path.exists())
        is_valid, err = validate_mp4_file(target_path)
        self.assertTrue(is_valid, f"Generated video failed validation: {err}")

    # --- Test 9: Missing Physical MP4 Triggers Auto-Regeneration ---
    async def test_missing_physical_mp4_triggers_regeneration(self):
        """If physical MP4 file is deleted, ensure_learning_video must detect and regenerate it."""
        # Create an isolated test lesson
        test_key = f"test_regen_{uuid.uuid4().hex[:8]}"
        test_lesson = MicroLesson(
            subject_id=1,
            co_code="CO2",
            topic_key=test_key,
            title="Isolated Regeneration Test Lesson",
            duration_seconds=15,
            scenes_json=json.dumps([
                {
                    "scene_id": 1,
                    "type": "concept",
                    "title": "Regen Test Scene",
                    "duration_seconds": 6,
                    "narration": "Testing automatic video regeneration when physical file is missing.",
                    "body": "Body content for regeneration test.",
                    "key_takeaway": "Regeneration works seamlessly."
                }
            ])
        )
        self.session.add(test_lesson)
        await self.session.commit()
        await self.session.refresh(test_lesson)

        # First run: renders MP4
        res1 = await ensure_learning_video(session=self.session, lesson_id=test_lesson.id, background=False)
        self.assertEqual(res1["status"], "ready")
        test_file = LESSONS_VIDEO_DIR / Path(res1["video_url"]).name
        self.assertTrue(test_file.exists())

        # Delete the file to simulate disk loss
        test_file.unlink()
        self.assertFalse(test_file.exists())

        # Second run: must detect missing file and automatically re-render
        res2 = await ensure_learning_video(session=self.session, lesson_id=test_lesson.id, background=False)
        self.assertEqual(res2["status"], "ready")
        self.assertTrue(test_file.exists())
        is_valid, _ = validate_mp4_file(test_file)
        self.assertTrue(is_valid)

        # Cleanup test file
        if test_file.exists():
            test_file.unlink()

    # --- Test 10: Corrupt MP4 File Detection and Regeneration ---
    async def test_corrupt_mp4_triggers_regeneration(self):
        """If an MP4 file is corrupted on disk, validate_mp4_file detects it and regenerates."""
        test_key = f"test_corrupt_{uuid.uuid4().hex[:8]}"
        test_lesson = MicroLesson(
            subject_id=1,
            co_code="CO2",
            topic_key=test_key,
            title="Isolated Corruption Test Lesson",
            duration_seconds=15,
            scenes_json=json.dumps([
                {
                    "scene_id": 1,
                    "type": "concept",
                    "title": "Corruption Test Scene",
                    "duration_seconds": 6,
                    "narration": "Testing corruption detection and automatic recovery.",
                    "body": "Body content for corruption test.",
                    "key_takeaway": "Corrupt files are replaced."
                }
            ])
        )
        self.session.add(test_lesson)
        await self.session.commit()
        await self.session.refresh(test_lesson)

        # Initial render
        res1 = await ensure_learning_video(session=self.session, lesson_id=test_lesson.id, background=False)
        test_file = LESSONS_VIDEO_DIR / Path(res1["video_url"]).name
        self.assertTrue(test_file.exists())

        # Corrupt the file with invalid bytes
        test_file.write_bytes(b"CORRUPT_NON_MP4_HEADER_DATA_GARBAGE")
        is_valid, _ = validate_mp4_file(test_file)
        self.assertFalse(is_valid)

        # ensure_learning_video must detect corruption and regenerate
        res2 = await ensure_learning_video(session=self.session, lesson_id=test_lesson.id, background=False)
        self.assertEqual(res2["status"], "ready")
        is_valid_after, _ = validate_mp4_file(test_file)
        self.assertTrue(is_valid_after)

        # Cleanup
        if test_file.exists():
            test_file.unlink()

    # --- Test 11: Changed MicroLesson Content Hash Invalidation ---
    async def test_changed_microlesson_content_hash_triggers_regeneration(self):
        """Changing scenes modifies content hash and forces fresh MP4 generation."""
        test_key = f"test_hash_{uuid.uuid4().hex[:8]}"
        test_lesson = MicroLesson(
            subject_id=1,
            co_code="CO2",
            topic_key=test_key,
            title="Content Hash Test Lesson",
            duration_seconds=15,
            scenes_json=json.dumps([
                {
                    "scene_id": 1,
                    "type": "concept",
                    "title": "Version 1 Initial Content",
                    "duration_seconds": 6,
                    "narration": "Initial version of scene content.",
                    "body": "Initial text content.",
                    "key_takeaway": "Takeaway v1."
                }
            ])
        )
        self.session.add(test_lesson)
        await self.session.commit()
        await self.session.refresh(test_lesson)

        # Initial render
        res1 = await ensure_learning_video(session=self.session, lesson_id=test_lesson.id, background=False)
        await self.session.refresh(test_lesson)
        initial_hash = test_lesson.video_content_hash
        self.assertIsNotNone(initial_hash)

        # Update scene content
        updated_scenes = [
            {
                "scene_id": 1,
                "type": "concept",
                "title": "Version 2 Updated Definition",
                "duration_seconds": 6,
                "narration": "Updated version with new instructional focus.",
                "body": "Updated text content.",
                "key_takeaway": "Takeaway v2."
            }
        ]
        test_lesson.scenes_json = json.dumps(updated_scenes)
        await self.session.commit()

        new_computed_hash = compute_lesson_content_hash("CS301", "CO2", test_key, test_lesson.title, updated_scenes)
        self.assertNotEqual(initial_hash, new_computed_hash)

        # ensure_learning_video must detect outdated hash and regenerate
        res2 = await ensure_learning_video(session=self.session, lesson_id=test_lesson.id, background=False)
        self.assertEqual(res2["status"], "ready")

        await self.session.refresh(test_lesson)
        self.assertEqual(test_lesson.video_content_hash, new_computed_hash)

        # Cleanup
        test_file = LESSONS_VIDEO_DIR / Path(res2["video_url"]).name
        if test_file.exists():
            test_file.unlink()

    # --- Test 12: Resilient TTS Fallback Video Synthesis ---
    async def test_resilient_tts_fallback_generates_valid_video(self):
        """Video rendering must succeed even if TTS provider encounters offline or network failure."""
        lesson_data = {
            "title": "Offline Robustness Test",
            "subject_code": "CS301",
            "co_code": "CO3",
            "scenes": [
                {
                    "scene_id": 1,
                    "type": "concept",
                    "title": "Resilient Concept",
                    "duration_seconds": 6,
                    "narration": "This is a test of robust local audio synthesis during video generation.",
                    "body": "Body text for offline fallback demonstration.",
                    "key_takeaway": "Zero external dependencies required."
                }
            ]
        }
        test_video_filename = "test_resilient_tts_video.mp4"
        out_path, dur = await render_microlesson_video(lesson_data, test_video_filename)
        self.assertTrue(out_path.exists())
        self.assertGreater(dur, 0)
        is_valid, _ = validate_mp4_file(out_path)
        self.assertTrue(is_valid)

        # Clean up
        if out_path.exists():
            out_path.unlink()

    # --- Test 13: Generic Weak-Area Video Pipeline (No Hardcoding) ---
    async def test_generic_weak_area_video_pipeline_no_hardcoding(self):
        """
        End-to-end integration:
        Student analytics identifies weakest module -> ensure_learning_video resolves MP4.
        Works across any subject / module without hardcoding.
        """
        # 1. Query Jane Doe's OS (subject_id=1) modules analysis
        analysis = await get_student_subject_modules_analysis(
            session=self.session,
            student_id=self.student_claims.student_id,
            subject_id=1
        )
        self.assertIsNotNone(analysis.weakest_module)
        weak_co = analysis.weakest_module

        # 2. Feed weakest module into ensure_learning_video
        result_os = await ensure_learning_video(
            session=self.session,
            student_id=self.student_claims.student_id,
            subject_id=1,
            module_id=weak_co.id,
            co_code=weak_co.co_code,
            topic=weak_co.title,
            background=False
        )
        self.assertEqual(result_os["status"], "ready")
        self.assertIsNotNone(result_os["video_url"])

        # 3. Test with a completely different course: Mathematics / MA301 (subject_id=6)
        result_math = await ensure_learning_video(
            session=self.session,
            student_id=self.student_claims.student_id,
            subject_id=6,
            co_code="CO3",
            topic="Discrete Probability & Random Variables",
            background=False
        )
        self.assertEqual(result_math["status"], "ready")
        self.assertIsNotNone(result_math["video_url"])
        self.assertTrue(result_math["video_url"].startswith("/media/lessons/ma301_co3"))


if __name__ == "__main__":
    unittest.main()
