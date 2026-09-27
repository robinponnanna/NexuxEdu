# System Design Document
## Multi-Tenant RBAC-RAG Campus ERP & Fleet Tracking Pipeline

---

### 1. High-Level System Architecture

The system uses a decoupled client-server architecture consisting of four core tiers:
1. **Client Presentation Tier:** Next.js single-page application rendering role-specific portals (Student, Faculty, Parent, Admin) with Leaflet.js map layers and an integrated chat interface.
2. **Application & Routing Tier:** FastAPI gateway enforcing JWT authentication, role verification, and intent routing.
3. **Intelligence & Telemetry Tier:**
   * *Telemetry Broker:* Redis Pub/Sub handling ephemeral GPS coordinate streams.
   * *Hybrid RAG Pipeline:* Metadata-filtered pgvector engine + deterministic SQL tools.
4. **Data Persistence Tier:** PostgreSQL containing relational business logic, transit routes, and vector embeddings.

```
                     +---------------------------------------+
                     |       Client Layer (Next.js)          |
                     |  [Student]  [Faculty] [Parent] [Admin]|
                     +---------------------------------------+
                                        │
                               HTTP / WebSocket
                                        ▼
                     +---------------------------------------+
                     |       API Gateway (FastAPI)           |
                     | - JWT Authenticator & RBAC Claims     |
                     | - Intent Router (Chat vs CRUD vs Map) |
                     +---------------------------------------+
                                    │         │
                 ┌──────────────────┘         └──────────────────┐
                 ▼                                               ▼
+---------------------------------+             +----------------------------------+
|      RAG Intelligence Engine    |             |    Real-Time Transit Broker      |
|  - Semantic Query Classifier    |             |  - GPS Ingestion Worker          |
|  - Metadata Pre-Filter (pgvector|             |  - Redis Pub/Sub (Coordinates)   |
|  - Scoped SQL Parametric Tool   |             |  - WebSocket Dispatcher          |
|  - LLM Context Synthesis        |             +----------------------------------+
+---------------------------------+                              │
                 │                                               │
                 ▼                                               ▼
+----------------------------------------------------------------------------------+
|                    PostgreSQL 16 + pgvector Unified Storage                      |
|  [Users]  [Faculty]  [Students]  [Attendance]  [Buses]  [Document_Embeddings]    |
+----------------------------------------------------------------------------------+
```

---

### 2. Database Schema Design (PostgreSQL + pgvector)

```sql
-- Extension Setup
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 1. Authentication & Base User Table
CREATE TYPE user_role AS ENUM ('student', 'faculty', 'parent', 'admin');

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    public_id UUID DEFAULT uuid_generate_v4() UNIQUE,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role user_role NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Transit Entity: Buses
CREATE TABLE buses (
    id SERIAL PRIMARY KEY,
    bus_number VARCHAR(30) UNIQUE NOT NULL,
    route_name VARCHAR(100) NOT NULL,
    driver_name VARCHAR(100) NOT NULL,
    driver_phone VARCHAR(20) NOT NULL,
    current_lat DOUBLE PRECISION DEFAULT 28.613939,
    current_lng DOUBLE PRECISION DEFAULT 77.209021,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Parents Profile
CREATE TABLE parents (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    phone VARCHAR(20) NOT NULL,
    emergency_contact VARCHAR(20)
);

-- 4. Faculty Profile
CREATE TABLE faculty (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    emp_code VARCHAR(30) UNIQUE NOT NULL,
    department VARCHAR(60) NOT NULL,
    designation VARCHAR(60) NOT NULL,
    annual_salary NUMERIC(12, 2) NOT NULL -- Critical RBAC sensitive field
);

-- 5. Student Profile
CREATE TABLE students (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    parent_id INT REFERENCES parents(id) ON DELETE SET NULL,
    bus_id INT REFERENCES buses(id) ON DELETE SET NULL,
    roll_number VARCHAR(30) UNIQUE NOT NULL,
    department VARCHAR(60) NOT NULL,
    semester INT NOT NULL
);

-- 6. Academic Attendance Records
CREATE TABLE attendance (
    id SERIAL PRIMARY KEY,
    student_id INT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    subject VARCHAR(60) NOT NULL,
    total_classes INT DEFAULT 40,
    attended_classes INT NOT NULL,
    attendance_pct NUMERIC(5, 2) GENERATED ALWAYS AS (
        ROUND((attended_classes::numeric / NULLIF(total_classes, 0)::numeric) * 100, 2)
    ) STORED
);

-- 7. Document Embeddings with Access Control Metadata
CREATE TABLE document_embeddings (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    allowed_roles user_role[] NOT NULL,
    department VARCHAR(60),
    embedding vector(1536) -- Standard OpenAI dimension (or 768 for local models)
);

CREATE INDEX idx_doc_embedding ON document_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_doc_allowed_roles ON document_embeddings USING GIN (allowed_roles);
```

