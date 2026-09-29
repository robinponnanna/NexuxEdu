"""
Database Connection Utility for Educational ERP System.

This module provides a unified connection factory (`get_erp_connection`) that securely
connects to the existing ERP relational database (SQLite, PostgreSQL, or MySQL) to fetch
records for chunking and vector storage without modifying existing tables.
"""

import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

# Load environment configuration from erp_rag_chatbot/.env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


def get_erp_connection():
    """
    Connects to the existing ERP database based on environment configuration.

    Supports:
    - 'sqlite': Local SQLite file (default: backend/campus.db)
    - 'postgresql': Enterprise PostgreSQL database (via psycopg2 or psycopg)
    - 'mysql': Enterprise MySQL database (via pymysql or mysql.connector)

    Returns:
        A database connection object configured with row dictionary/cursor capabilities.
    """
    db_type = os.getenv("ERP_DB_TYPE", "sqlite").lower()

    if db_type == "sqlite":
        # Resolve SQLite file path relative to current working directory or absolute
        db_path_env = os.getenv("ERP_DB_PATH", "../backend/campus.db")
        db_path = Path(db_path_env)
        
        # If relative, check both relative to cwd and relative to chatbot root
        if not db_path.is_absolute() and not db_path.exists():
            candidate = Path(__file__).resolve().parent.parent / db_path_env
            if candidate.exists():
                db_path = candidate

        if not db_path.exists():
            raise FileNotFoundError(
                f"Existing ERP SQLite database file not found at: {db_path}. "
                f"Please verify ERP_DB_PATH in your .env file."
            )

        conn = sqlite3.connect(str(db_path))
        # Enable sqlite3.Row for dict-like column access (e.g., row['email'])
        conn.row_factory = sqlite3.Row
        return conn

    elif db_type in ("postgresql", "postgres"):
        # =========================================================================
        # PostgreSQL Connection Implementation
        # Required package: pip install psycopg2-binary (or psycopg)
        # =========================================================================
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
        except ImportError:
            raise ImportError(
                "PostgreSQL driver 'psycopg2' not installed. "
                "Install it using: pip install psycopg2-binary"
            )

        host = os.getenv("ERP_DB_HOST", "localhost")
        port = int(os.getenv("ERP_DB_PORT", "5432"))
        dbname = os.getenv("ERP_DB_NAME", "erp_system")
        user = os.getenv("ERP_DB_USER", "erp_user")
        password = os.getenv("ERP_DB_PASSWORD", "your_password")

        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
            cursor_factory=RealDictCursor,
        )
        return conn

    elif db_type == "mysql":
        # =========================================================================
        # MySQL Connection Implementation
        # Required package: pip install pymysql (or mysql-connector-python)
        # =========================================================================
        try:
            import pymysql
            from pymysql.cursors import DictCursor
        except ImportError:
            raise ImportError(
                "MySQL driver 'pymysql' not installed. "
                "Install it using: pip install pymysql"
            )

        host = os.getenv("ERP_DB_HOST", "localhost")
        port = int(os.getenv("ERP_DB_PORT", "3306"))
        dbname = os.getenv("ERP_DB_NAME", "erp_system")
        user = os.getenv("ERP_DB_USER", "erp_user")
        password = os.getenv("ERP_DB_PASSWORD", "your_password")

        conn = pymysql.connect(
            host=host,
            port=port,
            database=dbname,
            user=user,
            password=password,
            cursorclass=DictCursor,
        )
        return conn

    else:
        raise ValueError(
            f"Unsupported ERP_DB_TYPE: '{db_type}'. Supported values are 'sqlite', 'postgresql', 'mysql'."
        )


def execute_query(conn, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """
    Executes a read-only query on the ERP database connection and returns a list of dictionaries.

    Args:
        conn: The database connection object.
        query: SQL query string.
        params: Tuple of query parameters for safe parameterized execution.

    Returns:
        List of row dictionaries where keys correspond to column names.
    """
    cursor = conn.cursor()
    cursor.execute(query, params)
    
    # Check if rows are sqlite3.Row or RealDictCursor or tuple
    rows = cursor.fetchall()
    results: List[Dict[str, Any]] = []

    for row in rows:
        if isinstance(row, dict):
            results.append(row)
        elif hasattr(row, "keys"):
            # sqlite3.Row instance
            results.append({k: row[k] for k in row.keys()})
        elif cursor.description:
            # Fallback for plain tuples with description
            col_names = [col[0] for col in cursor.description]
            results.append(dict(zip(col_names, row)))
        else:
            results.append(dict(row))

    cursor.close()
    return results


def table_exists(conn, table_name: str) -> bool:
    """
    Checks whether a specific table exists in the connected ERP database.
    Useful for conditionally querying optional ERP tables (e.g. assignments, marks, salaries).
    """
    db_type = os.getenv("ERP_DB_TYPE", "sqlite").lower()
    cursor = conn.cursor()

    try:
        if db_type == "sqlite":
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
                (table_name,),
            )
            return cursor.fetchone() is not None
        elif db_type in ("postgresql", "postgres"):
            cursor.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name=%s;",
                (table_name,),
            )
            return cursor.fetchone() is not None
        elif db_type == "mysql":
            cursor.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name=%s;",
                (table_name,),
            )
            return cursor.fetchone() is not None
        return False
    finally:
        cursor.close()
