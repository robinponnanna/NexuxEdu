# NexusEdu ERP RAG Chatbot with Role-Based Access Control (RBAC)

A secure, zero-trust Retrieval-Augmented Generation (RAG) chatbot engine for educational ERP systems. It integrates directly with existing relational ERP databases (SQLite, PostgreSQL, or MySQL), performs role-based pre-retrieval filtering in ChromaDB, and runs fully locally on CPU using Ollama (`llama3.2:3b` and `nomic-embed-text`).

---

## 1. System Architecture & RBAC Invariants

In educational ERP systems, users have strictly separated data boundaries:
1. **Student**: Can only view their own academic records, enrolled subjects, and attendance. Lateral querying of other students, faculty salaries, or institutional finances is strictly blocked.
2. **Parent**: Can only view their enrolled children's/ward's academic records. Cross-family queries, faculty salaries, and institutional finances are strictly blocked.
3. **Faculty**: Can view academic records and the faculty directory, but are strictly blocked from faculty salaries and institutional accounts (`sensitivity != 'confidential'`).
4. **Admin**: Unrestricted visibility across all records, salaries, and institutional financials.

### Pre-Retrieval Filtering Guarantee
All access boundaries are enforced **pre-retrieval** at the vector database level using ChromaDB metadata filters (`where={"student_id": user.student_id}`, `where={"sensitivity": {"$ne": "confidential"}}`, etc.). If an unauthorized query returns zero matching records, the engine immediately halts with an authorized refusal (`"I don't have access to that information."`) **without invoking the synthesis LLM**, mathematically preventing hallucinations or prompt-injection jailbreaks.

---

## 2. Directory Structure

```
erp_rag_chatbot/
├── .env                  # Ollama, ChromaDB, and ERP DB configuration
├── main.py               # Interactive CLI, ERP auth integration, and test suite
├── rag_pipeline.py       # ERPRAGChatbot, Ollama models, and ChromaDB retrieval
├── chunking.py           # Read-only extraction & transformation of ERP records
├── database/
│   └── chroma_db/        # Local persistent Chroma vector store
└── utils/
    ├── __init__.py
    ├── rbac_filters.py   # User identity class & ChromaDB filter builder
    └── db_connection.py  # Unified DB connection factory (SQLite/PostgreSQL/MySQL)
```

---

## 3. Configuration (`.env`)

Edit `erp_rag_chatbot/.env` to configure your models and database connection:

```ini
# Ollama Local Runtime
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_MODEL=nomic-embed-text
CHAT_MODEL=llama3.2:3b

# ChromaDB Persistence Directory
CHROMA_PERSIST_DIR=./database/chroma_db

# Existing ERP Database Connection
ERP_DB_TYPE=sqlite                     # Options: sqlite, postgresql, mysql
ERP_DB_PATH=../backend/campus.db       # Path to existing SQLite DB

# If using PostgreSQL or MySQL:
ERP_DB_HOST=localhost
ERP_DB_PORT=5432
ERP_DB_NAME=erp_system
ERP_DB_USER=erp_user
ERP_DB_PASSWORD=your_password
```

---

## 4. Usage Instructions

### Step 1: Initialize / Rebuild the Vector Index from the ERP Database
Run this command once or whenever records in your ERP database are updated:
```bash
./.venv/bin/python erp_rag_chatbot/main.py --init-db
```
This performs a **read-only** extraction from your ERP tables (`students`, `faculty`, `attendance`, `parents`, etc.) and indexes them into `./database/chroma_db/`.

### Step 2: Run the Automated RBAC Security Verification Suite
Verify that all 4 roles strictly enforce zero-trust isolation:
```bash
./.venv/bin/python erp_rag_chatbot/main.py --test-rbac
```
This runs 8 automated queries testing:
- Student accessing own attendance (**Permitted**)
- Student querying another student's attendance (**Blocked**)
- Student attempting to see faculty salaries (**Blocked**)
- Faculty querying faculty directory (**Permitted**)
- Faculty attempting to see salaries (**Blocked**)
- Parent querying linked ward's record (**Permitted**)
- Admin querying confidential faculty salaries (**Permitted**)
- Admin querying university endowment balance (**Permitted**)

### Step 3: Start Interactive Chat Session
Run the interactive chatbot:
```bash
./.venv/bin/python erp_rag_chatbot/main.py
```
You can select a demo persona or log in using existing ERP user credentials:
- **Admin**: `admin@campus.edu` / `password123`
- **Faculty**: `faculty@campus.edu` / `password123`
- **Parent**: `parent@campus.edu` / `password123`
- **Student**: `student@campus.edu` / `password123`
- **Student (Alex)**: `alex@campus.edu` / `password123`

You can also authenticate directly from the command line:
```bash
./.venv/bin/python erp_rag_chatbot/main.py --user-email student@campus.edu
```

During a chat session, you can use these commands:
- `switch`: Switch between user roles without restarting.
- `info`: Display current authenticated claims and active ChromaDB filter.
- `rebuild`: Re-index vectors from the active ERP database.
- `exit` / `quit` / `bye`: End session.

---

## 5. Integration Points

- **Database Connection** (`utils/db_connection.py`):
  Set `ERP_DB_TYPE` to `postgresql` or `mysql` in `.env` to connect to production database engines.
- **Authentication** (`main.py` -> `authenticate_erp_user`):
  Queries the existing ERP `users` table and verifies password hash with `bcrypt`. In production, you can replace or wrap this function with your institutional SSO, JWT bearer validator, or session store.
- **Index Rebuilding** (`chunking.py` & `rag_pipeline.py`):
  Can be invoked programmatically via `create_all_chunks()` and `chatbot.initialize_database(docs)` inside a cron job or background task whenever ERP records are modified.
