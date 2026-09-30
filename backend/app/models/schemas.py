from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field

# --- User & Security Schemas ---

class UserSecurityClaims(BaseModel):
    user_id: int
    public_id: Optional[str] = "USR-000"
    role: Literal["student", "faculty", "parent", "admin"]
    email: str
    name: Optional[str] = "Campus Member"
    department: Optional[str] = None
    student_id: Optional[int] = None
    ward_id: Optional[int] = None
    bus_id: Optional[int] = None
    faculty_id: Optional[int] = None
    is_hod: bool = False

class LoginRequest(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    public_id: str
    name: str
    email: str
    role: Literal["student", "faculty", "parent", "admin"]
    department: Optional[str] = None
    student_id: Optional[int] = None
    ward_id: Optional[int] = None
    bus_id: Optional[int] = None
    faculty_id: Optional[int] = None
    is_hod: bool = False

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# --- Chat & Agent Execution Schemas ---

class AgentMessage(BaseModel):
    sender: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Citation(BaseModel):
    title: str
    section: Optional[str] = None
    type: Literal["policy_doc", "sql_record", "telemetry"]
    detail: Optional[str] = None

class ChatRequest(BaseModel):
    message: Optional[str] = None
    query: Optional[str] = None
    conversation_history: List[AgentMessage] = Field(default_factory=list)

class ChatResponse(BaseModel):
    reply: str
    sources: List[Citation] = Field(default_factory=list)
    classified_intent: Optional[str] = None
    access_denied: bool = False
    audit_flag: Optional[str] = None

class ERPGraphState(BaseModel):
    # Immutable session context (Read-Only to worker agents)
    claims: UserSecurityClaims
    
    # Input & conversation memory
    raw_query: str
    conversation_history: List[AgentMessage] = Field(default_factory=list)
    
    # Intermediate routing and worker execution state
    classified_intent: Optional[str] = None
    target_agents: List[str] = Field(default_factory=list)
    retrieved_structured_data: Optional[Dict[str, Any]] = None
    retrieved_unstructured_context: List[Dict[str, Any]] = Field(default_factory=list)
    transit_telemetry_data: Optional[Dict[str, Any]] = None
    
    # Final output synthesis
    egress_passed: bool = False
    access_denied: bool = False
    final_response: Optional[str] = None
    citations: List[Citation] = Field(default_factory=list)
    audit_event: Optional[str] = None

# --- ERP Data Schemas ---

class AttendanceRecord(BaseModel):
    id: int
    subject: str
    attended_classes: int
    total_classes: int
    attendance_pct: float

class BusStop(BaseModel):
    name: str
    lat: float
    lng: float
    sequence: int
    eta_minutes: Optional[int] = None

class BusDetails(BaseModel):
    id: int
    bus_number: str
    route_name: str
    driver_name: str
    driver_phone: str
    current_lat: Optional[float] = None
    current_lng: Optional[float] = None
    speed_kmh: float = 0.0
    status: str = "Active"
    driver_connected: bool = False
    last_updated: Optional[str] = None
    stops: List[BusStop] = Field(default_factory=list)
    waypoints: List[List[float]] = Field(default_factory=list)

class BusTelemetryUpdate(BaseModel):
    bus_id: int
    bus_number: str
    lat: float
    lng: float
    speed_kmh: float
    status: str = "Active"
    timestamp: str
    next_stop: Optional[str] = None
    next_stop_eta_mins: Optional[int] = None
    distance_to_stop_km: Optional[float] = None
    geofence_active: bool = False
    geofence_radius_meters: int = 500
    registered_stop_name: Optional[str] = None
    distance_to_registered_stop_m: Optional[int] = None

# --- Academic Support & Learning Management Schemas ---

class SubjectModuleResponse(BaseModel):
    id: int
    module_number: int
    co_code: str
    title: str
    description: Optional[str] = None

class SubjectResponse(BaseModel):
    id: int
    code: str
    name: str
    department: str
    semester: int
    credits: int
    modules: List[SubjectModuleResponse] = Field(default_factory=list)

class AssessmentQuestionResponse(BaseModel):
    id: int
    question_label: str
    co_code: str
    module_id: Optional[int] = None
    max_marks: float
    is_optional: bool = False
    or_group_id: Optional[str] = None

class AssessmentResponse(BaseModel):
    id: int
    subject_id: int
    category: str
    name: str
    max_marks: float
    weightage_pct: float
    assessment_date: Optional[str] = None
    questions: List[AssessmentQuestionResponse] = Field(default_factory=list)

class StudentQuestionMarkResponse(BaseModel):
    id: int
    question_id: int
    question_label: str
    co_code: str
    max_marks: float
    marks_obtained: float
    is_attempted: bool
    or_group_id: Optional[str] = None
    feedback: Optional[str] = None

class ModulePerformanceSummary(BaseModel):
    id: int
    module_number: int
    co_code: str
    title: str
    description: Optional[str] = None
    marks_obtained: float
    marks_available: float
    percentage: Optional[float] = None
    status: Literal["Strong", "Developing", "Needs Support", "No Data"]

class StudentSubjectSummary(BaseModel):
    id: int
    code: str
    name: str
    department: str
    semester: int
    credits: int
    total_marks_obtained: float
    total_marks_available: float
    percentage: Optional[float] = None
    status: Literal["Strong", "Developing", "Needs Support", "No Data"]
    strongest_module: Optional[ModulePerformanceSummary] = None
    weakest_module: Optional[ModulePerformanceSummary] = None

class AssessmentPerformanceDetail(BaseModel):
    id: int
    category: str
    name: str
    max_marks: float
    weightage_pct: float
    assessment_date: Optional[str] = None
    marks_obtained: float
    marks_available: float
    percentage: Optional[float] = None
    questions: List[StudentQuestionMarkResponse] = Field(default_factory=list)

class SubjectMarksDetailResponse(BaseModel):
    subject: SubjectResponse
    total_marks_obtained: float
    total_marks_available: float
    percentage: Optional[float] = None
    status: Literal["Strong", "Developing", "Needs Support", "No Data"]
    assessments: List[AssessmentPerformanceDetail] = Field(default_factory=list)
    modules: List[ModulePerformanceSummary] = Field(default_factory=list)
    strongest_module: Optional[ModulePerformanceSummary] = None
    weakest_module: Optional[ModulePerformanceSummary] = None

class SubjectModulesAnalysisResponse(BaseModel):
    subject_id: int
    subject_code: str
    subject_name: str
    modules: List[ModulePerformanceSummary] = Field(default_factory=list)
    strongest_module: Optional[ModulePerformanceSummary] = None
    weakest_module: Optional[ModulePerformanceSummary] = None

class StudentMarksOverviewResponse(BaseModel):
    student_id: int
    student_name: str
    roll_number: str
    semester: int
    overall_percentage: Optional[float] = None
    total_credits: int
    subjects: List[StudentSubjectSummary] = Field(default_factory=list)

class AssessmentBreakdownItem(BaseModel):
    assessment_id: int
    assessment_category: str
    assessment_name: str
    weightage_pct: float
    max_marks: float
    marks_obtained: float
    percentage: float
    questions: List[StudentQuestionMarkResponse] = Field(default_factory=list)

class COPerformanceResponse(BaseModel):
    co_code: str
    module_title: str
    total_max_marks: float
    total_marks_obtained: float
    percentage: float
    status: Literal["Strong", "Moderate", "Weak", "Developing", "Needs Support", "No Data"]
    assessment_breakdown: List[Dict[str, Any]] = Field(default_factory=list)

class SubjectPerformanceResponse(BaseModel):
    subject_id: int
    subject_code: str
    subject_name: str
    overall_percentage: float
    co_breakdown: List[COPerformanceResponse] = Field(default_factory=list)
    weak_areas: List[str] = Field(default_factory=list)

class MaterialPageResponse(BaseModel):
    id: int
    page_number: int
    page_title: str
    content_text: str
    structured_json: Optional[str] = None

class MaterialChunkResponse(BaseModel):
    id: int
    material_id: int
    page_id: Optional[int] = None
    page_number: Optional[int] = None
    topic_name: str
    co_code: Optional[str] = None
    chunk_index: int
    chunk_text: str
    similarity: Optional[float] = None

class LearningMaterialResponse(BaseModel):
    id: int
    subject_id: int
    subject_code: Optional[str] = None
    subject_name: Optional[str] = None
    module_id: Optional[int] = None
    co_code: Optional[str] = None
    title: str
    source_reference: Optional[str] = None
    total_pages: int
    pages: List[MaterialPageResponse] = Field(default_factory=list)

class YouTubeResource(BaseModel):
    video_id: Optional[str] = None
    title: str
    channel: Optional[str] = "YouTube Academic"
    start_seconds: Optional[int] = 0
    end_seconds: Optional[int] = None
    description: Optional[str] = None
    search_url: Optional[str] = None
    search_query: Optional[str] = None
    is_embeddable: bool = True

class MicroLessonSceneResponse(BaseModel):
    scene_id: int
    title: str
    duration_seconds: int
    narration: Optional[str] = None
    visual_type: Optional[str] = "diagram"
    visual_data: Dict[str, Any] = Field(default_factory=dict)
    key_takeaway: Optional[str] = None
    body: Optional[str] = None

class MicroLessonResponse(BaseModel):
    id: int
    subject_id: int
    subject_code: Optional[str] = None
    subject_name: Optional[str] = None
    module_id: Optional[int] = None
    co_code: Optional[str] = None
    topic_key: str
    title: str
    duration_seconds: int
    scenes: List[Dict[str, Any]] = Field(default_factory=list)
    video_url: Optional[str] = None
    video_status: Optional[str] = "none" # "ready", "rendering", "queued", "none"
    youtube_resource: Optional[YouTubeResource] = None

class ModuleLearningMaterialResponse(BaseModel):
    module_id: int
    module_number: int
    co_code: str
    module_title: str
    subject_id: int
    subject_code: str
    subject_name: str
    materials: List[LearningMaterialResponse] = Field(default_factory=list)
    total_chunks: int = 0
    micro_lessons: List[MicroLessonResponse] = Field(default_factory=list)

class ConceptExplanationRequest(BaseModel):
    topic: str
    subject_code: Optional[str] = None
    user_question: Optional[str] = None

class ConceptExplanationResponse(BaseModel):
    topic: str
    title: str
    explanation: str
    analogies: List[str] = Field(default_factory=list)
    key_takeaways: List[str] = Field(default_factory=list)
    diagram_ascii: Optional[str] = None
    references: List[Citation] = Field(default_factory=list)
    recommended_micro_lesson_id: Optional[int] = None

# --- Academic RAG & Micro-Lesson Explanation Schemas ---

class AcademicExplainRequest(BaseModel):
    material_id: Optional[int] = None
    page_number: Optional[int] = None
    selected_text: str
    subject_id: Optional[int] = None
    module_id: Optional[int] = None
    co_code: Optional[str] = None
    topic: Optional[str] = None

class AcademicSourceCitation(BaseModel):
    material_id: int
    title: str
    page_number: int
    topic: str
    co_code: Optional[str] = None
    subject_code: Optional[str] = None

class GenerationMetadata(BaseModel):
    mode: Literal["cache", "live", "fallback"]
    model: str = "deterministic-academic-rag"
    cached: bool = True
    latency_ms: Optional[float] = None

class MicroLessonPayload(BaseModel):
    id: Optional[int] = None
    subject_id: Optional[int] = None
    subject_code: Optional[str] = None
    subject_name: Optional[str] = None
    module_id: Optional[int] = None
    co_code: Optional[str] = None
    topic_key: Optional[str] = None
    title: str
    topic: str
    difficulty: str = "Intermediate"
    duration_seconds: int = 45
    objective: str
    scenes: List[Dict[str, Any]] = Field(default_factory=list)
    sources: List[AcademicSourceCitation] = Field(default_factory=list)
    video_url: Optional[str] = None
    video_status: Optional[str] = "none" # "ready", "rendering", "queued", "none"
    youtube_resource: Optional[YouTubeResource] = None

class AcademicExplainResponse(BaseModel):
    status: Literal["success", "insufficient_context", "error"]
    lesson: MicroLessonPayload
    source_context: Dict[str, Any] = Field(default_factory=dict)
    generation: GenerationMetadata

# --- Video Generation & Job Schemas ---

class VideoGenerationRequest(BaseModel):
    lesson_id: Optional[int] = None
    topic_key: Optional[str] = None
    subject_id: Optional[int] = None
    module_id: Optional[int] = None
    topic: Optional[str] = None
    co_code: Optional[str] = None
    lesson_payload: Optional[Dict[str, Any]] = None

class VideoJobResponse(BaseModel):
    job_id: str
    lesson_id: Optional[int] = None
    topic_key: str
    status: Literal["queued", "rendering", "audio_generating", "video_rendering", "completed", "failed", "ready"]
    progress_pct: Optional[int] = 0
    video_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    error_message: Optional[str] = None
    retryable: bool = True

# --- Event-Exam Clash & Retake Rescheduling Schemas ---

class EventCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    start_at: str # ISO-8601 with Z
    end_at: str   # ISO-8601 with Z

class EventParticipantResponse(BaseModel):
    student_id: int
    name: str
    roll_number: str
    department: str
    section: str
    semester: int

class EventResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    start_at: str
    end_at: str
    created_by: int
    created_at: str
    participant_count: int = 0
    participants_count: int = 0
    clash_count: int = 0
    clashes_count: int = 0

class AddParticipantsRequest(BaseModel):
    student_ids: List[int] = Field(..., min_length=1)

class AssessmentResponse(BaseModel):
    id: int
    offering_id: int
    course_code: str
    subject: str
    section: str
    kind: str
    start_at: str
    end_at: str
    venue: Optional[str] = None
    faculty_id: Optional[int] = None
    faculty_name: Optional[str] = None

class CaseTimelineResponse(BaseModel):
    id: int
    case_id: int
    actor_user_id: Optional[int] = None
    actor_role: str
    from_status: Optional[str] = None
    to_status: str
    note: Optional[str] = None
    at: str

class ClashCaseResponse(BaseModel):
    id: int
    event_id: int
    event_title: str
    student_id: int
    student_name: str
    student_roll: str
    student_section: str = ""
    student_department: str = ""
    assessment_id: int
    course_code: str
    subject: str
    offering_section: str = ""
    assessment_kind: str
    assessment_start_at: str = ""
    assessment_end_at: str = ""
    assessment_start: Optional[str] = None
    assessment_end: Optional[str] = None
    faculty_id: Optional[int] = None
    faculty_name: Optional[str] = None
    status: str
    suggested_retake_assessment_id: Optional[int] = None
    suggested_retake_info: Optional[str] = None
    retake_assessment_id: Optional[int] = None
    retake_info: Optional[str] = None
    retake_at: Optional[str] = None
    retake_note: Optional[str] = None
    rejection_reason: Optional[str] = None
    filed_by: Optional[int] = None
    filed_at: Optional[str] = None
    decided_by: Optional[int] = None
    decided_at: Optional[str] = None
    created_at: str
    updated_at: str
    is_stuck: bool = False
    timeline: List[CaseTimelineResponse] = Field(default_factory=list)

class EventDetailResponse(EventResponse):
    clashes: List["ClashCaseResponse"] = Field(default_factory=list)

class ClashCaseDetailResponse(ClashCaseResponse):
    pass

class FileCasesRequest(BaseModel):
    case_ids: List[int] = Field(..., min_length=1)

CaseFileBulkRequest = FileCasesRequest

class DecisionRequest(BaseModel):
    case_ids: List[int] = Field(..., min_length=1)
    decision: str
    slot_id: Optional[int] = None
    retake_assessment_id: Optional[int] = None
    custom_at: Optional[str] = None
    retake_at: Optional[str] = None
    note: Optional[str] = None
    retake_note: Optional[str] = None
    rejection_reason: Optional[str] = None

CaseDecisionBulkRequest = DecisionRequest

class AcceptCounterRequest(BaseModel):
    note: Optional[str] = None

class SendBackRequest(BaseModel):
    note: str = Field(..., min_length=2)

CounterActionRequest = SendBackRequest

class OverrideRequest(BaseModel):
    slot_id: Optional[int] = None
    retake_assessment_id: Optional[int] = None
    custom_at: Optional[str] = None
    retake_at: Optional[str] = None
    note: str = Field(..., min_length=2)

HODOverrideRequest = OverrideRequest

class CompleteCaseRequest(BaseModel):
    note: Optional[str] = None

class HODOverviewResponse(BaseModel):
    department: Optional[str] = None
    total_cases: int = 0
    by_status: Dict[str, int] = Field(default_factory=dict)
    counts_by_status: Dict[str, int] = Field(default_factory=dict)
    escalated_cases: List[ClashCaseResponse] = Field(default_factory=list)
    stuck_cases: List[ClashCaseResponse] = Field(default_factory=list)
    per_professor_pending: Dict[str, int] = Field(default_factory=dict)
    pending_per_professor: Dict[str, int] = Field(default_factory=dict)

class NotificationResponse(BaseModel):
    id: int
    user_id: int
    type: str
    title: str
    body: str
    case_id: Optional[int] = None
    event_id: Optional[int] = None
    is_read: bool = False
    created_at: str

class CourseOfferingResponse(BaseModel):
    id: int
    course_code: str
    subject: str
    section: str
    semester: int
    department: str
    faculty_id: int
    faculty_name: Optional[str] = None
