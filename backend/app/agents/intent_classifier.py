import re
from typing import List, Tuple

def classify_intent(query: str) -> Tuple[str, List[str]]:
    """
    Deterministically and semantically classifies user intent into execution branches:
    - ACADEMIC_RECORD: personal attendance, grades, salary, student profile
    - INSTITUTIONAL_KNOWLEDGE: handbook, exam rules, syllabus, guidelines, memos
    - TRANSIT_TELEMETRY: bus location, route, ETA, speed, stop details
    - COMPOSITE: contains questions spanning multiple branches
    """
    lower = query.lower()
    
    academic_patterns = [
        r"\battendance\b", r"\bgrade(s)?\b", r"\bmark(s)?\b", r"\bpercent(age)?\b",
        r"\bclass(es)?\b", r"\bdebar(red|ment)?\b", r"\babsent\b", r"\bpresent\b",
        r"\bsalar(y|ies)\b", r"\bpayroll\b", r"\bcompensation\b", r"\broster(s)?\b",
        r"\boperating system(s)?\b", r"\bdbms\b", r"\bnetwork(s)?\b", r"\bexam key\b", r"\banswer key\b"
    ]
    
    knowledge_patterns = [
        r"\bpolic(y|ies)\b", r"\brule(s)?\b", r"\bregulation(s)?\b", r"\bguideline(s)?\b",
        r"\brequirement(s)?\b", r"\beligib(le|ility)\b", r"\bcriteria\b", r"\bthreshold(s)?\b",
        r"\bsyllabus\b", r"\bexam code\b", r"\bgrading scale\b", r"\bhandbook\b",
        r"\bcurfew\b", r"\bhostel\b", r"\bmedical emergency\b", r"\bcondonation\b",
        r"\bdiscretionary fund\b"
    ]

    
    transit_patterns = [
        r"\bbus(es)?\b", r"\btransit\b", r"\bvehicle(s)?\b", r"\broute(s)?\b",
        r"\beta\b", r"\bdriver\b", r"\blocation\b", r"\bcoordinate(s)?\b",
        r"\bspeed\b", r"\blive tracking\b", r"\bnext stop\b", r"\bwhere is\b", r"\bpickup\b"
    ]
    
    has_academic = any(re.search(pat, lower) for pat in academic_patterns)
    has_knowledge = any(re.search(pat, lower) for pat in knowledge_patterns)
    has_transit = any(re.search(pat, lower) for pat in transit_patterns)

    
    target_agents = []
    if has_academic:
        target_agents.append("STRUCTURED_RECORDS")
    if has_knowledge:
        target_agents.append("VECTOR_KNOWLEDGE")
    if has_transit:
        target_agents.append("TRANSIT_TELEMETRY")
        
    if len(target_agents) > 1:
        return "COMPOSITE", target_agents
    elif has_academic:
        return "ACADEMIC_RECORD", ["STRUCTURED_RECORDS"]
    elif has_knowledge:
        return "INSTITUTIONAL_KNOWLEDGE", ["VECTOR_KNOWLEDGE"]
    elif has_transit:
        return "TRANSIT_TELEMETRY", ["TRANSIT_TELEMETRY"]
    else:
        # Default fallback: check knowledge base first, then structured
        return "INSTITUTIONAL_KNOWLEDGE", ["VECTOR_KNOWLEDGE"]
