import re
from typing import Tuple
from app.models.schemas import UserSecurityClaims

JAILBREAK_PATTERNS = [
    r"ignore (all )?prior rules",
    r"act as (root|system|admin|superuser)",
    r"dan mode",
    r"jailbreak",
    r"bypass (security|rbac|permission)",
    r"developer mode",
    r"system prompt override",
    r"reveal all (salaries|passwords|keys)"
]

def check_input_guardrail(query: str, claims: UserSecurityClaims) -> Tuple[bool, str]:
    """
    Ingress perimeter defense: scans for known prompt injection / jailbreak patterns.
    Returns (is_safe, refusal_reason).
    """
    lower_query = query.lower()
    for pattern in JAILBREAK_PATTERNS:
        if re.search(pattern, lower_query, re.IGNORECASE):
            return False, f"Request rejected by security guardrail: Detected potentially adversarial query pattern matching policy violations."
    return True, ""
