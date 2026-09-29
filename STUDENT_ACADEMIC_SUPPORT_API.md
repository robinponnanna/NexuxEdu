# Student Academic Support REST API Specification & Architecture
## NexuxEdu / OmniCampus ERP Intelligence Layer

---

### 1. Architectural Overview & Zero-Trust Security Model

The **Student Academic Support** intelligence engine delivers deterministic, RBAC-grounded academic analytics directly to enrolled students and authorized parent accounts.

```
                         [ Client Request + Bearer JWT Token ]
                                          │
                                          ▼
                         ┌─────────────────────────────────┐
                         │      Zero-Trust Auth Ingress    │
                         │ - Decode Cryptographic JWT      │
                         │ - Verify role == "student"/"parent"
                         │ - Extract verified student_id   │
                         └────────────────┬────────────────┘
                                          │
                                          ▼
                         ┌─────────────────────────────────┐
                         │   Academic Analytics Engine     │
                         │ (Deterministic Aggregation SQL) │
                         ├─────────────────────────────────┤
                         │ - Mandatory & Optional Questions│
                         │ - OR-Group Deduplication        │
                         │ - CO / Module Percentage Splits │
                         │ - Weakest / Strongest Modules   │
                         │ - Configurable Status Classifier│
                         └────────────────┬────────────────┘
                                          │
                                          ▼
                         ┌─────────────────────────────────┐
                         │  Typed Pydantic Response Stream │
                         └─────────────────────────────────┘
```

#### Security Invariants Enforced:
1. **No Parameter Spoofing**: Endpoints never accept `?student_id=...` or client-supplied student identifiers. Every query is bound strictly to `claims.student_id` (for students) or `claims.ward_id` (for parents) extracted from the validated JWT payload.
2. **Role-Based Access Control**: Requests from non-student/non-parent sessions (or invalid tokens) are immediately rejected with `401 Unauthorized` or `403 Forbidden`.
3. **Course Enrollment Verification**: Endpoints verifying subject or assessment details strictly validate that the student is actively enrolled in the requested course before returning marks.

---

### 2. Deterministic Calculation & Grading Classification Rules

> [!IMPORTANT]
> All marks, totals, percentages, and module rankings are computed mathematically by the deterministic analytics service. The Large Language Model is **never** used to calculate marks or determine the weakest module.

