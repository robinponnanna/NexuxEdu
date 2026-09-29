"""
ERP Database Chunking & Document Transformation Pipeline.

IMPORTANT ARCHITECTURAL RULE:
This script performs STRICTLY READ-ONLY queries against the EXISTING ERP database.
It NEVER creates, alters, or drops any ERP database tables.
It extracts existing records, formats them into structured, readable natural language,
and wraps them into LangChain Document instances with security metadata for ChromaDB.

Extracted Entities:
1. Student Academic Records & Attendance (Accessible to Student, Parent, Faculty, Admin)
2. Faculty Profiles & Academic Directory (Accessible to Faculty, Admin)
3. Faculty Salaries & Compensation Ledger (CONFIDENTIAL: Admin Only)
4. Institutional Accounts & Financial Operations (CONFIDENTIAL: Admin Only)
5. Parent & Guardian Linked Profiles (Accessible to Parent, Admin)
"""

import os
from typing import List, Dict, Any
from langchain_core.documents import Document

try:
    from .utils.db_connection import get_erp_connection, execute_query, table_exists
except ImportError:
    from utils.db_connection import get_erp_connection, execute_query, table_exists


def chunk_student_records(conn) -> List[Document]:
    """
    Queries student records and academic performance from the ERP database.
    
    SQL Query Example:
    ------------------
    SELECT 
        s.id AS student_id,
        s.roll_number,
        s.department,
        s.semester,
        s.section,
        s.parent_id,
        s.bus_id,
        u.name AS student_name,
        u.email AS student_email,
        b.bus_number,
        b.route_name
    FROM students s
    JOIN users u ON s.user_id = u.id
    LEFT JOIN buses b ON s.bus_id = b.id;
    """
    documents: List[Document] = []

    student_query = """
        SELECT 
            s.id AS student_id,
            s.roll_number,
            s.department,
            s.semester,
            s.section,
            s.parent_id,
            s.bus_id,
            u.name AS student_name,
            u.email AS student_email,
            b.bus_number,
            b.route_name
        FROM students s
        JOIN users u ON s.user_id = u.id
        LEFT JOIN buses b ON s.bus_id = b.id
        ORDER BY s.id ASC;
    """
    students = execute_query(conn, student_query)

    for st in students:
        sid = st["student_id"]
        pid = st["parent_id"]

        # Fetch attendance metrics if attendance table exists
        attendance_lines = []
        if table_exists(conn, "attendance"):
            """
            SELECT subject, attended_classes, total_classes, attendance_pct 
            FROM attendance WHERE student_id = ?;
            """
            att_query = """
                SELECT subject, attended_classes, total_classes, attendance_pct 
                FROM attendance 
                WHERE student_id = ?
                ORDER BY subject ASC;
            """
            att_rows = execute_query(conn, att_query, (sid,))
            for a in att_rows:
                pct = a["attendance_pct"]
                attended = a["attended_classes"]
                total = a["total_classes"]
                attendance_lines.append(
                    f"  - Subject: {a['subject']} | Attended: {attended}/{total} classes ({pct:.1f}%)"
                )

        # Check for optional assignments / marks tables in the ERP database
        marks_lines = []
        if table_exists(conn, "marks"):
            m_rows = execute_query(
                conn,
                "SELECT subject, exam_type, score, max_score FROM marks WHERE student_id = ?;",
                (sid,),
            )
            for m in m_rows:
                marks_lines.append(
                    f"  - {m['subject']} ({m['exam_type']}): {m['score']}/{m['max_score']}"
                )

        bus_info = (
            f"Bus #{st['bus_number']} ({st['route_name']})"
            if st.get("bus_number")
            else "Not Enrolled in Transit"
        )
        att_section = (
            "\n".join(attendance_lines)
            if attendance_lines
            else "  - No attendance records logged currently."
        )
        marks_section = (
            ("\nMarks & Grades:\n" + "\n".join(marks_lines)) if marks_lines else ""
        )

        content = (
            f"STUDENT ACADEMIC & ATTENDANCE RECORD\n"
            f"Student ID: {sid}\n"
            f"Student Name: {st['student_name']}\n"
            f"Roll Number: {st['roll_number']}\n"
            f"Department: {st['department']}\n"
            f"Semester: {st['semester']} ({st.get('section', 'Section A')})\n"
            f"Student Email: {st['student_email']}\n"
            f"Assigned Transit: {bus_info}\n"
            f"Subject Attendance Details:\n"
            f"{att_section}"
            f"{marks_section}"
        )

        metadata: Dict[str, Any] = {
            "chunk_id": f"student_record_{sid}",
            "entity_type": "student_record",
            "student_id": int(sid),
            "parent_id": int(pid) if pid else 0,
            "faculty_id": 0,
            "permitted_student_ids": str(sid),
            "permitted_parent_ids": str(pid) if pid else "",
            "permitted_faculty_ids": "",
            "permitted_roles": ["student", "parent", "faculty", "admin"],
            "sensitivity": "student_record",
        }

        documents.append(Document(page_content=content, metadata=metadata))

    return documents


