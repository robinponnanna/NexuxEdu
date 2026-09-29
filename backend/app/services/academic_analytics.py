from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import (
    Subject, SubjectModule, Assessment, AssessmentQuestion,
    StudentQuestionMark, StudentEnrollment, Student, LearningMaterial,
    MaterialPage, MaterialChunk, MicroLesson
)
from app.models.schemas import (
    ModulePerformanceSummary, StudentSubjectSummary, AssessmentPerformanceDetail,
    SubjectMarksDetailResponse, SubjectModulesAnalysisResponse, StudentMarksOverviewResponse,
    StudentQuestionMarkResponse, SubjectResponse, SubjectModuleResponse,
    LearningMaterialResponse, MaterialPageResponse, MicroLessonResponse,
    ModuleLearningMaterialResponse
)

# Configurable Demo Performance Thresholds
STRONG_THRESHOLD: float = 75.0
DEVELOPING_THRESHOLD: float = 60.0

def classify_status(percentage: Optional[float]) -> str:
    """Classifies performance deterministically according to configurable thresholds."""
    if percentage is None:
        return "No Data"
    if percentage >= STRONG_THRESHOLD:
        return "Strong"
    elif percentage >= DEVELOPING_THRESHOLD:
        return "Developing"
    else:
        return "Needs Support"

def calculate_assessment_scores(
    questions: List[AssessmentQuestion],
    marks_map: Dict[int, StudentQuestionMark]
) -> Tuple[float, float, List[StudentQuestionMarkResponse]]:
    """
    Deterministically computes (marks_obtained, marks_available, question_responses)
    for an assessment, accounting for OR groups and optional questions.
    """
    total_obtained = 0.0
    total_available = 0.0
    question_responses: List[StudentQuestionMarkResponse] = []

    # Group questions by OR group
    standalone_questions: List[AssessmentQuestion] = []
    or_groups: Dict[str, List[AssessmentQuestion]] = {}

    for q in questions:
        if q.or_group_id:
            or_groups.setdefault(q.or_group_id, []).append(q)
        else:
            standalone_questions.append(q)

    # 1. Process Standalone Questions
    for q in standalone_questions:
        mark_record = marks_map.get(q.id)
        is_attempted = mark_record.is_attempted if mark_record else False
        marks_obtained = mark_record.marks_obtained if (mark_record and is_attempted) else 0.0
        # Clamp obtained marks defensively
        marks_obtained = max(0.0, min(q.max_marks, marks_obtained))

        if q.is_optional and not is_attempted:
            # Unattempted optional question: do not count in denominator
            pass
        else:
            total_available += q.max_marks
            total_obtained += marks_obtained

        question_responses.append(
            StudentQuestionMarkResponse(
                id=mark_record.id if mark_record else 0,
                question_id=q.id,
                question_label=q.question_label,
                co_code=q.co_code,
                max_marks=q.max_marks,
                marks_obtained=marks_obtained,
                is_attempted=is_attempted,
                or_group_id=q.or_group_id,
                feedback=mark_record.feedback if mark_record else None
            )
        )

    # 2. Process OR Groups
    for or_grp_id, group_qs in or_groups.items():
        max_possible = max(gq.max_marks for gq in group_qs)
        group_obtained = 0.0
        group_attempted = False

        for gq in group_qs:
            mark_record = marks_map.get(gq.id)
            is_attempted = mark_record.is_attempted if mark_record else False
            marks_obtained = mark_record.marks_obtained if (mark_record and is_attempted) else 0.0
            marks_obtained = max(0.0, min(gq.max_marks, marks_obtained))

            if is_attempted:
                group_attempted = True
                if marks_obtained > group_obtained:
                    group_obtained = marks_obtained

            question_responses.append(
                StudentQuestionMarkResponse(
                    id=mark_record.id if mark_record else 0,
                    question_id=gq.id,
                    question_label=gq.question_label,
                    co_code=gq.co_code,
                    max_marks=gq.max_marks,
                    marks_obtained=marks_obtained,
                    is_attempted=is_attempted,
                    or_group_id=gq.or_group_id,
                    feedback=mark_record.feedback if mark_record else None
                )
            )

        # If anyone attempted in the group or if group is mandatory
        is_group_optional = all(gq.is_optional for gq in group_qs)
        if not is_group_optional or group_attempted:
            total_available += max_possible
            total_obtained += group_obtained

    return round(total_obtained, 1), round(total_available, 1), question_responses