---

### 3. Real-Time Transit Subsystem Architecture

#### Data Flow:
1. **Publisher (GPS Ingestion):**
   * Vehicle driver client (or simulated background worker) sends periodic POST/WebSocket payloads:
     $$\text{Payload} = \{\text{bus\_id}: 4, \text{lat}: 28.535512, \text{lng}: 77.391024, \text{speed}: 34.2, \text{timestamp}: 1774780800\}$$
2. **Broker (Redis In-Memory Channel):**
   * Telemetry Service updates the coordinates in Redis cache (`HSET bus:4 current_lat 28.535512 ...`).
   * Publishes message to channel `channel:bus:4`.
3. **Subscriber Dispatcher (FastAPI WebSocket Worker):**
   * When Parent connects to `/ws/transit/{bus_id}`, backend validates that `token.bus_id == {bus_id}` or `token.role == 'admin'`.
   * Backend subscribes to Redis channel `channel:bus:{bus_id}` and forwards coordinate payloads down the active WebSocket connection.
4. **Client Render:**
   * Frontend Leaflet instance updates the vehicle marker with smooth interpolation (`L.Marker.slideTo`).

---

### 4. Hybrid RBAC-RAG Pipeline Architecture

```
User Query: "What is my attendance and the exam schedule?"
                          │
                          ▼
            +---------------------------+
            |  Query Intent Classifier  |
            +---------------------------+
             │                         │
  [Unstructured Semantic]     [Structured Tabular]
             │                         │
             ▼                         ▼
+-------------------------+  +--------------------------------+
| Vector Similarity Query |  | Parametric SQL Query Builder   |
| Filters:                |  | Enforced WHERE:                |
| WHERE role = ANY(roles) |  | student_id = token.student_id  |
+-------------------------+  +--------------------------------+
             │                         │
             └───────────┬─────────────┘
                         ▼
          +-------------------------------+
          |   Aggregated Context Window   |
          +-------------------------------+
                         │
                         ▼
          +-------------------------------+
          |   LLM Inference (Refusal if   |
          |       context is empty)       |
          +-------------------------------+
```

* **Zero-Trust Rule:** The LLM NEVER receives a generic database connection. It receives tools with hardcoded execution parameters extracted from verified session claims.

---

### 5. API Interface Definitions

#### A. Authentication
* `POST /api/v1/auth/login`
  * Request: `{"email": "student@campus.edu", "password": "password123"}`
  * Response: `{"access_token": "eyJhbG...", "token_type": "bearer", "user": {"id": 1, "role": "student", "name": "Jane Doe"}}`

#### B. Conversational Chatbot (RBAC Scoped)
* `POST /api/v1/chat/query`
  * Headers: `Authorization: Bearer <JWT>`
  * Request: `{"message": "What is my percentage in Operating Systems?"}`
  * Response:
    ```json
    {
      "reply": "Your attendance in Operating Systems is 87.5% (35 out of 40 classes attended). You are safely above the 75% eligibility threshold.",
      "sources": [{"type": "sql_query", "entity": "attendance"}]
    }
    ```

#### C. Transit Telemetry
* `WS /api/v1/transit/stream/{bus_id}`
  * Connection Headers: Query param `?token=<JWT>`
  * Outgoing Message (Server $\rightarrow$ Client):
    ```json
    {
      "bus_id": 1,
      "bus_number": "BUS-001",
      "lat": 28.535512,
      "lng": 77.391024,
      "speed_kmh": 32.5,
      "timestamp": "2026-09-26T15:30:00Z"
    }
    ```