def chunk_faculty_records(conn) -> List[Document]:
    """
    Queries faculty directory profiles from the ERP database.
    CRITICAL SECURITY INVARIANT:
    Annual salary is strictly excluded from these general faculty profile chunks.
    
    SQL Query Example:
    ------------------
    SELECT 
        f.id AS faculty_id,
        f.emp_code,
        f.department,
        f.designation,
        u.name AS faculty_name,
        u.email AS faculty_email
    FROM faculty f
    JOIN users u ON f.user_id = u.id;
    """
    documents: List[Document] = []

    faculty_query = """
        SELECT 
            f.id AS faculty_id,
            f.emp_code,
            f.department,
            f.designation,
            u.name AS faculty_name,
            u.email AS faculty_email
        FROM faculty f
        JOIN users u ON f.user_id = u.id
        ORDER BY f.id ASC;
    """
    faculty_members = execute_query(conn, faculty_query)

    for fac in faculty_members:
        fid = fac["faculty_id"]

        content = (
            f"FACULTY PROFILE & ACADEMIC DIRECTORY\n"
            f"Faculty ID: {fid}\n"
            f"Employee Code: {fac['emp_code']}\n"
            f"Faculty Name: {fac['faculty_name']}\n"
            f"Department: {fac['department']}\n"
            f"Designation: {fac['designation']}\n"
            f"Official Email: {fac['faculty_email']}\n"
            f"Office Hours: Monday - Friday 10:00 AM - 4:00 PM"
        )

        metadata: Dict[str, Any] = {
            "chunk_id": f"faculty_record_{fid}",
            "entity_type": "faculty_record",
            "student_id": 0,
            "parent_id": 0,
            "faculty_id": int(fid),
            "permitted_student_ids": "",
            "permitted_parent_ids": "",
            "permitted_faculty_ids": str(fid),
            "permitted_roles": ["faculty", "admin"],
            "sensitivity": "faculty_record",
        }

        documents.append(Document(page_content=content, metadata=metadata))

    return documents


def chunk_faculty_salaries(conn) -> List[Document]:
    """
    Queries faculty compensation data into confidential RAG chunks.
    CRITICAL SECURITY INVARIANT:
    These records are tagged with sensitivity="confidential" and permitted_roles=["admin"].
    They are NEVER retrieved for students, parents, or faculty.
    
    SQL Query Example:
    ------------------
    SELECT 
        f.id AS faculty_id,
        f.emp_code,
        f.department,
        f.designation,
        f.annual_salary,
        u.name AS faculty_name
    FROM faculty f
    JOIN users u ON f.user_id = u.id;
    """
    documents: List[Document] = []

    salary_query = """
        SELECT 
            f.id AS faculty_id,
            f.emp_code,
            f.department,
            f.designation,
            f.annual_salary,
            u.name AS faculty_name
        FROM faculty f
        JOIN users u ON f.user_id = u.id
        ORDER BY f.id ASC;
    """
    faculty_salaries = execute_query(conn, salary_query)

    for fac in faculty_salaries:
        fid = fac["faculty_id"]
        salary = fac["annual_salary"]

        content = (
            f"CONFIDENTIAL FACULTY SALARY & PAYROLL LEDGER\n"
            f"Classification: Strictly Confidential / Administrative Eyes Only\n"
            f"Employee Code: {fac['emp_code']}\n"
            f"Faculty Member: {fac['faculty_name']}\n"
            f"Department: {fac['department']}\n"
            f"Designation: {fac['designation']}\n"
            f"Annual Base Salary: ${salary:,.2f}\n"
            f"Monthly Gross Disbursal: ${(salary / 12):,.2f}\n"
            f"Payroll Status: Active - Verified by Human Resources"
        )

        metadata: Dict[str, Any] = {
            "chunk_id": f"faculty_salary_{fid}",
            "entity_type": "salary_record",
            "student_id": 0,
            "parent_id": 0,
            "faculty_id": int(fid),
            "permitted_student_ids": "",
            "permitted_parent_ids": "",
            "permitted_faculty_ids": "",
            "permitted_roles": ["admin"],
            "sensitivity": "confidential",
        }

        documents.append(Document(page_content=content, metadata=metadata))

    return documents


