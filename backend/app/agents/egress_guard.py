import os
import re
import httpx
from typing import Dict, Any, List, Optional
from app.models.schemas import ERPGraphState, ChatResponse, Citation

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("CHAT_MODEL", "llama3.2:3b")


async def call_local_llm_synthesizer(context: str, query: str) -> Optional[str]:
    """
    Executes local LLM inference via Ollama (llama3.2:3b) on the backend server.
    Ensures answers are dynamically generated in natural language and strictly grounded on verified context.
    """
    system_prompt = (
        "You are the NexusEdu Educational ERP AI Assistant. "
        "Your task is to answer the user's question using ONLY the verified context facts provided below. "
        "Speak naturally, clearly, and concisely directly addressing the question. "
        "Do NOT invent or assume any information outside the provided context. "
        "If the context does not contain enough information to answer the question, "
        "reply strictly: Access to this information is forbidden."
    )

    user_prompt = f"Context:\n{context}\n\nUser Question: {query}\n\nAnswer:"

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "stream": False,
                    "options": {
                        "temperature": 0.0,  # Zero temperature for deterministic grounding
                    },
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("message", {}).get("content", "").strip()
                if content:
                    return content
    except Exception as e:
        print(f"Warning: Could not connect to local Ollama LLM at {OLLAMA_BASE_URL}: {e}")
    return None


async def sanitize_and_synthesize_response(state: ERPGraphState) -> ChatResponse:
    """
    Synthesis and Egress Guardrail:
    1. Evaluates context grounding. If unauthorized or context is empty, emits 'Access to this information is forbidden.'
    2. Gathers verified context from structured SQL records, transit telematics, and vector knowledge.
    3. Invokes the local Ollama LLM (llama3.2:3b) to synthesize a dynamic, natural language answer.
    4. Runs an egress scan to ensure sensitive cross-role data (e.g., salaries to students) is never exposed.
    """
    claims = state.claims

    # 1. RBAC Authority Validation Check
    if state.access_denied:
        return ChatResponse(
            reply="Access to this information is forbidden.",
            sources=[],
            classified_intent=state.classified_intent,
            access_denied=True,
            audit_flag="EVENT_PRIVILEGE_PROBE",
        )

    structured = state.retrieved_structured_data
    docs = state.retrieved_unstructured_context
    telemetry = state.transit_telemetry_data

    # Check if context is completely empty
    has_structured = structured is not None and bool(structured)
    has_docs = len(docs) > 0
    has_telemetry = telemetry is not None and bool(telemetry)

    if not has_structured and not has_docs and not has_telemetry:
        return ChatResponse(
            reply="Access to this information is forbidden.",
            sources=[],
            classified_intent=state.classified_intent,
            access_denied=True,
        )

    # 2. Compile Verified Context Fragments for the LLM
    context_sections: List[str] = []

    # Student Attendance & Course Performance
    if has_structured and structured.get("type") == "student_attendance":
        records = structured.get("records", [])
        if records:
            att_lines = ["STUDENT ATTENDANCE & EXAM ELIGIBILITY:"]
            for rec in records:
                eligibility_str = (
                    "Eligible for final examinations"
                    if rec["is_eligible"]
                    else "Debarred from exam (< 75% threshold)"
                )
                att_lines.append(
                    f"- Subject: {rec['subject']} | Attended: {rec['attended_classes']}/{rec['total_classes']} "
                    f"classes ({rec['attendance_pct']}%) | Status: {eligibility_str}"
                )
            context_sections.append("\n".join(att_lines))

    # Faculty Salary Record (Authorized Faculty)
    elif has_structured and structured.get("type") == "faculty_salary":
        data = structured
        context_sections.append(
            f"FACULTY COMPENSATION RECORD:\n"
            f"- Faculty Member: {data.get('faculty_name')}\n"
            f"- Department: {data.get('department')}\n"
            f"- Designation: {data.get('designation')}\n"
            f"- Base Annual Salary: ${data.get('annual_salary'):,.2f}"
        )

    # Admin Salary Overview (Admin Only)
    elif has_structured and structured.get("type") == "admin_salary_overview":
        records = structured.get("records", [])
        sal_lines = ["ADMINISTRATIVE PAYROLL LEDGER:"]
        for rec in records:
            sal_lines.append(
                f"- {rec['name']} ({rec['designation']}, {rec['department']}): ${rec['annual_salary']:,.2f}"
            )
        context_sections.append("\n".join(sal_lines))

    # Faculty Student Class Roster
    elif has_structured and structured.get("type") == "faculty_roster":
        students = structured.get("students", [])
        roster_lines = [f"DEPARTMENT STUDENT ROSTER ({len(students)} Enrolled):"]
        for st in students:
            roster_lines.append(
                f"- {st['name']} (Roll: {st['roll_number']}, Semester {st['semester']}, {st['department']})"
            )
        context_sections.append("\n".join(roster_lines))

    # Real-Time Transit Telemetry
    if has_telemetry:
        data = telemetry
        context_sections.append(
            f"REAL-TIME BUS TELEMETRY:\n"
            f"- Vehicle: {data.get('bus_number', 'BUS-001')} (Route: {data.get('route_name', 'Campus Transit')})\n"
            f"- Coordinates: Latitude {data.get('lat')}, Longitude {data.get('lng')}\n"
            f"- Speed: {data.get('speed_kmh', 0.0)} km/h (Status: {data.get('status', 'Active')})\n"
            f"- Next Stop: {data.get('next_stop', 'Main Campus Gate')} "
            f"(ETA: ~{data.get('next_stop_eta_mins', 4)} mins, Distance: {data.get('distance_to_stop_km', 1.2)} km away)"
        )

    # Institutional Policy Documents
    if has_docs:
        doc_lines = ["INSTITUTIONAL POLICIES & REGULATIONS:"]
        for doc in docs:
            doc_lines.append(f"Title: {doc.get('title')}\nContent: {doc.get('content')}")
        context_sections.append("\n\n".join(doc_lines))

    compiled_context = "\n\n".join(context_sections)

    # 3. Dynamic Synthesis via Local LLM (llama3.2:3b)
    llm_generated_answer = await call_local_llm_synthesizer(
        context=compiled_context,
        query=state.raw_query,
    )

    if llm_generated_answer:
        final_text = llm_generated_answer
    else:
        # Fallback to formatted context if LLM is temporarily unreachable
        final_text = compiled_context

    # 4. Outbound Egress Guardrail: Guarantee zero cross-role salary leak to students/parents
    if claims.role in ["student", "parent"]:
        if re.search(r"\$\d{2,3},\d{3}", final_text):
            final_text = "Access to this information is forbidden."

    return ChatResponse(
        reply=final_text,
        sources=state.citations,
        classified_intent=state.classified_intent,
        access_denied=False,
    )
