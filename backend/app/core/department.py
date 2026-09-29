from typing import Optional

CANONICAL_DEPARTMENTS = {
    "computer science": "Computer Science",
    "software engineering": "Software Engineering",
    "information technology": "Information Technology",
    "electronics": "Electronics",
}

def normalize_department(dept: Optional[str]) -> str:
    """
    Normalizes department strings to prevent silent zero-match query issues.
    Falls back to cleaned title-cased string if not in predefined map.
    """
    if not dept:
        return "Computer Science"
    cleaned = dept.strip()
    return CANONICAL_DEPARTMENTS.get(cleaned.lower(), cleaned)

def is_hod_designation(designation: Optional[str]) -> bool:
    """
    Exact-match check for HOD designation matching database records.
    Explicitly checks against canonical values ('Head of Department' and 'HOD').
    No loose substring matching.
    """
    if not designation:
        return False
    cleaned = designation.strip().lower()
    return cleaned in ("head of department", "hod")
