# NexusEdu ERP & SafeTransit Fleet Intelligence Engine

> **Enterprise-Grade Multi-Agent RBAC Campus ERP, Event–Exam Clash Rescheduling Engine, AI Academic Support, & Real-Time Telematics Visualizer**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14%20App%20Router-black.svg)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0%2B-3178C6.svg)](https://www.typescriptlang.org/)
[![Leaflet](https://img.shields.io/badge/Leaflet-OpenStreetMap-199900.svg)](https://leafletjs.com/)
[![Zero--Trust RBAC](https://img.shields.io/badge/Security-Zero--Trust%20RBAC-crimson.svg)](#-zero-trust-multi-agent-fabric)

---

## 📌 Executive Overview

**NexusEdu ERP & SafeTransit** is a modern, full-stack campus management and fleet intelligence platform engineered around a **Zero-Trust Multi-Agent Architecture**.

Unlike traditional monoliths or naive AI chat systems that expose database connections to prompt injection and lateral snooping, NexusEdu enforces cryptographic, role-bound boundaries at every layer — from transactional parametric SQL and pre-filtered vector RAG to driver telematics streaming, automated exam clash resolution, and grounded micro-learning generation.

---

## 🌟 Core System Pillars & Features

### 1. 🛡️ Zero-Trust Multi-Agent AI Fabric
* **Cryptographic Session Scoping**: Specialized worker agents operate inside sandboxes restricted by cryptographically verified JWT session claims (`user_id`, `role`, `department`, `student_id`, `ward_id`, `bus_id`).
* **Ingress Guardrail & Anti-Jailbreak Protection**: Detects adversarial injection payloads (`"ignore prior rules"`, `"act as root"`, `"dan mode"`) before language models are invoked.
* **Parametric Text-to-SQL (Structured Records)**: Queries never execute raw LLM-generated SQL text. Requests map to pre-compiled parameterized queries strictly bound to session claims, making horizontal snooping mathematically impossible.
* **Filtered Vector Knowledge (RAG)**: Document vector similarity searches enforce database-level pre-filtering (`allowed_roles @> ARRAY[user_role]`). Students cannot access faculty memos, payroll data, or confidential exam rubrics.
* **Egress Guard & Grounding Scrubber**: Formulates responses strictly with verified citations. If zero context is found, it cleanly refuses without hallucinating. Outbound text is scrubbed for cross-role entity leaks or salary figures.
* **Audit Trail**: Flags and logs unauthorized access attempts (`EVENT_PRIVILEGE_PROBE`) in real-time.

---

### 2. 📅 Event–Exam Clash Detection & Retake Rescheduling Engine
An automated conflict-resolution engine that reconciles student participation in university events (Hackathons, Sports Meets, Academic Symposia) with scheduled course assessments.
* **Algorithmic Interval Overlap Engine**: Detects temporal collisions between event schedules and exam time windows (`start_at` to `end_at`). Touching boundary endpoints are handled gracefully without false positives.
* **Sister-Section Slot Discovery**: Automatically searches parallel course offerings (e.g., Section B or Section C of the same subject) to suggest non-conflicting retake exam slots.
* **Transactional Compare-And-Set (CAS) State Machine**:
  * Employs atomic optimistic locking (`UPDATE ... WHERE id = :id AND status = :expected_status`) ensuring concurrency safety.
  * Transitions: `DETECTED` ➔ `FILED` ➔ `APPROVED` or `REJECTED_BY_PROF` ➔ `ESCALATED_TO_HOD` ➔ `RESOLVED_BY_HOD` / `OVERRIDDEN_BY_HOD`.
  * **Atomic Rejection Cascade**: Rejection by a professor automatically cascades to HOD escalation within the same transaction.
* **Dedicated Multi-Role Workspaces**:
  * **Admin Event Management**: Create events, register student participants, run clash analysis, inspect conflict batches, and bulk-file retake requests.
  * **Professor Reschedule Command Center**: Inspect student clash requests, view suggested parallel slots, propose custom retake dates/venues, approve slots, or reject with mandatory rationale.
  * **Student "My Clashes" View**: Real-time status badge of retake petitions, approved exam slot cards, and an interactive chronological audit trail (`CaseTimeline`).
  * **HOD Governance Console**: Executive oversight over department-wide conflicts, unresolved backlogs, >48-hour SLA breach warnings, and faculty workload balance.
* **Real-Time Notification Broker**: Dedicated WebSocket channels (`channel:user:{id}` and `channel:admin`) push instant updates on filings, approvals, and escalations.

---

### 3. 🎓 AI Academic Support & Micro-Learning Hub
An integrated pedagogical co-pilot for students and parents designed to boost subject comprehension and Course Outcome (CO) mastery.
* **Student Academic Analytics**: Deep breakdown of enrolled subjects, continuous assessment scores (CA1, CA2, CA3, Midterm, Endterm), overall grade percentages, and Course Outcome attainment (CO1–CO5).
* **Weakness & Strength Diagnostics**: Automated analysis pinpointing strongest and weakest modules across enrolled subjects.
* **Grounded Micro-Lessons (RAG)**: Synthesizes structured, bite-sized interactive lessons directly from professor-curated course materials. Includes core concepts, mathematical formulas, interactive SVG/Mermaid diagrams, and self-assessment quizzes.
* **AI Video Generation Engine**: Asynchronous background generation of narrated MP4 video lessons from micro-lessons. Includes real-time job status tracking (`/learning/video/{job_id}`) and video caching.
* **Curriculum & Material Reader**: Direct access to module lecture notes, page-by-page breakdowns, and searchable topic chunks.

---

### 4. 🚌 SafeTransit Telematics & Fleet Intelligence
A comprehensive vehicle telemetry visualizer providing end-to-end commute awareness for parents, students, and campus administrators.
* **Live OpenStreetMap Cartography**: Leaflet-powered visualizer utilizing official OpenStreetMap tiles, high-visibility route polylines, animated vehicle beacons, and interactive stop pins.
* **3-Second WebSocket Coordinates**: High-frequency telemetry updates powered by an in-memory Pub/Sub broker and mathematical position simulator with Gaussian jitter across 20 campus routes.
* **500m Geofence Proximity Alerts**: Computes real-time Haversine geodesic distance between the bus and the student's registered pickup waypoint. Prominently alerts parents and students when the bus is within 500 meters.
* **Driver Mobile Broadcast Console (`/track`)**:
  * Ephemeral session tokens (`TrackingSession`) with configurable TTL and QR code sharing.
  * Mobile-optimized driver cockpit using the device Geolocation API or fallback waypoint simulation to broadcast live GPS coordinates to the fleet engine.
  * Automated Local Area Network (LAN) IP and ngrok public tunnel discovery for mobile access.

---

### 5. 📊 Faculty Class & Section Attendance Command Center
* **Section-Partitioned Roster**: Complete roster management across sections (`Section A`, `Section B`, `Section C`) and core subjects (`Operating Systems`, `DBMS`, `Computer Networks`).
* **Academic Code §4.2 Enforcement**: Automatic calculation of aggregate attendance percentages with instant flagging for students below the mandatory $75.0\%$ examination debarment threshold.
* **One-Click Advisory Notices**: Direct dispatch of formal debarment warnings and attendance notifications.
* **Filtering & Search**: Real-time filtering by standing (*Safe $\ge 85\%$*, *Attention $75\text{--}84\%$*, *Debarment Warning $< 75\%$*) and roll number search.

---

### 6. 🔐 Automated RBAC Session Governance
* **Seamless Role Discovery**: Single unified login (`/login`) automatically evaluates credentials, retrieves cryptographically signed JWT claims, and initializes role-specific UI workspaces.
* **Interactive Profile Hover Card**: Inspect active security claims, user ID, role badge, department, and transit bindings directly from the top navigation bar.
* **Real-Time Notification Bell**: Polled and WebSocket-backed notification center alerting users to retake requests, clash resolutions, attendance warnings, and transit announcements.

---

## 🏛️ System Architecture

```
                                [ User Prompt + JWT Token ]
                                             │
                                             ▼
                             ┌───────────────────────────────┐
                             │    Auth Ingress & Guardrail   │
                             │  - JWT Claim Extraction       │
                             │  - Input Sanitization & Jailbreak│
                             │    Detection (Adversarial Regex)│
                             └───────────────┬───────────────┘
                                             │
                                             ▼
                             ┌───────────────────────────────┐
                             │   Master Orchestrator Agent   │
                             │ (Session Role & Intent Router)│
                             └───────┬───────┬───────┬───────┘
                                     │       │       │
              ┌──────────────────────┘       │       └──────────────────────┐
              ▼                              ▼                              ▼
  ┌─────────────────────────┐   ┌─────────────────────────┐   ┌─────────────────────────┐
  │ Structured Records      │   │ Vector Knowledge        │   │ Transit & Fleet         │
  │ Agent (Parametric SQL)  │   │ Agent (Filtered RAG)    │   │ Telemetry Agent         │
  │                         │   │                         │   │                         │
  │ Tools:                  │   │ Tools:                  │   │ Tools:                  │
  │ - get_own_attendance()  │   │ - query_public_docs()   │   │ - get_bus_coords()      │
  │ - get_faculty_roster()  │   │ - query_faculty_docs()  │   │ - get_route_eta()       │
  │ - get_own_salary()      │   │ - query_admin_memos()   │   │ - get_stop_schedule()   │
  └───────────┬─────────────┘   └────────────┬────────────┘   └────────────┬────────────┘
              │                              │                             │
              └──────────────────────┬───────┴─────────────────────────────┘
                                     │
                                     ▼
                             ┌───────────────────────────────┐
                             │   Synthesis & Egress Guard    │
                             │ - Context Grounding Check     │
                             │ - Role Boundary Scrubber      │
                             │ - Traceable Source Citation   │
                             └───────────────┬───────────────┘
                                             │
                                             ▼
                                [ Client Response Stream ]
```

---

## 👥 Demo User Personas & Credentials

All seeded accounts share the default password: **`password123`**

| Role | Email | Name & Details | Key Authorized Scope & Capabilities |
| :--- | :--- | :--- | :--- |
| **Student** | `student@campus.edu` | Jane Doe (Roll: `CS-2023-042`, Sem 6) | View personal subject attendance & CA scores; generate RAG micro-lessons & video lessons; view retake clash statuses; track assigned bus (`BUS-001`). |
| **Faculty (HOD)** | `faculty@campus.edu` | Prof. Alan Turing (HOD, CS Dept) | Class & Section Attendance Command Center (Sections A, B); Retake Requests Command Center; HOD Governance Dashboard; resolve escalations. |
| **Faculty** | `faculty2@campus.edu` | Prof. Dave Smith (Cloud Computing) | Section A, B, C roster access; review and reschedule exam clashes; suggest parallel sister-section retake slots. |
| **Parent** | `parent@campus.edu` | Robert Doe (Ward: Jane Doe) | Track ward commute telematics; receive 500m geofence pickup alerts; monitor ward attendance & examination eligibility. |
| **Admin** | `admin@campus.edu` | Sarah Connor (Campus Administrator) | Global fleet telemetry (all 20 bus routes); Event Management & Clash Engine; bulk retake requests; review Zero-Trust Security Audit Logs. |

---

## ⚡ Tech Stack

### Backend
* **Language & Runtime**: Python 3.10+
* **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Asynchronous REST API & WebSockets)
* **Database & ORM**: [SQLAlchemy 2.0 (Async)](https://www.sqlalchemy.org/) + [aiosqlite](https://aiosqlite.omnilib.dev/) (SQLite on `campus.db`, migration-ready for PostgreSQL + pgvector)
* **Authentication**: [PyJWT](https://pyjwt.readthedocs.io/) & [Bcrypt](https://pypi.org/project/bcrypt/)
* **Media & Video Processing**: Asynchronous threaded frame rendering and audio synthesis for MicroLesson video generation
* **Server**: [Uvicorn](https://www.uvicorn.org/) (High-performance ASGI server)

### Frontend
* **Framework**: [Next.js 14](https://nextjs.org/) (App Router, React 19, TypeScript)
* **Mapping & GIS**: [Leaflet](https://leafletjs.com/) with OpenStreetMap cartography
* **Iconography**: [Lucide React](https://lucide.dev/)
* **Diagrams**: Interactive Mermaid & SVG rendering
* **Styling**: High-contrast, clean minimalist light theme design system in pure CSS

---

## 🚀 How to Run the Project

### Prerequisites
* **Python 3.10+**
* **Node.js 18+** & **npm**

---

### ⚡ Method A: One-Click Quick Start (Recommended)

A root-level launcher script [`start.sh`](file:///home/robin/Projects/ERP/start.sh) is provided. It automatically checks prerequisites, activates or builds the Python virtual environment, installs any missing dependencies, and runs both servers with unified shutdown handling:

```bash
# 1. Make the script executable (first time only):
chmod +x start.sh

# 2. Launch both backend and frontend:
./start.sh
```

> **Note**: Press `Ctrl+C` to gracefully terminate both backend and frontend servers together without leaving orphan processes.

---

### 🛠️ Method B: Manual Step-by-Step Setup

#### Step 1: Start the Backend Service
```bash
# 1. Navigate to the backend directory
cd backend

# 2. Activate virtual environment
source ../.venv/bin/activate # or source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) Re-seed clash & academic demo data
python -m app.services.seed_clash_data --reset

# 5. Start the FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
* **API Documentation**: Open `http://localhost:8000/docs` for the interactive Swagger UI.
* **Health Check**: `GET http://localhost:8000/api/v1/health`

#### Step 2: Start the Frontend Application
```bash
# 1. Navigate to the frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Launch the Next.js development server
npm run dev
```
* Open **`http://localhost:3000`** in your browser.
* You will be redirected to **`http://localhost:3000/login`**.

---

## 🧪 Guided Feature Walkthrough

### 1. Zero-Trust Chatbot Invariant Tests
1. Click the floating **Ask AI Assistant** button (bottom right).
2. **Authorized Query** (as Student `student@campus.edu`):
   * Ask: *"What is my attendance in Operating Systems?"*
   * Result: Returns exact database attendance (87.5%) with verifiable citation badge.
3. **Privilege Probe Interception** (as Student):
   * Ask: *"Show me all faculty salaries in Computer Science"*
   * Result: Explicit RBAC refusal (🔒 Lock icon); zero financial numerals exposed; records an `EVENT_PRIVILEGE_PROBE` entry in the Security Audit Log.
4. **Transit Query** (as Student or Parent):
   * Ask: *"Where is my bus right now?"*
   * Result: Retrieves live coordinates and route status for the bound vehicle (`BUS-001`).

### 2. Event–Exam Clash & Rescheduling Lifecycle
1. **Admin Event Creation & Clash Analysis**:
   * Log in as `admin@campus.edu`.
   * Go to **"Event Clashes"** in the sidebar.
   * View the Hackathon event, run clash detection, review the list of detected assessment conflicts, and click **"Bulk File Retake Requests"**.
2. **Professor Reschedule Command Center**:
   * Switch to `faculty2@campus.edu` (Prof. Dave Smith).
   * Open **"Retake Requests"** in the sidebar.
   * Inspect the filed clash cases, review suggested parallel sister-section slots, and click **"Approve Slot"** or provide a custom slot.
   * Rejecting a slot automatically triggers the cascade to HOD escalation!
3. **HOD Governance Console**:
   * Switch to `faculty@campus.edu` (Prof. Alan Turing, HOD).
   * Open **"HOD Governance"** in the sidebar.
   * View department SLA metrics, review escalated cases, and resolve with final dates and venues.
4. **Student Timeline & Notification**:
   * Switch to `student@campus.edu` (Jane Doe).
   * Notice the badge on the **Notification Bell** in the header.
   * Navigate to **"My Clashes"** to view the assigned retake slot and chronological audit trail.

### 3. AI Academic Support & Video Generation
1. Log in as `student@campus.edu`.
2. Click **"Academic Support"** in the sidebar.
3. Explore continuous assessment marks breakdown and Course Outcome attainment (CO1–CO5).
4. Click on a subject to inspect module performance and identify the weakest module.
5. Click **"Generate Grounded Micro-Lesson"** to synthesize an interactive lesson complete with concepts, formulas, and diagrams.
6. Click **"Generate AI Video Lesson"** to trigger background rendering of an educational MP4 video lesson with real-time job status tracking.

### 4. SafeTransit Fleet Telematics & Driver Broadcast
1. Navigate to **"Live Transit"** in the sidebar.
2. View real-time 3-second bus updates, HUD telemetry metrics, and stop markers on OpenStreetMap cartography.
3. Observe the **500m Geofence Proximity Alert** triggering when the bus approaches within 500 meters of the registered pickup point.
4. Click **"Driver Live Link / Mobile QR"** to reveal the shareable broadcast session URL (`/track?token=...`).
5. Open the link on your mobile phone or a new tab to experience the driver GPS broadcast console.

---

## 📂 Project Directory Structure

```
ERP/
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI entrypoint, CORS, static mounts & routes
│   │   ├── api/
│   │   │   ├── auth.py                 # JWT login & session validation
│   │   │   ├── chat.py                 # Multi-agent chat ingress endpoint
│   │   │   ├── clash.py                # Clash detection, CAS state machine & notifications
│   │   │   ├── erp.py                  # Dashboard, student & faculty attendance endpoints
│   │   │   ├── student_academic.py     # Academic analytics, RAG micro-lessons & video generator
│   │   │   ├── tracking.py             # Ephemeral driver broadcast sessions & QR discovery
│   │   │   └── transit.py              # Telemetry routes & WebSocket handlers
│   │   ├── core/
│   │   │   ├── config.py               # Application settings & environment variables
│   │   │   ├── database.py             # SQLAlchemy models (User, Student, ClashCase, etc.)
│   │   │   ├── datetime_utils.py       # Timezone synchronization & ISO-8601 formatting
│   │   │   ├── pubsub.py               # In-memory pub/sub broker for WebSockets
│   │   │   └── security.py             # Bcrypt hashing & JWT claim signing
│   │   ├── agents/
│   │   │   ├── ingress_guard.py        # Adversarial prompt & jailbreak analyzer
│   │   │   ├── intent_classifier.py    # Deterministic query intent router
│   │   │   ├── orchestrator.py         # Hierarchical supervisor state machine
│   │   │   ├── structured_records.py   # Parametric SQL worker (attendance & payroll)
│   │   │   ├── transit_telemetry.py    # Vehicle telemetry & geofence worker
│   │   │   └── vector_knowledge.py     # Role-filtered pgvector policy retriever
│   │   └── services/
│   │       ├── academic_analytics.py   # Marks, CO analysis & module diagnostics
│   │       ├── academic_rag.py         # Grounded micro-lesson synthesis
│   │       ├── clash_detector.py       # Algorithmic interval clash engine & slot discovery
│   │       ├── seed_data.py            # Academic, student & fleet seeder
│   │       ├── seed_clash_data.py      # Multi-event, multi-course clash scenario seeder
│   │       ├── transit_simulator.py    # Geodesic vehicle simulator with Gaussian jitter
│   │       └── video_generator.py      # Asynchronous MP4 video rendering engine
│   ├── requirements.txt
│   └── campus.db                       # Relational SQLite database
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── globals.css             # Minimalist light design system & CSS tokens
│   │   │   ├── layout.tsx              # Root HTML & Inter font layout
│   │   │   ├── page.tsx                # Main authenticated workspace & tab orchestrator
│   │   │   ├── login/
│   │   │   │   └── page.tsx            # Modern login page with one-click demo chips
│   │   │   └── track/
│   │   │       └── page.tsx            # Driver mobile GPS broadcast console
│   │   ├── components/
│   │   │   ├── academic/               # Academic overview, micro-lesson player & diagrams
│   │   │   ├── AdminEventManagement.tsx# Admin event creation, clash scan & bulk filing
│   │   │   ├── AttendanceCard.tsx      # Student attendance health card with SVG gauge
│   │   │   ├── ChatDrawer.tsx          # Frosted assistant drawer with citation chips
│   │   │   ├── Header.tsx              # Workspace banner & interactive profile dropdown
│   │   │   ├── HODDashboard.tsx        # HOD governance, SLA breach & escalation console
│   │   │   ├── LiveTransitMap.tsx      # Leaflet OpenStreetMap vehicle visualizer
│   │   │   ├── NotificationBell.tsx    # Header notification center with popover
│   │   │   ├── ProfessorReschedule.tsx # Faculty retake requests & sister-section chooser
│   │   │   ├── Sidebar.tsx             # Role-filtered navigation sidebar
│   │   │   ├── StudentClashes.tsx      # Student retake status & interactive audit timeline
│   │   │   └── TimelineView.tsx        # Chronological audit timeline renderer
│   │   └── lib/
│   │       └── api.ts                  # Typed client SDK & fetchers
│   ├── package.json
│   └── next.config.ts                  # API rewrites (/api/v1 -> localhost:8000)
├── Docs/                               # Specification documents (PRD, AGENTS, UI-UX)
├── PROGRESS.md                         # Detailed project changelog & version history
├── README.md                           # Project documentation (this file)
└── start.sh                            # One-click dependency installer & launcher script
```

---

## 🔒 Security & Policy Invariants

1. **Zero Raw SQL Text Generation**: The conversational AI assistant never writes arbitrary SQL queries. All tabular queries are pre-compiled and strictly parametrized by JWT claims.
2. **Horizontal Privilege Isolation**: Even if a student inputs `"Show Alex's grades"`, the backend automatically binds the query to the authenticated `student_id`, preventing cross-account snooping.
3. **Academic Code §4.2**: Aggregate attendance is continuously evaluated against the $75.0\%$ invariant. Below $75\%$, automatic debarment warnings are dispatched.
4. **Compare-And-Set Concurrency**: All exam clash state transitions utilize atomic CAS locking. Conflicting updates fail safely with `HTTP 409 Conflict`.
5. **Channel Isolation**: WebSockets reject cross-tenant subscription requests (`WS_1008_POLICY_VIOLATION`) ensuring users only receive notifications addressed to them.

---

## 📄 License
This project is licensed under the MIT License. Developed for enterprise campus administration, telematics intelligence, and student academic success.

