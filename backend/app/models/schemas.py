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
    clash_count: int = 0

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
    student_section: str
    student_department: str
    assessment_id: int
    course_code: str
    subject: str
    offering_section: str
    assessment_kind: str
    assessment_start_at: str
    assessment_end_at: str
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

class FileCasesRequest(BaseModel):
    case_ids: List[int] = Field(..., min_length=1)

class DecisionRequest(BaseModel):
    case_ids: List[int] = Field(..., min_length=1)
    decision: Literal["approve", "counter", "reject"]
    retake_assessment_id: Optional[int] = None
    retake_at: Optional[str] = None
    retake_note: Optional[str] = None
    rejection_reason: Optional[str] = None

class AcceptCounterRequest(BaseModel):
    note: Optional[str] = None

class SendBackRequest(BaseModel):
    note: str = Field(..., min_length=2)

class OverrideRequest(BaseModel):
    retake_assessment_id: Optional[int] = None
    retake_at: Optional[str] = None
    note: str = Field(..., min_length=2)

class CompleteCaseRequest(BaseModel):
    note: Optional[str] = None

class HODOverviewResponse(BaseModel):
    total_cases: int
    by_status: Dict[str, int]
    escalated_cases: List[ClashCaseResponse]
    stuck_cases: List[ClashCaseResponse]
    pending_per_professor: Dict[str, int]

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


