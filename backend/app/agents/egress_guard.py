import re
from typing import Dict, Any, List, Optional
from app.models.schemas import ERPGraphState, ChatResponse, Citation

def sanitize_and_synthesize_response(state: ERPGraphState) -> ChatResponse:
    """
    Synthesis and Egress Guardrail:
    1. Evaluates context grounding. If unauthorized or empty context, produces an explicit refusal.
    2. Synthesizes a factual, coherent response strictly grounded on retrieved data.
    3. Runs egress check for sensitive cross-role data leaks (e.g. salary numbers to students).
    """
    claims = state.claims
    
    # 1. RBAC Denial Check
    if state.access_denied:
        return ChatResponse(
            reply=(
                f"🔒 **Restricted Access**: You do not have authorization to view this data. "
                f"Your account role (`{claims.role.upper()}`) does not possess permission for confidential "
                f"departmental or compensation records. This event has been logged in the institutional security audit."
            ),
            sources=[],
            classified_intent=state.classified_intent,
            access_denied=True,
            audit_flag="EVENT_PRIVILEGE_PROBE"
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
            reply=(
                "I am unable to locate records or institutional documentation matching your inquiry "
                "within your authorized account scope. Please verify your query or contact the Academic Registrar."
            ),
            sources=[],
            classified_intent=state.classified_intent,
            access_denied=False
        )
    
    # 2. Build Grounded Response
    parts: List[str] = []
    
    # Tabular / Structured Attendance
    if has_structured and structured.get("type") == "student_attendance":
        records = structured.get("records", [])
        if records:
            parts.append("### 📊 Verified Academic Attendance Records")
            for rec in records:
                status_icon = "🟢" if rec["attendance_pct"] >= 85.0 else ("🟡" if rec["attendance_pct"] >= 75.0 else "🔴")
                eligibility_str = "Eligible for final examinations" if rec["is_eligible"] else "⚠️ Debarment Warning (< 75% threshold)"
                parts.append(
                    f"* **{rec['subject']}**: {status_icon} **{rec['attendance_pct']}%** "
                    f"({rec['attended_classes']}/{rec['total_classes']} classes attended) — {eligibility_str}"
                )
    
    # Faculty Salary (Authorized Faculty / Admin)
    elif has_structured and structured.get("type") == "faculty_salary":
        data = structured
        parts.append(
            f"### 💼 Confidential Faculty Compensation Record\n"
            f"* **Faculty Member:** {data.get('faculty_name')}\n"
            f"* **Department:** {data.get('department')}\n"
            f"* **Designation:** {data.get('designation')}\n"
            f"* **Base Annual Salary:** ${data.get('annual_salary'):,.2f}"
        )
        
    # Faculty Student Roster
    elif has_structured and structured.get("type") == "faculty_roster":
        students = structured.get("students", [])
        parts.append(f"### 📋 Department Student Roster ({len(students)} Enrolled)")
        for st in students:
            parts.append(f"* **{st['name']}** (Roll: `{st['roll_number']}`) — Semester {st['semester']}, {st['department']}")
            
    # Transit Telemetry
    if has_telemetry:
        data = telemetry
        parts.append("### 🚌 Real-Time Transit Telemetry")
        parts.append(
            f"* **Vehicle:** **{data.get('bus_number', 'BUS-001')}** ({data.get('route_name', 'Campus Transit')})\n"
            f"* **Current Location:** Latitude `{data.get('lat')}`, Longitude `{data.get('lng')}`\n"
            f"* **Live Speed:** `{data.get('speed_kmh', 0.0)} km/h` ({data.get('status', 'Active')})\n"
            f"* **Next Registered Stop:** {data.get('next_stop', 'Main Campus Gate')} "
            f"(ETA: ~{data.get('next_stop_eta_mins', 4)} mins, {data.get('distance_to_stop_km', 1.2)} km away)"
        )
        
    # Document Policies
    if has_docs:
        parts.append("### 📜 Institutional Policy & Regulations")
        for doc in docs:
            parts.append(f"**{doc.get('title')}**\n> {doc.get('content')}")
            
    final_text = "\n\n".join(parts)
    
    # 3. Egress Leak Scanner: ensure no salary amounts leaked to non-faculty/non-admin
    if claims.role in ["student", "parent"]:
        if re.search(r"\$\d{2,3},\d{3}", final_text):
            final_text = (
                "🔒 **Security Egress Alert**: Output contained restricted financial tokens and was redacted "
                "by the multi-agent egress firewall."
            )
            
    return ChatResponse(
        reply=final_text,
        sources=state.citations,
        classified_intent=state.classified_intent,
        access_denied=False
    )
