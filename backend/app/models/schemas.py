from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field

# --- User & Security Schemas ---

class UserSecurityClaims(BaseModel):
    user_id: int
    public_id: str
    role: Literal["student", "faculty", "parent", "admin"]
    email: str
    name: str
    department: Optional[str] = None
    student_id: Optional[int] = None
    ward_id: Optional[int] = None
    bus_id: Optional[int] = None

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
    message: str
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
    current_lat: float
    current_lng: float
    speed_kmh: float = 0.0
    status: str = "Active"
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

class MicroLessonSceneResponse(BaseModel):
    scene_id: int
    title: str
    duration_seconds: int
    narration: str
    visual_type: Literal["diagram", "flowchart", "code", "table", "step_by_step"]
    visual_data: Dict[str, Any] = Field(default_factory=dict)
    key_takeaway: str

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
    title: str
    topic: str
    topic_key: Optional[str] = None
    difficulty: str = "Intermediate"
    duration_seconds: int = 45
    objective: str
    scenes: List[Dict[str, Any]] = Field(default_factory=list)
    sources: List[AcademicSourceCitation] = Field(default_factory=list)

class AcademicExplainResponse(BaseModel):
    status: Literal["success", "insufficient_context", "error"]
    lesson: MicroLessonPayload
    source_context: Dict[str, Any] = Field(default_factory=dict)
    generation: GenerationMetadata