def calculate_modules_performance(
    modules: List[SubjectModule],
    questions: List[AssessmentQuestion],
    marks_map: Dict[int, StudentQuestionMark]
) -> List[ModulePerformanceSummary]:
    """
    Deterministically computes module/CO-level performance breakdown,
    accounting for cross-CO OR questions and unattempted optional questions.
    """
    mod_stats: Dict[int, Dict[str, Any]] = {}
    for m in modules:
        mod_stats[m.id] = {
            "module": m,
            "obtained": 0.0,
            "available": 0.0
        }

    # Group questions by assessment and or_group_id
    ass_groups: Dict[int, List[AssessmentQuestion]] = {}
    for q in questions:
        ass_groups.setdefault(q.assessment_id, []).append(q)

    for ass_id, ass_qs in ass_groups.items():
        handled_or_groups = set()
        for q in ass_qs:
            target_mod_id = q.module_id
            if not target_mod_id:
                # Try finding by co_code
                mod_match = next((m for m in modules if m.co_code == q.co_code), None)
                target_mod_id = mod_match.id if mod_match else None

            if q.or_group_id:
                if q.or_group_id in handled_or_groups:
                    continue
                handled_or_groups.add(q.or_group_id)

                group_qs = [gq for gq in ass_qs if gq.or_group_id == q.or_group_id]
                # Check which question in group was attempted
                attempted_in_grp = [
                    gq for gq in group_qs
                    if marks_map.get(gq.id) and marks_map[gq.id].is_attempted
                ]

                if attempted_in_grp:
                    # Pick best attempted question in group
                    best_q = max(
                        attempted_in_grp,
                        key=lambda x: marks_map[x.id].marks_obtained
                    )
                    best_mark = marks_map[best_q.id]
                    b_mod_id = best_q.module_id
                    if not b_mod_id:
                        m_match = next((m for m in modules if m.co_code == best_q.co_code), None)
                        b_mod_id = m_match.id if m_match else None

                    if b_mod_id and b_mod_id in mod_stats:
                        mod_stats[b_mod_id]["available"] += best_q.max_marks
                        mod_stats[b_mod_id]["obtained"] += max(0.0, min(best_q.max_marks, best_mark.marks_obtained))
                else:
                    # None attempted in OR group; if mandatory, assign to default question's module
                    if not all(gq.is_optional for gq in group_qs):
                        first_q = group_qs[0]
                        f_mod_id = first_q.module_id
                        if not f_mod_id:
                            m_match = next((m for m in modules if m.co_code == first_q.co_code), None)
                            f_mod_id = m_match.id if m_match else None
                        if f_mod_id and f_mod_id in mod_stats:
                            mod_stats[f_mod_id]["available"] += first_q.max_marks
            else:
                # Standalone question
                mark_rec = marks_map.get(q.id)
                is_att = mark_rec.is_attempted if mark_rec else False
                obt = mark_rec.marks_obtained if (mark_rec and is_att) else 0.0
                obt = max(0.0, min(q.max_marks, obt))

                if q.is_optional and not is_att:
                    continue

                if target_mod_id and target_mod_id in mod_stats:
                    mod_stats[target_mod_id]["available"] += q.max_marks
                    mod_stats[target_mod_id]["obtained"] += obt

    summaries: List[ModulePerformanceSummary] = []
    for m in modules:
        data = mod_stats[m.id]
        obt = round(data["obtained"], 1)
        avail = round(data["available"], 1)
        pct = round((obt / avail) * 100, 1) if avail > 0 else None
        status = classify_status(pct)

        summaries.append(
            ModulePerformanceSummary(
                id=m.id,
                module_number=m.module_number,
                co_code=m.co_code,
                title=m.title,
                description=m.description,
                marks_obtained=obt,
                marks_available=avail,
                percentage=pct,
                status=status
            )
        )

    # Sort by module_number
    summaries.sort(key=lambda x: x.module_number)
    return summaries

