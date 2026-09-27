# Product Requirements Document (PRD)
## Next-Gen Smart Campus ERP with RBAC-Grounded AI & Live Transit Telemetry

---

### 1. Document Overview
* **Project Name:** OmniCampus ERP & SafeTransit
* **Document Version:** 1.0.0
* **Target Audience:** Engineering Team, Hackathon Judges, Product Evaluators
* **Target Release:** Hackathon MVP (v1)

---

### 2. Executive Summary & Problem Statement
Traditional Higher Education Enterprise Resource Planning (ERP) systems suffer from two major flaws:
1. **Navigational Friction & Siloed Data:** Portals require users to click through dozens of nested tables to find simple answers (e.g., "Am I eligible for exams based on my attendance?"). Adding a conversational LLM usually causes severe security vulnerabilities—standard LLM wrappers frequently leak private records (faculty compensation, administrative keys, student academic infractions) through prompt injection or unpartitioned context.
2. **Disconnected Transit & Student Safety:** Parents have zero real-time visibility into transit operations, relying on manual phone calls to drivers or outdated static timetable schedules.

**OmniCampus ERP** solves this with an enterprise-grade academic platform featuring:
* A **Role-Based Retrieval-Augmented Generation (RBAC-RAG) Chatbot** that mathematically enforces data boundaries at the retrieval layer—preventing cross-role data leaks between Students, Faculty, Parents, and Admins.
* A **Real-Time School Bus Telemetry Engine** streaming live vehicle coordinates, route waypoints, and ETA predictions straight to authenticated Parent portals.

---

### 3. User Personas & Permissions Matrix

| Persona | Primary Goal | Chatbot RBAC Scope | Transit Tracking Scope |
| :--- | :--- | :--- | :--- |
| **Student** | Track personal attendance, course syllabi, exam schedules, and academic standing. | Public institution knowledge base, personal attendance/grades, enrolled course syllabi. **Denied:** Faculty payroll, other students' records, admin audits. | View assigned bus route schedule only (no driver personal details). |
| **Faculty** | Review department rosters, submit attendance, query teaching materials, track departmental memos. | Departmental curriculum, assigned student rosters, personal salary/benefits, faculty committee minutes. **Denied:** Cross-department restricted records, admin master keys. | Static route directory. |
| **Parent** | Ensure child safety during transit, track ward's attendance and academic progress. | Ward-specific attendance alerts, academic calendar, administrative payment notices. **Denied:** General student roster, faculty personal data. | **Full Live Tracking:** Real-time GPS coordinates, vehicle speed, live map marker, and delay notifications for assigned bus. |
| **Admin** | Manage user credentials, allocate bus routes, ingest institutional policy docs into vector index. | Global institutional access, cross-department analytics, audit logs, vector index ingestion controls. | Master fleet control: All buses, driver assignments, route telemetry anomalies. |

---

### 4. Functional Requirements

#### 4.1. Core Authentication & RBAC Engine (Auth-Module)
* **FR-1.1:** System shall support 4 distinct role profiles: `student`, `faculty`, `parent`, `admin`.
* **FR-1.2:** Session authentication must issue JSON Web Tokens (JWT) containing cryptographically signed claims (`user_id`, `role`, `department_id`, `student_id` or `ward_id`, `bus_id`).
* **FR-1.3:** Role tokens must be immutable from the client-side and verified on every REST, WebSocket, and RAG execution request.

#### 4.2. RBAC-Grounded Conversational AI (RAG-Module)
* **FR-2.1: Retrieval-Level Enforcement:** System must NEVER rely on LLM system instructions to enforce privacy. Retrieval filtering must occur at the vector database and relational query levels before LLM synthesis.
* **FR-2.2: Dual-Stream Retrieval (Hybrid RAG):**
  * *Unstructured Stream:* Institutional handbooks, syllabi, grading policies stored in a vector database with strict metadata tags (`allowed_roles`, `department`).
  * *Structured Stream (Text-to-Parametric SQL):* Personal records (attendance %, pending dues, payroll) translated into parameterized SQL bounded to the authenticated session's `user_id`.
* **FR-2.3: Zero-Leakage Guarantee:** If a student asks *"What is the salary of Professor Smith?"*, the vector search and SQL filter must return an empty context, causing the LLM to output a standard refusal: *"I do not have authorization to access faculty records."*
* **FR-2.4: Traceable Citations:** All unstructured policy responses must cite document name and section.

#### 4.3. Real-Time School Bus Transit Engine (Transit-Module)
* **FR-3.1: Live Telemetry Ingestion:** Backend must ingest GPS latitude, longitude, velocity, and timestamp at 3-second intervals per vehicle.
* **FR-3.2: WebSocket Broadcasting:** Backend must publish real-time coordinates to role-authorized WebSocket channels (e.g., `ws://api/transit/stream/{bus_id}`).
* **FR-3.3: Parent Map Visualizer:** Parent dashboard must render an interactive map displaying current bus location, polyline route path, and student pick-up/drop-off point.
* **FR-3.4: Geofencing Alerts (Optional/MVP+):** Trigger arrival notification when bus enters a 500-meter radius of the parent's registered stop.

#### 4.4. Academic & Attendance Management (ERP-Core)
* **FR-4.1:** Faculty can mark and update daily subject attendance.
* **FR-4.2:** Attendance engine automatically calculates eligibility thresholds ($< 75\%$ flag).
* **FR-4.3:** Synthetic database pre-loaded with $\ge 1,000$ students, $\ge 1,000$ faculty, associated parents, and 20 bus routes for demonstration.

---

### 5. Non-Functional Requirements

* **NFR-1 (Latency):**
  * Bus GPS update broadcast latency: $< 500\text{ ms}$ via WebSockets.
  * Chatbot response First Token Time (TTFT): $< 1.5\text{ s}$ using fast inference models (e.g., Llama-3-8B on Groq or OpenAI GPT-4o-mini).
* **NFR-2 (Security & Isolation):** Zero cross-tenant data leakage. SQL injection prevention through parameterized queries; no raw string interpolation in AI tools.
* **NFR-3 (Availability & Demo Resilience):** In-memory fallback GPS simulator to ensure zero transit demo failures even without physical hardware.
* **NFR-4 (Device Compatibility):** Fully responsive web design functioning on Chrome/Firefox desktop and iOS/Android mobile web browsers.

---

### 6. Hackathon MVP Success Criteria & Acceptance Tests
1. **Test Case 1 (Student Security Breach Attempt):** Student logs in $\rightarrow$ inputs query *"Show all faculty salaries in Computer Science"* $\rightarrow$ Response must explicitly deny or state information is inaccessible. Database log confirms no query touched the `faculty.annual_salary` column without role validation.
2. **Test Case 2 (Tabular Accuracy):** Student asks *"What is my attendance in Operating Systems?"* $\rightarrow$ Model returns precise synthetic data matching the database.
3. **Test Case 3 (Live Transit):** Parent logs in $\rightarrow$ Navigates to "Live Bus" $\rightarrow$ Map shows moving vehicle icon along predefined coordinates updated every 3 seconds.