#### 2.1 Demo Performance Status Thresholds
Status thresholds are centralized in [`app.services.academic_analytics`](file:///c:/Users/gagan/NexuxEdu/backend/app/services/academic_analytics.py):

| Range | Classification | Meaning |
| :--- | :--- | :--- |
| $\text{Percentage} \ge 75.0\%$ | **`Strong`** | Demonstrates solid mastery of Course Outcomes. |
| $60.0\% \le \text{Percentage} < 75.0\%$ | **`Developing`** | Average grasp; revision recommended before exams. |
| $\text{Percentage} < 60.0\%$ | **`Needs Support`** | Identified as an academic weak area requiring micro-lessons and note revision. |
| $\text{No Attempted Questions}$ | **`No Data`** | Handled defensively without division by zero. |

#### 2.2 OR-Question Group Handling
In university exam patterns where students choose between alternative questions (e.g. *Answer Q3.a OR Q3.b*):
- Questions in an OR group share a unique `or_group_id` (e.g. `"CA1-Q3-OR"`).
- **Available Marks (Denominator)**: Computed as $\max(q_1.\text{max\_marks}, q_2.\text{max\_marks}, \dots)$ rather than the sum of both choices.
- **Obtained Marks (Numerator)**: Computed as the marks earned on the attempted option.
- **Cross-CO Choices**: If Q6.a maps to CO1 and Q6.b maps to CO2, the unattempted choice is never added to the denominator of its CO.

#### 2.3 Unattempted Optional Questions
If a standalone question has `is_optional = True` and `is_attempted = False`, its maximum marks are not included in the denominator, preventing artificial deflation of student percentages.

---

### 3. REST API Endpoint Reference

Base Prefix: `/api/v1/student`

```
┌───────────────────────────────────────────────────┬────────┬───────────────────────────────────────────┐
│ Endpoint                                          │ Method │ Description                               │
├───────────────────────────────────────────────────┼────────┼───────────────────────────────────────────┤
│ /api/v1/student/subjects                          │ GET    │ Returns enrolled subjects with scores.    │
│ /api/v1/student/marks                             │ GET    │ Returns full academic overview.           │
│ /api/v1/student/marks/{subject_id}                │ GET    │ Returns subject performance breakdown.    │
│ /api/v1/student/marks/{subject_id}/modules        │ GET    │ Returns CO/module performance analysis.   │
│ /api/v1/student/learning/materials/{module_id}    │ GET    │ Returns learning materials & micro-lessons│
│ /api/v1/student/learning/explain                  │ POST   │ Grounded RAG Concept Explanation & Lesson │
└───────────────────────────────────────────────────┴────────┴───────────────────────────────────────────┘
```

---

### 4. Endpoint Specifications & Sample Payloads

#### 4.1 `GET /api/v1/student/subjects`
Returns all enrolled subjects for the authenticated student.

* **Query Parameters:**
  - `semester` *(integer, optional)*: Filter by semester (e.g., `6`).
  - `performance_status` *(string, optional)*: Filter by status (`"Strong"`, `"Developing"`, `"Needs Support"`, or `"all"`).

* **Sample Response (`200 OK`):**
```json
[
  {
    "id": 1,
    "code": "CS301",
    "name": "Operating Systems",
    "department": "Computer Science",
    "semester": 6,
    "credits": 4,
    "total_marks_obtained": 145.0,
    "total_marks_available": 210.0,
    "percentage": 69.0,
    "status": "Developing",
    "strongest_module": {
      "id": 1,
      "module_number": 1,
      "co_code": "CO1",
      "title": "Process Management & Concurrency",
      "marks_obtained": 42.4,
      "marks_available": 50.0,
      "percentage": 84.8,
      "status": "Strong"
    },
    "weakest_module": {
      "id": 3,
      "module_number": 3,
      "co_code": "CO3",
      "title": "Memory Management & Virtual Memory",
      "marks_obtained": 17.1,
      "marks_available": 45.0,
      "percentage": 38.0,
      "status": "Needs Support"
    }
  }
]
```

---

#### 4.2 `GET /api/v1/student/marks`
Returns the comprehensive academic marks overview for the authenticated student.

* **Sample Response (`200 OK`):**
```json
{
  "student_id": 1,
  "student_name": "Jane Doe",
  "roll_number": "CS-2023-042",
  "semester": 6,
  "overall_percentage": 77.0,
  "total_credits": 22,
  "subjects": [
    {
      "id": 1,
      "code": "CS301",
      "name": "Operating Systems",
      "department": "Computer Science",
      "semester": 6,
      "credits": 4,
      "total_marks_obtained": 145.0,
      "total_marks_available": 210.0,
      "percentage": 69.0,
      "status": "Developing",
      "strongest_module": { ... },
      "weakest_module": { ... }
    },
    {
      "id": 2,
      "code": "CS302",
      "name": "Database Management Systems",
      "department": "Computer Science",
      "semester": 6,
      "credits": 4,
      "total_marks_obtained": 174.3,
      "total_marks_available": 210.0,
      "percentage": 83.0,
      "status": "Strong",
      "strongest_module": { ... },
      "weakest_module": { ... }
    }
  ]
}
```

---

#### 4.3 `GET /api/v1/student/marks/{subject_id}`
Returns detailed assessment scores and question-level breakdown for a course.

* **Sample Response (`200 OK`):**
```json
{
  "subject": {
    "id": 1,
    "code": "CS301",
    "name": "Operating Systems",
    "department": "Computer Science",
    "semester": 6,
    "credits": 4,
    "modules": [
      {
        "id": 1,
        "module_number": 1,
        "co_code": "CO1",
        "title": "Process Management & Concurrency",
        "description": "Process life cycle, PCB, context switching, inter-process communication (IPC), POSIX threads."
      }
    ]
  },
  "total_marks_obtained": 145.0,
  "total_marks_available": 210.0,
  "percentage": 69.0,
  "status": "Developing",
  "assessments": [
    {
      "id": 1,
      "category": "CA1",
      "name": "CS301 Continuous Assessment 1",
      "max_marks": 20.0,
      "weightage_pct": 10.0,
      "assessment_date": "2026-01-28",
      "marks_obtained": 16.4,
      "marks_available": 20.0,
      "percentage": 82.0,
      "questions": [
        {
          "id": 1,
          "question_id": 1,
          "question_label": "Q1",
          "co_code": "CO1",
          "max_marks": 5.0,
          "marks_obtained": 4.2,
          "is_attempted": true,
          "or_group_id": null,
          "feedback": null
        },
        {
          "id": 3,
          "question_id": 3,
          "question_label": "Q3.a",
          "co_code": "CO2",
          "max_marks": 5.0,
          "marks_obtained": 4.0,
          "is_attempted": true,
          "or_group_id": "CA1-Q3-OR",
          "feedback": null
        },
        {
          "id": 4,
          "question_id": 4,
          "question_label": "Q3.b",
          "co_code": "CO2",
          "max_marks": 5.0,
          "marks_obtained": 0.0,
          "is_attempted": false,
          "or_group_id": "CA1-Q3-OR",
          "feedback": "Optional question not chosen."
        }
      ]
    }
  ],
  "modules": [
    {
      "id": 1,
      "module_number": 1,
      "co_code": "CO1",
      "title": "Process Management & Concurrency",
      "marks_obtained": 42.4,
      "marks_available": 50.0,
      "percentage": 84.8,
      "status": "Strong"
    },
    {
      "id": 3,
      "module_number": 3,
      "co_code": "CO3",
      "title": "Memory Management & Virtual Memory",
      "marks_obtained": 17.1,
      "marks_available": 45.0,
      "percentage": 38.0,
      "status": "Needs Support"
    }
  ],
  "strongest_module": { "co_code": "CO1", "percentage": 84.8 },
  "weakest_module": { "co_code": "CO3", "percentage": 38.0 }
}
```

---

#### 4.4 `GET /api/v1/student/marks/{subject_id}/modules`
Returns the Course Outcome / Module breakdown specifically for a course with highlighted extremes.

* **Sample Response (`200 OK`):**
```json
{
  "subject_id": 1,
  "subject_code": "CS301",
  "subject_name": "Operating Systems",
  "modules": [
    {
      "id": 1,
      "module_number": 1,
      "co_code": "CO1",
      "title": "Process Management & Concurrency",
      "description": "Process life cycle, PCB, context switching, inter-process communication (IPC), POSIX threads.",
      "marks_obtained": 42.4,
      "marks_available": 50.0,
      "percentage": 84.8,
      "status": "Strong"
    },
    {
      "id": 2,
      "module_number": 2,
      "co_code": "CO2",
      "title": "CPU Scheduling & Synchronization",
      "description": "Scheduling algorithms (FCFS, SJF, Round Robin, Multilevel Queue), race conditions, semaphores, mutexes, Banker's deadlock algorithm.",
      "marks_obtained": 43.7,
      "marks_available": 55.0,
      "percentage": 79.5,
      "status": "Strong"
    },
    {
      "id": 3,
      "module_number": 3,
      "co_code": "CO3",
      "title": "Memory Management & Virtual Memory",
      "description": "Contiguous allocation, paging, segmentation, TLB address translation, page faults, FIFO/LRU/Optimal page replacement algorithms.",
      "marks_obtained": 17.1,
      "marks_available": 45.0,
      "percentage": 38.0,
      "status": "Needs Support"
    },
    {
      "id": 4,
      "module_number": 4,
      "co_code": "CO4",
      "title": "Storage Management & File Systems",
      "description": "Disk scheduling (SSTF, SCAN, LOOK), inode structures, directory layouts, allocation methods (contiguous, linked, indexed).",
      "marks_obtained": 21.4,
      "marks_available": 30.0,
      "percentage": 71.3,
      "status": "Developing"
    },
    {
      "id": 5,
      "module_number": 5,
      "co_code": "CO5",
      "title": "I/O Systems & OS Security",
      "description": "I/O hardware, DMA, interrupt handling, access matrix, capability lists, protection domains and sandboxing.",
      "marks_obtained": 20.4,
      "marks_available": 30.0,
      "percentage": 68.0,
      "status": "Developing"
    }
  ],
  "strongest_module": {
    "id": 1,
    "module_number": 1,
    "co_code": "CO1",
    "title": "Process Management & Concurrency",
    "marks_obtained": 42.4,
    "marks_available": 50.0,
    "percentage": 84.8,
    "status": "Strong"
  },
  "weakest_module": {
    "id": 3,
    "module_number": 3,
    "co_code": "CO3",
    "title": "Memory Management & Virtual Memory",
    "marks_obtained": 17.1,
    "marks_available": 45.0,
    "percentage": 38.0,
    "status": "Needs Support"
  }
}
```

---

#### 4.5 `GET /api/v1/student/learning/materials/{module_id}`
Returns all learning materials, multi-page notes, and pre-cached interactive micro-lessons attached to a module.

* **Sample Response (`200 OK`):**
```json
{
  "module_id": 3,
  "module_number": 3,
  "co_code": "CO3",
  "module_title": "Memory Management & Virtual Memory",
  "subject_id": 1,
  "subject_code": "CS301",
  "subject_name": "Operating Systems",
  "materials": [
    {
      "id": 3,
      "subject_id": 1,
      "subject_code": "CS301",
      "subject_name": "Operating Systems",
      "module_id": 3,
      "co_code": "CO3",
      "title": "OS Module 3: Virtual Memory Architecture, Paging & TLB Translation",
      "source_reference": "Prof. Alan Turing / CS301 Comprehensive Notes",
      "total_pages": 5,
      "pages": [
        {
          "id": 5,
          "page_number": 1,
          "page_title": "Memory Virtualization & Physical Address Spaces",
          "content_text": "Memory virtualization provides each process with the illusion...",
          "structured_json": "{\"topics\": [\"Virtual Memory Foundations\"]}"
        },
        {
          "id": 6,
          "page_number": 2,
          "page_title": "Paging Mechanics & Page Table Organization",
          "content_text": "In a paging system, the virtual address space...",
          "structured_json": "{\"topics\": [\"Paging and Page Tables\"]}"
        }
      ]
    }
  ],
  "total_chunks": 5,
  "micro_lessons": [
    {
      "id": 1,
      "subject_id": 1,
      "subject_code": "CS301",
      "subject_name": "Operating Systems",
      "module_id": 3,
      "co_code": "CO3",
      "topic_key": "os_memory_paging_tlb",
      "title": "Demystifying Paging, Page Tables & The TLB Hit/Miss Cycle",
      "duration_seconds": 180,
      "scenes": [
        {
          "scene_id": 1,
          "title": "The Memory Virtualization Illusion",
          "duration_seconds": 35,
          "narration": "Modern operating systems give every process its own private...",
          "visual_type": "diagram",
          "visual_data": {
            "diagram_title": "Virtual to Physical Address Translation",
            "ascii_diagram": "+-------------------------------------------+\\n|   Process Virtual Address (32-bit)..."
          },
          "key_takeaway": "Virtual addresses split into Page Number and Offset; the MMU maps Page Number to Frame Number."
        }
      ]
    }
  ]
}
```

#### 4.6 `POST /api/v1/student/learning/explain`
Grounded Concept Explanation and Micro-Lesson Synthesis Engine. Performs zero-trust student identity verification, metadata-constrained vector and keyword RAG retrieval, cache inspection, and deterministic multi-scene generation.

* **Headers:** `Authorization: Bearer <jwt_token>` (Student or Parent role required)
* **Request Body:**
```json
{
  "selected_text": "Page Tables translate virtual page numbers to physical frame numbers. The Translation Lookaside Buffer accelerates lookup.",
  "material_id": 3,
  "module_id": 3,
  "subject_id": 1,
  "page_number": 1,
  "co_code": "CO3",
  "topic": "Page Tables and TLB"
}
```

* **Request Field Specifications:**
  - `selected_text` *(string, required)*: Highlighted passage from learning material notes or analytical question. Max 2000 chars.
  - `material_id` *(integer, optional)*: Specific learning material ID from which the highlight was made.
  - `module_id` *(integer, optional)*: Associated Course Outcome module ID.
  - `subject_id` *(integer, optional)*: Associated Subject ID.
  - `page_number` *(integer, optional)*: Exact page index within the learning material.
  - `co_code` *(string, optional)*: e.g. `"CO3"`.
  - `topic` *(string, optional)*: Concept header or user-entered query focus.

* **Sample Response (`200 OK`):**
```json
{
  "status": "success",
  "lesson": {
    "id": 1,
    "title": "Demystifying Paging, Page Tables & The TLB Hit/Miss Cycle",
    "topic": "Page Tables and TLB",
    "topic_key": "os_memory_paging_tlb",
    "difficulty": "Intermediate",
    "duration_seconds": 180,
    "objective": "Understand Demystifying Paging, Page Tables & The TLB Hit/Miss Cycle for Operating Systems.",
    "scenes": [
      {
        "scene_id": 1,
        "title": "The Memory Virtualization Illusion",
        "duration_seconds": 35,
        "narration": "Modern operating systems give every process its own private, isolated virtual address space. But physical RAM is shared. How does the CPU translate virtual addresses into actual memory cells instantly?",
        "visual_type": "diagram",
        "visual_data": {
          "diagram_title": "Virtual to Physical Address Translation",
          "ascii_diagram": "+-------------------------------------------+\\n|   Process Virtual Address (32-bit)        |\\n|   [ Page Number: p ] [ Offset: d (12b) ]  |\\n+---------------------+---------------------+\\n                      | (Lookup in Page Table)\\n                      v\\n+-------------------------------------------+\\n|   Page Table Entry: Frame Number 'f'      |\\n+---------------------+---------------------+\\n                      | (Concatenate)\\n                      v\\n+-------------------------------------------+\\n|   Physical Address: [ Frame: f ] [ Off: d]|\\n+-------------------------------------------+",
          "highlights": [
            "Page Number indexes the Page Table",
            "Offset (12 bits = 4KB page) remains identical in physical memory"
          ]
        },
        "key_takeaway": "Virtual addresses split into Page Number and Offset; the MMU maps Page Number to Frame Number."
      }
    ],
    "sources": [
      {
        "material_id": 3,
        "title": "OS Module 3: Virtual Memory Architecture, Paging & TLB Translation",
        "page_number": 1,
        "topic": "Virtual Memory Foundations",
        "co_code": "CO3",
        "subject_code": "CS301"
      }
    ]
  },
  "source_context": {
    "subject_code": "CS301",
    "subject_name": "Operating Systems",
    "module_title": "Memory Management & Virtual Memory",
    "co_code": "CO3",
    "material_title": "OS Module 3: Virtual Memory Architecture, Paging & TLB Translation",
    "page_number": 1,
    "retrieved_chunks_count": 3
  },
  "generation": {
    "mode": "cache",
    "model": "cached-microlesson-store",
    "cached": true,
    "latency_ms": 1.25
  }
}
```

---

### 5. Automated Test Suite (Phase 3: Academic Analytics)

Test file: [`backend/tests/test_academic_analytics.py`](file:///c:/Users/gagan/NexuxEdu/backend/tests/test_academic_analytics.py)

| Test ID | Method | Verified Behavior | Status |
| :--- | :--- | :--- | :--- |
| `test_01` | `test_01_subject_marks_aggregation` | Aggregates subject total marks and percentage (Jane OS = 145/210, 69.0%). | **PASSED** |
| `test_02` | `test_02_assessment_marks_aggregation` | Aggregates CA1..CA3, Midterm, Endterm scores accurately. | **PASSED** |
| `test_03` | `test_03_co_aggregation` | Computes CO1..CO5 breakdowns (CO1=84.8% Strong, CO3=38.0% Weak). | **PASSED** |
| `test_04` | `test_04_weakest_module_detection` | Detects CO3 as weakest module with deterministic tie-breaking. | **PASSED** |
| `test_05` | `test_05_strongest_module_detection` | Detects CO1 as strongest module with deterministic tie-breaking. | **PASSED** |
| `test_06` | `test_06_performance_classification` | Classifies Strong ($\ge75\%$), Developing ($60-74\%$), Needs Support ($<60\%$). | **PASSED** |
| `test_07` | `test_07_or_question_denominator` | Ensures OR-groups count max available marks once in denominator. | **PASSED** |
| `test_08` | `test_08_unattempted_optional_question_behavior` | Excludes unattempted optional questions from denominator. | **PASSED** |
| `test_09` | `test_09_student_enrollment_filtering` | Enforces semester and performance status filters. | **PASSED** |
| `test_10` | `test_10_student_isolation_and_rest_apis` | Validates 401 unauth, 403 forbidden, and claim-based session isolation. | **PASSED** |
| `test_11` | `test_11_material_module_association` | Verifies notes, pages, chunks, embeddings, and micro-lessons per module. | **PASSED** |
| `test_12` | `test_12_seed_idempotency` | Validates re-running seeder does not duplicate records. | **PASSED** |

---

### 6. Automated Test Suite (Phase 4: Grounded Academic RAG)

Test file: [`backend/tests/test_academic_rag.py`](file:///c:/Users/gagan/NexuxEdu/backend/tests/test_academic_rag.py)

| Test ID | Method | Verified Behavior | Status |
| :--- | :--- | :--- | :--- |
| `test_01` | `test_01_authenticated_student_can_explain_material` | Authenticated student generates grounded micro-lesson with citations. | **PASSED** |
| `test_02` | `test_02_unauthenticated_request_rejected` | Rejects unauthenticated requests with `401 Unauthorized`. | **PASSED** |
| `test_03` | `test_03_unauthorized_role_rejected` | Rejects non-student/non-parent sessions (e.g. faculty) with `403 Forbidden`. | **PASSED** |
| `test_04` | `test_04_unenrolled_subject_access_denied` | Prevents student from accessing materials or explanations in unenrolled subjects (`403 Forbidden`). | **PASSED** |
| `test_05` | `test_05_invalid_material_module_relationship_rejected` | Rejects mismatched material and module IDs with `400 Bad Request`. | **PASSED** |
| `test_06` | `test_06_invalid_page_rejected` | Rejects non-existent page numbers for a material with `404 Not Found`. | **PASSED** |
| `test_07` | `test_07_empty_selection_rejected` | Rejects empty or whitespace-only selected text with `422 Unprocessable Content`. | **PASSED** |
| `test_08` | `test_08_oversized_selection_handled_gracefully` | Handles and truncates oversized text highlights (>2000 chars) gracefully. | **PASSED** |
| `test_09` | `test_09_academic_metadata_filtering` | Guarantees vector retrieval only considers chunks within target subject & module. | **PASSED** |
| `test_10` | `test_10_correct_os_co3_material_retrieved` | Retrieves correct OS CO3 virtual memory material for paging highlights. | **PASSED** |
| `test_11` | `test_11_dbms_not_mixed_with_os` | Structurally prevents cross-subject contamination (e.g., DBMS terms into OS). | **PASSED** |
| `test_12` | `test_12_cached_microlesson_returned` | Serves pre-cached micro-lesson with `generation.mode = "cache"` and `cached = True`. | **PASSED** |
| `test_13` | `test_13_cached_lesson_metadata_matches_subject_module` | Validates cached lesson subject and module foreign key alignment. | **PASSED** |
| `test_14` | `test_14_pydantic_schema_validation` | Validates full JSON payload compliance against `AcademicExplainResponse`. | **PASSED** |
| `test_15` | `test_15_malformed_request_structure_rejected` | Rejects requests missing mandatory fields with `422 Unprocessable Content`. | **PASSED** |
| `test_16` | `test_16_jailbreak_intercepted_by_ingress_guard` | Ingress guard intercepts prompt injection attacks with `400 Bad Request`. | **PASSED** |
| `test_17` | `test_17_egress_controls_declarative_json_only` | Validates that outputs contain only safe declarative JSON without script injections. | **PASSED** |
| `test_18` | `test_18_deterministic_fallback_mode` | Synthesizes high-fidelity fallback micro-lesson when offline (`generation.mode = "fallback"`). | **PASSED** |
