# NexuxEdu — Hybrid AI Learning Video System Architecture

## 1. Architectural Philosophy & Overview

The **NexuxEdu Hybrid AI Learning Video System** extends the Student Academic Support pipeline by transforming structured concept explanations into multi-modal educational assets. 

Rather than treating interactive lessons, video generation, and external reference material as disconnected subsystems, NexuxEdu establishes **MicroLesson JSON as the immutable Single Source of Truth (SSOT)**.

```
                                [ Student Highlight & Explain ]
                                               │
                                               ▼
                             ┌───────────────────────────────────┐
                             │  Academic RAG & Grounding Engine  │
                             │  - Token-bound RBAC Context       │
                             │  - Vector + Page Chunk Retrieval  │
                             │  - Structured MicroLesson JSON    │
                             └─────────────────┬─────────────────┘
                                               │
                                               ▼
                      ┌─────────────────────────────────────────────────┐
                      │          MicroLesson JSON (Single SSOT)         │
                      │  - Title, Subject, Module, CO, Source Citation   │
                      │  - Ordered Scenes (Concept, Diagram, Table, etc.)│
                      │  - Narration Script & Per-Scene Durations       │
                      │  - Curated YouTube Resource Metadata            │
                      │  - Video Cache Reference (`video_url`)          │
                      └────────┬───────────────┼───────────────┬────────┘
                               │               │               │
            ┌──────────────────┘               │               └──────────────────┐
            ▼                                  ▼                                  ▼
┌───────────────────────┐          ┌───────────────────────┐          ┌───────────────────────┐
│   Interactive Mode    │          │  Narrated Video (MP4) │          │  Related Lecture      │
│  (Default / Instant)  │          │  (Async / Streamable) │          │  (Curated External)   │
│                       │          │                       │          │                       │
│ - Step-by-step viewer │          │ - Neural Voice (Edge) │          │ - NPTEL / MIT / Gate  │
│ - Visual diagrams     │          │ - 720p 30fps H.264/AAC│          │   Smashers / Bari     │
│ - Code & comparisons  │          │ - Scene chapter jumps │          │ - Embedded player     │
│ - Zero latency        │          │ - Disk-cached payload │          │ - Clearly labeled 3rd │
└───────────────────────┘          └───────────────────────┘          │   party resource      │
                                                                      └───────────────────────┘
```

---

## 2. Canonical Video Renderer & Dependency Architecture

### Authoritative Engine: Python Canvas Video Engine (`backend/app/services/video_generator.py`)

The **Python Canvas Video Engine** is the **canonical production renderer** for NexuxEdu.

The canonical renderer requires Python video dependencies (`Pillow`, `imageio-ffmpeg`, `edge-tts`) but does **not** require Node.js, Chromium, browser automation, or Remotion for production rendering.

### Production Dependencies (`backend/requirements.txt`):
```text
Pillow>=10.2.0
imageio-ffmpeg>=0.4.9
edge-tts>=6.1.10
```

### Installation (One-Step Setup):
```powershell
pip install -r backend/requirements.txt
```

### Capability Detection & Graceful Degradation:
The video engine defines explicit subsystem capability flags:
- `VIDEO_RENDERING_AVAILABLE`: True when both `Pillow` and `FFmpeg` are available.
- `PILLOW_AVAILABLE`: True when PIL module is importable.
- `FFMPEG_AVAILABLE`: True when `imageio-ffmpeg` static binary or system `ffmpeg` is located.
- `EDGE_TTS_AVAILABLE`: True when `edge_tts` module is importable.
- `TTS_AVAILABLE`: True (guaranteed by built-in offline tone synthesizer).

If video rendering dependencies are missing on a deployment server:
1. **Core ERP Remains 100% Operational:** FastAPI boots cleanly without error. Authentication, student marks, Course Outcome analytics, and academic RAG text explanations function normally.
2. **Predictable Video API Response:** Calls to generate unseeded videos return a structured `{ "status": "failed", "retryable": false, "error_message": "..." }` response rather than crashing or throwing unhandled HTTP 500 errors.
3. **Cached MP4 Playback Still Works:** Pre-rendered showcase videos remain streamable even if generator dependencies are uninstalled.

### Why Python Canvas is Canonical:
1. **Self-Contained Portability:** Leverages `Pillow` and `imageio-ffmpeg` (which bundles static FFmpeg). It requires no headless Chrome, Puppeteer, or external rendering microservices.
2. **Direct Asynchronous Integration:** Runs seamlessly inside FastAPI's execution loop, sharing in-memory database connections and SQLAlchemy session models directly.
3. **Cross-Platform Determinism:** Produces identical 720p 30fps progressive H.264 (High Profile) / AAC audio MP4 output across Windows PowerShell, Linux, WSL2, and macOS.
4. **Native TTS Integration:** Synthesizes and measures audio segment durations on the fly via `TTSProvider`, assembling perfectly synchronized video frames and audio channels without sub-process overhead.
5. **High Render Speed:** Renders educational slides, code blocks, diagrams, and comparison tables at ~15–20 fps, producing a complete 2-minute video in ~5–10 seconds.

