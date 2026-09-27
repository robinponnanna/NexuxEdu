from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, and_
from typing import Dict, Any, List, Optional
from app.models.schemas import UserSecurityClaims, AttendanceRecord
from app.api.auth import get_current_user_claims
from app.core.database import AsyncSessionLocal, Attendance, Student, Faculty, Bus, User, AuditLog
from app.core.pubsub import broker

router = APIRouter(prefix="/erp", tags=["ERP Core"])

@router.get("/dashboard")
async def get_dashboard_data(claims: UserSecurityClaims = Depends(get_current_user_claims)) -> Dict[str, Any]:
    """
    Returns role-specific high-level dashboard data:
    - student / parent: attendance metrics, overall %, bus state, active courses
    - faculty: assigned classes, student counts, department summary, section breakdown
    - admin: system health, active buses, audit log summary
    """
    async with AsyncSessionLocal() as session:
        if claims.role in ["student", "parent"]:
            target_sid = claims.student_id if claims.role == "student" else claims.ward_id
            attendance_records = []
            overall_pct = 0.0
            
            if target_sid:
                res = await session.execute(select(Attendance).where(Attendance.student_id == target_sid))
                rows = res.scalars().all()
                total_att = sum(r.attended_classes for r in rows)
                total_cls = sum(r.total_classes for r in rows)
                overall_pct = round((total_att / total_cls) * 100, 1) if total_cls > 0 else 0.0
                
                for r in rows:
                    attendance_records.append({
                        "id": r.id,
                        "subject": r.subject,
                        "attended_classes": r.attended_classes,
                        "total_classes": r.total_classes,
                        "attendance_pct": r.attendance_pct,
                        "status": "Safe" if r.attendance_pct >= 85.0 else ("Warning" if r.attendance_pct >= 75.0 else "Debarment Danger")
                    })
                    
            bus_telemetry = None
            if claims.bus_id:
                bus_telemetry = await broker.get_bus_telemetry(claims.bus_id)

            return {
                "role": claims.role,
                "name": claims.name,
                "department": claims.department,
                "overall_attendance_pct": overall_pct,
                "attendance_records": attendance_records,
                "assigned_bus_id": claims.bus_id,
                "live_bus": bus_telemetry,
                "semester": 6
            }

        elif claims.role == "faculty":
            # Department students count
            dept = claims.department or "Computer Science"
            res = await session.execute(select(func.count(Student.id)).where(Student.department == dept))
            student_count = res.scalar() or 0

            # Count per section
            sec_res = await session.execute(
                select(Student.section, func.count(Student.id))
                .where(Student.department == dept)
                .group_by(Student.section)
            )
            section_counts = {sec: cnt for sec, cnt in sec_res.all()}
            
            return {
                "role": "faculty",
                "name": claims.name,
                "department": dept,
                "active_courses": [
                    {"code": "CS-301", "name": "Operating Systems", "enrolled": student_count, "avg_attendance": 81.3},
                    {"code": "CS-302", "name": "Database Management Systems", "enrolled": student_count, "avg_attendance": 84.6},
                    {"code": "CS-303", "name": "Computer Networks", "enrolled": student_count, "avg_attendance": 81.1}
                ],
                "student_count": student_count,
                "section_counts": section_counts,
                "sections": list(section_counts.keys()) or ["Section A", "Section B"],
                "shuttle_status": "Regular hourly service active"
            }

        elif claims.role == "admin":
            user_count = (await session.execute(select(func.count(User.id)))).scalar() or 0
            bus_count = (await session.execute(select(func.count(Bus.id)))).scalar() or 0
            audit_count = (await session.execute(select(func.count(AuditLog.id)))).scalar() or 0
            
            recent_audits = (await session.execute(select(AuditLog).order_by(AuditLog.id.desc()).limit(5))).scalars().all()
            
            return {
                "role": "admin",
                "name": claims.name,
                "total_users": user_count,
                "active_buses": bus_count,
                "total_audit_events": audit_count,
                "recent_audits": [
                    {
                        "id": a.id,
                        "role": a.role,
                        "event_type": a.event_type,
                        "details": a.details,
                        "timestamp": a.timestamp.isoformat()
                    }
                    for a in recent_audits
                ]
            }