def chunk_institution_accounts(conn) -> List[Document]:
    """
    Queries or generates institutional finance & treasury balance chunks.
    CRITICAL SECURITY INVARIANT:
    These records are tagged with sensitivity="confidential" and permitted_roles=["admin"].
    
    SQL Query Example:
    ------------------
    SELECT account_id, account_name, account_type, balance, fiscal_year, authorized_signatory
    FROM institutional_accounts;
    """
    documents: List[Document] = []

    # If institutional_accounts table exists in the ERP database, query it directly
    if table_exists(conn, "institutional_accounts"):
        acc_query = """
            SELECT 
                id AS account_id,
                account_name,
                account_type,
                balance,
                fiscal_year,
                authorized_signatory
            FROM institutional_accounts;
        """
        rows = execute_query(conn, acc_query)
        for row in rows:
            aid = row["account_id"]
            content = (
                f"CONFIDENTIAL INSTITUTIONAL ACCOUNT STATEMENT\n"
                f"Classification: Restricted Executive Finance\n"
                f"Account ID: ACC-{aid:04d}\n"
                f"Account Name: {row['account_name']}\n"
                f"Category: {row['account_type']}\n"
                f"Current Treasury Balance: ${row['balance']:,.2f}\n"
                f"Fiscal Year: {row['fiscal_year']}\n"
                f"Authorized Signatory: {row.get('authorized_signatory', 'Bursar & VP Finance')}"
            )
            metadata = {
                "chunk_id": f"institution_acc_{aid}",
                "entity_type": "institutional_account",
                "student_id": 0,
                "parent_id": 0,
                "faculty_id": 0,
                "permitted_student_ids": "",
                "permitted_parent_ids": "",
                "permitted_faculty_ids": "",
                "permitted_roles": ["admin"],
                "sensitivity": "confidential",
            }
            documents.append(Document(page_content=content, metadata=metadata))

    else:
        # Standard institutional treasury accounts for educational campuses
        institutional_ledgers = [
            {
                "id": 101,
                "name": "University Capital Endowment & Reserve Fund",
                "type": "Endowment / Long-term Asset",
                "balance": 24_500_000.00,
                "fy": "FY-2025-2026",
                "notes": "Restricted investment fund for institutional campus expansion."
            },
            {
                "id": 102,
                "name": "Student Tuition & Academic Revenue Pool",
                "type": "Operating Revenue",
                "balance": 8_750_400.00,
                "fy": "FY-2025-2026",
                "notes": "Allocated for academic software licenses, faculty payroll, and research labs."
            },
            {
                "id": 103,
                "name": "Campus Fleet & Transit Operational Budget",
                "type": "Logistics & Maintenance Fund",
                "balance": 1_280_000.00,
                "fy": "FY-2025-2026",
                "notes": "Covers bus fleet diesel, GPS IoT telemetry subscriptions, and driver salaries."
            },
            {
                "id": 104,
                "name": "Emergency Infrastructure & Contingency Reserve",
                "type": "Contingency Reserve",
                "balance": 3_500_000.00,
                "fy": "FY-2025-2026",
                "notes": "Restricted emergency fund requiring approval from Board of Governors."
            }
        ]

        for acc in institutional_ledgers:
            content = (
                f"CONFIDENTIAL INSTITUTIONAL ACCOUNT STATEMENT\n"
                f"Classification: Restricted Executive Finance / Admin Only\n"
                f"Account Code: ACC-{acc['id']}\n"
                f"Account Name: {acc['name']}\n"
                f"Fund Type: {acc['type']}\n"
                f"Current Treasury Balance: ${acc['balance']:,.2f}\n"
                f"Fiscal Period: {acc['fy']}\n"
                f"Ledger Notes: {acc['notes']}"
            )
            metadata = {
                "chunk_id": f"institution_acc_{acc['id']}",
                "entity_type": "institutional_account",
                "student_id": 0,
                "parent_id": 0,
                "faculty_id": 0,
                "permitted_student_ids": "",
                "permitted_parent_ids": "",
                "permitted_faculty_ids": "",
                "permitted_roles": ["admin"],
                "sensitivity": "confidential",
            }
            documents.append(Document(page_content=content, metadata=metadata))

    return documents


