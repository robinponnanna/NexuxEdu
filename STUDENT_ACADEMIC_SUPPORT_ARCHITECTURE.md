# NexuxEdu Student Academic Support — Architecture Analysis & Technical Specification

**Document Version:** 1.0.0 (Design & Architecture Baseline)  
**Date:** September 29, 2026  
**Status:** Read-Only Technical Architecture Specification  
**Target Repository:** [https://github.com/robinponnanna/NexuxEdu.git](https://github.com/robinponnanna/NexuxEdu.git)  

---

## 1. Existing Project Summary

**NexuxEdu** (internally branded as **OmniCampus ERP & SafeTransit**) is an integrated higher education ERP and fleet intelligence platform combining:
* **Zero-Trust Multi-Agent RBAC Conversational AI:** An orchestrated multi-agent supervisor pipeline ([`orchestrator.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/agents/orchestrator.py)) that strictly scopes all database queries and semantic document retrieval to cryptographically verified JSON Web Token (JWT) session claims (`user_id`, `role`, `department`, `student_id`, `ward_id`, `bus_id`), preventing lateral cross-account data leaks and adversarial prompt injection.
* **Real-Time Fleet Telemetry:** An asynchronous background simulator ([`transit_simulator.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/services/transit_simulator.py)) and in-memory pub/sub broker ([`pubsub.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/core/pubsub.py)) broadcasting live GPS coordinates, velocity, ETA, and 500-meter geodesic Haversine geofence proximity alerts for 20 campus buses over WebSockets.
* **Academic Attendance & Faculty Governance:** Role-partitioned dashboards providing subject attendance progress rings, examination debarment warnings (<75% threshold under Academic Regulation §4.2), and a faculty command center for section rosters and attendance advisory dispatches.

---

## 2. Existing Student Experience

The current student user journey consists of:
1. **Authentication (`/login`):** The student enters `student@campus.edu` / `password123` (or clicks the "Jane Doe" one-click preset).
2. **Session Verification & Claims Binding:** The backend issues a JWT containing `role: "student"`, `student_id: 1`, `bus_id: 1`, `department: "Computer Science"`. The frontend stores this in `localStorage` (`omnicampus_session`).
3. **Workspace Dashboard (`/`):**
   * **KPIs:** Overall Attendance percentage ($81.9\%$), Assigned Bus (`BUS-001`), Academic Standing (Semester 6, Computer Science).
   * **Attendance Cards:** 4 subject cards with SVG circular progress rings ([`AttendanceCard.tsx`](file:///c:/Users/gagan/NexuxEdu/frontend/src/components/AttendanceCard.tsx)):
     * Operating Systems: $87.5\%$ ($35/40$ classes) — Safe Standing
     * Database Management Systems: $92.5\%$ ($37/40$ classes) — Safe Standing
     * Computer Networks: $77.5\%$ ($31/40$ classes) — Attention Required ($75\text{--}84\%$)
     * Theory of Computation: $70.0\%$ ($28/40$ classes) — Debarment Risk flag ($<75\%$)
4. **Live Transit Visualizer:** Leaflet.js canvas ([`LiveTransitMap.tsx`](file:///c:/Users/gagan/NexuxEdu/frontend/src/components/LiveTransitMap.tsx)) tracking the student's assigned bus (`BUS-001`) with live speed, route polyline, and next stop ETA.
5. **AI Assistant Drawer:** Floating action button expanding into [`ChatDrawer.tsx`](file:///c:/Users/gagan/NexuxEdu/frontend/src/components/ChatDrawer.tsx), allowing verified attendance lookups and university handbook inquiries with verifiable source citation badges.

---

## 3. Existing Student Routes & UI Components

### Routes & Screens
* [`frontend/src/app/login/page.tsx`](file:///c:/Users/gagan/NexuxEdu/frontend/src/app/login/page.tsx) — Login page with student credentials preset.
* [`frontend/src/app/page.tsx`](file:///c:/Users/gagan/NexuxEdu/frontend/src/app/page.tsx) — Single-page dashboard containing tabbed views:
  * `activeTab === "dashboard"`: Workspace overview and attendance health preview.
  * `activeTab === "attendance"`: Granular subject attendance cards.
  * `activeTab === "transit"`: Live transit Leaflet map.

### UI Components
* [`frontend/src/components/Header.tsx`](file:///c:/Users/gagan/NexuxEdu/frontend/src/components/Header.tsx) — Header with profile avatar and floating hover role badge (`#role-hover-card`).
* [`frontend/src/components/Sidebar.tsx`](file:///c:/Users/gagan/NexuxEdu/frontend/src/components/Sidebar.tsx) — Navigation menu displaying role-permitted tabs (`dashboard`, `transit`, `attendance`).
* [`frontend/src/components/AttendanceCard.tsx`](file:///c:/Users/gagan/NexuxEdu/frontend/src/components/AttendanceCard.tsx) — SVG circular progress ring component with status tags.
* [`frontend/src/components/LiveTransitMap.tsx`](file:///c:/Users/gagan/NexuxEdu/frontend/src/components/LiveTransitMap.tsx) — Leaflet transit visualizer with HUD and 500m geofence alert.
* [`frontend/src/components/ChatDrawer.tsx`](file:///c:/Users/gagan/NexuxEdu/frontend/src/components/ChatDrawer.tsx) — Grounded conversational assistant drawer.

---

## 4. Existing Academic Backend

### Endpoints
* `POST /api/v1/auth/login` — Issues signed JWT containing `student_id`.
* `GET /api/v1/auth/me` — Decodes and returns active security claims.
* `GET /api/v1/erp/dashboard` — Aggregates attendance records, overall percentage, and assigned bus.
* `GET /api/v1/erp/attendance` — Returns list of `AttendanceRecord` models for the authenticated student.
* `GET /api/v1/erp/faculty/class-attendance` — Class roster (strictly blocked with `403 Forbidden` for students).
* `POST /api/v1/chat/query` — Zero-trust multi-agent query pipeline.

---

## 5. Existing Database Models

Located in [`backend/app/core/database.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/core/database.py):

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
│ id, bus_number, route_name,     │◄────┤ id, student_id(FK)│
│ driver_name, driver_phone,      │     │ subject, total,   │
│ current_lat, current_lng, speed,│     │ attended, pct     │
│ status, stops_json, waypoints   │     └───────────────────┘
└─────────────────────────────────┘
```

---

## 6. Existing Attendance Architecture

* **Database Table:** `attendance` with columns `id`, `student_id`, `subject`, `total_classes`, `attended_classes`, `attendance_pct`.
* **Calculation:** $\text{attendance\_pct} = (\text{attended\_classes} / \text{total\_classes}) \times 100$.
* **Scoping:** Parameterized SQL queries strictly filter by `student_id = claims.student_id` (or `claims.ward_id` for parents). Client cannot pass arbitrary student IDs.
* **Debarment Logic:** 
  * $\ge 85.0\%$: Safe Standing (Emerald `#10B981`)
  * $75.0\text{--}84.9\%$: Attention Required (Amber `#F59E0B`)
  * $< 75.0\%$: Debarment Risk (Red `#EF4444` under Academic Regulation §4.2)

---

## 7. Existing Marks Architecture

* **Status:** **ABSENT / NOT IMPLEMENTED**
* **Finding:** The repository currently has zero models, tables, API endpoints, or UI views for assessment marks (CA1, CA2, CA3, Midterm, Endterm). In `page.tsx`, only attendance and course names are rendered.

---

## 8. Existing CO / Module Architecture

* **Status:** **ABSENT / NOT IMPLEMENTED**
* **Finding:** Course Outcomes (CO1..CO5) and Subject Modules (Module 1..5) are mentioned in documentation and requirements, but are not modeled in `database.py` or `schemas.py`.

---

## 9. Existing Assessment Architecture

* **Status:** **ABSENT / NOT IMPLEMENTED**
* **Finding:** No tables or services currently store question-level marks, max marks, question CO mappings, or OR-choice question groups.

---

## 10. Existing Document / Material Infrastructure

* **Status:** **PARTIALLY PRESENT (POLICIES ONLY)**
* **Current Implementation:** Table `document_embeddings` exists in [`backend/app/core/database.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/core/database.py#L72-L81) storing institutional handbook texts with metadata (`allowed_roles`, `department`, `embedding_json`).
* **Gap:** No entity or table exists for course-specific textbook chapters, lecture notes, page-by-page slides, or academic PDF materials. No PDF reader (e.g. PDF.js) is installed in `package.json`.

---

## 11. Existing RAG Architecture

* **Worker:** [`backend/app/agents/vector_knowledge.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/agents/vector_knowledge.py).
* **Mechanism:**
  1. Computes 384-dimensional dense pseudo-embedding for the query.
  2. Applies SQL metadata pre-filter: `claims.role in doc.allowed_roles` and department scope match.
  3. Computes cosine similarity via `numpy`: $\text{Sim}(\vec{q}, \vec{d}) = (\vec{q} \cdot \vec{d}) / (\|\vec{q}\|\|\vec{d}\|)$.
  4. Ranks top results, extracts citation metadata (`title`, `section`), and forwards context to synthesis.
* **Extensibility:** The existing vector knowledge worker can naturally be extended to search academic textbook/lecture note chunks when scoped to a student's enrolled courses.

---

## 12. Existing Security Architecture

* **Invariant 1 (Session Ingress):** `get_current_user_claims()` in [`backend/app/api/auth.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/api/auth.py#L11-L24) extracts and validates JWT bearer tokens.
* **Invariant 2 (Parameter Isolation):** Parametric SQL queries strictly bind `student_id = claims.student_id`. Prompt text cannot alter query IDs.
* **Invariant 3 (Metadata Pre-Filter):** Vector similarity is restricted to rows matching user role.
* **Invariant 4 (Egress Guardrail):** Scans outbound assistant tokens for cross-role leaks (e.g., salary figures) and redacts unauthorized data.
* **Invariant 5 (Audit Trail):** Privilege probes trigger `EVENT_PRIVILEGE_PROBE` logs into `audit_logs` table.

---

## 13. Proposed Student Academic Support Architecture

```
[ Student View: Academic Support ]
                │
                ├──────────────────────────────────────────────┐
                ▼                                              ▼
 ┌─────────────────────────────┐                ┌─────────────────────────────┐
 │    Attendance Explorer      │                │        Marks Explorer       │
 │ - Overall & per-subject %   │                │ - CA1, CA2, CA3, Midterm,   │
 │ - Debarment risk flags      │                │   Endterm score breakdown   │
 └─────────────────────────────┘                └──────────────┬──────────────┘
                                                               │
                                                               ▼
                                                ┌─────────────────────────────┐
                                                │   Module / CO Performance   │
                                                │ - CO1..CO5 percentage score │
                                                │ - Deterministic weak module │
                                                │   identification (e.g. CO3) │
                                                └──────────────┬──────────────┘
                                                               │
                                                               ▼ Click "Needs Support"
                                                ┌─────────────────────────────┐
                                                │   Material-Based Learning   │
                                                │ - Interactive Document/Notes│
                                                │   Reader for Subject Module │
                                                └──────────────┬──────────────┘
                                                               │
                                                               ▼ Student highlights text
                                                ┌─────────────────────────────┐
                                                │   Highlight-to-Explain      │
                                                │ - Contextual Action Trigger │
                                                │ - Sends Text + Page + CO    │
                                                └──────────────┬──────────────┘
                                                               │
                                                               ▼ POST /student/learning/explain
                                                ┌─────────────────────────────┐
                                                │  Academic RAG & AI Engine   │
                                                │ - Scoped to course material │
                                                │ - Structured micro-lesson   │
                                                │   generation / cached match │
                                                └──────────────┬──────────────┘
                                                               │
                                                               ▼ Micro-Lesson JSON
                                                ┌─────────────────────────────┐
                                                │  Interactive Micro-Lesson   │
                                                │           Player            │
                                                │ - Timed visual scenes       │
                                                │ - Concept, Diagram, Example,│
                                                │   Common Mistake, Takeaway  │
                                                └─────────────────────────────┘
```

---

## 14. Proposed Data Model

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   EXISTING ENTITIES (REUSED)                                    │
├────────────────────────────────┬────────────────────────────────┬───────────────────────────────┤
│ User                           │ Student                        │ Attendance                    │
│ id, public_id, name, email, ...│ id, user_id, roll_number, ...  │ id, student_id, subject, ...  │
└────────────────────────────────┴────────────────────────────────┴───────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       NEW ACADEMIC ENTITIES                                     │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. Subject                                                                                      │
│    - id: Integer (PK)                                                                           │
│    - code: String (e.g. "CS-301")                                                               │
│    - name: String (e.g. "Operating Systems")                                                    │
│    - department: String (e.g. "Computer Science")                                               │
│    - semester: Integer (e.g. 6)                                                                 │
│                                                                                                 │
│ 2. SubjectModule (Course Outcomes)                                                              │
│    - id: Integer (PK)                                                                           │
│    - subject_id: Integer (FK -> Subject.id)                                                     │
│    - module_number: Integer (1 to 5)                                                            │
│    - co_code: String (e.g. "CO1", "CO2", "CO3")                                                 │
│    - title: String (e.g. "Memory Management & Paging")                                          │
│    - description: Text                                                                          │
│                                                                                                 │
│ 3. Assessment                                                                                   │
│    - id: Integer (PK)                                                                           │
│    - subject_id: Integer (FK -> Subject.id)                                                     │
│    - name: String (e.g. "Continuous Assessment 1", "Midterm Examination", "Endterm Exam")       │
│    - category: String ("CA1", "CA2", "CA3", "Midterm", "Endterm")                               │
│    - max_marks: Float (e.g. 20.0, 50.0, 100.0)                                                  │
│    - weightage_pct: Float (e.g. 15.0, 30.0, 50.0)                                               │
│                                                                                                 │
│ 4. AssessmentQuestion                                                                           │
│    - id: Integer (PK)                                                                           │
│    - assessment_id: Integer (FK -> Assessment.id)                                               │
│    - question_label: String (e.g. "Q1", "Q6A", "Q6B")                                           │
│    - module_id: Integer (FK -> SubjectModule.id)                                                │
│    - co_code: String (e.g. "CO3")                                                               │
│    - max_marks: Float (e.g. 2.0, 10.0)                                                          │
│    - is_optional: Boolean (Default False)                                                       │
│    - or_group_id: Optional[String] (e.g. "Q6_OR_GROUP" for Q6A vs Q6B handling)                 │
│                                                                                                 │
│ 5. StudentQuestionMark                                                                          │
│    - id: Integer (PK)                                                                           │
│    - student_id: Integer (FK -> Student.id)                                                     │
│    - question_id: Integer (FK -> AssessmentQuestion.id)                                         │
│    - marks_obtained: Float (e.g. 4.0 out of 10.0)                                               │
│    - is_attempted: Boolean (True if student selected this OR option)                            │
│                                                                                                 │
│ 6. LearningMaterial                                                                             │
│    - id: Integer (PK)                                                                           │
│    - subject_id: Integer (FK -> Subject.id)                                                     │
│    - module_id: Integer (FK -> SubjectModule.id)                                                │
│    - title: String (e.g. "Operating Systems Module 3: Virtual Memory & Page Tables")            │
│    - total_pages: Integer                                                                       │
│    - content_json: Text (Serialized pages array with title, page_number, formatted text/html)   │
│                                                                                                 │
│ 7. MaterialChunk                                                                                │
│    - id: Integer (PK)                                                                           │
│    - material_id: Integer (FK -> LearningMaterial.id)                                           │
│    - module_id: Integer (FK -> SubjectModule.id)                                                │
│    - topic_name: String (e.g. "Page Table Mechanics")                                           │
│    - page_number: Integer                                                                       │
│    - chunk_text: Text                                                                           │
│    - embedding_json: Text (384-dim semantic vector)                                             │
│                                                                                                 │
│ 8. MicroLesson (Pre-generated & Cached Lessons)                                                 │
│    - id: Integer (PK)                                                                           │
│    - topic_key: String (e.g. "os-paging", "dbms-normalization", "cn-routing")                   │
│    - title: String                                                                              │
│    - subject_code: String                                                                       │
│    - co_code: String                                                                            │
│    - duration_seconds: Integer                                                                  │
│    - scenes_json: Text (JSON array of timed educational scenes)                                 │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 15. Proposed API Architecture

All endpoints enforce Zero-Trust JWT authentication via `get_current_user_claims`:

| Method | Endpoint | Description | RBAC Requirement |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/student/subjects` | Returns enrolled subjects, attendance summary, and overall marks | `student` (own) or `parent` (ward) |
| `GET` | `/api/v1/student/marks` | Returns full marks breakdown across all subjects with performance filters | `student` (own) or `parent` (ward) |
| `GET` | `/api/v1/student/marks/{subject_id}` | Detailed assessment breakdown (CA1..Endterm) and CO1..CO5 scores | `student` (own) or `parent` (ward) |
| `GET` | `/api/v1/student/learning/materials/{module_id}` | Fetches learning material pages and content for a given module | `student` / `faculty` / `admin` |
| `POST` | `/api/v1/student/learning/explain` | Highlight-to-Explain endpoint generating a structured micro-lesson JSON | `student` / `faculty` / `admin` |
| `GET` | `/api/v1/student/learning/lessons/{lesson_id}` | Retrieves pre-generated or cached micro-lesson by key | All authenticated users |

---

## 16. Proposed Frontend Architecture

### View Hierarchy
```
Page (page.tsx)
 ├── Sidebar Navigation -> New Tab: "academic" ("Academic Support")
 └── Academic Support Hub
      ├── Performance Overview Tabs: [ Attendance | Marks Explorer ]
      │    ├── Attendance View (Reuses AttendanceCard grid)
      │    └── Marks Explorer View
      │         ├── Status Filter Bar: [ All Subjects | Strong (≥75%) | Developing (60-74%) | Needs Support (<60%) ]
      │         ├── Subject Performance Cards (Score %, Status Badge, Weakest Module callout)
      │         └── Expanded Subject Detail Drawer / Modal:
      │              ├── Assessment Breakdown (CA1, CA2, CA3, Midterm, Endterm)
      │              ├── Module / CO Performance Bars (CO1..CO5) with "Needs Support" highlights
      │              └── "Open Study Material" Action Button
      │
      ├── Interactive Material Reader Modal / Workspace
      │    ├── Module Breadcrumbs & Page Navigator
      │    ├── Text Reader Surface with Highlight Selection Listener
      │    └── Contextual Floating Action Button: [ ✨ Explain this Selection ]
      │
      └── Micro-Lesson Player Overlay / Drawer
           ├── Animated Video-like Scene Stage (SVG Diagrams, Concept Cards, Worked Examples)
           ├── Scene Timeline Tracker (Scene 1 of 5: "Concept Explanation")
           ├── Play / Pause / Replay / Scrub Controls & Progress Bar
           └── Key Takeaway Summary Card
```

---

## 17. Performance Analytics Architecture

To maintain strict determinism, mathematical aggregation is performed **entirely by database queries and Python logic, never by the LLM**:

### 1. Assessment Category Score
$$\text{AssessmentScore}(\text{category}) = \frac{\sum \text{marks\_obtained for attempted questions in category}}{\sum \text{max\_marks for attempted questions in category}} \times 100$$

### 2. Course Outcome (CO) / Module Score
$$\text{COScore}(k) = \frac{\sum_{q \in \text{CO}_k} \text{marks\_obtained}_q}{\sum_{q \in \text{CO}_k} \text{max\_marks}_q} \times 100$$

### 3. Subject Overall Score
$$\text{SubjectScore} = \sum_{\text{assessment}} \left( \text{AssessmentScore}(\text{assessment}) \times \frac{\text{weightage\_pct}}{100} \right)$$

### 4. Weak Area Classification
* **Strong:** Score $\ge 75\%$
* **Developing:** Score $60.0\text{--}74.9\%$
* **Needs Support:** Score $< 60.0\%$
* **Weakest Module:** $\text{argmin}_{k} (\text{COScore}(k))$

---

## 18. Learning Material Architecture

* **Module-to-Material Scoping:** Each `SubjectModule` maps directly to a `LearningMaterial` record.
* **Document Representation:** Text structured in ordered pages (`content_json`), enabling lightweight, dependency-free in-browser rendering with rich typography, code snippets, and diagrams without heavy PDF.js binary overhead.
* **Granular Chunking:** Pages are split into topic-level `MaterialChunk` records with precomputed semantic embeddings for fast retrieval context augmentation.

---

## 19. Highlight-to-Explain Architecture

```
1. Student selects text in Material Reader:
   Selection: "A page table stores the mapping between virtual pages and physical frames..."
   Metadata: { subject_id: 1, module_id: 3, co_code: "CO3", page_number: 7 }

2. In-Browser Floating Tooltip appears at cursor position: [ ✨ Explain this ]

3. User clicks trigger -> Frontend executes:
   POST /api/v1/student/learning/explain
   Payload: {
     "selected_text": "...",
     "subject_id": 1,
     "module_id": 3,
     "co_code": "CO3",
     "page_number": 7
   }

4. Backend Execution:
   a. Verifies JWT token and student enrollment.
   b. Retrieves surrounding text chunks from MaterialChunk.
   c. Checks if pre-cached MicroLesson matches topic key (e.g. "os-paging").
   d. Returns structured Micro-Lesson JSON payload.
```

---

## 20. Micro-Lesson Architecture

Rather than requiring video rendering pipelines (FFmpeg, MP4, TTS, video hosting), the micro-lesson is delivered as a **Video-Like Interactive React Component** driven by a declarative scene schema:

```json
{
  "title": "Understanding Page Tables & Virtual Memory",
  "topic": "Page Tables",
  "subject": "Operating Systems",
  "co_code": "CO3",
  "total_duration": 45,
  "scenes": [
    {
      "scene_index": 1,
      "type": "concept_intro",
      "duration": 8,
      "title": "What is a Page Table?",
      "highlight_text": "A page table is the operating system's address translation ledger.",
      "bullets": [
        "Divides virtual memory into fixed-size Pages",
        "Maps pages directly to Physical Memory Frames",
        "Managed by the OS Memory Management Unit (MMU)"
      ]
    },
    {
      "scene_index": 2,
      "type": "interactive_diagram",
      "duration": 12,
      "title": "Address Translation Flow",
      "diagram_type": "translation_pipeline",
      "steps": [
        "CPU emits Virtual Address: [ Page Number (P) | Offset (D) ]",
        "Hardware references Page Table at index P",
        "Retrieves Physical Frame Number (F)",
        "Physical Address generated: [ Frame Number (F) | Offset (D) ]"
      ]
    },
    {
      "scene_index": 3,
      "type": "worked_example",
      "duration": 10,
      "title": "Numerical Example",
      "example": "Virtual Address 0x1A40 with 4KB page size -> Page 1 mapped to Frame 5 -> Physical Address 0x5A40."
    },
    {
      "scene_index": 4,
      "type": "common_mistake",
      "duration": 8,
      "title": "Common Exam Trap",
      "warning": "Page Offset NEVER changes during translation—only the Page Number is translated to a Frame Number!"
    },
    {
      "scene_index": 5,
      "type": "key_takeaway",
      "duration": 7,
      "title": "Core Summary",
      "takeaway": "Page tables eliminate external fragmentation by allowing contiguous virtual space to reside in non-contiguous physical RAM."
    }
  ]
}
```

---

## 21. Synthetic Data Architecture

To support comprehensive testing and demonstration, the seeder will generate:
* **10 Students** across Semester 6 Computer Science.
* **6 Subjects:** Operating Systems (`CS-301`), Database Management Systems (`CS-302`), Computer Networks (`CS-303`), Data Structures & Algorithms (`CS-304`), Python Programming (`CS-305`), Web Technologies (`CS-306`).
* **5 Modules per Subject (30 Modules / COs total)** with titles and descriptions.
* **5 Assessments per Subject** (`CA1`, `CA2`, `CA3`, `Midterm`, `Endterm`).
* **Question Ledger** with explicit CO mappings, point allocations, and OR-group configurations.
* **Realistic Question-Level Marks** populated for all 10 students.
* **Academic Learning Materials & Chunks** for key modules.
* **Pre-Generated Micro-Lessons** for core hackathon concepts (Paging, TLB, B-Trees, Normalization, Dijkstra, TCP Flow Control).

---

## 22. Demo Data Strategy (Hero Demo Student)

**Hero Persona: Jane Doe (`student@campus.edu`)**
* **Target Subject Performance:**
  * Python Programming: $88\%$ (Strong)
  * Computer Networks: $84\%$ (Strong)
  * Database Management Systems: $78\%$ (Strong)
  * Data Structures & Algorithms: $72\%$ (Developing)
  * Web Technologies: $69\%$ (Developing)
  * **Operating Systems:** $61\%$ (Developing / Low)
* **Operating Systems Module Breakdown:**
  * CO1 — Process Management: $79\%$ (Strong)
  * CO2 — CPU Scheduling: $68\%$ (Developing)
  * **CO3 — Memory Management & Paging:** **$42\%$** (⚠️ **Needs Support / Weakest**)
  * CO4 — Storage & File Systems: $71\%$ (Developing)
  * CO5 — Protection & Security: $66\%$ (Developing)
* **Hero Demo Journey:**
  1. Student logs in $\rightarrow$ Opens **Academic Support** tab.
  2. Filters by **"Needs Support"** $\rightarrow$ Operating Systems highlights **CO3 (42%)**.
  3. Clicks **"CO3 Memory Management"** $\rightarrow$ Opens Reference Material.
  4. Highlights `"A page table stores the mapping between virtual pages..."`.
  5. Clicks **✨ Explain this** $\rightarrow$ Launches **Interactive Micro-Lesson Player** with address translation diagram and exam takeaways.

---

## 23. Security Considerations

1. **Student Isolation Invariant:** All marks, subject summaries, and learning explanations strictly enforce `student_id = claims.student_id`. No student can query another student's marks.
2. **Parent Visibility:** Parents can only access marks where `student_id = claims.ward_id`.
3. **Faculty Scope:** Faculty can only view aggregate section analytics for their assigned department courses.
4. **Adversarial Scrubber:** The AI explanation service rejects prompts containing privilege escalation tokens (`"ignore rules"`, `"print database schema"`).

---

## 24. Reusable Existing Components

* **Header & Profile Hover Card:** [`frontend/src/components/Header.tsx`](file:///c:/Users/gagan/NexuxEdu/frontend/src/components/Header.tsx)
* **Sidebar Navigation:** [`frontend/src/components/Sidebar.tsx`](file:///c:/Users/gagan/NexuxEdu/frontend/src/components/Sidebar.tsx)
* **Attendance Cards & Rings:** [`frontend/src/components/AttendanceCard.tsx`](file:///c:/Users/gagan/NexuxEdu/frontend/src/components/AttendanceCard.tsx)
* **Design Tokens & Theme CSS:** [`frontend/src/app/globals.css`](file:///c:/Users/gagan/NexuxEdu/frontend/src/app/globals.css)
* **JWT Auth Helpers:** [`backend/app/core/security.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/core/security.py), [`backend/app/api/auth.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/api/auth.py)
* **Vector Cosine Similarity & Embeddings:** [`backend/app/agents/vector_knowledge.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/agents/vector_knowledge.py), [`backend/app/services/seed_data.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/services/seed_data.py)
* **Zero-Trust Ingress & Egress Guards:** [`backend/app/agents/ingress_guard.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/agents/ingress_guard.py), [`backend/app/agents/egress_guard.py`](file:///c:/Users/gagan/NexuxEdu/backend/app/agents/egress_guard.py)

---

## 25. New Components Likely Required (Proposals Only)

1. `MarksExplorer.tsx` — Grid of subject performance cards with status filters (`All`, `Strong`, `Developing`, `Needs Support`).
2. `SubjectDetailModal.tsx` — Deep-dive modal showing assessment marks breakdown and CO1..CO5 progress bars with weak module highlights.
3. `MaterialReader.tsx` — Clean, document-style reader with page navigation and text highlight selection listener.
4. `HighlightTooltip.tsx` — Contextual floating action button (`✨ Explain this`) appearing on text selection.
5. `MicroLessonPlayer.tsx` — Interactive video-like animated player rendering timed concept scenes, SVG diagrams, and exam takeaways.

---

## 26. New Backend Services Likely Required (Proposals Only)

1. `academic_analytics.py` — Deterministic marks aggregation engine (assessment score, CO percentages, weak module ranking).
2. `learning_service.py` — Academic material reader provider and highlight explanation generator.
3. `seed_academic_data.py` — Comprehensive synthetic generator for subjects, modules, assessments, questions, marks, and micro-lessons.
4. `api/academic.py` — FastAPI router mounting `/api/v1/student/*` academic support endpoints.

---

## 27. Potential Technical Risks & Mitigations

| Risk | Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| **Heavy PDF.js bundle bloat & SSR issues** | Slow load times, Next.js build failures | Use lightweight structured document page models (`content_json`) with rich typography and SVG diagrams rather than complex binary canvas PDF decoders. |
| **LLM Hallucinations on Mathematical Marks** | Inaccurate student scores | Strict mathematical separation: all marks, percentages, and weak areas are calculated deterministically via SQLAlchemy/Python. LLM is never invoked for grades. |
| **AI Latency during Live Demo** | Delay during hackathon presentation | Pre-generate and cache micro-lessons for hero demo concepts (Paging, Normalization, Routing). Fallback to instant cache if external API is slow. |
| **OR-Choice Question Scoring Discrepancies** | Skewed denominator marks | Model explicit `or_group_id` and `is_attempted` flags so only the student's chosen option counts toward available marks. |

---

## 28. Implementation Dependency Graph

```
[ Phase 1: Academic Data Schema (database.py & schemas.py) ]
                          │
                          ▼
[ Phase 2: Rich Synthetic Seed Generator (seed_academic_data.py) ]
                          │
                          ▼
[ Phase 3: Deterministic Analytics Service (academic_analytics.py) ]
                          │
                          ▼
[ Phase 4: Student Academic REST APIs (api/academic.py) ]
                          │
                          ▼
[ Phase 5: Frontend Marks Explorer & Subject Deep Dive UI ]
                          │
                          ▼
[ Phase 6: Material Reader & Highlight Selection Listener ]
                          │
                          ▼
[ Phase 7: Highlight-to-Explain Service & Micro-Lesson Generator ]
                          │
                          ▼
[ Phase 8: Interactive Micro-Lesson Player Component ]
                          │
                          ▼
[ Phase 9: End-to-End Verification & Hero Demo Journey ]
```

---

## 29. Recommended Implementation Order (Plan Only)

* **Step 1: Database & Schemas** — Define `Subject`, `SubjectModule`, `Assessment`, `AssessmentQuestion`, `StudentQuestionMark`, `LearningMaterial`, `MaterialChunk`, `MicroLesson`.
* **Step 2: Synthetic Seeder** — Populate 6 subjects, 30 modules, assessments, question marks, notes, and micro-lessons for 10 students (with Jane Doe as hero).
* **Step 3: Analytics Service & REST APIs** — Implement deterministic marks calculations and mount `/api/v1/student/*` endpoints.
* **Step 4: Frontend Marks Explorer** — Add "Academic Support" tab with filters and subject modal in `page.tsx`.
* **Step 5: Material Reader & Selection** — Implement text selection and floating `✨ Explain this` trigger.
* **Step 6: Micro-Lesson Player** — Implement interactive timed scene player with SVG diagrams.
* **Step 7: Verification** — Run full end-to-end acceptance tests.

---

## 30. Open Questions / Confirmations for User

1. **Document Format Preference:** Are structured document pages (rendered directly in React with rich markdown/HTML/code blocks) preferred over embedding binary PDF files via PDF.js for maximum performance, responsiveness, and seamless text selection?
2. **Assessment Weights:** Is the 5-tier assessment distribution (CA1: 15%, CA2: 15%, CA3: 10%, Midterm: 30%, Endterm: 30%) acceptable as the default configurable weighting?

---
