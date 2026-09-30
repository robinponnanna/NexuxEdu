export interface UserProfile {
  id: number;
  public_id: string;
  name: string;
  email: string;
  role: "student" | "faculty" | "parent" | "admin";
  department?: string;
  student_id?: number;
  ward_id?: number;
  bus_id?: number;
}

export interface AuthSession {
  token: string;
  user: UserProfile;
}

export interface Citation {
  title: string;
  section?: string;
  type: "policy_doc" | "sql_record" | "telemetry";
  detail?: string;
}

export interface ChatResponse {
  reply: string;
  sources: Citation[];
  classified_intent?: string;
  access_denied: boolean;
  audit_flag?: string;
}

export interface BusStop {
  name: string;
  lat: number;
  lng: number;
  sequence: number;
  eta_minutes?: number;
}

export interface BusDetails {
  id: number;
  bus_number: string;
  route_name: string;
  driver_name: string;
  driver_phone: string;
  current_lat?: number;
  current_lng?: number;
  speed_kmh?: number;
  status?: string;
  driver_connected?: boolean;
  last_updated?: string;
  stops?: BusStop[];
  waypoints?: [number, number][];
}

// Dynamically resolves API Base URL (proxied through Next.js /api/v1 or direct to port 8000)
export function getApiBase(): string {
  if (typeof window !== "undefined") {
    return "/api/v1";
  }
  return process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";
}

export async function login(email: string, password = "password123"): Promise<AuthSession> {
  const apiBase = getApiBase();
  const res = await fetch(`${apiBase}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Authentication failed (${res.status})`);
  }
  const data = await res.json();
  return {
    token: data.access_token,
    user: data.user,
  };
}

