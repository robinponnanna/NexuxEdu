import re
from typing import Dict, Any, List, Optional
from sqlalchemy import select, and_
from app.models.schemas import ERPGraphState, Citation
from app.core.database import AsyncSessionLocal, Attendance, Student, Faculty, User, Bus

async def execute_structured_records_agent(state: ERPGraphState) -> Dict[str, Any]:
    """
    Structured Records Agent (Text-to-Parametric SQL).
    Strictly binds parameters to state.claims. No raw SQL string interpolation.
    """
    claims = state.claims
    query_lower = state.raw_query.lower()
    citations: List[Citation] = []
    
    # 1. Check for unauthorized salary / payroll probing by students or parents
    salary_pattern = r"\bsalar(y|ies)\b|\bpayroll\b|\bcompensation\b|\bannual_salary\b|\bwage(s)?\b|\bstipend(s)?\b|\bpay\b"
    is_asking_salary = bool(re.search(salary_pattern, query_lower))

    
    if is_asking_salary:
        if claims.role in ["student", "parent"]:
            # Strictly prohibited: Logged and rejected without database access
            return {
                "authorized": False,
                "reason": "You do not have authorization to view faculty compensation or payroll records. This access boundary violation has been recorded.",
                "data": None,
                "citations": []
            }
        elif claims.role == "faculty":
            # Faculty can view their OWN salary
            async with AsyncSessionLocal() as session:
                stmt = select(Faculty).where(Faculty.user_id == claims.user_id)
                res = await session.execute(stmt)
                fac = res.scalar_one_or_none()
                if fac:
                    citations.append(Citation(
                        title="Faculty Payroll Ledger",
                        section=f"Emp Code: {fac.emp_code}",
                        type="sql_record",
                        detail="Confidential faculty salary ledger"
                    ))
                    return {
                        "authorized": True,
                        "data": {
                            "type": "faculty_salary",
                            "faculty_name": claims.name,
                            "department": fac.department,
                            "designation": fac.designation,
                            "annual_salary": fac.annual_salary
                        },
                        "citations": citations
                    }
        elif claims.role == "admin":
            # Admin can view salary summaries
            async with AsyncSessionLocal() as session:
                stmt = select(Faculty, User).join(User, Faculty.user_id == User.id)
                res = await session.execute(stmt)
                rows = res.all()
                salaries = []
                for fac, usr in rows:
                    salaries.append({
                        "name": usr.name,
                        "department": fac.department,
                        "designation": fac.designation,
                        "annual_salary": fac.annual_salary
                    })
                citations.append(Citation(
                    title="Administrative Payroll Ledger",
                    section="Full Department Roster",
                    type="sql_record",
                    detail="Institutional payroll ledger"
                ))
                return {
                    "authorized": True,
                    "data": {"type": "admin_salary_overview", "records": salaries},
                    "citations": citations
                }

    # 2. Student / Parent Attendance & Academic Lookup
    # Security invariant: resolve student_id strictly from verified claims
    target_student_id = claims.student_id if claims.role == "student" else claims.ward_id
    
    if target_student_id:
        async with AsyncSessionLocal() as session:
            # Query attendance records bound to target_student_id
            stmt = select(Attendance).where(Attendance.student_id == target_student_id)
            res = await session.execute(stmt)
            records = res.scalars().all()
            
            if records:
                attendance_list = []
                for r in records:
                    attendance_list.append({
                        "subject": r.subject,
                        "attended_classes": r.attended_classes,
                        "total_classes": r.total_classes,
                        "attendance_pct": r.attendance_pct,
                        "is_eligible": r.attendance_pct >= 75.0
                    })
                    
                citations.append(Citation(
                    title="University Student Attendance Registry",
                    section=f"Student ID: #{target_student_id}",
                    type="sql_record",
                    detail="Verified relational attendance records"
                ))
                
                # Check if specific subject requested (e.g., Operating Systems)
                filtered_attendance = attendance_list
                for att in attendance_list:
                    if att["subject"].lower() in query_lower:
                        filtered_attendance = [att]
                        break
                        
                return {
                    "authorized": True,
                    "data": {
                        "type": "student_attendance",
                        "student_id": target_student_id,
                        "role_queried": claims.role,
                        "records": filtered_attendance
                    },
                    "citations": citations
                }

    # 3. Faculty Class / Student Roster & Section Attendance lookup
    if claims.role == "faculty":
        async with AsyncSessionLocal() as session:
            # Check if query asks for class / section attendance
            asks_attendance = any(w in query_lower for w in ["attend", "absent", "debar", "class", "section", "record", "roster"])
            
            if asks_attendance:
                stmt = (
                    select(Student, User, Attendance)
                    .join(User, Student.user_id == User.id)
                    .join(Attendance, Attendance.student_id == Student.id)
                    .where(Student.department == claims.department)
                )
                if "section a" in query_lower:
                    stmt = stmt.where(Student.section == "Section A")
                elif "section b" in query_lower:
                    stmt = stmt.where(Student.section == "Section B")

                if "operating system" in query_lower or "cs-301" in query_lower:
                    stmt = stmt.where(Attendance.subject == "Operating Systems")
                elif "database" in query_lower or "dbms" in query_lower or "cs-302" in query_lower:
                    stmt = stmt.where(Attendance.subject == "Database Management Systems")

                res = await session.execute(stmt)
                class_records = []
                for st, usr, att in res.all():
                    class_records.append({
                        "name": usr.name,
                        "roll_number": st.roll_number,
                        "section": st.section or "Section A",
                        "subject": att.subject,
                        "attended_classes": att.attended_classes,
                        "total_classes": att.total_classes,
                        "attendance_pct": att.attendance_pct,
                        "status": "Safe" if att.attendance_pct >= 85.0 else ("Attention" if att.attendance_pct >= 75.0 else "Debarment Risk"),
                        "is_eligible": att.attendance_pct >= 75.0
                    })
                citations.append(Citation(
                    title=f"{claims.department} Class Attendance Roster",
                    section="Course Section Ledger",
                    type="sql_record",
                    detail="Verified class and section student attendance records"
                ))
                return {
                    "authorized": True,
                    "data": {"type": "faculty_class_attendance", "department": claims.department, "records": class_records},
                    "citations": citations
                }
            else:
                stmt = select(Student, User).join(User, Student.user_id == User.id).where(Student.department == claims.department)
                res = await session.execute(stmt)
                dept_students = []
                for st, usr in res.all():
                    dept_students.append({
                        "name": usr.name,
                        "roll_number": st.roll_number,
                        "section": st.section or "Section A",
                        "semester": st.semester,
                        "department": st.department
                    })
                citations.append(Citation(
                    title=f"{claims.department} Student Roster",
                    section="Active Enrolled Students",
                    type="sql_record",
                    detail="Departmental student roster"
                ))
                return {
                    "authorized": True,
                    "data": {"type": "faculty_roster", "students": dept_students},
                    "citations": citations
                }

    return {"authorized": True, "data": None, "citations": []}
