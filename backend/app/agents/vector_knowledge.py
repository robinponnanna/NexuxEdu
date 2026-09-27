import json
import re
import numpy as np

from typing import List, Dict, Any
from sqlalchemy import select
from app.models.schemas import ERPGraphState, Citation
from app.core.database import AsyncSessionLocal, DocumentEmbedding
from app.services.seed_data import generate_pseudo_embedding

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    v1 = np.array(vec1, dtype=float)
    v2 = np.array(vec2, dtype=float)
    denom = np.linalg.norm(v1) * np.linalg.norm(v2)
    if denom == 0:
        return 0.0
    return float(np.dot(v1, v2) / denom)

async def execute_vector_knowledge_agent(state: ERPGraphState) -> Dict[str, Any]:
    """
    Vector Knowledge Agent (Pre-Filtered RAG).
    Applies strict database-level metadata filtering:
    Only documents where state.claims.role in doc.allowed_roles AND
    (doc.department IS NULL or doc.department == state.claims.department)
    are eligible for semantic similarity scoring.
    """
    claims = state.claims
    query = state.raw_query
    query_vec = generate_pseudo_embedding(query)
    
    async with AsyncSessionLocal() as session:
        # Fetch candidate documents
        stmt = select(DocumentEmbedding)
        res = await session.execute(stmt)
        all_docs = res.scalars().all()
        
        matches = []
        for doc in all_docs:
            allowed = [r.strip().lower() for r in doc.allowed_roles.split(",")]
            # Security Invariant: Metadata Pre-Filter
            if claims.role.lower() not in allowed:
                continue
            
            # Department isolation
            if doc.department and claims.department and doc.department.lower() != claims.department.lower():
                continue
            
            # Semantic distance calculation
            if doc.embedding_json:
                doc_vec = json.loads(doc.embedding_json)
                sim = cosine_similarity(query_vec, doc_vec)
            else:
                sim = 0.5
            
            # Keyword relevance booster for high-precision retrieval
            clean_query_words = [re.sub(r"[^\w]", "", w.lower()) for w in query.split()]
            keywords = [w for w in clean_query_words if len(w) >= 3 and w not in ["what", "when", "where", "how", "the", "for", "and", "are", "you"]]
            
            match_count = 0
            for kw in keywords:
                if kw in doc.title.lower():
                    match_count += 2
                elif kw in doc.content.lower():
                    match_count += 1
                    
            score = sim + (match_count * 0.25)
            
            if score > 0.25 or match_count >= 1:
                matches.append({
                    "id": doc.id,
                    "title": doc.title,
                    "section": doc.section,
                    "content": doc.content,
                    "score": score
                })

        
        matches.sort(key=lambda x: x["score"], reverse=True)
        top_matches = matches[:3]
        
        citations = []
        for m in top_matches:
            citations.append(Citation(
                title=m["title"],
                section=m["section"],
                type="policy_doc",
                detail=m["content"][:140] + "..."
            ))
            
        return {
            "authorized": True,
            "documents": top_matches,
            "citations": citations
        }
