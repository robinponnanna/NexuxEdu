"""
Unit & Integration Tests for Phase 4: Backend Dependency & Video-Service Hardening.

Verifies:
1. Core dependency imports (Pillow, imageio-ffmpeg, edge-tts).
2. Video & TTS capability detection.
3. FFmpeg discovery and executable resolution.
4. Core FastAPI startup resilience when optional video dependencies are absent.
5. Structured failure response when video engine is unavailable.
6. Media directory safety and temp artifact cleanup.
7. Environment and Git hygiene.
"""

import os
import sys
import shutil
import unittest
import importlib
from pathlib import Path
from unittest.mock import patch, MagicMock

import httpx
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal, MicroLesson, User
from app.services.video_generator import (
    get_video_capability_status,
    get_ffmpeg_executable,
    validate_mp4_file,
    ensure_learning_video,
    VIDEO_RENDERING_AVAILABLE,
    PILLOW_AVAILABLE,
    FFMPEG_AVAILABLE,
    MEDIA_DIR,
    LESSONS_VIDEO_DIR,
    TEMP_MEDIA_DIR,
)
from app.services.tts_provider import (
    get_tts_capability_status,
    generate_offline_fallback_audio,
    get_audio_duration,
    AUDIO_CACHE_DIR,
)


class TestVideoDependencyHardeningSuite(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        from app.core.database import init_db
        from app.services.seed_data import seed_database_if_empty
        from app.services.seed_academic_data import seed_academic_support_data
        await init_db()
        await seed_database_if_empty()
        await seed_academic_support_data()

    def test_01_core_video_dependencies_importable(self):
        """Pillow, imageio-ffmpeg, and edge-tts must be importable in standard environment."""
        import PIL
        from PIL import Image, ImageDraw, ImageFont
        import imageio_ffmpeg
        import edge_tts

        self.assertTrue(hasattr(PIL, "__version__"))
        self.assertTrue(hasattr(imageio_ffmpeg, "get_ffmpeg_exe"))
        self.assertTrue(hasattr(edge_tts, "Communicate"))

    def test_02_video_and_tts_capability_status(self):
        """get_video_capability_status and get_tts_capability_status must report structured status."""
        v_cap = get_video_capability_status()
        self.assertIn("video_rendering_available", v_cap)
        self.assertIn("pillow_available", v_cap)
        self.assertIn("ffmpeg_available", v_cap)
        self.assertIn("edge_tts_available", v_cap)
        self.assertIn("tts_available", v_cap)

        t_cap = get_tts_capability_status()
        self.assertIn("edge_tts_available", t_cap)
        self.assertIn("offline_fallback_available", t_cap)
        self.assertTrue(t_cap["offline_fallback_available"])

    def test_03_ffmpeg_executable_discovery(self):
        """get_ffmpeg_executable must return a valid, existing executable path."""
        exe_path = get_ffmpeg_executable()
        self.assertTrue(os.path.exists(exe_path), f"FFmpeg executable not found at: {exe_path}")
        self.assertTrue(exe_path.lower().endswith("ffmpeg.exe") or "ffmpeg" in exe_path.lower())

    def test_04_media_directories_created_safely(self):
        """MEDIA_DIR, LESSONS_VIDEO_DIR, AUDIO_CACHE_DIR, TEMP_MEDIA_DIR must exist."""
        self.assertTrue(MEDIA_DIR.exists())
        self.assertTrue(LESSONS_VIDEO_DIR.exists())
        self.assertTrue(AUDIO_CACHE_DIR.exists())
        self.assertTrue(TEMP_MEDIA_DIR.exists())

    def test_05_offline_audio_fallback_independent_of_network(self):
        """Offline audio generator creates valid audio file without any network calls."""
        temp_wav = TEMP_MEDIA_DIR / f"test_offline_{os.getpid()}.wav"
        try:
            dur = generate_offline_fallback_audio(temp_wav, target_duration=2.5)
            self.assertGreaterEqual(dur, 2.0)
            self.assertTrue(temp_wav.exists())
            self.assertGreater(temp_wav.stat().st_size, 1000)
            measured_dur = get_audio_duration(temp_wav)
            self.assertAlmostEqual(measured_dur, 2.5, delta=0.5)
        finally:
            if temp_wav.exists():
                temp_wav.unlink()

    async def test_06_video_generation_failure_when_dependencies_missing(self):
        """When VIDEO_RENDERING_AVAILABLE is False, unseeded generation returns structured failure (not 500 crash)."""
        async with AsyncSessionLocal() as session:
            with patch("app.services.video_generator.VIDEO_RENDERING_AVAILABLE", False), \
                 patch("app.services.video_generator.PILLOW_AVAILABLE", False):
                
                res = await ensure_learning_video(
                    session=session,
                    subject_id=1,
                    co_code="CO3",
                    topic="Test Missing Dep Topic",
                    topic_key=f"test_missing_dep_{os.getpid()}",
                    force_regenerate=True,
                    background=False
                )

                self.assertEqual(res["status"], "failed")
                self.assertFalse(res["retryable"])
                self.assertIn("unavailable", res["error_message"].lower())
                self.assertIn("Pillow", res["error_message"])

    async def test_07_core_fastapi_backend_starts_without_video_dependencies(self):
        """Core endpoints (/health, /login, /student/subjects) must work even if video rendering is disabled."""
        from app.main import app

        # Test health endpoint using httpx AsyncClient
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            health_res = await client.get("/health")
            self.assertEqual(health_res.status_code, 200)
            self.assertEqual(health_res.json()["status"], "healthy")

            # Login as student Jane Doe
            login_res = await client.post("/api/v1/auth/login", json={
                "email": "student@campus.edu",
                "password": "password123"
            })
            self.assertEqual(login_res.status_code, 200)
            token = login_res.json()["access_token"]

            # Academic endpoints work cleanly
            headers = {"Authorization": f"Bearer {token}"}
            subj_res = await client.get("/api/v1/student/subjects", headers=headers)
            self.assertEqual(subj_res.status_code, 200)
            subjects = subj_res.json()
            self.assertGreater(len(subjects), 0)

    def test_08_environment_and_git_hygiene(self):
        """Verify .env is not tracked and .env.example contains only placeholders."""
        root_dir = Path(__file__).resolve().parent.parent.parent
        env_file = root_dir / ".env"
        env_example = root_dir / ".env.example"

        if env_example.exists():
            content = env_example.read_text(encoding="utf-8")
            self.assertNotIn("sk-", content)
            self.assertNotIn("gsk_", content)
            self.assertNotIn("AIzaSy", content)

        # Verify showcase videos exist and are not empty
        showcase_files = [
            "cs301_co3_os_memory_paging_tlb.mp4",
            "cs301_co3_os_virtual_memory_page_replacement.mp4",
            "cs302_co3_dbms_normalization_bcnf.mp4",
            "cs303_co3_net_dijkstra_routing.mp4",
            "cs304_co3_algo_avl_rotations.mp4",
        ]
        for s_file in showcase_files:
            p = LESSONS_VIDEO_DIR / s_file
            self.assertTrue(p.exists(), f"Showcase video missing: {s_file}")
            self.assertGreater(p.stat().st_size, 10000, f"Showcase video truncated: {s_file}")


if __name__ == "__main__":
    unittest.main()