def find_extreme_modules(
    modules: List[ModulePerformanceSummary]
) -> Tuple[Optional[ModulePerformanceSummary], Optional[ModulePerformanceSummary]]:
    """
    Deterministically identifies (weakest_module, strongest_module).
    Handles ties deterministically by module_number.
    """
    valid = [m for m in modules if m.percentage is not None]
    if not valid:
        return None, None

    # Weakest: lowest percentage, tie-break by lower module_number
    weakest = min(valid, key=lambda m: (m.percentage, m.module_number))

    # Strongest: highest percentage, tie-break by lower module_number
    strongest = max(valid, key=lambda m: (m.percentage, -m.module_number))

    return weakest, strongest

# -------------------------------------------------------------------------
# Core Analytics Service Functions
# -------------------------------------------------------------------------

async def get_student_subjects_analytics(
    session: AsyncSession,
    student_id: int,
    semester: Optional[int] = None,
    performance_status: Optional[str] = None
) -> List[StudentSubjectSummary]:
    """
    Retrieves all subjects enrolled by the student with computed marks,
    percentages, performance status, strongest module, and weakest module.
    """
    # 1. Fetch Student Enrollments
    query = (
        select(StudentEnrollment)
        .where(StudentEnrollment.student_id == student_id)
        .options(
            selectinload(StudentEnrollment.subject)
            .selectinload(Subject.modules),
            selectinload(StudentEnrollment.subject)
            .selectinload(Subject.assessments)
            .selectinload(Assessment.questions)
        )
    )
    if semester:
        query = query.where(StudentEnrollment.semester == semester)

    result = await session.execute(query)
    enrollments = result.scalars().all()

    # 2. Fetch all marks for this student
    marks_res = await session.execute(
        select(StudentQuestionMark).where(StudentQuestionMark.student_id == student_id)
    )
    student_marks = marks_res.scalars().all()
    marks_map = {m.question_id: m for m in student_marks}

    summaries: List[StudentSubjectSummary] = []

    for enr in enrollments:
        subj = enr.subject
        if not subj:
            continue

        # Compute subject module performances
        all_questions: List[AssessmentQuestion] = []
        for ass in subj.assessments:
            all_questions.extend(ass.questions)

        module_summaries = calculate_modules_performance(subj.modules, all_questions, marks_map)
        weakest, strongest = find_extreme_modules(module_summaries)

        # Compute total subject marks across assessments
        subj_obtained = 0.0
        subj_available = 0.0
        for ass in subj.assessments:
            ass_obt, ass_avail, _ = calculate_assessment_scores(ass.questions, marks_map)
            subj_obtained += ass_obt
            subj_available += ass_avail

        subj_obtained = round(subj_obtained, 1)
        subj_available = round(subj_available, 1)
        subj_pct = round((subj_obtained / subj_available) * 100, 1) if subj_available > 0 else None
        status = classify_status(subj_pct)

        # Apply optional performance status filter
        if performance_status and performance_status.lower() != "all":
            if status.lower() != performance_status.lower():
                continue

        summaries.append(
            StudentSubjectSummary(
                id=subj.id,
                code=subj.code,
                name=subj.name,
                department=subj.department,
                semester=subj.semester,
                credits=subj.credits,
                total_marks_obtained=subj_obtained,
                total_marks_available=subj_available,
                percentage=subj_pct,
                status=status,
                strongest_module=strongest,
                weakest_module=weakest
            )
        )

    # Sort deterministically by subject code
    summaries.sort(key=lambda s: s.code)
    return summaries