export async function getDashboard(token: string) {
  const apiBase = getApiBase();
  const res = await fetch(`${apiBase}/erp/dashboard`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to fetch dashboard");
  return res.json();
}

export async function sendChatMessage(token: string, message: string, history: any[] = []): Promise<ChatResponse> {
  const apiBase = getApiBase();
  const res = await fetch(`${apiBase}/chat/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ message, conversation_history: history }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Chat query failed");
  }
  return res.json();
}

export async function getBuses(token: string): Promise<BusDetails[]> {
  const apiBase = getApiBase();
  const res = await fetch(`${apiBase}/transit/buses`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to fetch buses");
  return res.json();
}

export async function getBusById(token: string, busId: number): Promise<BusDetails> {
  const apiBase = getApiBase();
  const res = await fetch(`${apiBase}/transit/buses/${busId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to fetch bus details");
  return res.json();
}

export async function getAuditLogs(token: string) {
  const apiBase = getApiBase();
  const res = await fetch(`${apiBase}/erp/audit-logs`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to fetch audit logs");
  return res.json();
}

export function getTransitWebSocketUrl(busId: number, token: string) {
  if (typeof window !== "undefined") {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    let hostPart = window.location.host;
    if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
      hostPart = `${window.location.hostname}:8000`;
    }
    return `${proto}//${hostPart}/ws/transit/${busId}?token=${encodeURIComponent(token)}`;
  }
  return `ws://127.0.0.1:8000/ws/transit/${busId}?token=${encodeURIComponent(token)}`;
}

export function getUnifiedWebSocketUrl(token: string): string {
  if (typeof window !== "undefined") {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    let hostPart = window.location.host;
    if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
      hostPart = `${window.location.hostname}:8000`;
    }
    return `${proto}//${hostPart}/ws?token=${encodeURIComponent(token)}`;
  }
  return `ws://127.0.0.1:8000/ws?token=${encodeURIComponent(token)}`;
}

export interface CreateTrackingSessionResponse {
  token: string;
  trackingUrl: string;
  publicUrl?: string;
  lanUrl?: string;
  localUrl?: string;
  expiresAt: string;
  busId: number;
  busNumber?: string;
  routeName?: string;
}

export async function createTrackingSession(
  token: string,
  busId: number,
  ttlMinutes: number = 1440
): Promise<CreateTrackingSessionResponse> {
  const apiBase = getApiBase();
  const res = await fetch(`${apiBase}/tracking/sessions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ busId, ttlMinutes }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to create tracking session link");
  }
  return res.json();
}

export async function getUserAssignedBuses(token: string): Promise<{ role: string; busIds: number[] }> {
  const apiBase = getApiBase();
  const res = await fetch(`${apiBase}/tracking/user-assigned-buses`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to fetch assigned buses");
  return res.json();
}

export interface FacultyStudentAttendance {
  student_id: number;
  roll_number: string;
  name: string;
  email: string;
  section: string;
  semester: number;
  subject: string;
  attended_classes: number;
  total_classes: number;
  attendance_pct: number;
  status: "Safe" | "Attention" | "Debarment Risk";
}

export interface FacultyAttendanceRosterResponse {
  department: string;
  selected_subject: string;
  selected_section: string;
  classes: { code: string; name: string }[];
  sections: string[];
  summary: {
    total_students: number;
    class_avg_pct: number;
    safe_count: number;
    attention_count: number;
    debarment_risk_count: number;
  };
  students: FacultyStudentAttendance[];
}

export async function getFacultyClassAttendance(
  token: string,
  subject?: string,
  section?: string
): Promise<FacultyAttendanceRosterResponse> {
  const apiBase = getApiBase();
  const params = new URLSearchParams();
  if (subject) params.append("subject", subject);
  if (section && section !== "All Sections") params.append("section", section);

  const queryStr = params.toString() ? `?${params.toString()}` : "";
  const res = await fetch(`${apiBase}/erp/faculty/class-attendance${queryStr}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to fetch faculty class attendance roster");
  return res.json();
}

// ============================================================
// STUDENT ACADEMIC SUPPORT TYPES & CLIENT METHODS
// ============================================================

export interface ExtremeModuleInfo {
  id: number;
  module_number: number;
  co_code: string;
  title: string;
  marks_obtained: number;
  marks_available: number;
  percentage: number;
  status: "Strong" | "Developing" | "Needs Support" | "No Data";
}

export interface StudentSubjectSummary {
  id: number;
  code: string;
  name: string;
  department: string;
  semester: number;
  credits: number;
  total_marks_obtained: number;
  total_marks_available: number;
  percentage: number;
  status: "Strong" | "Developing" | "Needs Support" | "No Data";
  strongest_module?: ExtremeModuleInfo | null;
  weakest_module?: ExtremeModuleInfo | null;
}

export interface StudentMarksOverviewResponse {
  student_id: number;
  student_name: string;
  roll_number: string;
  semester: number;
  overall_percentage: number;
  total_credits: number;
  subjects: StudentSubjectSummary[];
}

export interface QuestionMarkDetail {
  id?: number;
  question_id: number;
  question_label: string;
  co_code: string;
  max_marks: number;
  marks_obtained: number;
  is_attempted: boolean;
  or_group_id?: string | null;
  feedback?: string | null;
}

export interface SubjectAssessmentDetail {
  id: number;
  category: "CA1" | "CA2" | "CA3" | "Midterm" | "Endterm";
  name: string;
  max_marks: number;
  weightage_pct: number;
  assessment_date?: string | null;
  marks_obtained: number;
  marks_available: number;
  percentage: number;
  questions: QuestionMarkDetail[];
}

export interface SubjectModuleMarksDetail {
  id: number;
  module_number: number;
  co_code: string;
  title: string;
  description?: string | null;
  marks_obtained: number;
  marks_available: number;
  percentage: number;
  status: "Strong" | "Developing" | "Needs Support" | "No Data";
}

export interface SubjectMarksDetailResponse {
  subject: {
    id: number;
    code: string;
    name: string;
    department: string;
    semester: number;
    credits: number;
    modules: {
      id: number;
      module_number: number;
      co_code: string;
      title: string;
      description?: string | null;
    }[];
  };
  total_marks_obtained: number;
  total_marks_available: number;
  percentage: number;
  status: "Strong" | "Developing" | "Needs Support" | "No Data";
  assessments: SubjectAssessmentDetail[];
  modules: SubjectModuleMarksDetail[];
  strongest_module?: ExtremeModuleInfo | null;
  weakest_module?: ExtremeModuleInfo | null;
}

export interface SubjectModulesAnalysisResponse {
  subject_id: number;
  subject_code: string;
  subject_name: string;
  modules: SubjectModuleMarksDetail[];
  strongest_module?: ExtremeModuleInfo | null;
  weakest_module?: ExtremeModuleInfo | null;
}

export interface MaterialPageDetail {
  id: number;
  page_number: number;
  page_title: string;
  content_text: string;
  structured_json?: string | null;
}

export interface LearningMaterialDetail {
  id: number;
  subject_id: number;
  subject_code?: string | null;
  subject_name?: string | null;
  module_id?: number | null;
  co_code?: string | null;
  title: string;
  source_reference?: string | null;
  total_pages: number;
  pages: MaterialPageDetail[];
}

export interface AcademicSourceCitation {
  material_id: number;
  title: string;
  page_number: number;
  topic: string;
  co_code?: string | null;
  subject_code?: string | null;
}

export interface YouTubeResource {
  video_id?: string | null;
  title: string;
  channel?: string | null;
  start_seconds?: number | null;
  end_seconds?: number | null;
  description?: string | null;
  search_url?: string | null;
  search_query?: string | null;
  is_embeddable?: boolean;
}

export interface MicroLessonScene {
  scene_id: number;
  type?: "concept" | "diagram" | "example" | "comparison" | "flow" | "common_mistake" | "formula" | "takeaway";
  visual_type?: string;
  title: string;
  duration_seconds: number;
  narration?: string;
  body?: string;
  visual_data?: any;
  diagram?: {
    type?: string;
    nodes?: { id: string; label: string }[];
    edges?: { from: string; to: string; label?: string }[];
  };
  key_takeaway?: string;
}

export interface MicroLessonPayload {
  id?: number;
  subject_id?: number;
  subject_code?: string | null;
  subject_name?: string | null;
  module_id?: number | null;
  co_code?: string | null;
  topic_key?: string;
  title: string;
  topic?: string;
  difficulty?: string;
  duration_seconds: number;
  objective?: string;
  scenes: MicroLessonScene[];
  sources: AcademicSourceCitation[];
  video_url?: string | null;
  video_status?: VideoStatusType | null;
  youtube_resource?: YouTubeResource | null;
}

export interface ModuleLearningMaterialResponse {
  module_id: number;
  module_number: number;
  co_code: string;
  module_title: string;
  subject_id: number;
  subject_code: string;
  subject_name: string;
  materials: LearningMaterialDetail[];
  total_chunks: number;
  micro_lessons: MicroLessonPayload[];
}

export interface AcademicExplainRequest {
  selected_text: string;
  material_id?: number;
  module_id?: number;
  subject_id?: number;
  page_number?: number;
  co_code?: string;
  topic?: string;
}

export interface GenerationMetadata {
  mode: "cache" | "fallback" | "live";
  model: string;
  cached: boolean;
  latency_ms: number;
}

export interface AcademicExplainResponse {
  status: string;
  lesson: MicroLessonPayload;
  source_context?: {
    subject_code?: string;
    subject_name?: string;
    module_title?: string;
    co_code?: string;
    material_title?: string;
    page_number?: number;
    retrieved_chunks_count?: number;
  };
  generation: GenerationMetadata;
}

export type VideoStatusType =
  | "none"
  | "queued"
  | "rendering"
  | "audio_generating"
  | "video_rendering"
  | "completed"
  | "ready"
  | "failed";

export type FrontendVideoState =
  | "NO_VIDEO"
  | "QUEUED"
  | "GENERATING"
  | "READY"
  | "FAILED_RETRY";

export type FrontendYouTubeState =
  | "EMBEDDED_VIDEO"
  | "SEARCH_FALLBACK"
  | "UNAVAILABLE";

export interface VideoGenerationRequest {
  lesson_id?: number | null;
  topic_key?: string | null;
  subject_id?: number | null;
  module_id?: number | null;
  topic?: string | null;
  co_code?: string | null;
  lesson_payload?: any;
}

export interface VideoJobResponse {
  job_id: string;
  lesson_id?: number | null;
  topic_key: string;
  status: "queued" | "rendering" | "audio_generating" | "video_rendering" | "completed" | "ready" | "failed";
  progress_pct?: number;
  video_url?: string | null;
  duration_seconds?: number | null;
  error_message?: string | null;
  retryable?: boolean;
}

// Helper to resolve media URLs to the FastAPI backend host
export function resolveMediaUrl(pathOrUrl?: string | null): string {
  if (!pathOrUrl) return "";
  if (pathOrUrl.startsWith("http://") || pathOrUrl.startsWith("https://")) {
    return pathOrUrl;
  }
  const base = typeof window !== "undefined"
    ? `${window.location.protocol}//${window.location.hostname}:8000`
    : "http://127.0.0.1:8000";
  const cleanPath = pathOrUrl.startsWith("/") ? pathOrUrl : `/${pathOrUrl}`;
  return `${base}${cleanPath}`;
}

// Academic Support API Calls
export async function getStudentSubjects(
  token: string,
  semester?: number,
  status?: string
): Promise<StudentSubjectSummary[]> {
  const apiBase = getApiBase();
  const params = new URLSearchParams();
  if (semester) params.append("semester", semester.toString());
  if (status && status !== "all") params.append("performance_status", status);

  const queryStr = params.toString() ? `?${params.toString()}` : "";
  const res = await fetch(`${apiBase}/student/subjects${queryStr}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch student subjects (${res.status})`);
  }
  return res.json();
}

export async function getStudentMarksOverview(
  token: string,
  semester?: number,
  status?: string
): Promise<StudentMarksOverviewResponse> {
  const apiBase = getApiBase();
  const params = new URLSearchParams();
  if (semester) params.append("semester", semester.toString());
  if (status && status !== "all") params.append("performance_status", status);

  const queryStr = params.toString() ? `?${params.toString()}` : "";
  const res = await fetch(`${apiBase}/student/marks${queryStr}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch student marks overview (${res.status})`);
  }
  return res.json();
}

export async function getSubjectMarksDetail(
  token: string,
  subjectId: number
): Promise<SubjectMarksDetailResponse> {
  const apiBase = getApiBase();
  const res = await fetch(`${apiBase}/student/marks/${subjectId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch subject marks detail (${res.status})`);
  }
  return res.json();
}

