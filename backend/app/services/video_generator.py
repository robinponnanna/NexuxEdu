"""
NexuxEdu Video Generation & Guaranteed Weak-Area Video Engine.

Architectural Principles:
1. MicroLesson JSON as Single Source of Truth: Renders scenes declaratively.
2. Controlled Educational Visuals: Deterministic diagrams, tables, formulas, flowcharts, and code.
3. Synchronized Narration: Visual scene timing dynamically aligns with TTS speech duration.
4. Non-blocking Async Architecture: Background job worker with status polling.
5. Disk Cache & Validation: Encodes H.264/AAC MP4 directly into backend/media/lessons/ with content hash verification.
6. Guaranteed Video Availability: Any weak area / module dynamically resolves or synthesizes a MicroLesson and MP4 path.
"""

import os
import sys
import json
import time
import math
import uuid
import shutil
import hashlib
import asyncio
import datetime
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union

# Optional video rendering dependencies with guarded isolation
try:
    from PIL import Image, ImageDraw, ImageFont
    PILLOW_AVAILABLE = True
except ImportError:
    Image = None
    ImageDraw = None
    ImageFont = None
    PILLOW_AVAILABLE = False

try:
    import imageio_ffmpeg
    try:
        _cached_ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        FFMPEG_AVAILABLE = bool(_cached_ffmpeg_exe and os.path.exists(_cached_ffmpeg_exe))
    except Exception:
        _cached_ffmpeg_exe = None
        FFMPEG_AVAILABLE = bool(shutil.which("ffmpeg"))
except ImportError:
    imageio_ffmpeg = None
    _cached_ffmpeg_exe = shutil.which("ffmpeg")
    FFMPEG_AVAILABLE = bool(_cached_ffmpeg_exe)

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    edge_tts = None
    EDGE_TTS_AVAILABLE = False

VIDEO_RENDERING_AVAILABLE = PILLOW_AVAILABLE and FFMPEG_AVAILABLE

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import (
    AsyncSessionLocal, MicroLesson, Subject, SubjectModule, StudentEnrollment
)
from app.models.schemas import MicroLessonPayload, VideoJobResponse
from app.services.tts_provider import (
    tts_manager, generate_offline_fallback_audio, get_audio_duration
)

MEDIA_DIR = Path(__file__).resolve().parent.parent.parent / "media"
LESSONS_VIDEO_DIR = MEDIA_DIR / "lessons"
TEMP_MEDIA_DIR = MEDIA_DIR / "temp"
for d in [MEDIA_DIR, LESSONS_VIDEO_DIR, TEMP_MEDIA_DIR]:
    d.mkdir(parents=True, exist_ok=True)

def get_video_capability_status() -> Dict[str, Any]:
    """Returns current capability flags of the video rendering subsystem."""
    return {
        "video_rendering_available": VIDEO_RENDERING_AVAILABLE,
        "pillow_available": PILLOW_AVAILABLE,
        "ffmpeg_available": FFMPEG_AVAILABLE,
        "ffmpeg_executable": _cached_ffmpeg_exe or shutil.which("ffmpeg"),
        "edge_tts_available": EDGE_TTS_AVAILABLE,
        "tts_available": True,
    }

def get_ffmpeg_executable() -> str:
    """
    Locates the packaged imageio-ffmpeg executable or system FFmpeg binary.
    """
    if _cached_ffmpeg_exe and os.path.exists(_cached_ffmpeg_exe):
        return _cached_ffmpeg_exe
    if imageio_ffmpeg:
        try:
            exe = imageio_ffmpeg.get_ffmpeg_exe()
            if exe and os.path.exists(exe):
                return exe
        except Exception:
            pass
    sys_exe = shutil.which("ffmpeg")
    if sys_exe:
        return sys_exe
    raise RuntimeError("FFmpeg executable not found. Please install imageio-ffmpeg or ensure ffmpeg is on system PATH.")

# In-memory background job tracker for video rendering
_video_jobs: Dict[str, Dict[str, Any]] = {}