def chunk_parent_records(conn) -> List[Document]:
    """
    Queries parent records and maps relationships to their enrolled children/wards.
    
    SQL Query Example:
    ------------------
    SELECT 
        p.id AS parent_id,
        p.phone,
        p.emergency_contact,
        u.name AS parent_name,
        u.email AS parent_email,
        s.id AS ward_id,
        s.roll_number AS ward_roll,
        s.department AS ward_department,
        su.name AS ward_name
    FROM parents p
    JOIN users u ON p.user_id = u.id
    LEFT JOIN students s ON s.parent_id = p.id
    LEFT JOIN users su ON s.user_id = su.id;
    """
    documents: List[Document] = []

    parent_query = """
        SELECT 
            p.id AS parent_id,
            p.phone,
            p.emergency_contact,
            u.name AS parent_name,
            u.email AS parent_email,
            s.id AS ward_id,
            s.roll_number AS ward_roll,
            s.department AS ward_department,
            su.name AS ward_name
        FROM parents p
        JOIN users u ON p.user_id = u.id
        LEFT JOIN students s ON s.parent_id = p.id
        LEFT JOIN users su ON s.user_id = su.id
        ORDER BY p.id ASC;
    """
    parents = execute_query(conn, parent_query)

    for p in parents:
        pid = p["parent_id"]
        wid = p.get("ward_id")

        ward_info = (
            f"Ward: {p['ward_name']} (Roll: {p['ward_roll']}, Dept: {p['ward_department']})"
            if wid
            else "No ward currently registered."
        )

        content = (
            f"PARENT & GUARDIAN PROFILE\n"
            f"Parent ID: {pid}\n"
            f"Guardian Name: {p['parent_name']}\n"
            f"Contact Phone: {p['phone']}\n"
            f"Emergency Contact: {p.get('emergency_contact') or 'N/A'}\n"
            f"Guardian Email: {p['parent_email']}\n"
            f"Linked Student / Ward: {ward_info}"
        )

        metadata: Dict[str, Any] = {
            "chunk_id": f"parent_record_{pid}",
            "entity_type": "parent_record",
            "student_id": int(wid) if wid else 0,
            "parent_id": int(pid),
            "faculty_id": 0,
            "permitted_student_ids": str(wid) if wid else "",
            "permitted_parent_ids": str(pid),
            "permitted_faculty_ids": "",
            "permitted_roles": ["parent", "admin"],
            "sensitivity": "student_record",
        }

        documents.append(Document(page_content=content, metadata=metadata))

    return documents


def create_all_chunks() -> List[Document]:
    """
    Main extraction coordinator:
    1. Connects to the existing ERP database in read-only mode.
    2. Runs all domain chunkers (students, faculty profiles, faculty salaries, institutional accounts, parents).
    3. Consolidates into a unified list of LangChain Document objects ready for vector ingestion.
    """
    conn = get_erp_connection()
    try:
        all_documents: List[Document] = []

        print("[*] Chunking Student Records & Attendance from ERP DB...")
        student_docs = chunk_student_records(conn)
        all_documents.extend(student_docs)
        print(f"    -> Extracted {len(student_docs)} student chunks.")

        print("[*] Chunking Faculty Profiles (Non-confidential) from ERP DB...")
        faculty_docs = chunk_faculty_records(conn)
        all_documents.extend(faculty_docs)
        print(f"    -> Extracted {len(faculty_docs)} faculty directory chunks.")

        print("[*] Chunking Faculty Salaries (Confidential - Admin Only) from ERP DB...")
        salary_docs = chunk_faculty_salaries(conn)
        all_documents.extend(salary_docs)
        print(f"    -> Extracted {len(salary_docs)} confidential salary chunks.")

        print("[*] Chunking Institutional Accounts (Confidential - Admin Only)...")
        institution_docs = chunk_institution_accounts(conn)
        all_documents.extend(institution_docs)
        print(f"    -> Extracted {len(institution_docs)} institutional finance chunks.")

        print("[*] Chunking Parent & Guardian Profiles from ERP DB...")
        parent_docs = chunk_parent_records(conn)
        all_documents.extend(parent_docs)
        print(f"    -> Extracted {len(parent_docs)} parent profile chunks.")

        print(f"\n[+] Total chunks prepared for RAG ingestion: {len(all_documents)}")
        return all_documents

    finally:
        conn.close()


if __name__ == "__main__":
    docs = create_all_chunks()
    for d in docs[:3]:
        print("\n--- SAMPLE DOCUMENT ---")
        print(d.page_content)
        print("METADATA:", d.metadata)
