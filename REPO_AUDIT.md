# NexuxEdu Repository Audit

**Audit Date:** September 29, 2026  
**Repository:** [https://github.com/robinponnanna/NexuxEdu.git](https://github.com/robinponnanna/NexuxEdu.git)  
**Branch:** `main` (Commit `029a704` / Merge PR #2)  
**Auditor:** Antigravity AI  

---

## 1. Executive Summary

**NexuxEdu** (branded internally as **OmniCampus ERP & SafeTransit**) is a Next-Gen Smart Campus Enterprise Resource Planning (ERP) platform featuring:
1. A **Zero-Trust Multi-Agent Role-Based Access Control (RBAC) Conversational AI Assistant** that strictly confines information retrieval to verified JSON Web Token (JWT) claims, preventing cross-tenant data leaks (such as student access to faculty payroll or admin audit logs).
2. A **Real-Time School Bus Fleet Telemetry Engine** streaming live vehicle GPS coordinates, ETA predictions, route polylines, and a 500-meter geodesic Haversine geofencing proximity alert system directly to authenticated parent and student interfaces over WebSockets.
3. An **Academic Attendance & Faculty Governance Module** providing granular course attendance health rings, debarment danger flags (<75% threshold under Academic Regulation §4.2), and a faculty command center for section rosters and attendance advisory dispatches.

The project is structured as a decoupled full-stack monorepo consisting of a **FastAPI backend** (Python 3.11 with SQLite/SQLAlchemy Async & in-memory pub/sub broker) and a **Next.js 16 (App Router) frontend** with TypeScript, Leaflet.js interactive maps, and a vanilla CSS design system.

---

## 2. Current Tech Stack

### Frontend
* **Framework:** Next.js `16.3.6` (App Router, Turbopack)
* **Language:** TypeScript `5.x`, React `19.2.8`, React-DOM `19.2.8`
* **Build Tool:** Turbopack (`next dev`, `next build`)
* **Styling:** Custom CSS variables & design system in [`frontend/src/app/globals.css`](file:///c:/Users/gagan/NexuxEdu/frontend/src/app/globals.css) (minimalist light theme, `#FFFFFF` canvas, `#0F172A` typography)
* **State Management:** React local hooks (`useState`, `useEffect`, `useRef`) with `localStorage` persistence for session tokens (`omnicampus_session`)
* **Routing:** Next.js App Router (`/login`, `/`) with dynamic tab switching (`dashboard`, `transit`, `attendance`, `audits`)
* **UI & Component Libraries:** 
  * `lucide-react` (`^1.48.0`) for iconography
  * `leaflet` (`^1.9.4`) & `@types/leaflet` (`^1.9.22`) for OpenStreetMap cartography and transit visualizer
* **API Client / Transport:** Native `fetch` with proxy rewrites (`/api/v1/*` -> `http://127.0.0.1:8000/api/v1/*`) and HTML5 standard `WebSocket` (`/ws/transit/{bus_id}`)

### Backend
* **Runtime:** Python `3.11` (compatible with 3.10+)
* **Framework:** FastAPI (`0.141.1` / `>=0.110.0`), Starlette (`1.7.0`), Uvicorn (`0.54.0` / standard `>=0.28.0`)
* **Language:** Python 3.11 async (`asyncio`)
* **API Architecture:** REST (FastAPI APIRouter) + WebSockets (`FastAPI.websocket`)
* **Authentication:** JWT (JSON Web Tokens via `pyjwt 2.15.1`, `cryptography 50.0.1`, `bcrypt 5.0.0`)
* **Validation & Settings:** Pydantic v2 (`2.13.5`), Pydantic Settings (`2.15.0`)
* **Asynchronous Networking:** `httpx` (`0.28.1`), `websockets` (`17.1`), `aiosqlite` (`0.22.1`)
* **Math & Embeddings:** `numpy` (`2.4.6`) for pseudo-embeddings and cosine distance calculations

### Database
* **Database Engine:** SQLite (stored at [`backend/campus.db`](file:///c:/Users/gagan/NexuxEdu/backend/campus.db)) accessed asynchronously via `aiosqlite` (`sqlite+aiosqlite:///./campus.db`)
* **ORM:** SQLAlchemy `2.1.1` (2.0-style declarative mapping with `AsyncSession`)
* **Schema Location:** [`backend/app/core/database.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/core/database.py)
* **Migrations:** None (auto-initialized at startup via `Base.metadata.create_all` in [`backend/app/main.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/main.py#L19))
* **Seed Data:** Automated on initial launch in [`backend/app/services/seed_data.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/services/seed_data.py) (seeds 20 buses, 6 users/profiles, 4 attendance records, 6 policy embeddings)

### Infrastructure & External Services
* **Hosting/Deployment:** Local daemon launcher via [`start.sh`](file:///c:/Users/gagan/NexuxEdu/start.sh); production deployable to Docker / standard cloud VMs
* **Pub/Sub Broker:** Local high-performance `InMemoryBroker` in [`backend/app/core/pubsub.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/core/pubsub.py) providing Redis-compatible Pub/Sub semantics without external Redis installation
* **AI Providers:** Self-contained deterministic RAG pipeline (pseudo-embedding generator + cosine similarity + parametric SQL tools + rule-based egress guardrail). Configured with optional fallback hooks for `GROQ_API_KEY` and `OPENAI_API_KEY` in [`backend/app/core/config.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/core/config.py)
* **Cartography Tile Server:** Standard OpenStreetMap (`https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png`)

---

## 3. Repository Structure

```
NexuxEdu/
├── .agent/rules/                 # Assistant execution rules (e.g. env.md)
├── backend/                      # FastAPI Python backend application
│   ├── app/
│   │   ├── agents/               # Zero-trust multi-agent supervisor modules
│   │   │   ├── egress_guard.py       # Context grounding, synthesis & leak scrubber
│   │   │   ├── ingress_guard.py      # Prompt injection / jailbreak regex scanner
│   │   │   ├── intent_classifier.py  # Deterministic semantic branch classifier
│   │   │   ├── orchestrator.py       # State machine coordinating workers & logs
│   │   │   ├── structured_records.py # Parametric SQL executor for tabular metrics
│   │   │   ├── transit_telemetry.py  # Vehicle telematics & schedule worker
│   │   │   └── vector_knowledge.py   # Pre-filtered pgvector-style similarity agent
│   │   ├── api/                  # REST API routes and WebSocket endpoints
│   │   │   ├── auth.py               # /api/v1/auth (login, /me, claims extraction)
│   │   │   ├── chat.py               # /api/v1/chat/query (AI endpoint)
│   │   │   ├── erp.py                # /api/v1/erp (dashboard, attendance, roster, audits)
│   │   │   └── transit.py            # /api/v1/transit (buses, bus by id, WebSocket stream)
│   │   ├── core/                 # Core utilities and global configurations
│   │   │   ├── config.py             # Pydantic environment configuration & secrets
│   │   │   ├── database.py           # SQLAlchemy async models & engine
│   │   │   ├── pubsub.py             # In-memory Redis-compatible telemetry broker
│   │   │   └── security.py           # Bcrypt hashing & PyJWT token encoder/decoder
│   │   ├── models/
│   │   │   └── schemas.py            # Pydantic validation models & state schemas
│   │   ├── services/
│   │   │   ├── seed_data.py          # Synthetic demo data generator (buses, users, policies)
│   │   │   └── transit_simulator.py  # Waypoint progression & geofence simulator
│   │   └── main.py               # FastAPI application entrypoint & lifespan manager
│   ├── campus.db                 # Seeded persistent SQLite database
│   └── requirements.txt          # Python pip dependencies
├── frontend/                     # Next.js 16 React frontend application
│   ├── public/                   # Static SVG assets & icons
│   ├── src/
│   │   ├── app/
│   │   │   ├── favicon.ico           # Application icon
│   │   │   ├── globals.css           # Global CSS variables & UI styling
│   │   │   ├── layout.tsx            # HTML root layout & Leaflet CSS link
│   │   │   ├── login/
│   │   │   │   └── page.tsx          # Dedicated login page with 1-click role presets
│   │   │   └── page.tsx              # Main dashboard view (all role-specific tabs)
│   │   ├── components/
│   │   │   ├── AttendanceCard.tsx    # SVG progress ring attendance component
│   │   │   ├── ChatDrawer.tsx        # Floating AI drawer with verified citations
│   │   │   ├── Header.tsx            # Brand header & interactive hover profile card
│   │   │   ├── LiveTransitMap.tsx    # Leaflet OpenStreetMap canvas, HUD & 500m geofence alert
│   │   │   └── Sidebar.tsx           # Role-scoped sidebar navigation
│   │   └── lib/
│   │       └── api.ts                # TypeScript interfaces & API client methods
│   ├── eslint.config.mjs         # ESLint configuration
│   ├── next.config.ts            # Next.js configuration & API proxy rewrites
│   ├── package.json              # Node.js dependencies
│   ├── package-lock.json         # Locked Node.js dependency tree
│   └── tsconfig.json             # TypeScript compiler settings
├── AGENTS.md                     # Zero-Trust Multi-Agent Supervisor specification
├── ARCHITECTURE.md               # Technical architecture & mathematical simulator spec
├── PRD.md                        # Product Requirements Document & Persona matrix
├── PROGRESS.md                   # Engineering progress tracker & acceptance test logs
├── README.md                     # Comprehensive project documentation & quickstart guide
├── SYSTEM_DESIGN.md              # System design & SQL schema specification
├── UI-UX_DESIGN_SPECIFICATIONS.md# Design tokens, typography & interaction rules
└── start.sh                      # One-click startup script for Unix/Linux/macOS
```

---

## 4. Current Architecture

```
                                [ User / Web Browser ]
                                           │
                                 HTTP / WebSocket (Port 3000)
                                           ▼
               ┌───────────────────────────────────────────────────────┐
               │              Next.js 16 App Router Frontend           │
               │  - /login: Role determination & 1-click presets       │
               │  - /: Role-tailored Dashboard (Student/Faculty/Parent/Admin) │
               │  - LiveTransitMap: Leaflet canvas + 500m Geofence HUD │
               │  - ChatDrawer: Multi-Agent AI Drawer with Citations   │
               └───────────────────────────┬───────────────────────────┘
                                           │ Next.js Proxy Rewrites (/api/v1/*)
                                           ▼
               ┌───────────────────────────────────────────────────────┐
               │                 FastAPI Backend Gateway               │
               │            (Port 8000 / SQLite + PubSub)              │
               │  - Auth Ingress & JWT Claim Extraction                │
               │  - Ingress Guardrail (Prompt Injection Scanner)       │
               └───────┬───────────────────┬───────────────────┬───────┘
                       │                   │                   │
                       ▼                   ▼                   ▼
       ┌───────────────────────┐ ┌───────────────────┐ ┌───────────────────────┐
       │   ERP Core Routes     │ │  Transit Service  │ │ Multi-Agent Supervisor│
       │ - /erp/dashboard      │ │ - /transit/buses  │ │ - Ingress Guardrail   │
       │ - /erp/attendance     │ │ - /transit/buses/{id}│ - Intent Classifier │
       │ - /erp/faculty/class- │ │ - WS /ws/transit/ │ │ - Structured Worker   │
       │   attendance (Roster) │ │   {bus_id}        │ │ - Vector Worker (RAG) │
       │ - /erp/audit-logs     │ │                   │ │ - Transit Worker      │
       └───────────┬───────────┘ └─────────┬─────────┘ │ - Egress Guardrail    │
                   │                       │           └───────────┬───────────┘
                   │                       ▼                       │
                   │           ┌───────────────────────┐           │
                   │           │    Transit Simulator  │           │
                   │           │ - 20 Bus GPS Waypoints│           │
                   │           │ - 500m Haversine Calc │           │
                   │           │ - 3s PubSub Broadcast │           │
                   │           └───────────┬───────────┘           │
                   │                       │                       │
                   ▼                       ▼                       ▼
       ┌───────────────────────────────────────────────────────────────────────┐
       │                  Data & State Persistence Layer                       │
       │  - SQLite (campus.db): Users, Students, Faculty, Attendance, Policies │
       │  - InMemoryBroker: Redis-compatible Sub-ms Pub/Sub & Telemetry Cache  │
       │  - AuditLog Table: EVENT_PRIVILEGE_PROBE Security Intercepts          │
       └───────────────────────────────────────────────────────────────────────┘
```

---

## 5. Implemented Features Inventory

| Feature Name | Location in Code | Status | Current Functionality | Evidence from Code |
| :--- | :--- | :--- | :--- | :--- |
| **JWT Multi-Persona Auth** | [`backend/app/api/auth.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/api/auth.py), [`backend/app/core/security.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/core/security.py) | **COMPLETE** | Login issues JWT with `user_id`, `role`, `department`, `student_id`, `ward_id`, `bus_id`. Validates bcrypt hashes. | `login()`, `create_access_token()`, `decode_access_token()`. Verified 4 personas login successfully. |
| **Dedicated Login UI** | [`frontend/src/app/login/page.tsx`](file:///c:/Users/gagan/NexuxEdu/frontend/src/app/login/page.tsx) | **COMPLETE** | Form with email/password input, visibility toggle, error notifications, and 4 one-click demo presets. | `handleLogin()`, `demoAccounts.map()`, redirects to `/` on success. |
| **Role-Based Header & Profile Hover** | [`frontend/src/components/Header.tsx`](file:///c:/Users/gagan/NexuxEdu/frontend/src/components/Header.tsx) | **COMPLETE** | Displays authenticated user, floating glassmorphic profile card on hover (`#role-hover-card`) with role badge, email, and sign out. | `Header` component, `isHovered` state, `getRoleBadgeClass()`. |
| **Role-Partitioned Sidebar** | [`frontend/src/components/Sidebar.tsx`](file:///c:/Users/gagan/NexuxEdu/frontend/src/components/Sidebar.tsx) | **COMPLETE** | Filters visible navigation items based on `user.role` (e.g. Audits only for Admin, Transit for Student/Parent/Admin). | `navItems.filter(i => i.visible)`. |
| **Attendance Progress Rings** | [`frontend/src/components/AttendanceCard.tsx`](file:///c:/Users/gagan/NexuxEdu/frontend/src/components/AttendanceCard.tsx) | **COMPLETE** | SVG circular progress ring color-coded by thresholds: Safe ($\ge 85\%$), Attention ($75\text{--}84\%$), Debarment Risk ($<75\%$). | SVG circumference dashoffset calculations, status badges. |
| **Student/Parent Dashboard** | [`backend/app/api/erp.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/api/erp.py#L20), [`frontend/src/app/page.tsx`](file:///c:/Users/gagan/NexuxEdu/frontend/src/app/page.tsx#L586) | **COMPLETE** | Computes overall attendance %, lists subject breakdown, shows assigned bus and semester. | `get_dashboard_data()`, student branch with dynamic calculation. |
| **Faculty Class Attendance Roster** | [`backend/app/api/erp.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/api/erp.py#L132), [`frontend/src/app/page.tsx`](file:///c:/Users/gagan/NexuxEdu/frontend/src/app/page.tsx#L901) | **COMPLETE** | Department attendance ledger filtered by course and section, search query, status dropdown, KPI metrics, notice toast, CSV export. | `get_faculty_class_attendance()`, RBAC check strictly blocking non-faculty/non-admin (403). |
| **Admin Security Audit Logs** | [`backend/app/api/erp.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/api/erp.py#L216), [`frontend/src/app/page.tsx`](file:///c:/Users/gagan/NexuxEdu/frontend/src/app/page.tsx#L1250) | **COMPLETE** | Admin-only audit ledger viewing `EVENT_PRIVILEGE_PROBE` entries with timestamps and query details. | `get_audit_logs()`, tested with 403 blocks for students. |
| **Live Transit Map & HUD** | [`frontend/src/components/LiveTransitMap.tsx`](file:///c:/Users/gagan/NexuxEdu/frontend/src/components/LiveTransitMap.tsx) | **COMPLETE** | Leaflet OpenStreetMap canvas, polyline route, animated bus marker, velocity/ETA HUD, Center Bus & Full Route controls. | `setupMap()`, `L.tileLayer()`, `L.polyline()`, `L.marker()`. |
| **500m Geofencing Proximity Alerts** | [`backend/app/services/transit_simulator.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/services/transit_simulator.py#L134), [`frontend/src/components/LiveTransitMap.tsx`](file:///c:/Users/gagan/NexuxEdu/frontend/src/components/LiveTransitMap.tsx#L437) | **COMPLETE** | Computes Haversine distance between bus and registered stop; broadcasts `geofence_active: True` when $\le 500\text{m}$, displaying alert toast. | `math.radians()`, `6371.0 * c`, `dist_to_registered_m <= 500`. |
| **20-Bus Telemetry Simulator** | [`backend/app/services/transit_simulator.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/services/transit_simulator.py) | **COMPLETE** | Async loop ticking every 3s interpolating coordinates along waypoints with Gaussian jitter $\mathcal{N}(0, \sigma^2)$. | `TransitSimulator`, `_simulation_loop()`, `broker.set_bus_telemetry()`. |
| **In-Memory Pub/Sub Telemetry Broker** | [`backend/app/core/pubsub.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/core/pubsub.py) | **COMPLETE** | Lock-synchronized in-memory broker with `publish()`, `subscribe()`, `hset()`, `hgetall()`. | `InMemoryBroker` class. Sub-millisecond dispatch to WebSockets. |
| **WebSocket Stream Endpoint** | [`backend/app/api/transit.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/api/transit.py#L92), [`backend/app/main.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/main.py#L50) | **COMPLETE** | `/ws/transit/{bus_id}` and `/api/v1/transit/stream/{bus_id}` streaming live telemetry frames to authenticated clients. | `handle_transit_websocket()`, checks token claims and bus assignment. |
| **Zero-Trust Ingress Guardrail** | [`backend/app/agents/ingress_guard.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/agents/ingress_guard.py) | **COMPLETE** | Regex perimeter scanner matching adversarial prompt injection patterns (`"ignore prior rules"`, `"act as admin"`, etc.). | `check_input_guardrail()`, returns refusal & logs event. |
| **AI Intent Classification** | [`backend/app/agents/intent_classifier.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/agents/intent_classifier.py) | **COMPLETE** | Regex-based semantic router classifying queries into `ACADEMIC_RECORD`, `INSTITUTIONAL_KNOWLEDGE`, `TRANSIT_TELEMETRY`, `COMPOSITE`. | `classify_intent()`, keyword pattern matchers. |
| **Parametric SQL Structured Worker** | [`backend/app/agents/structured_records.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/agents/structured_records.py) | **COMPLETE** | Parametric SQL queries binding `student_id` strictly from JWT claims; blocks student/parent salary probing; handles faculty rosters. | `execute_structured_records_agent()`. |
| **Vector Knowledge Pre-Filtered Worker** | [`backend/app/agents/vector_knowledge.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/agents/vector_knowledge.py) | **COMPLETE** | Pre-retrieval metadata filter (`doc.allowed_roles` and department scope) before computing cosine similarity. | `execute_vector_knowledge_agent()`, `cosine_similarity()`. |
| **Transit AI Telemetry Worker** | [`backend/app/agents/transit_telemetry.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/agents/transit_telemetry.py) | **COMPLETE** | Responds to AI transit queries with live cached coordinates scoped to authorized `bus_id`. | `execute_transit_telemetry_agent()`. |
| **Egress Guardrail & Synthesis** | [`backend/app/agents/egress_guard.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/agents/egress_guard.py) | **COMPLETE** | Formats grounded answers, verifies citations, executes egress regex leak scanner against financial tokens for students/parents. | `sanitize_and_synthesize_response()`. |
| **Chat Drawer UI Component** | [`frontend/src/components/ChatDrawer.tsx`](file:///c:/Users/gagan/NexuxEdu/frontend/src/components/ChatDrawer.tsx) | **COMPLETE** | Floating action button (FAB) expanding into 410px chat drawer with sample test chips, citations pills, and security lock banners. | `ChatDrawer` component, `sendChatMessage()` integration. |
| **External LLM Cloud Inference (Groq/OpenAI)** | [`backend/app/core/config.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/core/config.py#L19) | **CONFIGURED BUT NOT FUNCTIONAL** | Settings declare `GROQ_API_KEY` and `OPENAI_API_KEY`, but the active multi-agent pipeline uses deterministic local RAG synthesis without making external HTTP requests. | In `config.py` keys are read, but `orchestrator.py` synthesizes via local `egress_guard.py`. |
| **PostgreSQL + pgvector Engine** | [`ARCHITECTURE.md`](file:///c:/Users/gagan/NexuxEdu/ARCHITECTURE.md), [`SYSTEM_DESIGN.md`](file:///c:/Users/gagan/NexuxEdu/SYSTEM_DESIGN.md) | **REFERENCED BUT NOT IMPLEMENTED** | Documented in system architecture specifications as production target; currently implemented with SQLite + NumPy cosine distance for zero-dependency hackathon portability. | `campus.db` SQLite engine used in `database.py`. |
| **Interactive Faculty Daily Attendance Input** | [`PROGRESS.md`](file:///c:/Users/gagan/NexuxEdu/PROGRESS.md#L294) | **REFERENCED BUT NOT IMPLEMENTED** | Listed in roadmap milestone `[FR-4.1]`. Form to mark daily student presence into attendance table is not yet built. | Not present in `erp.py` or frontend. |
| **Admin Knowledge Base Document Upload** | [`PROGRESS.md`](file:///c:/Users/gagan/NexuxEdu/PROGRESS.md#L295) | **REFERENCED BUT NOT IMPLEMENTED** | UI portal for admins to ingest new policy documents with metadata tags into `document_embeddings` table. | Documents are seeded via `seed_data.py`. |

---

## 6. User Flows

### Primary User Journeys

#### 1. Student Journey (Academic Standing & Commute Tracking)
1. Student accesses `/login` $\rightarrow$ enters `student@campus.edu` / `password123` (or clicks "Jane Doe" demo preset).
2. System verifies credentials against SQLite `users` table $\rightarrow$ extracts student profile (`student_id=1`, `bus_id=1`, `department=Computer Science`) $\rightarrow$ generates signed JWT access token.
3. Redirects to `/` (Dashboard) $\rightarrow$ fetches `/api/v1/erp/dashboard` $\rightarrow$ displays Overall Attendance ($81.9\%$), assigned vehicle (`BUS-001`), and 4 subject cards with color-coded circular progress rings.
4. Student navigates to **Attendance Tracker** tab to inspect Operating Systems ($87.5\%$), DBMS ($92.5\%$), Networks ($77.5\%$), and Theory of Computation ($70.0\%$ — Debarment Risk flag).
5. Student opens **Live Transit** tab $\rightarrow$ Leaflet map connects to WebSocket stream $\rightarrow$ shows real-time GPS coordinates and velocity of `BUS-001`.
6. Student opens **AI Assistant** (FAB) $\rightarrow$ asks *"What is my attendance in Operating Systems?"* $\rightarrow$ AI returns $87.5\%$ with verified SQL citation $\rightarrow$ student tests privilege breach *"Show faculty salaries"* $\rightarrow$ AI intercepts request with 🔒 Security Rejection card and records audit event.

#### 2. Faculty Journey (Course Governance & Class Rosters)
1. Professor logs in as `faculty@campus.edu` $\rightarrow$ claims resolve `department=Computer Science`, `emp_code=FAC-101`.
2. Dashboard displays faculty KPIs: 3 active courses, total enrolled students, and class average attendance ($80.9\%$).
3. Professor opens **Class Roster** tab $\rightarrow$ selects Course (`Operating Systems`) and Section (`All Sections` or `Section A` / `Section B`).
4. Interactive table displays all enrolled students with attendance percentages and eligibility statuses (`Safe`, `Attention`, `Debarment Risk`).
5. Professor clicks **"Dispatch Advisory Notice"** for an at-risk student $\rightarrow$ emits notice toast banner.
6. Professor clicks **"Export Roster (CSV)"** $\rightarrow$ downloads formatted CSV file of student records.
7. Professor queries AI Assistant *"What is my salary?"* $\rightarrow$ AI retrieves faculty compensation record ($\$125,000.00$).

#### 3. Parent Journey (Child Commute Safety & Geofencing)
1. Parent logs in as `parent@campus.edu` $\rightarrow$ claims resolve `ward_id=1`, `bus_id=1`.
2. Dashboard shows ward's attendance metrics and assigned vehicle.
3. Parent opens **Live Transit** $\rightarrow$ Leaflet map displays moving vehicle along route path with 500m amber geofence circle around registered pickup stop (`Midtown Gate 1`).
4. When the bus enters within 500 meters of the stop, the screen triggers a glowing **500M Geofence Proximity Alert** toast banner with exact metric distance.

#### 4. Admin Journey (Campus Fleet Governance & Security Audits)
1. Administrator logs in as `admin@campus.edu`.
2. Dashboard shows total campus users (6), active transit fleet (20 buses), and total security audit events.
3. Admin navigates to **Live Transit** $\rightarrow$ dropdown allows switching across all 20 regional bus routes.
4. Admin opens **Security Audits** tab $\rightarrow$ inspects real-time security logs showing blocked `EVENT_PRIVILEGE_PROBE` attempts, actor roles, and full query details.

---

## 7. Frontend Routes & Screens

| Route / Screen | Purpose | Implemented? | Backend Connected? | DB Connected? | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/login` | Dedicated authentication page with 1-click presets for all 4 roles | **Yes** | **Yes** (`POST /api/v1/auth/login`) | **Yes** (`users` table) | Fully reactive with password toggle and error states |
| `/` (Dashboard Tab) | Role-specific overview KPIs, attendance rings, fleet summary | **Yes** | **Yes** (`GET /api/v1/erp/dashboard`) | **Yes** (`attendance`, `students`, `buses`) | Dynamically adjusts based on verified role claims |
| `/` (Live Transit Tab) | Interactive Leaflet map with live 3s GPS updates and 500m geofence alerts | **Yes** | **Yes** (`GET /api/v1/transit/buses`, `WS /ws/transit/{bus_id}`) | **Yes** (`buses` table + telemetry broker) | Route selector available for Admin |
| `/` (Attendance Tracker Tab - Student/Parent) | Granular subject attendance cards with circular SVG rings | **Yes** | **Yes** (`GET /api/v1/erp/attendance`) | **Yes** (`attendance` table) | Color-coded thresholds: $\ge85\%$, $75-84\%$, $<75\%$ |
| `/` (Class Roster Tab - Faculty) | Full department attendance roster with subject/section/status filters & CSV export | **Yes** | **Yes** (`GET /api/v1/erp/faculty/class-attendance`) | **Yes** (`students`, `users`, `attendance`) | Includes student search, notice action, and CSV generator |
| `/` (Security Audits Tab - Admin) | Table of intercepted security violations & jailbreak attempts | **Yes** | **Yes** (`GET /api/v1/erp/audit-logs`) | **Yes** (`audit_logs` table) | Strictly forbidden (403) to non-admins |
| Chat Drawer (Global Modal) | Conversational AI assistant with source citation badges and RBAC lock card | **Yes** | **Yes** (`POST /api/v1/chat/query`) | **Yes** (`document_embeddings`, `attendance`, `buses`) | Available from all screens via floating action button |

---

## 8. Backend APIs

| Method | Path | Purpose | Auth Required | Request Body / Params | Response Structure | DB Interaction | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/login` | Authenticate user & issue JWT | No | `LoginRequest` (`email`, `password`) | `TokenResponse` (`access_token`, `user`) | Select `User`, `Student`, `Faculty`, `Parent` | **Working** |
| `GET` | `/api/v1/auth/me` | Fetch authenticated session profile | Yes (`Bearer`) | None | `UserResponse` | Decoded from JWT claims | **Working** |
| `GET` | `/api/v1/erp/dashboard` | Role-tailored dashboard metrics | Yes (`Bearer`) | None | `dict` (attendance, bus, courses, audits) | Select `Attendance`, `Student`, `User`, `Bus`, `AuditLog` | **Working** |
| `GET` | `/api/v1/erp/attendance` | Granular student attendance records | Yes (`Bearer`) | None | `List[AttendanceRecord]` | Select `Attendance` where `student_id = claims.student_id` | **Working** |
| `GET` | `/api/v1/erp/faculty/class-attendance` | Faculty class roster & section breakdown | Yes (`Bearer` - Faculty/Admin) | Query: `subject`, `section` | `FacultyAttendanceRosterResponse` | Join `Student`, `User`, `Attendance` | **Working** (403 for non-faculty) |
| `GET` | `/api/v1/erp/audit-logs` | Admin security audit event ledger | Yes (`Bearer` - Admin) | None | `List[AuditLog]` | Select `AuditLog` order by id desc limit 50 | **Working** (403 for non-admin) |
| `GET` | `/api/v1/transit/buses` | List all active campus buses | Yes (`Bearer`) | None | `List[BusDetails]` | Select `Bus` + merge telemetry broker | **Working** |
| `GET` | `/api/v1/transit/buses/{bus_id}` | Details, stops, and waypoints for specific bus | Yes (`Bearer`) | Path: `bus_id` | `BusDetails` | Select `Bus` where `id = bus_id` | **Working** (403 for foreign bus tracking) |
| `WS` | `/ws/transit/{bus_id}` | WebSocket live 3s coordinate telemetry stream | Query: `?token=<JWT>` | Path: `bus_id` | JSON frames (`lat`, `lng`, `speed`, `geofence`) | Subscribes to `broker.channel:bus:{bus_id}` | **Working** |
| `WS` | `/api/v1/transit/stream/{bus_id}` | Alias for transit WebSocket stream | Query: `?token=<JWT>` | Path: `bus_id` | JSON frames (`lat`, `lng`, `speed`, `geofence`) | Subscribes to `broker.channel:bus:{bus_id}` | **Working** |
| `POST` | `/api/v1/chat/query` | RBAC Multi-Agent conversational query pipeline | Yes (`Bearer`) | `ChatRequest` (`message`, `conversation_history`) | `ChatResponse` (`reply`, `sources`, `access_denied`, `audit_flag`) | Queries `DocumentEmbedding`, `Attendance`, `Faculty`, `AuditLog` | **Working** |
| `GET` | `/health` | Application health check probe | No | None | `{"status": "healthy"}` | None | **Working** |
| `GET` | `/api/v1/health` | API v1 health check probe | No | None | `{"status": "healthy"}` | None | **Working** |

---

## 9. Database Layer

### Entity-Relationship Architecture

```
  ┌───────────────────────────────────────────────────────────┐
  │                           User                            │
  │ id (PK), public_id, name, email, password_hash, role      │
  └───────┬───────────────────┬───────────────────┬───────────┘
          │ 1:1               │ 1:1               │ 1:1
          ▼                   ▼                   ▼
  ┌──────────────┐    ┌──────────────┐    ┌───────────────────┐
  │   Faculty    │    │    Parent    │    │      Student      │
  │ id, user_id, │    │ id, user_id, │    │ id, user_id,      │
  │ emp_code,    │    │ phone,       │    │ parent_id (FK),   │
  │ department,  │    │ emergency    │    │ bus_id (FK),      │
  │ designation, │    └───────┬──────┘    │ roll_number,      │
  │ annual_salary│            │ 1:N       │ department, sem,  │
  └──────────────┘            └──────────►│ section           │
                                          └─────────┬─────────┘
                                                    │ 1:N
                                                    ▼
  ┌─────────────────────────────────┐     ┌───────────────────┐
  │               Bus               │     │    Attendance     │
  │ id (PK), bus_number, route_name,│◄────┤ id (PK),          │
  │ driver_name, driver_phone,      │     │ student_id (FK),  │
  │ current_lat, current_lng, speed,│     │ subject, total,   │
  │ status, stops_json, waypoints   │     │ attended, pct     │
  └─────────────────────────────────┘     └───────────────────┘

  ┌─────────────────────────────────┐     ┌───────────────────┐
  │        DocumentEmbedding        │     │     AuditLog      │
  │ id (PK), title, section,        │     │ id (PK), user_id, │
  │ content, allowed_roles,         │     │ role, event_type, │
  │ department, embedding_json      │     │ details, timestamp│
  └─────────────────────────────────┘     └───────────────────┘
```

### Persistence Summary
* **Persistent Entities:** All 8 tables (`users`, `buses`, `parents`, `faculty`, `students`, `attendance`, `document_embeddings`, `audit_logs`) persist to SQLite disk (`backend/campus.db`).
* **In-Memory Ephemeral State:** Real-time bus GPS coordinates and WebSocket subscriber channels are managed via `InMemoryBroker` in [`backend/app/core/pubsub.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/core/pubsub.py).
* **Seeded Records:**
  * 20 Bus Routes with waypoints and 4 sequenced stops each.
  * 6 Users: `admin@campus.edu` (Sarah Connor), `faculty@campus.edu` (Prof. Alan Turing), `smith@campus.edu` (Prof. Smith), `hamilton@campus.edu` (Prof. Hamilton), `parent@campus.edu` (Robert Doe), `student@campus.edu` (Jane Doe), `alex@campus.edu` (Alex Smith).
  * 4 Granular Attendance records for Jane Doe.
  * 6 Institutional Policy documents with embeddings (Academic Regs §4.2, Exam Code §7.1, SafeTransit Guidelines §11.3, Faculty Discretionary Fund §18.4, CS Answer Keys, Master Admin Security Ops).

---

## 10. Environment Variables

| Variable Name | Purpose | Required? | Default Value (if unset) | Configured in Repo? |
| :--- | :--- | :--- | :--- | :--- |
| `JWT_SECRET_KEY` | Cryptographic secret for signing JWT session tokens | No (has fallback) | `omnicampus-super-secret-jwt-key-2026-secure-hackathon` | Configured in [`backend/app/core/config.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/core/config.py#L11) |
| `DATABASE_URL` | SQLAlchemy database connection URI | No (has fallback) | `sqlite+aiosqlite:///./campus.db` | Configured in [`backend/app/core/config.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/core/config.py#L16) |
| `GROQ_API_KEY` | Optional API key for Groq Cloud LLM inference | Optional | `None` | Optional fallback |
| `OPENAI_API_KEY`| Optional API key for OpenAI LLM inference | Optional | `None` | Optional fallback |
| `NEXT_PUBLIC_API_URL` | Base URL for frontend API client during SSR | Optional | `http://127.0.0.1:8000/api/v1` | Handled via Next.js proxy rewrites |

---

## 11. Runtime Status

* **Python Environment:** Created at `.\.venv` (CPython 3.11.16) with all 32 packages installed.
* **Backend Verification:** Executed [`verify_backend.py`](file:///c:/Users/gagan/.gemini/antigravity/brain/f0b92ff9-c495-4b39-87f2-b34795b3734e/scratch/verify_backend.py) against `backend/campus.db`:
  * Database initialization: **Passed**
  * Multi-persona authentication (Student, Faculty, Parent, Admin): **Passed**
  * RBAC Scoping & 403 blocks for unauthorized endpoints: **Passed**
  * Multi-agent conversational AI pipeline (TC-1, TC-2, TC-3, Ingress jailbreak check): **Passed**
  * Transit Telemetry & 500m geofencing calculation: **Passed**
  * Security audit logs persistence: **Passed**
* **Frontend Node Environment:** Node modules installed (`added 348 packages in 2m`).
* **Frontend Production Build:** `npm.cmd --prefix frontend run build` succeeded (`✓ Compiled successfully in 9.3s`, all 3 static routes prerendered).
* **ESLint Verification:** Linter completed with 36 style/typing problems (17 errors, 19 warnings regarding `@typescript-eslint/no-explicit-any`, unused imports, and React hook dependency arrays).

---

## 12. Git History Summary

* **Commit `17e6cea`:** Initial commit adding repository `LICENSE`.
* **Commit `e87ceeb`:** Built initial OmniCampus ERP portal (FastAPI backend + Next.js frontend + Zero-Trust Multi-Agent architecture).
* **Commit `5baafd3`:** Merged branch fixes.
* **Commit `6a31dc5`:** Pull Request #1 building complete ERP portal, dark theme, telemetry simulator, and documentation.
* **Commit `029a704`:** Merged Pull Request #2 from `robinponnanna/ERP` into `main`. Clean working tree, all work preserved.

---

## 13. TODO / FIXME / Incomplete Areas

### Functional Gaps
1. **Interactive Attendance Marking Form:** Faculty can inspect class rosters and dispatch advisories, but there is no interactive input form to write updated daily attendance marks directly to SQLite.
2. **Dynamic Knowledge Base Upload:** Adding new university policy handbooks currently requires adding rows to `seed_data.py`; there is no admin web portal for PDF/document ingestion.

### Technical Debt
1. **TypeScript Linting & Purity:** 36 ESLint issues in frontend code (`ChatDrawer.tsx`, `LiveTransitMap.tsx`, `api.ts`) regarding `Date.now()` inside render callbacks, `any` type annotations, and hook dependency arrays.
2. **Single Monolithic Page Component:** [`frontend/src/app/page.tsx`](file:///c:/Users/gagan/NexuxEdu/frontend/src/app/page.tsx) is ~1575 lines containing all tab views inline rather than modularized into separate route/page components.

### Demo Shortcuts
1. **In-Memory Pub/Sub:** Uses `InMemoryBroker` instead of external Redis daemon for zero-setup execution.
2. **Deterministic Pseudo-Embeddings:** Uses 384-dimensional seeded vector generator (`generate_pseudo_embedding`) and NumPy cosine similarity rather than an external vector DB service.

---

## 14. Security Findings

1. **Robust Ingress Defense:** Prompt injection phrases (`"ignore prior rules"`, `"act as root"`, `"dan mode"`) are successfully intercepted by [`backend/app/agents/ingress_guard.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/agents/ingress_guard.py) and logged to the database.
2. **Zero Cross-Role Leakage:** Parametric SQL queries strictly ignore prompt text when resolving student/faculty IDs, preventing lateral account access. Egress guardrail scans output tokens for salary numerals and redacts them if a student or parent queries financial data.
3. **Hardcoded Fallback JWT Secret:** `JWT_SECRET_KEY` has a default fallback string in `config.py` if not set in the environment. For production deployment, this should be mandated via `.env`.
4. **Permissive CORS:** `CORSMiddleware` in `main.py` is configured with `allow_origins=["*"]`. Suitable for local hackathon demo, should be locked to frontend domain in production.

---

## 15. Technical Debt

1. **Dual DB Paths:** `Settings.DATABASE_URL` is `"sqlite+aiosqlite:///./campus.db"`. When running Python from repository root vs `backend/`, SQLite resolves relative to the current working directory. `start.sh` handles this by changing directory to `backend/` before launching Uvicorn.
2. **Frontend Mock Fallbacks:** `page.tsx` contains hardcoded initial states (`DEFAULT_FACULTY_ROSTER` with 8 mock students) while `seed_data.py` seeds 2 students. When the live API loads, it replaces the mock data, but unifying seed records avoids visual state shifts.

---

## 16. Demo / Hackathon Readiness

* **Zero-Trust RBAC AI Assistant:** Demonstrably functional end-to-end. Intercepts jailbreaks, prevents cross-role privilege escalation, returns exact verified tabular metrics, and displays citation pills.
* **Live Transit Telemetry & 500m Geofencing:** Demonstrably functional end-to-end. 20 buses simulate movement along cyclic waypoints, broadcasting over WebSockets every 3 seconds. Leaflet map animates bus marker, updates HUD velocity, and triggers glowing 500m geofence alert banner.
* **Faculty Command Center:** Demonstrably functional end-to-end. Displays section breakdowns, class average attendance, debarment warnings, search filtering, advisory notice dispatches, and CSV exports.
* **Authentication & Role Switching:** Demonstrably functional end-to-end. `/login` provides 1-click presets for all 4 roles; header profile hover card provides instant role status and logout actions.

---

## 17. Known Blockers

* **None.** The backend starts without errors, SQLite seeds automatically on startup, the frontend builds cleanly (`npm run build` passes), and all acceptance test criteria are verified.

---

## 18. Recommended Next-Step Dependency Map

If future enhancements or features are requested:

1. **Feature: Faculty Daily Attendance Input Form**
   * *Dependencies:* Requires new `POST /api/v1/erp/faculty/attendance` endpoint in [`backend/app/api/erp.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/api/erp.py) $\rightarrow$ updates `Attendance` model in [`backend/app/core/database.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/core/database.py) $\rightarrow$ connect to interactive UI form in `page.tsx`.

2. **Feature: Dynamic Admin Document Ingestion**
   * *Dependencies:* Requires `python-multipart` upload route in `erp.py` $\rightarrow$ text extraction & chunking $\rightarrow$ insert into `DocumentEmbedding` table with `allowed_roles` metadata.

3. **Feature: Token-by-Token Streaming Chat Responses (SSE)**
   * *Dependencies:* Requires `StreamingResponse` endpoint in [`backend/app/api/chat.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/api/chat.py) $\rightarrow$ async generator in `orchestrator.py` $\rightarrow$ `ReadableStream` reader in `ChatDrawer.tsx`.
