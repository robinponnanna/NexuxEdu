from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.models.schemas import (
    UserSecurityClaims, StudentSubjectSummary, SubjectMarksDetailResponse,
    SubjectModulesAnalysisResponse, StudentMarksOverviewResponse,
    ModuleLearningMaterialResponse, AcademicExplainRequest, AcademicExplainResponse
)
from app.api.auth import get_current_user_claims
from app.core.database import AsyncSessionLocal
from app.services.academic_analytics import (
    get_student_subjects_analytics,
    get_student_subject_detail,
    get_student_subject_modules_analysis,
    get_student_marks_overview,
    get_module_learning_materials
)
from app.services.academic_rag import generate_grounded_microlesson

router = APIRouter(prefix="/student", tags=["Student Academic Support"])

def resolve_authorized_student_id(claims: UserSecurityClaims) -> int:
    """
    Enforces Zero-Trust role and session claim verification.
    Guarantees that a student or parent can only access the bound student_id.
    """
    if claims.role not in ["student", "parent"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="RBAC Restriction: Academic support endpoints are accessible to students and parents only."
        )

    target_sid = claims.student_id if claims.role == "student" else claims.ward_id
    if not target_sid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No student record associated with this authenticated session."
        )
    return target_sid

@router.get("/subjects", response_model=List[StudentSubjectSummary])
async def get_enrolled_subjects(
    semester: Optional[int] = Query(None, description="Filter by semester (e.g. 6)"),
    performance_status: Optional[str] = Query(None, description="Filter by status: 'Strong', 'Developing', 'Needs Support', or 'all'"),
    claims: UserSecurityClaims = Depends(get_current_user_claims)
):
    """
    Returns all enrolled subjects for the authenticated student with computed marks,
    percentages, performance status, strongest module, and weakest module.
    """
    student_id = resolve_authorized_student_id(claims)
    async with AsyncSessionLocal() as session:
        subjects = await get_student_subjects_analytics(
            session=session,
            student_id=student_id,
            semester=semester,
            performance_status=performance_status
        )
        return subjects

@router.get("/marks", response_model=StudentMarksOverviewResponse)
async def get_student_marks_overview_endpoint(
    semester: Optional[int] = Query(None, description="Filter by semester (e.g. 6)"),
    performance_status: Optional[str] = Query(None, description="Filter by status: 'Strong', 'Developing', 'Needs Support', or 'all'"),
    claims: UserSecurityClaims = Depends(get_current_user_claims)
):
    """
    Returns the comprehensive academic marks overview for the authenticated student.
    """
    student_id = resolve_authorized_student_id(claims)
    async with AsyncSessionLocal() as session:
        overview = await get_student_marks_overview(
            session=session,
            student_id=student_id,
            semester=semester,
            performance_status=performance_status
        )
        if not overview:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student academic profile could not be loaded."
            )
        return overview

@router.get("/marks/{subject_id}", response_model=SubjectMarksDetailResponse)
async def get_subject_marks_detail(
    subject_id: int,
    claims: UserSecurityClaims = Depends(get_current_user_claims)
):
    """
    Returns detailed subject performance for a specific enrolled subject,
    including assessment score breakdown, question marks, and CO/module analysis.
    """
    student_id = resolve_authorized_student_id(claims)
    async with AsyncSessionLocal() as session:
        detail = await get_student_subject_detail(
            session=session,
            student_id=student_id,
            subject_id=subject_id
        )
        if not detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subject with ID {subject_id} not found or student is not enrolled in this course."
            )
        return detail

@router.get("/marks/{subject_id}/modules", response_model=SubjectModulesAnalysisResponse)
async def get_subject_modules_analysis(
    subject_id: int,
    claims: UserSecurityClaims = Depends(get_current_user_claims)
):
    """
    Returns the Course Outcome (CO) and module performance analysis for a subject,
    explicitly highlighting the weakest and strongest modules.
    """
    student_id = resolve_authorized_student_id(claims)
    async with AsyncSessionLocal() as session:
        analysis = await get_student_subject_modules_analysis(
            session=session,
            student_id=student_id,
            subject_id=subject_id
        )
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subject with ID {subject_id} not found or student is not enrolled in this course."
            )
        return analysis

@router.get("/learning/materials/{module_id}", response_model=ModuleLearningMaterialResponse)
async def get_learning_materials_for_module(
    module_id: int,
    claims: UserSecurityClaims = Depends(get_current_user_claims)
):
    """
    Returns learning materials, pages, topic chunks, and cached micro-lessons
    for the specified module.
    """
    resolve_authorized_student_id(claims)
    async with AsyncSessionLocal() as session:
        mat_data = await get_module_learning_materials(
            session=session,
            module_id=module_id
        )
        if not mat_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Module with ID {module_id} not found."
            )
        return mat_data

@router.post("/learning/explain", response_model=AcademicExplainResponse)
async def explain_academic_concept(
    req: AcademicExplainRequest,
    claims: UserSecurityClaims = Depends(get_current_user_claims)
):
    """
    Academic RAG & Concept Explanation Endpoint.
    Grounded synthesis of interactive MicroLessons from highlighted learning materials.
    Enforces Zero-Trust student enrollment boundaries and pre-filtered semantic retrieval.
    """
    student_id = resolve_authorized_student_id(claims)
    async with AsyncSessionLocal() as session:
        response = await generate_grounded_microlesson(
            session=session,
            student_id=student_id,
            req=req,
            claims=claims
        )
        return response

