from fastapi import APIRouter, Depends
from app.models.schemas import ChatRequest, ChatResponse, UserSecurityClaims
from app.api.auth import get_current_user_claims
from app.agents.orchestrator import run_agent_workflow

router = APIRouter(prefix="/chat", tags=["Conversational AI"])

@router.post("/query", response_model=ChatResponse)
async def query_chat(
    req: ChatRequest,
    claims: UserSecurityClaims = Depends(get_current_user_claims)
):
    """
    Executes the RBAC-Grounded conversational agent pipeline.
    Enforces the zero-trust retrieval firewall, parametric SQL isolation,
    and metadata pre-filtered RAG.
    """
    response = await run_agent_workflow(
        query=req.message,
        claims=claims,
        history=req.conversation_history
    )
    return response