export async function getSubjectModulesAnalysis(
  token: string,
  subjectId: number
): Promise<SubjectModulesAnalysisResponse> {
  const apiBase = getApiBase();
  const res = await fetch(`${apiBase}/student/marks/${subjectId}/modules`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch subject modules analysis (${res.status})`);
  }
  return res.json();
}

export async function getModuleLearningMaterials(
  token: string,
  moduleId: number
): Promise<ModuleLearningMaterialResponse> {
  const apiBase = getApiBase();
  const res = await fetch(`${apiBase}/student/learning/materials/${moduleId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch learning materials (${res.status})`);
  }
  return res.json();
}

export async function explainAcademicConcept(
  token: string,
  payload: AcademicExplainRequest
): Promise<AcademicExplainResponse> {
  const apiBase = getApiBase();
  const res = await fetch(`${apiBase}/student/learning/explain`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Concept explanation failed (${res.status})`);
  }
  return res.json();
}

export async function requestVideoGeneration(
  token: string,
  payload: VideoGenerationRequest
): Promise<VideoJobResponse> {
  const apiBase = getApiBase();
  const res = await fetch(`${apiBase}/student/learning/video`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Video generation request failed (${res.status})`);
  }
  return res.json();
}

export async function getVideoJobStatus(
  token: string,
  jobId: string
): Promise<VideoJobResponse> {
  const apiBase = getApiBase();
  const res = await fetch(`${apiBase}/student/learning/video/${jobId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch video job status (${res.status})`);
  }
  return res.json();
}

export async function getVideoByLesson(
  token: string,
  lessonId: number
): Promise<VideoJobResponse> {
  const apiBase = getApiBase();
  const res = await fetch(`${apiBase}/student/learning/video/by-lesson/${lessonId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch video for lesson (${res.status})`);
  }
  return res.json();
}