### How Cached Videos are Produced:
```powershell
$env:PYTHONPATH="backend"
.\.venv\Scripts\python.exe backend/app/services/video_generator.py
```
This CLI reports system capability status, verifies/pre-renders all showcase database micro-lessons, and updates their `video_path`, `video_status="ready"`, and `video_duration` in SQLite.

---

## 3. Secondary Video Renderer

### Framework: Remotion React Video Project (`video/`)

The **Remotion framework** under `video/` is retained as an **optional advanced motion graphics and preview renderer**.

### Role & Purpose of the Secondary Renderer:
- **Motion Graphics Experimentation:** Provides a React 19 + Tailwind CSS environment for testing advanced spring physics, typography animations, and particle effects.
- **Developer Preview Studio:** Developers can run `npm run start` inside `video/` to inspect scenes frame-by-frame in the Remotion Visual Previewer.
- **Shared MicroLesson Contract:** Consumes the identical `MicroLessonPayload` schema (`title`, `subject_code`, `co_code`, `scenes`), ensuring zero architectural drift between engines.

---

## 4. Generated Media Policy

### Storage Location & Classification
- **Cached Showcase MP4s:** Stored in `backend/media/lessons/` (e.g., `cs301_co3_os_memory_paging_tlb.mp4`, `cs304_co3_algo_avl_rotations.mp4`).
- **Temporary Audio Cache:** Stored in `backend/media/audio/` (SHA-256 hashed `.mp3` / `.wav` voice chunks).
- **Temporary Scratch Frames:** Stored in `backend/media/temp/`.

### Git Handling & Versioning Policy:
1. **Source Code & Metadata Versioned:** All model definitions, seeds, TTS engines, renderer scripts, and YouTube metadata are 100% version-controlled.
2. **Deterministic Regeneration:** Any MP4 can be regenerated on demand in seconds via `video_generator.py`.
3. **Generated Media Exclusion:**
   - `.gitignore` explicitly ignores `backend/media/audio/`, `backend/media/temp/`, `video/node_modules/`, and `video/out/`.
   - The 5 showcase MP4s total only ~4.4 MB and serve offline hackathon demo requirements, while `.gitignore` ensures temporary and runtime render jobs never pollute Git tracking.

---

## 5. Metadata Consistency & Academic Grounding

Every layer of NexuxEdu enforces strict 1-to-1 consistency across the academic data model:

$$\text{Subject} \longrightarrow \text{SubjectModule (CO)} \longrightarrow \text{LearningMaterial} \longrightarrow \text{MicroLesson} \longrightarrow \text{Video Asset}$$

### Course Code Authority (CS304):
The authoritative course code for **Design and Analysis of Algorithms** across all database entities is **`CS304`**:
- `Subject.code`: `"CS304"` (Semester 6, Credits 4)
- `SubjectModule.co_code`: `"CO3"` ("Greedy Strategies & Balanced Trees")
- `MicroLesson.subject_id`: `4` (`CS304`)
- `MicroLesson.topic_key`: `"algo_avl_rotations"`
- `MicroLesson.video_path`: `"lessons/cs304_co3_algo_avl_rotations.mp4"`
- `MicroLesson.youtube_resource`: Abdul Bari — *AVL Tree Insertion and Rotations*

---

## 6. Pre-Seeded Video Courseware Catalog

Five core computer science modules are pre-rendered, cached on disk in `backend/media/lessons/`, and pre-configured with curated YouTube lecture references:

| Subject | Module / CO | Topic | Cached MP4 File | Size | Duration | Curated YouTube Channel |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Operating Systems (CS301)** | CO3: Memory Management | TLB & Effective Access Time | `cs301_co3_os_memory_paging_tlb.mp4` | 1.35 MB | 70.5s | MIT / Gate Smashers |
| **Operating Systems (CS301)** | CO3: Memory Management | Virtual Memory & Page Replacement | `cs301_co3_os_virtual_memory_page_replacement.mp4` | 865 KB | 44.1s | Gate Smashers |
| **Database Management (CS302)** | CO3: Relational Normalization | BCNF vs 3NF Decomposition | `cs302_co3_dbms_normalization_bcnf.mp4` | 860 KB | 45.1s | Gate Smashers |
| **Design & Analysis of Algo (CS304)** | CO3: Balanced Search Trees | AVL Tree Rotations (LL, RR, LR, RL) | `cs304_co3_algo_avl_rotations.mp4` | 777 KB | 42.2s | Abdul Bari |
| **Computer Networks (CS303)** | CO3: Network Layer Routing | Dijkstra Link-State Routing | `cs303_co3_net_dijkstra_routing.mp4` | 483 KB | 27.5s | Computerphile / NPTEL |