async def get_student_subject_detail(
    session: AsyncSession,
    student_id: int,
    subject_id: int
) -> Optional[SubjectMarksDetailResponse]:
    """
    Returns full detailed performance breakdown for a single enrolled subject:
    assessments list with question details, module/CO analysis, weakest & strongest modules.
    """
    # 1. Verify enrollment
    enr_res = await session.execute(
        select(StudentEnrollment).where(
            and_(
                StudentEnrollment.student_id == student_id,
                StudentEnrollment.subject_id == subject_id
            )
        )
    )
    if not enr_res.scalar_one_or_none():
        return None

    # 2. Fetch Subject with modules and assessments
    subj_res = await session.execute(
        select(Subject)
        .where(Subject.id == subject_id)
        .options(
            selectinload(Subject.modules),
            selectinload(Subject.assessments)
            .selectinload(Assessment.questions)
        )
    )
    subj = subj_res.scalar_one_or_none()
    if not subj:
        return None

    # 3. Fetch marks
    all_q_ids = [q.id for ass in subj.assessments for q in ass.questions]
    marks_res = await session.execute(
        select(StudentQuestionMark).where(
            and_(
                StudentQuestionMark.student_id == student_id,
                StudentQuestionMark.question_id.in_(all_q_ids)
            )
        )
    )
    student_marks = marks_res.scalars().all()
    marks_map = {m.question_id: m for m in student_marks}

    # 4. Compute Assessment Details
    assessment_details: List[AssessmentPerformanceDetail] = []
    total_obtained = 0.0
    total_available = 0.0

    # Ensure consistent order of assessments (CA1, CA2, CA3, Midterm, Endterm)
    cat_order = {"CA1": 1, "CA2": 2, "CA3": 3, "Midterm": 4, "Endterm": 5}
    sorted_assessments = sorted(
        subj.assessments,
        key=lambda a: cat_order.get(a.category, 99)
    )

    for ass in sorted_assessments:
        obt, avail, q_responses = calculate_assessment_scores(ass.questions, marks_map)
        total_obtained += obt
        total_available += avail
        ass_pct = round((obt / avail) * 100, 1) if avail > 0 else None

        assessment_details.append(
            AssessmentPerformanceDetail(
                id=ass.id,
                category=ass.category,
                name=ass.name,
                max_marks=ass.max_marks,
                weightage_pct=ass.weightage_pct,
                assessment_date=ass.assessment_date,
                marks_obtained=obt,
                marks_available=avail,
                percentage=ass_pct,
                questions=q_responses
            )
        )

    # 5. Compute Module Breakdown
    all_questions = [q for ass in subj.assessments for q in ass.questions]
    module_summaries = calculate_modules_performance(subj.modules, all_questions, marks_map)
    weakest, strongest = find_extreme_modules(module_summaries)

    total_obtained = round(total_obtained, 1)
    total_available = round(total_available, 1)
    overall_pct = round((total_obtained / total_available) * 100, 1) if total_available > 0 else None
    overall_status = classify_status(overall_pct)

    subject_response = SubjectResponse(
        id=subj.id,
        code=subj.code,
        name=subj.name,
        department=subj.department,
        semester=subj.semester,
        credits=subj.credits,
        modules=[
            SubjectModuleResponse(
                id=m.id,
                module_number=m.module_number,
                co_code=m.co_code,
                title=m.title,
                description=m.description
            )
            for m in sorted(subj.modules, key=lambda x: x.module_number)
        ]
    )

    return SubjectMarksDetailResponse(
        subject=subject_response,
        total_marks_obtained=total_obtained,
        total_marks_available=total_available,
        percentage=overall_pct,
        status=overall_status,
        assessments=assessment_details,
        modules=module_summaries,
        strongest_module=strongest,
        weakest_module=weakest
    )

async def get_student_subject_modules_analysis(
    session: AsyncSession,
    student_id: int,
    subject_id: int
) -> Optional[SubjectModulesAnalysisResponse]:
    """
    Returns the CO/Module analysis specifically for a subject, with weakest and strongest modules.
    """
    detail = await get_student_subject_detail(session, student_id, subject_id)
    if not detail:
        return None

    return SubjectModulesAnalysisResponse(
        subject_id=detail.subject.id,
        subject_code=detail.subject.code,
        subject_name=detail.subject.name,
        modules=detail.modules,
        strongest_module=detail.strongest_module,
        weakest_module=detail.weakest_module
    )