@router.get("/attendance", response_model=List[AttendanceRecord])
async def get_attendance(claims: UserSecurityClaims = Depends(get_current_user_claims)):
    """Returns granular attendance for authorized student or parent."""
    target_sid = claims.student_id if claims.role == "student" else claims.ward_id
    if not target_sid:
        raise HTTPException(status_code=400, detail="No student record linked to session.")
        
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Attendance).where(Attendance.student_id == target_sid))
        rows = res.scalars().all()
        return [
            AttendanceRecord(
                id=r.id,
                subject=r.subject,
                attended_classes=r.attended_classes,
                total_classes=r.total_classes,
                attendance_pct=r.attendance_pct
            )
            for r in rows
        ]

@router.get("/faculty/class-attendance")
async def get_faculty_class_attendance(
    subject: Optional[str] = None,
    section: Optional[str] = None,
    claims: UserSecurityClaims = Depends(get_current_user_claims)
):
    """
    Faculty & Admin endpoint:
    Returns full attendance of all students across class and sections taught by faculty.
    Strictly restricted under RBAC to claims.role in ['faculty', 'admin'].
    """
    if claims.role not in ["faculty", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="RBAC Restriction: Only faculty members and administrators can access class attendance rosters."
        )

    dept = claims.department or "Computer Science"
    target_subject = subject or "Operating Systems"

    async with AsyncSessionLocal() as session:
        query = (
            select(Student, User, Attendance)
            .join(User, Student.user_id == User.id)
            .join(Attendance, and_(Attendance.student_id == Student.id, Attendance.subject == target_subject))
            .where(Student.department == dept)
        )
        if section and section != "All Sections":
            query = query.where(Student.section == section)

        query = query.order_by(Student.section, Student.roll_number)
        res = await session.execute(query)
        rows = res.all()

        students_data = []
        for st, usr, att in rows:
            pct = att.attendance_pct
            status_label = "Safe" if pct >= 85.0 else ("Attention" if pct >= 75.0 else "Debarment Risk")
            students_data.append({
                "student_id": st.id,
                "roll_number": st.roll_number,
                "name": usr.name,
                "email": usr.email,
                "section": st.section or "Section A",
                "semester": st.semester,
                "subject": att.subject,
                "attended_classes": att.attended_classes,
                "total_classes": att.total_classes,
                "attendance_pct": pct,
                "status": status_label
            })

        total = len(students_data)
        avg_pct = round(sum(s["attendance_pct"] for s in students_data) / total, 1) if total > 0 else 0.0
        safe_cnt = sum(1 for s in students_data if s["status"] == "Safe")
        att_cnt = sum(1 for s in students_data if s["status"] == "Attention")
        risk_cnt = sum(1 for s in students_data if s["status"] == "Debarment Risk")

        # Distinct sections present in the department
        res_sections = await session.execute(
            select(Student.section).where(Student.department == dept).distinct().order_by(Student.section)
        )
        avail_sections = ["All Sections"] + [s for s in res_sections.scalars().all() if s]

        return {
            "department": dept,
            "selected_subject": target_subject,
            "selected_section": section or "All Sections",
            "classes": [
                {"code": "CS-301", "name": "Operating Systems"},
                {"code": "CS-302", "name": "Database Management Systems"},
                {"code": "CS-303", "name": "Computer Networks"}
            ],
            "sections": avail_sections,
            "summary": {
                "total_students": total,
                "class_avg_pct": avg_pct,
                "safe_count": safe_cnt,
                "attention_count": att_cnt,
                "debarment_risk_count": risk_cnt
            },
            "students": students_data
        }

@router.get("/audit-logs")
async def get_audit_logs(claims: UserSecurityClaims = Depends(get_current_user_claims)):
    """Admin-only endpoint for security logs inspection."""
    if claims.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="RBAC Restriction: Only administrators can access system audit logs."
        )
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(AuditLog).order_by(AuditLog.id.desc()).limit(50))
        logs = res.scalars().all()
        return [
            {
                "id": l.id,
                "user_id": l.user_id,
                "role": l.role,
                "event_type": l.event_type,
                "details": l.details,
                "timestamp": l.timestamp.isoformat()
            }
            for l in logs
        ]