---

## 7. WSL / Windows Developer Workflow

NexuxEdu requires **zero platform-specific hacks** or container prerequisites:

### Windows Developer Environment (Default)
- **Backend & Video Generation:** Runs directly in Windows PowerShell via `.\.venv\Scripts\python.exe`.
- **FFmpeg Binary:** Automatically resolved from the self-contained `imageio-ffmpeg` package (bundles `ffmpeg-win-x86_64-v7.1.exe`).
- **Frontend App:** Runs via `npm.cmd run dev` on port 3000.
- **Browser Playback:** Edge, Chrome, and Firefox natively decode H.264 High Profile / AAC streams with zero lag.

### Linux / WSL2 Developer Environment
- **Backend & Video Generation:** Runs via `./.venv/bin/python`.
- **FFmpeg Binary:** Automatically resolves the platform-appropriate Linux static binary from `imageio-ffmpeg`.
- **Headless Mode:** Completely functional without X11 or DISPLAY server configuration.

---

## 8. Neural Text-To-Speech (TTS) Engine & Caching

The TTS subsystem is designed with a pluggable provider interface (`TTSProvider` in `backend/app/services/tts_provider.py`):

1. **`EdgeTTSProvider` (Primary / Default):**
   - Uses Microsoft Edge Neural TTS (`edge-tts`) with conversational neural voices (`en-US-ChristopherNeural` for instructors, `en-US-AriaNeural` for clear enunciations).
   - Generates broadcast-quality MP3 audio with natural prosody and academic cadence.
   - Requires **zero API keys** and runs completely free with local async synthesis.

2. **`ElevenLabsTTSProvider` (Optional Cloud Enhancement):**
   - Automatically activates if `ELEVENLABS_API_KEY` is present in environment variables.
   - Routes requests to ElevenLabs Voice API with studio-quality expressiveness.

3. **`OfflineFallbackTTSProvider` (Guaranteed Local Fallback):**
   - Automatically activates if network connectivity is unavailable or external synthesis fails.
   - Generates valid PCM audio with programmatic frequency modulation matching scene narration length.
   - Ensures the video encoding pipeline never crashes even in strict offline/air-gapped environments.

---

## 9. Frontend User Experience (`MicroLessonPlayer.tsx`)

The student learning player includes three dedicated viewing modes:

1. **Interactive Mode (Default):**
   - Instant zero-latency lesson stepper.
   - Interactive scene navigation (Next, Prev, Scene index pills).
   - Visual step diagrams, code blocks, and key takeaways.
   - Direct link to jump into video mode.

2. **Watch Video Mode:**
   - HTML5 Video Player with controls, autoplay option, and progress timeline.
   - **Scene Chapter Jump Bookmarks:** Clickable scene pills below the player calculate exact timestamp offsets ($t = \sum_{i=0}^{k-1} d_i$) and seek video playback directly.
   - Real-time generation trigger & polling indicator for unrendered custom lessons.
   - Download MP4 button for offline study.

3. **Related Lecture Mode:**
   - Responsive 16:9 embedded YouTube player (`youtube-nocookie.com`).
   - Clearly displays Channel Name, Duration, and Covered Topics.
   - Prominent disclaimer: *"External Educational Resource — Curated to supplement your course material."*

---

## 10. Security, RBAC & Data Isolation

- **Student Identity Binding:** All video requests extract student identity directly from verified JWT claims (`claims.student_id`).
- **Enrollment Validation:** Students cannot trigger video generation or view lessons for subjects they are not enrolled in ($403\text{ Forbidden}$).
- **Path Traversal Protection:** Static media serving (`/media`) uses strict file path resolution within `backend/media/`, rejecting directory traversal probes (`../`).
- **Offline Safety:** No user data or student PII is transmitted to third-party endpoints.

---

## 11. Verification Commands

```powershell
# Run full backend test suite (56 tests across analytics, RAG, hybrid video, YouTube, and dependencies)
$env:PYTHONPATH="backend" ; .\.venv\Scripts\python.exe -m unittest discover -s backend/tests -v

# Run Next.js production build
npm.cmd run build --prefix frontend

# Verify dependency imports
.\.venv\Scripts\python.exe -c "from PIL import Image; import imageio_ffmpeg; import edge_tts; print('Video dependencies OK')"

# Re-render showcase videos & inspect capability
$env:PYTHONPATH="backend" ; .\.venv\Scripts\python.exe backend/app/services/video_generator.py
```
