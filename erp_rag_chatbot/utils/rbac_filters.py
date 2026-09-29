"""
Role-Based Access Control (RBAC) Filter Logic for ChromaDB Vector Retrieval.

This module defines the `User` identity abstraction and the `build_query_filters(user)`
function which creates ChromaDB-compatible metadata query filters to enforce zero-trust
boundaries at retrieval time.

Access Rules:
1. Student: Can ONLY see their own academic data (subjects, assignments, attendance, marks).
            Blocked from other students' records, faculty salaries, and institutional finances.
2. Parent:  Can ONLY see their own children's / ward's academic records.
            Blocked from other students, faculty salaries, and institutional accounts.
3. Faculty: Can see student academic records and faculty profiles.
            Explicitly blocked from faculty salaries and institutional accounts (sensitivity != 'confidential').
4. Admin:   Unrestricted access to all institutional records, faculty salaries, and financials.
"""

from typing import Any, Dict, Optional


class User:
    """
    Represents an authenticated user within the ERP ecosystem.
    
    Attributes:
        user_id (int): Primary key from the ERP users table.
        role (str): One of 'student', 'parent', 'faculty', 'admin'.
        additional_context (dict): Role-specific context (student_id, parent_id, faculty_id, department, etc.).
    """

    def __init__(
        self,
        user_id: int,
        role: str,
        additional_context: Optional[Dict[str, Any]] = None,
    ):
        self.user_id = user_id
        self.role = role.strip().lower()
        self.additional_context = additional_context or {}

        # Derived convenience properties bound from verified ERP database records
        self.student_id: Optional[int] = self.additional_context.get("student_id")
        self.parent_id: Optional[int] = self.additional_context.get("parent_id")
        self.faculty_id: Optional[int] = self.additional_context.get("faculty_id")
        self.department: Optional[str] = self.additional_context.get("department")
        self.name: str = self.additional_context.get("name", "Unknown User")
        self.email: str = self.additional_context.get("email", "")

    def __repr__(self) -> str:
        return (
            f"User(id={self.user_id}, name='{self.name}', role='{self.role}', "
            f"student_id={self.student_id}, parent_id={self.parent_id}, faculty_id={self.faculty_id})"
        )


def build_query_filters(user: User) -> Dict[str, Any]:
    """
    Constructs a ChromaDB-compliant `where` metadata filter based on the user's role and identity.

    All filtering is enforced PRE-RETRIEVAL (before documents reach the LLM), mathematically
    preventing unauthorized cross-role entity extraction or lateral privilege escalation.

    Args:
        user (User): The authenticated ERP user requesting retrieval.

    Returns:
        Dict[str, Any]: ChromaDB `where` filter dictionary.
    """
    role = user.role.lower()

    if role == "student":
        # Rule 1: Student can only retrieve documents bound to their own student_id.
        # Fallback to an impossible ID (-1) if student_id is missing, preventing leakage.
        sid = user.student_id if user.student_id is not None else -1
        return {"student_id": int(sid)}

    elif role == "parent":
        # Rule 2: Parent can only retrieve documents bound to their own parent_id (their children).
        pid = user.parent_id if user.parent_id is not None else -1
        return {"parent_id": int(pid)}

    elif role == "faculty":
        # Rule 3: Faculty can view student records and faculty profiles,
        # but are strictly blocked from 'confidential' records (e.g. salary ledger & institutional accounts).
        return {"sensitivity": {"$ne": "confidential"}}

    elif role == "admin":
        # Rule 4: Admin has full unrestricted visibility across all entities and sensitivity tiers.
        return {}

    else:
        # Default zero-trust fallback: Deny all documents for unrecognized roles
        return {"sensitivity": "__NO_ACCESS__"}


def describe_permissions(user: User) -> str:
    """
    Returns a human-readable summary of the security boundaries active for the user.
    """
    filters = build_query_filters(user)
    if user.role == "admin":
        return "ADMIN (Full Access): Can view all academic records, faculty salaries, and institutional finances."
    elif user.role == "faculty":
        return f"FACULTY (Dept: {user.department or 'N/A'}): Can view student records and faculty directory. Salaries and financial accounts are blocked."
    elif user.role == "parent":
        return f"PARENT (Parent ID: {user.parent_id}): Restricted exclusively to linked ward's academic records."
    elif user.role == "student":
        return f"STUDENT (Student ID: {user.student_id}): Restricted exclusively to personal academic records and attendance."
    else:
        return f"UNKNOWN ROLE ({user.role}): Access locked."
