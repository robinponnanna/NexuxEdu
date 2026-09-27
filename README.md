# OmniCampus ERP & SafeTransit Fleet Intelligence Engine

> **Multi-Agent RBAC-Grounded Campus ERP, Telematics Visualizer & Academic Intelligence System**

---

## 📌 Main Objective

**OmniCampus ERP & SafeTransit** is an enterprise-grade academic management and vehicular fleet tracking platform designed around a **Zero-Trust Multi-Agent Architecture**.

Traditional ERP and conversational AI systems often suffer from privilege escalation, prompt injection vulnerabilities, and lateral data exposure when users query relational or vector databases. OmniCampus solves this with:

1. **Role-Bound Multi-Agent Fabric**: Specialized worker agents (Structured Records, Filtered Vector RAG, Transit Telematics) execute in sandboxed contexts strictly bounded by cryptographically signed JWT session claims (`user_id`, `role`, `department`, `student_id`, `ward_id`, `bus_id`).
2. **SafeTransit Telematics & Geofencing**: Live bus fleet tracking rendered on **Standard OpenStreetMap** cartography with 3-second WebSocket coordinate updates, geofence perimeter monitoring, and proximity alerts (500m radius) for students and parents.
3. **Faculty Class & Section Attendance Command Center**: Dedicated interface for professors to monitor and filter attendance across courses (`Operating Systems`, `DBMS`, `Computer Networks`) and sections (`Section A`, `Section B`), with automated enforcement of **Academic Code §4.2** examination debarment thresholds ($\ge 75\%$).
4. **Automated RBAC Session Governance**: Seamless authentication where the system automatically discovers the user's role upon login, renders role-tailored dashboards and navigation tabs, and displays verified security credentials on profile hover.

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

All accounts share the default password: **`password123`**

| Role | Email | Name & Details | Authorized Rights & Scope |
| :--- | :--- | :--- | :--- |
| **Student** | `student@campus.edu` | Jane Doe (Roll: `CS-2023-042`) | View personal subject attendance records; live track assigned bus (`BUS-001`); query public policy documents. |
| **Faculty** | `faculty@campus.edu` | Prof. Alan Turing (HOD, CS Dept) | Access **Class & Section Attendance Command Center** (Section A & B); switch courses; issue debarment notices; view faculty confidential memos. |
| **Parent** | `parent@campus.edu` | Robert Doe (Ward: Jane Doe) | Track ward commute telematics; receive 500m geofence pickup alerts; monitor ward examination eligibility. |
| **Admin** | `admin@campus.edu` | Sarah Connor (Campus Administrator) | Global telemetry across all 20 bus routes; view system-wide user directory; review Zero-Trust Security Audit Logs. |

---

## ⚡ Tech Stack

