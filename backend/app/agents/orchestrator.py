import asyncio
from typing import List, Dict, Any
from app.models.schemas import UserSecurityClaims, ERPGraphState, ChatResponse, Citation, AgentMessage
from app.agents.ingress_guard import check_input_guardrail
from app.agents.intent_classifier import classify_intent
from app.agents.structured_records import execute_structured_records_agent
from app.agents.vector_knowledge import execute_vector_knowledge_agent
from app.agents.transit_telemetry import execute_transit_telemetry_agent
from app.agents.egress_guard import sanitize_and_synthesize_response
from app.core.database import AsyncSessionLocal, AuditLog

async def log_security_event(claims: UserSecurityClaims, event_type: str, details: str):
    """Persists security audit log to the database."""
    try:
        async with AsyncSessionLocal() as session:
            entry = AuditLog(
                user_id=claims.user_id,
                role=claims.role,
                event_type=event_type,
                details=details
            )
            session.add(entry)
            await session.commit()
    except Exception as e:
        print(f"Error persisting audit log: {e}")

async def run_agent_workflow(query: str, claims: UserSecurityClaims, history: List[AgentMessage] = None) -> ChatResponse:
    """
    Hierarchical Multi-Agent Supervisor State Machine.
    Coordinates Ingress, Intent Classification, Fan-Out to Workers, Aggregation, and Egress Guard.
    """
    history = history or []
    
    # Initialize State
    state = ERPGraphState(
        claims=claims,
        raw_query=query,
        conversation_history=history
    )
    
    # Step 1: Ingress Guardrail Check
    is_safe, refusal_reason = check_input_guardrail(query, claims)
    if not is_safe:
        await log_security_event(claims, "EVENT_PRIVILEGE_PROBE", f"Adversarial jailbreak query rejected: {query[:100]}")
        return ChatResponse(
            reply="Access to this information is forbidden.",
            sources=[],
            access_denied=True,
            audit_flag="EVENT_PRIVILEGE_PROBE"
        )
        
    # Step 2: Intent Classification & Routing
    intent, target_agents = classify_intent(query)
    state.classified_intent = intent
    state.target_agents = target_agents
    
    # Step 3: Worker Agent Fan-Out
    tasks = []
    if "STRUCTURED_RECORDS" in target_agents:
        tasks.append(execute_structured_records_agent(state))
    if "VECTOR_KNOWLEDGE" in target_agents:
        tasks.append(execute_vector_knowledge_agent(state))
    if "TRANSIT_TELEMETRY" in target_agents:
        tasks.append(execute_transit_telemetry_agent(state))
        
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Step 4: Aggregate Intermediate Outputs
    task_idx = 0
    if "STRUCTURED_RECORDS" in target_agents:
        res = results[task_idx]
        task_idx += 1
        if isinstance(res, dict):
            if not res.get("authorized", True):
                state.access_denied = True
                await log_security_event(
                    claims, "EVENT_PRIVILEGE_PROBE", 
                    f"User role '{claims.role}' attempted unauthorized access to structured records. Query: '{query}'"
                )
            else:
                state.retrieved_structured_data = res.get("data")
                state.citations.extend(res.get("citations", []))

    if "VECTOR_KNOWLEDGE" in target_agents:
        res = results[task_idx]
        task_idx += 1
        if isinstance(res, dict):
            state.retrieved_unstructured_context = res.get("documents", [])
            state.citations.extend(res.get("citations", []))

    if "TRANSIT_TELEMETRY" in target_agents:
        res = results[task_idx]
        task_idx += 1
        if isinstance(res, dict):
            state.transit_telemetry_data = res.get("data")
            state.citations.extend(res.get("citations", []))

    # Step 5: Synthesis & Egress Guardrail Evaluation
    chat_response = await sanitize_and_synthesize_response(state)
    return chat_response
