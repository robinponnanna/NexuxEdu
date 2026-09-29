"""
ERP RAG Chatbot Utilities Module.
Contains database connection management and Role-Based Access Control (RBAC) filter logic.
"""

from .db_connection import get_erp_connection, execute_query, table_exists
from .rbac_filters import User, build_query_filters

__all__ = [
    "get_erp_connection",
    "execute_query",
    "table_exists",
    "User",
    "build_query_filters",
]