def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves current job status from in-memory tracker."""
    return _video_jobs.get(job_id)

def create_video_job(topic_key: str, lesson_id: Optional[int] = None) -> str:
    """Registers a new video rendering job."""
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    _video_jobs[job_id] = {
        "job_id": job_id,
        "lesson_id": lesson_id,
        "topic_key": topic_key,
        "status": "queued", # queued, audio_generating, video_rendering, completed, failed
        "progress_pct": 0,
        "video_url": None,
        "duration_seconds": None,
        "error_message": None,
        "retryable": True,
        "created_at": time.time()
    }
    return job_id

def compute_lesson_content_hash(
    subject_code: str,
    co_code: str,
    topic_key: str,
    title: str,
    scenes: List[Dict[str, Any]]
) -> str:
    """Computes a deterministic SHA-256 content hash representing the MicroLesson."""
    normalized_scenes = []
    for sc in scenes:
        normalized_scenes.append({
            "title": str(sc.get("title", "")).strip(),
            "type": str(sc.get("type") or sc.get("visual_type") or "").strip(),
            "body": str(sc.get("body", "")).strip(),
            "narration": str(sc.get("narration", "")).strip(),
            "key_takeaway": str(sc.get("key_takeaway", "")).strip(),
            "visual_data": sc.get("visual_data") or sc.get("diagram") or {}
        })
    raw_payload = {
        "subject_code": subject_code.strip().upper(),
        "co_code": co_code.strip().upper(),
        "topic_key": topic_key.strip().lower(),
        "title": title.strip(),
        "scenes": normalized_scenes
    }
    encoded = json.dumps(raw_payload, sort_keys=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

def validate_mp4_file(file_path: Path) -> Tuple[bool, Optional[str]]:
    """
    Validates that the file exists, is non-empty, and has a valid MP4 container/streams.
    Uses get_ffmpeg_executable / ffprobe integrity probe with binary header fallback.
    """
    if not file_path.exists():
        return False, f"File does not exist: {file_path}"
    
    size = file_path.stat().st_size
    if size < 1000:
        return False, f"File too small ({size} bytes): likely empty or truncated"

    try:
        ffmpeg_exe = get_ffmpeg_executable()
        cmd = [ffmpeg_exe, "-v", "error", "-i", str(file_path), "-t", "1", "-f", "null", "-"]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        if result.returncode != 0:
            return False, f"FFmpeg validation failed: {result.stderr.strip()[:200]}"
        return True, None
    except Exception:
        # Fallback binary header probe
        try:
            with open(file_path, "rb") as f:
                header = f.read(32)
                if b"ftyp" in header:
                    return True, None
        except Exception as e:
            return False, f"Validation probe error: {str(e)}"
        return False, "Validation probe could not confirm MP4 header"


class VideoFrameRenderer:
    """Renders 1280x720 crisp educational video frames for each micro-lesson scene."""

    def __init__(self, width: int = 1280, height: int = 720):
        self.width = width
        self.height = height

        # Load fonts or fall back to default
        try:
            self.font_title = ImageFont.truetype("arialbd.ttf", 32)
            self.font_subtitle = ImageFont.truetype("arialbd.ttf", 22)
            self.font_body = ImageFont.truetype("arial.ttf", 20)
            self.font_mono = ImageFont.truetype("consola.ttf", 18)
            self.font_small = ImageFont.truetype("arial.ttf", 15)
            self.font_badge = ImageFont.truetype("arialbd.ttf", 14)
        except Exception:
            self.font_title = ImageFont.load_default()
            self.font_subtitle = ImageFont.load_default()
            self.font_body = ImageFont.load_default()
            self.font_mono = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
            self.font_badge = ImageFont.load_default()

    def render_scene_frame(
        self,
        scene: Dict[str, Any],
        scene_idx: int,
        total_scenes: int,
        lesson_title: str,
        subject_label: str,
        progress_pct: float,
        elapsed_sec: float,
        total_scene_sec: float
    ) -> Image.Image:
        """Draws a single 1280x720 RGB frame for a given scene."""
        img = Image.new("RGB", (self.width, self.height), color="#0F172A") # Slate 900
        draw = ImageDraw.Draw(img)

        # 1. Header Bar
        draw.rectangle([(0, 0), (self.width, 70)], fill="#1E293B")
        draw.line([(0, 70), (self.width, 70)], fill="#334155", width=2)

        # AI Micro-Lesson Badge
        draw.rounded_rectangle([(30, 20), (190, 50)], radius=6, fill="#0284C7")
        draw.text((42, 27), "AI MICRO-LESSON", fill="#FFFFFF", font=self.font_badge)

        # Subject & Lesson Title
        draw.text((210, 26), f"{subject_label} • {lesson_title[:55]}", fill="#E2E8F0", font=self.font_subtitle)

        # Scene Counter & Timer on Right
        counter_text = f"Scene {scene_idx + 1}/{total_scenes}  |  {int(elapsed_sec)}s / {int(total_scene_sec)}s"
        draw.text((self.width - 270, 26), counter_text, fill="#94A3B8", font=self.font_subtitle)

        # 2. Scene Title
        scene_title = scene.get("title", "Core Concept")
        scene_type = scene.get("type") or scene.get("visual_type") or "concept"
        
        # Category tag
        type_color = "#10B981" if scene_type == "takeaway" else ("#EF4444" if scene_type == "common_mistake" else "#38BDF8")
        draw.text((30, 90), f"FOCUS: {scene_type.upper().replace('_', ' ')}", fill=type_color, font=self.font_badge)
        draw.text((30, 115), scene_title, fill="#F8FAFC", font=self.font_title)

        # 3. Main Content Visual Area
        visual_data = scene.get("visual_data") or scene.get("diagram") or {}
        v_type = scene.get("visual_type") or scene_type

        content_box = [(30, 175), (self.width - 30, 550)]
        draw.rounded_rectangle(content_box, radius=12, fill="#1E293B", outline="#334155", width=2)

        if v_type == "table" and "columns" in visual_data:
            self._draw_table(draw, visual_data, content_box)
        elif v_type == "code" and "code_snippet" in visual_data:
            self._draw_code(draw, visual_data, content_box)
        elif v_type in ["flowchart", "step_by_step"] and "steps" in visual_data:
            self._draw_flowchart(draw, visual_data, content_box)
        elif "ascii_diagram" in visual_data:
            self._draw_diagram(draw, visual_data, content_box)
        else:
            # Concept description text
            self._draw_concept_text(draw, scene, content_box)

        # 4. Key Takeaway Footer Callout
        takeaway = scene.get("key_takeaway")
        if takeaway:
            callout_box = [(30, 565), (self.width - 30, 645)]
            box_bg = "#1E3A8A" if scene_type != "common_mistake" else "#7F1D1D"
            box_border = "#3B82F6" if scene_type != "common_mistake" else "#EF4444"
            draw.rounded_rectangle(callout_box, radius=10, fill=box_bg, outline=box_border, width=2)
            
            badge_label = "EXAM PITFALL ALERT" if scene_type == "common_mistake" else "CORE TAKEAWAY"
            draw.text((50, 575), badge_label, fill="#60A5FA" if scene_type != "common_mistake" else "#FCA5A5", font=self.font_badge)
            draw.text((50, 600), takeaway[:130], fill="#FFFFFF", font=self.font_body)

        # 5. Bottom Timeline / Progress Bar
        bar_y = self.height - 18
        draw.rectangle([(0, bar_y), (self.width, self.height)], fill="#0F172A")
        # Base track
        draw.rectangle([(0, bar_y + 4), (self.width, bar_y + 12)], fill="#334155")
        # Active progress fill
        fill_w = max(4, int(self.width * (progress_pct / 100.0)))
        draw.rectangle([(0, bar_y + 4), (fill_w, bar_y + 12)], fill="#0284C7")

        return img

    def _draw_diagram(self, draw: ImageDraw.ImageDraw, visual_data: Dict[str, Any], box: List[Tuple[int, int]]):
        x0, y0 = box[0]
        x1, y1 = box[1]
        
        d_title = visual_data.get("diagram_title", "System Architecture & Concept Mechanics")
        draw.text((x0 + 20, y0 + 15), d_title, fill="#38BDF8", font=self.font_subtitle)

        ascii_text = visual_data.get("ascii_diagram", "")
        lines = ascii_text.splitlines()
        curr_y = y0 + 55
        for line in lines[:14]:
            draw.text((x0 + 25, curr_y), line, fill="#E2E8F0", font=self.font_mono)
            curr_y += 22

    def _draw_table(self, draw: ImageDraw.ImageDraw, visual_data: Dict[str, Any], box: List[Tuple[int, int]]):
        x0, y0 = box[0]
        x1, y1 = box[1]
        cols = visual_data.get("columns", [])
        rows = visual_data.get("rows", [])

        if not cols:
            return

        col_w = (x1 - x0 - 40) // len(cols)
        # Header row
        draw.rectangle([(x0 + 20, y0 + 20), (x1 - 20, y0 + 60)], fill="#334155")
        for i, col in enumerate(cols):
            draw.text((x0 + 30 + i * col_w, y0 + 28), str(col).upper(), fill="#F8FAFC", font=self.font_badge)

        # Data rows
        curr_y = y0 + 70
        for r_idx, row in enumerate(rows[:6]):
            bg = "#1E293B" if r_idx % 2 == 0 else "#243248"
            draw.rectangle([(x0 + 20, curr_y - 6), (x1 - 20, curr_y + 36)], fill=bg)
            for c_idx, cell in enumerate(row):
                if c_idx < len(cols):
                    cell_color = "#38BDF8" if c_idx == 0 else "#CBD5E1"
                    draw.text((x0 + 30 + c_idx * col_w, curr_y), str(cell), fill=cell_color, font=self.font_body)
            curr_y += 46

    def _draw_code(self, draw: ImageDraw.ImageDraw, visual_data: Dict[str, Any], box: List[Tuple[int, int]]):
        x0, y0 = box[0]
        x1, y1 = box[1]
        lang = visual_data.get("language", "python").upper()
        draw.text((x0 + 20, y0 + 15), f"CODE SNIPPET • {lang}", fill="#F59E0B", font=self.font_badge)

        snippet = visual_data.get("code_snippet", "")
        curr_y = y0 + 50
        for line in snippet.splitlines()[:13]:
            line_color = "#34D399" if line.strip().startswith("#") else ("#60A5FA" if "=" in line else "#E2E8F0")
            draw.text((x0 + 25, curr_y), line, fill=line_color, font=self.font_mono)
            curr_y += 24

    def _draw_flowchart(self, draw: ImageDraw.ImageDraw, visual_data: Dict[str, Any], box: List[Tuple[int, int]]):
        x0, y0 = box[0]
        x1, y1 = box[1]
        steps = visual_data.get("steps", [])
        
        draw.text((x0 + 20, y0 + 15), "STEP-BY-STEP EXECUTION FLOW", fill="#38BDF8", font=self.font_badge)
        curr_y = y0 + 50
        for i, step in enumerate(steps[:5]):
            step_box = [(x0 + 25, curr_y), (x1 - 25, curr_y + 48)]
            draw.rounded_rectangle(step_box, radius=8, fill="#243248", outline="#475569", width=1)
            # Step number circle
            draw.ellipse([(x0 + 35, curr_y + 10), (x0 + 65, curr_y + 38)], fill="#0284C7")
            draw.text((x0 + 46, curr_y + 14), str(i + 1), fill="#FFFFFF", font=self.font_badge)
            draw.text((x0 + 80, curr_y + 14), str(step)[:95], fill="#F1F5F9", font=self.font_body)
            curr_y += 58

    def _draw_concept_text(self, draw: ImageDraw.ImageDraw, scene: Dict[str, Any], box: List[Tuple[int, int]]):
        x0, y0 = box[0]
        x1, y1 = box[1]
        body = scene.get("body", "") or scene.get("narration", "")
        
        draw.text((x0 + 25, y0 + 20), "CONCEPT INSIGHT", fill="#38BDF8", font=self.font_badge)
        
        words = body.replace("\n", " ").split()
        lines = []
        cur_line = []
        for w in words:
            cur_line.append(w)
            if len(" ".join(cur_line)) > 75:
                lines.append(" ".join(cur_line))
                cur_line = []
        if cur_line:
            lines.append(" ".join(cur_line))

        curr_y = y0 + 55
        for line in lines[:8]:
            draw.text((x0 + 25, curr_y), line, fill="#E2E8F0", font=self.font_body)
            curr_y += 30


async def render_microlesson_video(
    lesson_data: Dict[str, Any],
    output_filename: str,
    job_id: Optional[str] = None
) -> Tuple[Path, float]:
    """
    Renders an authoritative H.264 MP4 video file from MicroLesson JSON.
    1. Validates capability requirements.
    2. Generates TTS audio for each scene (or loads cached audio), with resilient offline fallback.
    3. Builds frame video sequences matching exact scene timing.
    4. Merges video frames and synchronized narration into output MP4.
    """
    if not VIDEO_RENDERING_AVAILABLE:
        missing = []
        if not PILLOW_AVAILABLE:
            missing.append("Pillow")
        if not FFMPEG_AVAILABLE:
            missing.append("imageio-ffmpeg / FFmpeg")
        raise RuntimeError(f"Video rendering engine unavailable: Missing required dependency ({', '.join(missing)}).")

    if job_id and job_id in _video_jobs:
        _video_jobs[job_id]["status"] = "audio_generating"
        _video_jobs[job_id]["progress_pct"] = 10

    output_path = LESSONS_VIDEO_DIR / output_filename
    ffmpeg_exe = get_ffmpeg_executable()
    frame_renderer = VideoFrameRenderer()

    scenes = lesson_data.get("scenes", [])
    if not scenes:
        raise ValueError("MicroLesson contains 0 scenes to render.")

    lesson_title = lesson_data.get("title", "Micro-Lesson")
    subject_label = f"{lesson_data.get('subject_code', 'CS')} {lesson_data.get('co_code', 'CO')}".strip()

    # Step 1: Synthesize / retrieve audio for each scene with bulletproof fallback
    scene_audio_tracks: List[Tuple[Path, float]] = []
    total_audio_duration = 0.0

    for i, sc in enumerate(scenes):
        narration_text = sc.get("narration") or sc.get("body") or sc.get("title") or "Academic Concept"
        try:
            audio_path, duration = await tts_manager.get_or_generate_scene_audio(narration_text, voice_tag=f"sc_{i}")
        except Exception:
            # Resilient local fallback
            silence_path = TEMP_MEDIA_DIR / f"temp_fallback_audio_{uuid.uuid4().hex[:8]}.wav"
            duration = max(float(sc.get("duration_seconds", 8)), len(narration_text.split()) * 0.4)
            generate_offline_fallback_audio(silence_path, duration)
            audio_path = silence_path

        dur = max(float(sc.get("duration_seconds", 8.0)), duration + 0.5)
        scene_audio_tracks.append((audio_path, dur))
        total_audio_duration += dur

    if job_id and job_id in _video_jobs:
        _video_jobs[job_id]["status"] = "video_rendering"
        _video_jobs[job_id]["progress_pct"] = 35

    try:
        # Step 2: Render scene frame sequences and encode video clips with FFmpeg
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            scene_clip_paths: List[Path] = []
            fps = 30

            for s_idx, (sc, (a_path, s_dur)) in enumerate(zip(scenes, scene_audio_tracks)):
                scene_frame_img = frame_renderer.render_scene_frame(
                    scene=sc,
                    scene_idx=s_idx,
                    total_scenes=len(scenes),
                    lesson_title=lesson_title,
                    subject_label=subject_label,
                    progress_pct=(s_idx / len(scenes)) * 100,
                    elapsed_sec=0,
                    total_scene_sec=s_dur
                )

                frame_img_path = temp_dir_path / f"scene_{s_idx:03d}.png"
                scene_frame_img.save(frame_img_path)

                clip_video_path = temp_dir_path / f"clip_{s_idx:03d}.mp4"

                # FFmpeg render clip from image + audio
                cmd = [
                    ffmpeg_exe, "-y",
                    "-loop", "1",
                    "-framerate", str(fps),
                    "-i", str(frame_img_path),
                    "-i", str(a_path),
                    "-c:v", "libx264",
                    "-t", str(s_dur),
                    "-pix_fmt", "yuv420p",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-shortest",
                    str(clip_video_path)
                ]

                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                scene_clip_paths.append(clip_video_path)

                if job_id and job_id in _video_jobs:
                    _video_jobs[job_id]["progress_pct"] = 35 + int((s_idx + 1) / len(scenes) * 50)

            # Step 3: Concatenate all scene clips into final MP4
            concat_list_file = temp_dir_path / "concat_list.txt"
            with open(concat_list_file, "w") as f:
                for c_path in scene_clip_paths:
                    escaped = str(c_path).replace("\\", "/")
                    f.write(f"file '{escaped}'\n")

            concat_cmd = [
                ffmpeg_exe, "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_list_file),
                "-c", "copy",
                str(output_path)
            ]
            subprocess.run(concat_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        # Post-generation validation
        is_valid, err_msg = validate_mp4_file(output_path)
        if not is_valid:
            if output_path.exists():
                try:
                    output_path.unlink()
                except Exception:
                    pass
            raise RuntimeError(f"Generated MP4 file failed validation: {err_msg}")

        if job_id and job_id in _video_jobs:
            _video_jobs[job_id]["status"] = "ready"
            _video_jobs[job_id]["progress_pct"] = 100
            _video_jobs[job_id]["video_url"] = f"/media/lessons/{output_filename}"
            _video_jobs[job_id]["duration_seconds"] = int(total_audio_duration)

        return output_path, total_audio_duration

    except Exception as e:
        if output_path.exists():
            try:
                # Do not leave broken or truncated video files on disk
                output_path.unlink()
            except Exception:
                pass
        raise


async def ensure_learning_video(
    session: AsyncSession,
    student_id: Optional[int] = None,
    subject_id: Optional[int] = None,
    module_id: Optional[int] = None,
    lesson_id: Optional[int] = None,
    topic_key: Optional[str] = None,
    topic: Optional[str] = None,
    co_code: Optional[str] = None,
    direct_payload: Optional[Union[Dict[str, Any], MicroLessonPayload]] = None,
    force_regenerate: bool = False,
    background: bool = True
) -> Dict[str, Any]:
    """
    Guaranteed Video Engine Orchestrator.
    
    Ensures an authoritative, playable MP4 video exists for any course outcome / topic.
    1. Resolves or reconciles MicroLesson record in database.
    2. Enforces RBAC / student enrollment check if student_id is provided.
    3. Computes deterministic lesson content hash.
    4. Fast-path: Returns cached video immediately if file exists, valid, and hash matches.
    5. Cache-miss / Outdated / Missing / Corrupt: Automatically renders or re-renders MP4.
    """
    lesson: Optional[MicroLesson] = None

    # 1. Resolve MicroLesson
    if lesson_id:
        res = await session.execute(
            select(MicroLesson)
            .where(MicroLesson.id == lesson_id)
            .options(selectinload(MicroLesson.subject), selectinload(MicroLesson.module))
        )
        lesson = res.scalar_one_or_none()

    if not lesson and topic_key:
        res = await session.execute(
            select(MicroLesson)
            .where(MicroLesson.topic_key == topic_key)
            .options(selectinload(MicroLesson.subject), selectinload(MicroLesson.module))
        )
        lesson = res.scalar_one_or_none()

    if not lesson and not topic_key and module_id:
        res = await session.execute(
            select(MicroLesson)
            .where(MicroLesson.module_id == module_id)
            .options(selectinload(MicroLesson.subject), selectinload(MicroLesson.module))
        )
        lesson = res.scalars().first()

    if not lesson and not topic_key and subject_id and co_code:
        res = await session.execute(
            select(MicroLesson)
            .where(and_(MicroLesson.subject_id == subject_id, MicroLesson.co_code == co_code))
            .options(selectinload(MicroLesson.subject), selectinload(MicroLesson.module))
        )
        lesson = res.scalars().first()

    # 2. Dynamic MicroLesson persistence/reconciliation if not present in DB
    if not lesson:
        # If direct payload provided, build MicroLesson from payload
        if direct_payload:
            payload_dict = direct_payload.model_dump() if hasattr(direct_payload, "model_dump") else direct_payload
            p_subj_id = payload_dict.get("subject_id") or subject_id
            p_mod_id = payload_dict.get("module_id") or module_id
            p_co_code = payload_dict.get("co_code") or co_code or "CO3"
            p_title = payload_dict.get("title") or (topic or "Core Concept")
            p_topic_key = payload_dict.get("topic_key") or topic_key or f"dyn_{int(time.time())}"
            p_dur = payload_dict.get("duration_seconds") or 45
            p_scenes = payload_dict.get("scenes") or []

            # Resolve subject_id if needed
            if not p_subj_id and payload_dict.get("subject_code"):
                s_res = await session.execute(select(Subject).where(Subject.code == payload_dict.get("subject_code")))
                s_obj = s_res.scalar_one_or_none()
                if s_obj:
                    p_subj_id = s_obj.id

            if not p_subj_id:
                p_subj_id = 1 # Safe default subject

            # Ensure unique topic_key in DB
            check_res = await session.execute(select(MicroLesson).where(MicroLesson.topic_key == p_topic_key))
            if check_res.scalar_one_or_none():
                p_topic_key = f"{p_topic_key}_{uuid.uuid4().hex[:6]}"

            lesson = MicroLesson(
                subject_id=p_subj_id,
                module_id=p_mod_id,
                co_code=p_co_code,
                topic_key=p_topic_key,
                title=p_title,
                duration_seconds=p_dur,
                scenes_json=json.dumps(p_scenes),
                video_status="queued"
            )
            session.add(lesson)
            await session.flush()
            await session.refresh(lesson)
        else:
            # Generate deterministic fallback micro-lesson for the requested subject/module
            if not subject_id and module_id:
                m_res = await session.execute(select(SubjectModule).where(SubjectModule.id == module_id))
                m_obj = m_res.scalar_one_or_none()
                if m_obj:
                    subject_id = m_obj.subject_id
                    co_code = m_obj.co_code

            subj_code = "CS301"
            if subject_id:
                s_res = await session.execute(select(Subject).where(Subject.id == subject_id))
                s_obj = s_res.scalar_one_or_none()
                if s_obj:
                    subj_code = s_obj.code

            p_co = co_code or "CO3"
            p_topic = topic or f"{subj_code} {p_co} Core Learning Area"
            p_topic_key = topic_key or f"{subj_code.lower()}_{p_co.lower()}_{uuid.uuid4().hex[:6]}"

            fallback_scenes = [
                {
                    "scene_id": 1,
                    "type": "concept",
                    "title": f"Foundation of {p_topic}",
                    "duration_seconds": 12,
                    "narration": f"Welcome to the essential overview of {p_topic}.",
                    "body": f"Mastering {p_topic} is critical for understanding core concepts in {subj_code}.",
                    "key_takeaway": f"Foundational understanding of {p_topic}."
                },
                {
                    "scene_id": 2,
                    "type": "mechanism",
                    "title": "Core Mechanism & Analysis",
                    "duration_seconds": 15,
                    "narration": f"Here is how {p_topic} works during execution.",
                    "body": f"Key mechanical steps and logical execution path for {p_topic}.",
                    "key_takeaway": "Understand step-by-step logic."
                },
                {
                    "scene_id": 3,
                    "type": "takeaway",
                    "title": "Summary & Exam Application",
                    "duration_seconds": 10,
                    "narration": f"Remember these key principles for your {subj_code} assessment.",
                    "body": f"Essential formula and concept summary for {p_topic}.",
                    "key_takeaway": "Key concepts to remember."
                }
            ]

            lesson = MicroLesson(
                subject_id=subject_id or 1,
                module_id=module_id,
                co_code=p_co,
                topic_key=p_topic_key,
                title=p_topic,
                duration_seconds=37,
                scenes_json=json.dumps(fallback_scenes),
                video_status="queued"
            )
            session.add(lesson)
            await session.flush()
            await session.refresh(lesson)

    # 3. Security / RBAC Check
    if student_id and lesson.subject_id:
        enr_res = await session.execute(
            select(StudentEnrollment).where(
                and_(
                    StudentEnrollment.student_id == student_id,
                    StudentEnrollment.subject_id == lesson.subject_id
                )
            )
        )
        if not enr_res.scalars().first():
            raise PermissionError(f"Student ID {student_id} is not enrolled in subject ID {lesson.subject_id}")

    # 4. Resolve Metadata & Compute Content Hash
    subject_code = "CS"
    if lesson.subject_id:
        s_res = await session.execute(select(Subject).where(Subject.id == lesson.subject_id))
        s_obj = s_res.scalar_one_or_none()
        if s_obj:
            subject_code = s_obj.code

    lesson_co = lesson.co_code or "CO3"
    scenes = json.loads(lesson.scenes_json) if isinstance(lesson.scenes_json, str) else lesson.scenes_json
    current_hash = compute_lesson_content_hash(subject_code, lesson_co, lesson.topic_key, lesson.title, scenes)

    # 5. Determine Video File Target
    if lesson.video_path:
        out_name = Path(lesson.video_path).name
    else:
        out_name = f"{subject_code.lower()}_{lesson_co.lower()}_{lesson.topic_key}.mp4"

    target_file = LESSONS_VIDEO_DIR / out_name

    # 6. Check Cached MP4 Video
    if not force_regenerate and target_file.exists():
        is_valid, _ = validate_mp4_file(target_file)
        hash_matched = (lesson.video_content_hash == current_hash) if lesson.video_content_hash else True

        if is_valid and hash_matched:
            lesson.video_path = f"lessons/{out_name}"
            lesson.video_status = "ready"
            lesson.video_content_hash = current_hash
            if not lesson.video_duration:
                lesson.video_duration = lesson.duration_seconds
            await session.commit()

            return {
                "job_id": f"cached_{lesson.id}",
                "lesson_id": lesson.id,
                "topic_key": lesson.topic_key,
                "status": "ready",
                "progress_pct": 100,
                "video_url": f"/media/lessons/{out_name}",
                "duration_seconds": lesson.video_duration or lesson.duration_seconds,
                "error_message": None,
                "retryable": True
            }

    # 7. Video Needs Generation / Regeneration
    if not VIDEO_RENDERING_AVAILABLE:
        missing = []
        if not PILLOW_AVAILABLE:
            missing.append("Pillow")
        if not FFMPEG_AVAILABLE:
            missing.append("imageio-ffmpeg / FFmpeg")
        dep_err = f"Video rendering engine unavailable: Missing required dependency ({', '.join(missing)})."
        return {
            "job_id": f"failed_{lesson.id if lesson else 'gen'}",
            "lesson_id": lesson.id if lesson else None,
            "topic_key": lesson.topic_key if lesson else (topic_key or "unknown"),
            "status": "failed",
            "progress_pct": 0,
            "video_url": None,
            "duration_seconds": None,
            "error_message": dep_err,
            "retryable": False
        }

    lesson_data = {
        "title": lesson.title,
        "subject_code": subject_code,
        "co_code": lesson_co,
        "scenes": scenes
    }

    if background:
        job_id = create_video_job(topic_key=lesson.topic_key, lesson_id=lesson.id)
        lesson.video_status = "rendering"
        await session.commit()

        async def _bg_worker():
            try:
                path, dur = await render_microlesson_video(lesson_data, out_name, job_id=job_id)
                async with AsyncSessionLocal() as bg_session:
                    res = await bg_session.execute(select(MicroLesson).where(MicroLesson.id == lesson.id))
                    l_obj = res.scalar_one_or_none()
                    if l_obj:
                        l_obj.video_path = f"lessons/{out_name}"
                        l_obj.video_status = "ready"
                        l_obj.video_duration = int(dur)
                        l_obj.video_content_hash = current_hash
                        l_obj.video_generated_at = datetime.datetime.utcnow()
                        l_obj.video_error = None
                        await bg_session.commit()
            except Exception as e:
                if job_id in _video_jobs:
                    _video_jobs[job_id]["status"] = "failed"
                    _video_jobs[job_id]["error_message"] = str(e)
                async with AsyncSessionLocal() as bg_session:
                    res = await bg_session.execute(select(MicroLesson).where(MicroLesson.id == lesson.id))
                    l_obj = res.scalar_one_or_none()
                    if l_obj:
                        l_obj.video_status = "failed"
                        l_obj.video_error = str(e)
                        await bg_session.commit()

        asyncio.create_task(_bg_worker())

        return {
            "job_id": job_id,
            "lesson_id": lesson.id,
            "topic_key": lesson.topic_key,
            "status": "queued",
            "progress_pct": 0,
            "video_url": None,
            "duration_seconds": None,
            "error_message": None,
            "retryable": True
        }
    else:
        # Synchronous execution
        path, dur = await render_microlesson_video(lesson_data, out_name)
        lesson.video_path = f"lessons/{out_name}"
        lesson.video_status = "ready"
        lesson.video_duration = int(dur)
        lesson.video_content_hash = current_hash
        lesson.video_generated_at = datetime.datetime.utcnow()
        lesson.video_error = None
        await session.commit()

        return {
            "job_id": f"synced_{lesson.id}",
            "lesson_id": lesson.id,
            "topic_key": lesson.topic_key,
            "status": "ready",
            "progress_pct": 100,
            "video_url": f"/media/lessons/{out_name}",
            "duration_seconds": int(dur),
            "error_message": None,
            "retryable": True
        }


async def pre_render_demo_showcase_videos():
    """
    CLI utility: Renders and verifies showcase demonstration videos for pre-caching.
    Dynamically maps subjects and modules without hardcoded IDs.
    """
    print("============================================================")
    print("NexuxEdu Video Subsystem Capability Status:")
    cap = get_video_capability_status()
    for k, v in cap.items():
        print(f"  - {k}: {v}")
    print("============================================================")

    if not VIDEO_RENDERING_AVAILABLE:
        print("Notice: Video rendering dependencies are unavailable. Skipping pre-generation.")
        return

    print("Checking showcase demo micro-lessons for video pre-rendering...")
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(MicroLesson).options(
                selectinload(MicroLesson.subject),
                selectinload(MicroLesson.module)
            )
        )
        lessons = res.scalars().all()

        for ml in lessons:
            try:
                res = await ensure_learning_video(
                    session=session,
                    lesson_id=ml.id,
                    background=False
                )
                print(f"Verified/Generated video for {ml.topic_key} -> {res.get('video_url')}")
            except Exception as e:
                print(f"Failed rendering {ml.topic_key}: {e}")

        await session.commit()


if __name__ == "__main__":
    asyncio.run(pre_render_demo_showcase_videos())
