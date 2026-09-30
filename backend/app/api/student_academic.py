import json
import asyncio
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, and_

from app.models.schemas import (
    UserSecurityClaims, StudentSubjectSummary, SubjectMarksDetailResponse,
    SubjectModulesAnalysisResponse, StudentMarksOverviewResponse,
    ModuleLearningMaterialResponse, AcademicExplainRequest, AcademicExplainResponse,
    VideoGenerationRequest, VideoJobResponse
)
from app.api.auth import get_current_user_claims
from app.core.database import AsyncSessionLocal, MicroLesson, StudentEnrollment
from app.services.academic_analytics import (
    get_student_subjects_analytics,
    get_student_subject_detail,
    get_student_subject_modules_analysis,
    get_student_marks_overview,
    get_module_learning_materials
)
from app.services.academic_rag import generate_grounded_microlesson
from app.services.video_generator import (
    create_video_job, get_job_status, render_microlesson_video,
    ensure_learning_video, _video_jobs, LESSONS_VIDEO_DIR, MEDIA_DIR
)

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


@router.post("/learning/video", response_model=VideoJobResponse)
async def request_video_generation_job(
    req: VideoGenerationRequest,
    claims: UserSecurityClaims = Depends(get_current_user_claims)
):
    """
    Creates or ensures an asynchronous background job to render an MP4 narrated video
    from a MicroLesson JSON record, topic key, or dynamic lesson payload.
    Immediately returns a tracked job_id without blocking.
    """
    student_id = resolve_authorized_student_id(claims)

    async with AsyncSessionLocal() as session:
        try:
            job_info = await ensure_learning_video(
                session=session,
                student_id=student_id,
                subject_id=req.subject_id,
                module_id=req.module_id,
                lesson_id=req.lesson_id,
                topic_key=req.topic_key,
                topic=req.topic,
                co_code=req.co_code,
                direct_payload=req.lesson_payload,
                background=True
            )
            return VideoJobResponse(**job_info)
        except PermissionError as pe:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(pe)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Video engine error: {str(e)}"
            )


@router.get("/learning/video/{job_id}", response_model=VideoJobResponse)
async def get_video_generation_job_status(
    job_id: str,
    claims: UserSecurityClaims = Depends(get_current_user_claims)
):
    """
    Returns the real-time execution status of an async video rendering job.
    """
    resolve_authorized_student_id(claims)
    job_info = get_job_status(job_id)
    if not job_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video job '{job_id}' not found."
        )
    return VideoJobResponse(**job_info)


@router.get("/learning/video/by-lesson/{lesson_id}", response_model=VideoJobResponse)
async def get_video_for_lesson(
    lesson_id: int,
    claims: UserSecurityClaims = Depends(get_current_user_claims)
):
    """
    Retrieves video status or cached video for a given lesson ID.
    If video file is missing or unverified, ensures valid MP4 state.
    """
    student_id = resolve_authorized_student_id(claims)
    async with AsyncSessionLocal() as session:
        try:
            job_info = await ensure_learning_video(
                session=session,
                student_id=student_id,
                lesson_id=lesson_id,
                background=False
            )
            return VideoJobResponse(**job_info)
        except PermissionError as pe:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(pe)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MicroLesson or video not available: {str(e)}"
            )


