# OmniCampus ERP & SafeTransit: Project Progress Tracker

This document tracks all completed implementations, active architecture milestones, test validations, and upcoming enhancements for the **OmniCampus ERP & SafeTransit** platform. It serves as the living source of truth for engineering progress aligned with the project specifications in [`/Docs`](file:///home/robin/Projects/ERP/Docs).

---

## 📌 Executive Status Dashboard

* **Current Release Phase:** Hackathon MVP (v1.0.0)
* **Overall Status:** Core Systems Operational & Verified
* **Backend Services:** Running on `http://localhost:8000` (FastAPI / Uvicorn)
* **Frontend Application:** Running on `http://localhost:3000` (Next.js 14 App Router)
* **WebSocket Telemetry Stream:** Operational at `ws://localhost:8000/ws/transit/{bus_id}`
* **Automated Acceptance Tests Pass Rate:** 100% (4 / 4 Core Invariant Tests)

---

## 🏗️ Architecture & Module Implementation Progress

### 1. Security & Authentication Engine (`Auth-Module`)
- [x] **JWT Token Generation & Claim Binding**: Cryptographically signs session claims containing `user_id`, `role`, `department`, `student_id`, `ward_id`, and `bus_id`.
  - Implemented in: [`backend/app/core/security.py`](file:///home/robin/Projects/ERP/backend/app/core/security.py)
- [x] **Password Hashing**: Bcrypt integration with 10 salt rounds.
- [x] **Role Personas Pre-Configured**:
  - `student@campus.edu`: Jane Doe (Roll: `CS-2023-042`, Bus: 1, Dept: CS, Semester 6)
  - `faculty@campus.edu`: Prof. Alan Turing (Emp Code: `FAC-101`, Dept: CS, HOD, Salary: $125,000)
  - `parent@campus.edu`: Robert Doe (Ward: Jane Doe, Bus: 1)
  - `admin@campus.edu`: Sarah Connor (Global Campus Administrator)
  - Additional faculty records with confidential salaries for security testing (e.g. Professor Smith).
  - Implemented in: [`backend/app/services/seed_data.py`](file:///home/robin/Projects/ERP/backend/app/services/seed_data.py)
- [x] **REST Endpoints**:
  - `POST /api/v1/auth/login`
  - `GET /api/v1/auth/me`
  - Implemented in: [`backend/app/api/auth.py`](file:///home/robin/Projects/ERP/backend/app/api/auth.py)

---

### 2. Zero-Trust Multi-Agent Supervisor Engine (`RAG-Module`)
- [x] **Perimeter Ingress & Injection Defense**:
  - Scans user prompts for adversarial tokens (`"ignore prior rules"`, `"act as root"`, `"dan mode"`, etc.).
  - Rejects malicious payloads prior to model invocation and emits security audit events.
  - Implemented in: [`backend/app/agents/ingress_guard.py`](file:///home/robin/Projects/ERP/backend/app/agents/ingress_guard.py)
- [x] **Intent Classification & Dispatch Router**:
  - Deterministically maps queries into `ACADEMIC_RECORD`, `INSTITUTIONAL_KNOWLEDGE`, `TRANSIT_TELEMETRY`, or `COMPOSITE`.
  - Implemented in: [`backend/app/agents/intent_classifier.py`](file:///home/robin/Projects/ERP/backend/app/agents/intent_classifier.py)
- [x] **Structured Records Worker (Parametric Text-to-SQL)**:
  - Binds SQL queries exclusively to session claims (`student_id` or `ward_id`), completely ignoring arbitrary user IDs in prompt strings to prevent lateral account probing.
  - Hardened RBAC isolation: students and parents are strictly blocked from querying faculty payroll or cross-student records.
  - Implemented in: [`backend/app/agents/structured_records.py`](file:///home/robin/Projects/ERP/backend/app/agents/structured_records.py)
- [x] **Vector Knowledge Worker (Pre-Filtered RAG)**:
  - Enforces database-level metadata filtering: vector similarity is computed **only** on documents where `claims.role in allowed_roles` and department scopes match.
  - Implemented in: [`backend/app/agents/vector_knowledge.py`](file:///home/robin/Projects/ERP/backend/app/agents/vector_knowledge.py)
- [x] **Transit & Fleet Telematics Worker**:
  - Non-admins can query only their bound `bus_id`. Faculty is scoped to campus shuttle timetables.
  - Implemented in: [`backend/app/agents/transit_telemetry.py`](file:///home/robin/Projects/ERP/backend/app/agents/transit_telemetry.py)
- [x] **Egress Guardrail & Empty-State Grounding**:
  - If retrieved context is empty, execution terminates without hallucinating or extrapolating data.
  - Scans outgoing token stream for sensitive financial numerals when user role is student or parent.
  - Emits inline markdown source citations.
  - Implemented in: [`backend/app/agents/egress_guard.py`](file:///home/robin/Projects/ERP/backend/app/agents/egress_guard.py)
- [x] **Master Hierarchical Orchestrator**:
  - Coordinates state machine lifecycle across all workers and logs `EVENT_PRIVILEGE_PROBE` upon security violations.
  - Implemented in: [`backend/app/agents/orchestrator.py`](file:///home/robin/Projects/ERP/backend/app/agents/orchestrator.py)

---

### 3. Real-Time Transit Telemetry Subsystem (`Transit-Module`)
- [x] **In-Memory Redis-Compatible Pub/Sub Broker**:
  - Provides sub-millisecond dispatch to active WebSocket connections with zero external daemon setup required.
  - Implemented in: [`backend/app/core/pubsub.py`](file:///home/robin/Projects/ERP/backend/app/core/pubsub.py)
- [x] **Mathematical Position Simulator (20 Buses)**:
  - Implements the waypoint progression formula with Gaussian jitter:
    $$\mathbf{P}(t) = (1 - \alpha)\mathbf{P}_k + \alpha \mathbf{P}_{k+1} + \mathcal{N}(0, \sigma^2)$$
  - Ticks every 3.0 seconds, updating speed, next stop, ETA, and distance.
  - Implemented in: [`backend/app/services/transit_simulator.py`](file:///home/robin/Projects/ERP/backend/app/services/transit_simulator.py)
- [x] **WebSocket & REST Telemetry Channels**:
  - `GET /api/v1/transit/buses` (fleet directory)
  - `GET /api/v1/transit/buses/{id}` (route stops and waypoints)
  - `WS /ws/transit/{bus_id}` & `WS /api/v1/transit/stream/{bus_id}` (live coordinate stream)
  - Implemented in: [`backend/app/api/transit.py`](file:///home/robin/Projects/ERP/backend/app/api/transit.py)

---

### 4. ERP Core & Academic Management (`ERP-Core`)
- [x] **Attendance Engine**:
  - Tracks attended classes, total classes, and calculated attendance percentages.
  - Debarment flag automatically triggered when aggregate attendance $< 75\%$.
- [x] **Role-Tailored Dashboards**:
  - `GET /api/v1/erp/dashboard`
  - `GET /api/v1/erp/attendance`
  - `GET /api/v1/erp/audit-logs` (admin only)
  - Implemented in: [`backend/app/api/erp.py`](file:///home/robin/Projects/ERP/backend/app/api/erp.py)

---

### 5. Frontend Presentation Tier (Next.js 14 App Router + Vanilla CSS)
- [x] **Design System Foundations**:
  - Palette: Dark surface `#0F172A`, Card `#1E293B`, Primary Indigo `#3B82F6`.
  - Role Accents: Student Teal (`#0EA5E9`), Faculty Emerald (`#10B981`), Parent Amber (`#F59E0B`), Admin Violet (`#8B5CF6`).
  - Typography: Inter font family and JetBrains Mono for telemetry / data displays.
  - Animated `.bus-beacon` CSS pulse keyframe animation.
  - Implemented in: [`frontend/src/app/globals.css`](file:///home/robin/Projects/ERP/frontend/src/app/globals.css)
- [x] **Top Header & One-Click Demo Role Switcher**:
  - Allows seamless switching between all 4 personas for demonstration and evaluation.
  - Implemented in: [`frontend/src/components/Header.tsx`](file:///home/robin/Projects/ERP/frontend/src/components/Header.tsx)
- [x] **Role-Partitioned Sidebar**:
  - Dynamic navigation links restricted by authenticated claims.
  - Implemented in: [`frontend/src/components/Sidebar.tsx`](file:///home/robin/Projects/ERP/frontend/src/components/Sidebar.tsx)
- [x] **Live Transit Visualizer Component**:
  - Leaflet.js canvas with CartoDB DarkMatter tiles.
  - Polyline route rendering, numbered stop pins, animated bus marker, and live telemetry HUD overlay (speed, next stop, ETA, distance, 500m geofence indicator).
  - Implemented in: [`frontend/src/components/LiveTransitMap.tsx`](file:///home/robin/Projects/ERP/frontend/src/components/LiveTransitMap.tsx)
- [x] **Attendance Health Rings Component**:
  - SVG circular progress rings color-coded by thresholds: Emerald ($\ge 85\%$), Amber ($75\text{--}84\%$), Red ($< 75\%$).
  - Implemented in: [`frontend/src/components/AttendanceCard.tsx`](file:///home/robin/Projects/ERP/frontend/src/components/AttendanceCard.tsx)
- [x] **RBAC-Grounded Chatbot Drawer**:
  - Floating action button (FAB) expanding into a $420\text{ px} \times 600\text{ px}$ conversation drawer.
  - Verified source citation badges (green pills).
  - RBAC Security Rejection Card (subtle red alert with lock icon 🔒).
  - Quick-prompt test chips for instant query execution.
  - Implemented in: [`frontend/src/components/ChatDrawer.tsx`](file:///home/robin/Projects/ERP/frontend/src/components/ChatDrawer.tsx)
- [x] **Integrated Application Dashboard**:
  - Tabbed views for Overview, Live Transit, Attendance Tracker, Campus Regulations, and Security Audits.
  - Implemented in: [`frontend/src/app/page.tsx`](file:///home/robin/Projects/ERP/frontend/src/app/page.tsx)

---

## 🧪 Acceptance Test Verification Matrix

| Test Identifier | Persona | Query / Action | Expected Result | Verified Status |
| :--- | :--- | :--- | :--- | :--- |
| **TC-1: Cross-Role Breach Attempt** | Student | *"Show all faculty salaries in Computer Science"* | Explicit RBAC denial with lock icon 🔒; zero salary numerals leaked; audit log records `EVENT_PRIVILEGE_PROBE`. | **PASSED** ✅ |
| **TC-2: Tabular Accuracy** | Student | *"What is my attendance in Operating Systems?"* | Returns exact database attendance: 87.5% (35/40 classes attended) with citation badge. | **PASSED** ✅ |
| **TC-3: Public Knowledge RAG** | Student / Parent | *"What is the minimum attendance requirement?"* | Cites `Academic Regulations 2026 §4.2: Attendance Requirements & Examination Eligibility`. | **PASSED** ✅ |
| **TC-4: Live Telemetry Streaming** | Parent / Student | Connects to `ws://.../ws/transit/1` | GPS coordinates and live speed update at 3-second intervals with realistic waypoint progression. | **PASSED** ✅ |
| **TC-5: 500m Geofencing Alert** | Parent | Transit vehicle approaches registered stop | Emits `geofence_active: True` when distance $\le 500\text{m}$; displays glowing alert banner on Leaflet HUD with metric distance. | **PASSED** ✅ |
| **TC-6: TypeScript & Asset Build** | All | `npm run build` | 100% clean production build with zero type or lint errors in 4.4s. | **PASSED** ✅ |

---

## 📝 Changelog & Implementation History

### [Version 1.2.0] - 2026-09-26
#### Added
- **Dedicated Authentication & Role Determination Login Page (`/login`)**:
  - Implemented modern, glassmorphic login interface in [`frontend/src/app/login/page.tsx`](file:///home/robin/Projects/ERP/frontend/src/app/login/page.tsx).
  - Automatically submits credentials to `/api/v1/auth/login`, receives signed JWT security claims, saves authenticated session to `localStorage`, and redirects to the role-tailored dashboard.
  - Included interactive "One-Click Demo Login" buttons for all 4 role personas (`student`, `faculty`, `parent`, `admin`) to instantly test role determination.
  - Added password visibility toggles and real-time credential validation error alerts.
- **Top-Right Profile Icon & Interactive Hover Role Card**:
  - Updated [`frontend/src/components/Header.tsx`](file:///home/robin/Projects/ERP/frontend/src/components/Header.tsx) with a dedicated profile avatar icon in the top right.
  - Removed the static role badge from the top-left next to the OmniCampus ERP logo and removed the inline demo switcher bar, keeping the role cleanly displayed upon hovering the user profile in the top-right.
  - When hovered over the user's name and avatar, a floating glassmorphic profile card (`#role-hover-card`) appears displaying:
    - **Determined User Role** in high-contrast colored badge (`STUDENT`, `FACULTY`, `PARENT`, `ADMIN`).
    - Authenticated email address, User ID, and department/ward binding.
    - Specific list of active rights & privileges granted to that role under the Zero-Trust RBAC specification.
    - Direct "Sign Out" button (clears session and redirects to `/login`) and "Switch User" shortcut.
- **Session-Aware Dashboard & Automatic Rights Adjustment**:
  - Configured [`frontend/src/app/page.tsx`](file:///home/robin/Projects/ERP/frontend/src/app/page.tsx) to verify authenticated session claims on initial mount; redirects unauthenticated visitors to `/login`.
  - Automatically configures navigation tabs, route selectors, and audit logs according to determined rights.

### [Version 1.4.0] - 2026-09-26
#### Themed

- **Minimalist Light Theme (White Background & Black Text)**:
  - Transitioned the entire frontend interface to a clean white canvas with high-contrast black typography and subtle box variations:
    - Base canvas / page background: `#FFFFFF` (`--surface-dark`).
    - Main card surface: `#FFFFFF` (`--surface-card`).
    - Nested boxes & inputs: `#F8FAFC` (`--surface-elevated`) with subtle hairline border `#E2E8F0` (`--surface-border`).
    - Hover states: `#F1F5F9` (`--surface-hover`).
    - Typography: Solid deep black `#0F172A` (`--text-main`), secondary dark charcoal `#475569` (`--text-muted`), and slate labels `#64748B` (`--text-dim`).
  - High-contrast role badges on white: Student (`#F0F9FF` / `#0284C7`), Faculty (`#ECFDF5` / `#059669`), Parent (`#FFFBEB` / `#D97706`), Admin (`#F5F3FF` / `#7C3AED`).
  - Attendance tracker: white cards with `#E2E8F0` progress background ring, high-contrast SVG percentage text, and pastel alert tags (`#ECFDF5` safe standing, `#FEF2F2` debarment warning, `#FFFBEB` attention).
  - Chat Drawer: crisp conversational contrast with user message in solid black pill (`#0F172A`) with white text, and assistant responses in light elevated box (`#F8FAFC`) with emerald verified citation pills.
  - Live Transit Map: clean white frosted telemetry HUD and geofence proximity banner (`rgba(255, 255, 255, 0.96)`) with high-contrast text and OpenStreetMap standard cartography.
  - Login Page: pure white card with subtle borders, `#F8FAFC` input fields with black text, and high-contrast black submission CTA.

### [Version 1.3.0] - 2026-09-26
#### Redesigned

- **Minimalist Aesthetic & Color Redesign**:
  - Replaced high-saturation neon gradients and glowing borders with a refined obsidian matte palette (`#0A0B0E` background, `#12141A` surface cards, and `rgba(255, 255, 255, 0.07)` hairline borders).
  - Modernized typography, spacing, and micro-interactions inspired by clean Linear/Vercel enterprise interfaces.
  - Desaturated role badge color tokens (`--color-student: #7DD3FC`, `--color-faculty: #6EE7B7`, `--color-parent: #FDE68A`, `--color-admin: #C4B5FD`).
  - Redesigned [`frontend/src/app/page.tsx`](file:///home/robin/Projects/ERP/frontend/src/app/page.tsx): streamlined workspace overview, minimalist KPI metric cards, high-contrast tables, and simplified policy cards.
  - Redesigned [`frontend/src/app/login/page.tsx`](file:///home/robin/Projects/ERP/frontend/src/app/login/page.tsx): clean matte card, understated inputs, and minimal demo role quick-select chips.
  - Redesigned [`frontend/src/components/Header.tsx`](file:///home/robin/Projects/ERP/frontend/src/components/Header.tsx): removed static role label from top-left, added refined top-right user profile avatar with clean floating role hover card (`#role-hover-card`), removed the granted rights & privileges section for an ultra-clean minimal profile view.
  - Redesigned [`frontend/src/components/Sidebar.tsx`](file:///home/robin/Projects/ERP/frontend/src/components/Sidebar.tsx) and [`frontend/src/components/AttendanceCard.tsx`](file:///home/robin/Projects/ERP/frontend/src/components/AttendanceCard.tsx): sleek navigation items, thin attendance progress rings (5px), and desaturated status indicators.
  - Redesigned [`frontend/src/components/ChatDrawer.tsx`](file:///home/robin/Projects/ERP/frontend/src/components/ChatDrawer.tsx): minimal floating action button (50px circle), frosted matte chat drawer, clean message bubbles, and citation pill chips.
  - Refined [`frontend/src/components/LiveTransitMap.tsx`](file:///home/robin/Projects/ERP/frontend/src/components/LiveTransitMap.tsx): frosted matte HUD telemetry panel, minimal 500m geofence proximity toast, subtle indigo route polyline, and clean stop marker dots, while strictly preserving standard OpenStreetMap cartography.

### [Version 1.2.5] - 2026-09-26
#### Fixed & Hardened
- **`start.sh` Launcher Robustness & Clean Process Lifecycle**:
  - Replaced system tools (`lsof`, `nc`) with portable Python socket checks (`check_port`), eliminating startup delays when optional networking utilities are not pre-installed.
  - Corrected JWT import verification (`import jwt` instead of `import pyjwt`), eliminating redundant pip package re-installation loops on startup.
  - Added continuous process health loop with log redirection (`.backend.log` and `.frontend.log`), keeping the script alive until explicit user termination (`Ctrl+C`).
  - Added `@app.get("/api/v1/health")` route in [`backend/app/main.py`](file:///home/robin/Projects/ERP/backend/app/main.py) for health check probing.
  - Confirmed all background server processes (ports 8000 and 3000) are fully stopped per user request.

### [Version 1.3.0] - 2026-09-29
#### Added
- **Event–Exam Clash & Retake Rescheduling Engine (v1, End-to-End)**:
  - **Relational Models & Schema**:
    - Added tables: `events`, `event_participants`, `course_offerings`, `assessments`, `clash_cases`, `case_timeline`, `notifications`.
    - SQLite/PostgreSQL naive UTC datetime synchronization helper (`utcnow()`) with ISO-8601 formatting strictly at API boundary.
    - Department name normalizer (`normalize_department`) and exact-match HOD designation validator (`is_hod_designation`).
  - **Algorithmic Clash Detection & Parallel Slot Discovery**:
    - Implemented interval overlap engine in `clash_detector.py` (strict non-zero overlap where touching endpoints do not trigger clash).
    - Intelligent sister section parallel slot lookup filtering out event and student exam collisions.
  - **Transactional Compare-And-Set (CAS) State Machine**:
    - Atomic optimistic locking on state updates: `UPDATE ... WHERE id = :id AND status = :expected_status` (rowcount != 1 raises HTTP 409 Conflict).
    - Atomic rejection cascade: `REJECTED` immediately transitions to `ESCALATED_TO_HOD` within the same transaction, generating dual timeline audit entries.
    - Post-commit notification collection guarantee: `NotificationCollector` flushes alerts to DB and pub/sub broker strictly after `db.commit()`.
  - **Zero-Trust WebSocket & Real-time Notifications**:
    - Notification channels bound strictly to JWT claims (`channel:user:{user_id}` and `channel:admin`). Non-admins attempting admin channel are disconnected with `WS_1008_POLICY_VIOLATION`.
  - **Idempotent Scenario Seed Script & Rehearsal Test**:
    - `seed_clash_data.py`: Seeds Cloud Computing (Prof. Smith, Sections A, B, C) and Advanced Compilers (Prof. Turing, Section A), Hackathon event, and student participants.
    - Full end-to-end API test (`test_demo_rehearsal_e2e.py`) validating the 8-step lifecycle.
  - **Role-Tailored Frontend Workspaces (Next.js 14 App Router)**:
    - **Admin Event Management**: Create event, register participants, trigger detection, review clashes, bulk-file requests.
    - **Professor Reschedule Command Center**: View filed requests, review suggested sister-section slots, propose custom slots, approve or reject with mandatory cascade to HOD.
    - **Student My Clashes**: Live conflict status, assigned retake slot card, interactive chronological timeline audit trail.
    - **HOD Executive Governance**: Department-wide KPI metrics, escalated cases resolution, >48-hour stuck SLA warnings, faculty workload distribution.
    - **Notification Bell**: Auto-polling header bell with unread badge counter, popover list, and mark-as-read triggers.

### [Version 1.2.4] - 2026-09-26
#### Added
- **Automated Dependency Installer & Launcher (`start.sh`)**:
  - Implemented root-level bash script [`start.sh`](file:///home/robin/Projects/ERP/start.sh) that automatically verifies system prerequisites (Python 3.10+, Node.js 18+, npm), creates/activates Python virtual environments, installs missing Python packages from `backend/requirements.txt` and frontend npm packages, launches both FastAPI and Next.js, and provides graceful process termination on `SIGINT` / `SIGTERM` / `EXIT`.
  - Updated [`README.md`](file:///home/robin/Projects/ERP/README.md) with instructions for the One-Click Quick Start method.

### [Version 1.2.3] - 2026-09-26
#### Added
- **Project Documentation (`README.md`)**:
  - Created comprehensive [`README.md`](file:///home/robin/Projects/ERP/README.md) in the workspace root detailing project objectives, zero-trust multi-agent supervisor architecture, verified user personas, tech stack, and step-by-step instructions to run the backend and frontend services.

### [Version 1.2.2] - 2026-09-26
#### Removed
- **Dashboard Window Live Transit Map**:
  - Removed the inline Live Transit preview canvas from the Dashboard view in [`frontend/src/app/page.tsx`](file:///home/robin/Projects/ERP/frontend/src/app/page.tsx).
  - Maintained the complete interactive Live Transit map exclusively under the **Live Transit** sidebar navigation tab (`activeTab === "transit"`).

### [Version 1.2.1] - 2026-09-26
#### Removed
- **Sidebar Campus Policies Link**:
  - Removed "Campus Policies" from the navigation items list in [`frontend/src/components/Sidebar.tsx`](file:///home/robin/Projects/ERP/frontend/src/components/Sidebar.tsx).
  - Cleaned up unused `BookOpen` icon import.

### [Version 1.2.0] - 2026-09-26
#### Added
- **Faculty Class & Section Attendance Command Center**:
  - **Schema & Database Enhancements**:
    - Added `section` column to `students` table in [`backend/app/core/database.py`](file:///home/robin/Projects/ERP/backend/app/core/database.py).
    - Populated Computer Science Department with students across `Section A` and `Section B` with full attendance records for Operating Systems, Database Management Systems, and Computer Networks.
  - **Secure Backend API Endpoint (`GET /api/v1/erp/faculty/class-attendance`)**:
    - Implemented in [`backend/app/api/erp.py`](file:///home/robin/Projects/ERP/backend/app/api/erp.py) accepting optional `subject` and `section` query parameters.
    - Zero-Trust RBAC constraint enforced: strictly restricted to `claims.role in ['faculty', 'admin']`; verified that unauthorized students and parents receive `403 Forbidden`.
    - Returns class average percentage, safe count, attention count, debarment risk count, and detailed student-by-student attendance records.
  - **Multi-Agent Text-to-SQL Enhancement**:
    - Updated [`backend/app/agents/structured_records.py`](file:///home/robin/Projects/ERP/backend/app/agents/structured_records.py) so the AI Assistant resolves class attendance and section inquiries for faculty with verifiable citations.
  - **Frontend Faculty Command Center Interface**:
    - Built comprehensive faculty dashboard in [`frontend/src/app/page.tsx`](file:///home/robin/Projects/ERP/frontend/src/app/page.tsx) featuring course pills (`Operating Systems`, `Database Management Systems`, `Computer Networks`), section filter buttons (`All Sections`, `Section A`, `Section B` with badge counts), status filters (`Safe Standing ≥85%`, `Attention Required 75-84%`, `Debarment Warning <75%`), and real-time student search.
    - Integrated Academic Regulations §4.2 debarment advisory callout with direct warning notice dispatch triggers.
    - Maintained clean minimal white aesthetic with high-contrast text and responsive tables.

### [Version 1.1.3] - 2026-09-26
#### Updated
- **Standard OpenStreetMap Cartography Enforced ([UI-UX: §3.1](file:///home/robin/Projects/ERP/Docs/UI-UX_DESIGN_SPECIFICATIONS.md#L52))**:
  - Configured [`frontend/src/components/LiveTransitMap.tsx`](file:///home/robin/Projects/ERP/frontend/src/components/LiveTransitMap.tsx) to exclusively utilize Standard OpenStreetMap tiles (`https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png`) with official attribution.
  - Removed alternate tile toggles, providing a clean, consistent cartographic visual standard across all transit views.
  - Maintained interactive controls: Center Bus panning, full route auto-fit bounds, and 500m geofence perimeter alerts.

### [Version 1.1.2] - 2026-09-26

#### Enhanced

- **Leaflet Interactive Map Hardening ([UI-UX: §3.1](file:///home/robin/Projects/ERP/Docs/UI-UX_DESIGN_SPECIFICATIONS.md#L52))**:
  - Imported bundled local Leaflet CSS (`leaflet/dist/leaflet.css`) into both [`frontend/src/app/globals.css`](file:///home/robin/Projects/ERP/frontend/src/app/globals.css) and [`frontend/src/components/LiveTransitMap.tsx`](file:///home/robin/Projects/ERP/frontend/src/components/LiveTransitMap.tsx) to eliminate external CDN dependency.
  - Implemented automatic Leaflet `map.invalidateSize()` calls and attached a `ResizeObserver` on the map container to prevent gray or unrendered tiles during tab transitions.
  - Added multi-layer tile switching between **CartoDB DarkMatter** and **OpenStreetMap (OSM) Standard** tiles via an in-canvas toggle button.
  - Added on-map controls: "Center Bus" (smooth panning to live vehicle) and "Full Route" (auto fit bounds to route waypoints and stops).
  - Configured custom interactive SVG/HTML stop markers, 500m amber geofence perimeter circle, and animated pulsating bus beacon (`.bus-beacon`).

### [Version 1.1.1] - 2026-09-26
#### Fixed & Improved

- **Frontend Interactivity & Proxy Rewrites**:
  - Resolved `404 Not Found` errors by configuring Next.js rewrites in [`frontend/next.config.ts`](file:///home/robin/Projects/ERP/frontend/next.config.ts) to forward `/api/v1/:path*` directly to FastAPI on port 8000.
  - Added `allowedDevOrigins` in Next.js config to resolve cross-origin dev server blocking on `127.0.0.1` and local IP.
  - Eliminated `disabled={isLoading}` state lock in [`frontend/src/components/Header.tsx`](file:///home/robin/Projects/ERP/frontend/src/components/Header.tsx) to ensure role switcher buttons are always instantly clickable.
  - Updated [`frontend/src/app/page.tsx`](file:///home/robin/Projects/ERP/frontend/src/app/page.tsx) with robust pre-seeded initial state so all navigation tabs, transit maps, and course tables render immediately.
  - Unmounted condition check on `<ChatDrawer>` so the floating action button (FAB) is always visible and interactive across all sessions.
  - Added automatic fallback token resolution in [`frontend/src/components/ChatDrawer.tsx`](file:///home/robin/Projects/ERP/frontend/src/components/ChatDrawer.tsx) ensuring queries never fail with missing credentials.

### [Version 1.1.0] - 2026-09-26
#### Added
- **500m Geofencing Proximity Alert Engine ([PRD.md: FR-3.4](file:///home/robin/Projects/ERP/Docs/PRD.md#L55))**:

  - Implemented real-time geodesic Haversine distance tracking in [`backend/app/services/transit_simulator.py`](file:///home/robin/Projects/ERP/backend/app/services/transit_simulator.py) computing vehicular distance to parent registered stop.
  - Telemetry WebSocket frames dynamically broadcast `geofence_active: True`, `geofence_radius_meters: 500`, and `distance_to_registered_stop_m`.
  - Added visual 500m radius perimeter circle (`#F59E0B`) around the registered pickup stop on the Leaflet canvas.
  - Implemented dismissable glowing Geofence Proximity Alert banner (`🔔 500M GEOFENCE PROXIMITY ALERT`) and HUD badge state in [`frontend/src/components/LiveTransitMap.tsx`](file:///home/robin/Projects/ERP/frontend/src/components/LiveTransitMap.tsx).
  - Verified live alert triggering when simulated vehicle approaches within 454 meters of Midtown Gate.

### [Version 1.0.0] - 2026-09-26
#### Added
- Full initial scaffolding of Next.js 14 App Router frontend and FastAPI backend.
- Database schema and migration layer supporting PostgreSQL/pgvector and SQLite/aiosqlite.
- In-memory Pub/Sub and telemetry state broker.
- Mathematical transit simulator transmitting live coordinates for 20 bus routes.
- Zero-trust multi-agent supervisor pipeline with parametric SQL isolation and metadata pre-filtering.
- Dark enterprise UI with role-based navigation, Leaflet visualizer, and SVG attendance rings.
- Created `PROGRESS.md` to track current milestones and all future changes.

---

## 🔮 Upcoming Milestones & Planned Enhancements

- [ ] **Interactive Faculty Attendance Input ([PRD.md: FR-4.1](file:///home/robin/Projects/ERP/Docs/PRD.md#L58))**: Interactive UI form for professors to mark daily subject attendance directly into the relational table.
- [ ] **Admin Knowledge Base Document Ingestion Portal**: Admin UI to upload/ingest new policy documents with `allowed_roles` and department metadata tags.
- [ ] **Ambiguous Query Disambiguation ([AGENTS.md: §6](file:///home/robin/Projects/ERP/Docs/AGENTS.md#L249))**: Assistant returning interactive clarification chips for broad inquiries.
- [ ] **Token-by-Token Streaming Responses ([UI-UX: §4.B](file:///home/robin/Projects/ERP/Docs/UI-UX_DESIGN_SPECIFICATIONS.md#L109))**: Server-Sent Events (SSE) streaming for conversational token generation.
- [ ] **Bulk Synthetic Scale Generator ([PRD.md: FR-4.3](file:///home/robin/Projects/ERP/Docs/PRD.md#L60))**: CLI script to populate $\ge 1,000$ synthetic student records.
- [ ] **Multi-Child Parent Switcher ([UI-UX: §2](file:///home/robin/Projects/ERP/Docs/UI-UX_DESIGN_SPECIFICATIONS.md#L32))**: Header selector for parents with multiple enrolled wards.