async def get_student_marks_overview(
    session: AsyncSession,
    student_id: int,
    semester: Optional[int] = None,
    performance_status: Optional[str] = None
) -> Optional[StudentMarksOverviewResponse]:
    """
    Returns full student academic overview across all subjects.
    """
    # 1. Fetch Student profile & User
    from app.core.database import User
    student = (await session.execute(select(Student).where(Student.id == student_id))).scalar_one_or_none()
    if not student:
        return None

    user = (await session.execute(select(User).where(User.id == student.user_id))).scalar_one_or_none()
    student_name = user.name if user else "Student"

    # 2. Fetch subject summaries
    subjects = await get_student_subjects_analytics(
        session=session,
        student_id=student_id,
        semester=semester,
        performance_status=performance_status
    )

    total_obt = sum(s.total_marks_obtained for s in subjects)
    total_avail = sum(s.total_marks_available for s in subjects)
    total_credits = sum(s.credits for s in subjects)
    overall_pct = round((total_obt / total_avail) * 100, 1) if total_avail > 0 else None

    return StudentMarksOverviewResponse(
        student_id=student.id,
        student_name=student_name,
        roll_number=student.roll_number,
        semester=student.semester,
        overall_percentage=overall_pct,
        total_credits=total_credits,
        subjects=subjects
    )

async def get_module_learning_materials(
    session: AsyncSession,
    module_id: int
) -> Optional[ModuleLearningMaterialResponse]:
    """
    Returns learning materials, pages, topic chunks, and cached micro-lessons for a module.
    """
    # 1. Fetch Module and Subject
    mod_res = await session.execute(
        select(SubjectModule)
        .where(SubjectModule.id == module_id)
        .options(selectinload(SubjectModule.subject))
    )
    module = mod_res.scalar_one_or_none()
    if not module:
        return None

    subj = module.subject

    # 2. Fetch Learning Materials with pages
    mat_res = await session.execute(
        select(LearningMaterial)
        .where(
            and_(
                LearningMaterial.subject_id == subj.id,
                LearningMaterial.module_id == module.id
            )
        )
        .options(selectinload(LearningMaterial.pages))
    )
    materials = mat_res.scalars().all()

    # 3. Count total chunks
    chunk_res = await session.execute(
        select(MaterialChunk).where(MaterialChunk.module_id == module.id)
    )
    chunks = chunk_res.scalars().all()

    # 4. Fetch MicroLessons
    ml_res = await session.execute(
        select(MicroLesson).where(
            and_(
                MicroLesson.subject_id == subj.id,
                MicroLesson.module_id == module.id
            )
        )
    )
    micro_lessons = ml_res.scalars().all()

    materials_out: List[LearningMaterialResponse] = []
    for mat in materials:
        pages_out = [
            MaterialPageResponse(
                id=p.id,
                page_number=p.page_number,
                page_title=p.page_title,
                content_text=p.content_text,
                structured_json=p.structured_json
            )
            for p in sorted(mat.pages, key=lambda x: x.page_number)
        ]
        materials_out.append(
            LearningMaterialResponse(
                id=mat.id,
                subject_id=subj.id,
                subject_code=subj.code,
                subject_name=subj.name,
                module_id=module.id,
                co_code=module.co_code,
                title=mat.title,
                source_reference=mat.source_reference,
                total_pages=mat.total_pages,
                pages=pages_out
            )
        )

    import json
    mls_out: List[MicroLessonResponse] = []
    for ml in micro_lessons:
        scenes_data = json.loads(ml.scenes_json) if ml.scenes_json else []
        mls_out.append(
            MicroLessonResponse(
                id=ml.id,
                subject_id=subj.id,
                subject_code=subj.code,
                subject_name=subj.name,
                module_id=module.id,
                co_code=ml.co_code,
                topic_key=ml.topic_key,
                title=ml.title,
                duration_seconds=ml.duration_seconds,
                scenes=scenes_data
            )
        )

    return ModuleLearningMaterialResponse(
        module_id=module.id,
        module_number=module.module_number,
        co_code=module.co_code,
        module_title=module.title,
        subject_id=subj.id,
        subject_code=subj.code,
        subject_name=subj.name,
        materials=materials_out,
        total_chunks=len(chunks),
        micro_lessons=mls_out
    )