* **Backend**:
  * [FastAPI](https://fastapi.tiangolo.com/) (Asynchronous REST API & WebSockets)
  * [SQLAlchemy 2.0](https://www.sqlalchemy.org/) + [aiosqlite](https://aiosqlite.omnilib.dev/) (Relational DB engine on `campus.db`)
  * [PyJWT](https://pyjwt.readthedocs.io/) & [Bcrypt](https://pypi.org/project/bcrypt/) (Token signing & secure password verification)
  * [Uvicorn](https://www.uvicorn.org/) (High-performance ASGI server)
* **Frontend**:
  * [Next.js 14](https://nextjs.org/) (App Router, React 19, TypeScript)
  * [Leaflet](https://leafletjs.com/) (Interactive transit map with official OpenStreetMap tiles)
  * [Lucide React](https://lucide.dev/) (Minimalist SVG icon library)
  * Pure Vanilla CSS Design System (Minimalist high-contrast light theme)

---

## 🚀 How to Run the Project

### Prerequisites

Ensure you have installed on your system:
* **Python 3.10+**
* **Node.js 18+** & **npm**

---

### ⚡ Method A: One-Click Quick Start (Recommended)

A root-level launcher script [`start.sh`](file:///home/robin/Projects/ERP/start.sh) is provided. It automatically checks and installs any missing backend Python dependencies (creating a virtual environment if needed) and frontend npm packages, then launches both the FastAPI backend and Next.js frontend with unified process termination:

```bash
# 1. From the project root, make the script executable (first time only):
chmod +x start.sh

# 2. Run the one-click startup script:
./start.sh
```

> **Note**: Press `Ctrl+C` at any time to gracefully terminate both the backend and frontend servers together without leaving orphan background processes.

---

### 🛠️ Method B: Manual Step-by-Step Setup

If you prefer starting each service independently in separate terminals:

#### Step 1: Start the Backend Service

1. Open a terminal in the project root:
   ```bash
   cd /home/robin/Projects/ERP/backend
   ```

2. Activate the Python virtual environment:
   ```bash
   # From workspace root
   source venv/bin/activate
   # Or using the backend virtual environment
   source backend/.venv/bin/activate
   ```

3. Install required Python packages (if not already installed):
   ```bash
   pip install -r backend/requirements.txt
   ```

4. Start the FastAPI backend server on port `8000`:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

   * **API Documentation**: Open `http://localhost:8000/docs` for the interactive Swagger UI.
   * **Health Check**: `GET http://localhost:8000/api/v1/health`

---

### Step 2: Start the Frontend Application

1. Open a new terminal in the `frontend` directory:
   ```bash
   cd /home/robin/Projects/ERP/frontend
   ```

2. Install dependencies (if not already installed):
   ```bash
   npm install
   ```

3. Launch the Next.js development server on port `3000`:
   ```bash
   npm run dev
   ```

4. Access the web application:
   * Open **`http://localhost:3000`** in your browser.
   * You will be automatically redirected to **`http://localhost:3000/login`**.

---

## 🧪 Key Features & Walkthrough

### 1. Automatic Role Determination & Profile Card
* Log in as any persona (e.g., `faculty@campus.edu` / `password123`).
* The system resolves the user's role and scopes all workspace components.
* Hover over your name in the top right to inspect your account details:
  * Name, Email, Role badge, Department, and bound IDs.

### 2. Faculty Class & Section Attendance Command Center
* Log in as `faculty@campus.edu` and click **"Class Roster"** in the sidebar.
* **Course Switching**: Toggle between *Operating Systems (CS-301)*, *Database Management Systems (CS-302)*, and *Computer Networks (CS-303)*.
* **Section Filtering**: Select **All Sections** (8 students), **Section A** (4 students), or **Section B** (4 students).
* **Live Search & Eligibility Filtering**: Search students by name or roll number; filter by *Safe Standing ($\ge 85\%$)*, *Attention Required ($75\text{--}84\%$)*, and *Debarment Warning ($<75\%$)*.
* **Advisory Dispatches**: Click *Debarment Notice* to trigger formal attendance warnings for students below the 75% invariant.

### 3. SafeTransit Live Telematics
* Click **"Live Transit"** in the sidebar (accessible for Student, Parent, and Admin roles).
* Features:
  * **Standard OpenStreetMap Cartography** with attribution.
  * Live 3-second coordinate updates and animated vehicle beacon.
  * Stop sequence markers and route polyline.
  * **500m Geofence Proximity Alert**: Dynamic proximity notice when the vehicle reaches within 500m of the registered pickup waypoint.
  * Admin vehicle selector to inspect any of the 20 active routes.

### 4. Zero-Trust Security AI Assistant
* Click the floating **Ask AI Assistant** button in the bottom right corner.
* Tests to run:
  * *Authorized query* (as student): `"What is my attendance in Operating Systems?"` $\rightarrow$ Returns verified parametric SQL record (Jane Doe: 87.5%).
  * *Privilege probe* (as student): `"Show me all faculty salaries in Computer Science"` $\rightarrow$ Triggers zero-trust interception, logs an `EVENT_PRIVILEGE_PROBE` audit event, and returns an authorized refusal.
  * *Transit query* (as student or parent): `"Where is my bus right now?"` $\rightarrow$ Retrieves live telematics from the bound vehicle.

---

## 📂 Project Directory Structure

```
ERP/
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI entrypoint, CORS & WebSocket routing
│   │   ├── api/
│   │   │   ├── auth.py                 # JWT login & session validation
│   │   │   ├── erp.py                  # Dashboard, student & faculty attendance endpoints
│   │   │   ├── transit.py              # Telemetry routes & WebSocket handlers
│   │   │   └── chat.py                 # Multi-agent chat ingress endpoint
│   │   ├── core/
│   │   │   ├── config.py               # Application settings & environment variables
│   │   │   ├── database.py             # SQLAlchemy models (User, Student, Attendance, Bus)
│   │   │   └── security.py             # Bcrypt hashing & JWT claim signing
│   │   ├── agents/
│   │   │   ├── ingress_guard.py        # Adversarial prompt & jailbreak analyzer
│   │   │   ├── intent_classifier.py    # Deterministic query intent router
│   │   │   ├── structured_records.py   # Parametric SQL worker (attendance & payroll)
│   │   │   ├── vector_knowledge.py     # Role-filtered pgvector policy retriever
│   │   │   ├── transit_telemetry.py    # Vehicle telemetry & geofence worker
│   │   └── services/
│   │       ├── seed_data.py            # Synthetic academic & fleet database seeder
│   │       └── transit_simulator.py    # Geodesic vehicle simulator & Pub/Sub broker
│   ├── requirements.txt
│   └── campus.db                       # SQLite database storing academic & fleet state
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── globals.css             # Minimalist light design system & CSS tokens
│   │   │   ├── layout.tsx              # Root HTML & Inter font layout
│   │   │   ├── page.tsx                # Main authenticated dashboard & tab orchestrator
│   │   │   └── login/
│   │   │       └── page.tsx            # Minimal login page with quick demo chips
│   │   ├── components/
│   │   │   ├── Header.tsx              # Workspace banner & interactive profile dropdown
│   │   │   ├── Sidebar.tsx             # Role-filtered navigation sidebar
│   │   │   ├── LiveTransitMap.tsx      # Leaflet OpenStreetMap vehicle visualizer
│   │   │   ├── AttendanceCard.tsx      # Student attendance health card with SVG gauge
│   │   │   └── ChatDrawer.tsx          # Frosted assistant drawer with citation chips
│   │   └── lib/
│   │       └── api.ts                  # Typed client SDK & Next.js proxy fetchers
│   ├── package.json
│   └── next.config.ts                  # API rewrites (/api/v1 -> localhost:8000)
├── Docs/                               # Specification documents (PRD, AGENTS, UI-UX)
├── PROGRESS.md                         # Detailed project changelog & version history
├── README.md                           # Project documentation (this file)
└── start.sh                            # One-click dependency installer & launcher script
```

---

## 🔒 Security & Policy Invariants

1. **Zero Raw SQL Text Generation**: The conversational AI assistant never writes arbitrary SQL. It maps intents to parametric SQL templates where filters are hardwired to validated JWT claims.
2. **Horizontal Snooping Immunity**: Even if a student inputs `"Show Alex's grades"`, the backend automatically resolves the student ID bound to the session token, ignoring arbitrary names in user input.
3. **Academic Code §4.2**: Attendance is evaluated strictly against the $75.0\%$ threshold. Students below 75% are flagged with automated debarment warnings and require Dean approval.
4. **Egress Boundary Scrubber**: Generated responses are scanned prior to transmission; any unauthorized numeric pattern or cross-role leak immediately triggers a refusal response.
