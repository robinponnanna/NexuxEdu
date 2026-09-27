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

