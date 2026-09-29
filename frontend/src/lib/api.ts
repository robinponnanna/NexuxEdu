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
  faculty_id?: number;
  is_hod?: boolean;
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
  current_lat: number;
  current_lng: number;
  speed_kmh: number;
  status: string;
  last_updated?: string;
  stops: BusStop[];
  waypoints: [number, number][];
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
    const host = window.location.hostname;
    return `${proto}//${host}:8000/ws/transit/${busId}?token=${encodeURIComponent(token)}`;
  }
  return `ws://127.0.0.1:8000/ws/transit/${busId}?token=${encodeURIComponent(token)}`;
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

// --- Event-Exam Clash & Retake Rescheduling Types & Methods ---

export interface EventItem {
  id: number;
  title: string;
  description?: string;
  start_at: string;
  end_at: string;
  created_by: number;
  created_at: string;
  participants_count?: number;
  clashes_count?: number;
}

export interface CaseTimelineEntry {
  id: number;
  case_id: number;
  actor_user_id?: number;
  actor_name?: string;
  actor_role: string;
  from_status?: string;
  to_status: string;
  note?: string;
  at: string;
}

export interface ClashCaseItem {
  id: number;
  event_id: number;
  event_title: string;
  student_id: number;
  student_name: string;
  student_roll: string;
  student_section?: string;
  student_department?: string;
  assessment_id: number;
  course_code: string;
  subject: string;
  offering_section?: string;
  assessment_kind: string;
  assessment_start?: string;
  assessment_end?: string;
  assessment_start_at?: string;
  assessment_end_at?: string;
  faculty_id?: number;
  faculty_name?: string;
  status: "DETECTED" | "REQUEST_FILED" | "COUNTER_PROPOSED" | "REJECTED" | "ESCALATED_TO_HOD" | "APPROVED" | "COMPLETED";
  suggested_retake_assessment_id?: number;
  suggested_retake_info?: string;
  retake_assessment_id?: number;
  retake_info?: string;
  retake_at?: string;
  retake_note?: string;
  rejection_reason?: string;
  created_at: string;
  updated_at: string;
  timeline?: CaseTimelineEntry[];
}

export interface EventDetailItem extends EventItem {
  clashes: ClashCaseItem[];
}

export interface HODOverview {
  department: string;
  counts_by_status: Record<string, number>;
  escalated_cases: ClashCaseItem[];
  stuck_cases: ClashCaseItem[];
  per_professor_pending: Record<string, number>;
}

export interface NotificationItem {
  id: number;
  user_id: number;
  type: string;
  title: string;
  body: string;
  case_id?: number;
  event_id?: number;
  is_read: boolean;
  created_at: string;
}

export interface ReferenceStudent {
  id: number;
  user_id: number;
  name: string;
  roll_number: string;
  department: string;
  semester: number;
  section: string;
}

export interface ReferenceAssessment {
  id: number;
  kind: string;
  start_at: string;
  end_at: string;
  venue?: string;
}

export interface ReferenceOffering {
  id: number;
  course_code: string;
  subject: string;
  section: string;
  semester: number;
  department: string;
  faculty_id: number;
  faculty_name: string;
  assessments: ReferenceAssessment[];
}

export async function getEvents(token: string): Promise<EventItem[]> {
  const res = await fetch(`${getApiBase()}/clash/events`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to fetch events");
  return res.json();
}

export async function createEvent(
  token: string,
  data: { title: string; description?: string; start_at: string; end_at: string }
): Promise<EventItem> {
  const res = await fetch(`${getApiBase()}/clash/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to create event");
  }
  return res.json();
}

export async function getEventDetail(token: string, eventId: number): Promise<EventDetailItem> {
  const res = await fetch(`${getApiBase()}/clash/events/${eventId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to fetch event details");
  return res.json();
}

export async function addEventParticipants(
  token: string,
  eventId: number,
  studentIds: number[]
): Promise<{ message: string; event_id: number; clashes_count: number }> {
  const res = await fetch(`${getApiBase()}/clash/events/${eventId}/participants`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ student_ids: studentIds }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to add participants");
  }
  return res.json();
}

export async function manualDetectClashes(token: string, eventId: number) {
  const res = await fetch(`${getApiBase()}/clash/events/${eventId}/detect`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Detection run failed");
  return res.json();
}

export async function getClashCases(
  token: string,
  filters?: { status?: string; event_id?: number; assessment_id?: number }
): Promise<ClashCaseItem[]> {
  const params = new URLSearchParams();
  if (filters?.status) params.append("status", filters.status);
  if (filters?.event_id) params.append("event_id", String(filters.event_id));
  if (filters?.assessment_id) params.append("assessment_id", String(filters.assessment_id));

  const query = params.toString() ? `?${params.toString()}` : "";
  const res = await fetch(`${getApiBase()}/clash/cases${query}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to fetch clash cases");
  return res.json();
}

export async function getClashCaseDetail(token: string, caseId: number): Promise<ClashCaseItem> {
  const res = await fetch(`${getApiBase()}/clash/cases/${caseId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to fetch case details");
  return res.json();
}

export async function fileClashCasesBulk(token: string, caseIds: number[]): Promise<ClashCaseItem[]> {
  const res = await fetch(`${getApiBase()}/clash/cases/file`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ case_ids: caseIds }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to file requests");
  }
  return res.json();
}

export async function professorDecideCases(
  token: string,
  payload: {
    case_ids: number[];
    decision: "approve" | "counter" | "reject";
    slot_id?: number;
    custom_at?: string;
    note?: string;
    rejection_reason?: string;
  }
): Promise<ClashCaseItem[]> {
  const res = await fetch(`${getApiBase()}/clash/cases/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Decision failed");
  }
  return res.json();
}

export async function acceptCounterProposal(token: string, caseId: number): Promise<ClashCaseItem> {
  const res = await fetch(`${getApiBase()}/clash/cases/${caseId}/accept-counter`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Accept counter failed");
  }
  return res.json();
}

export async function sendBackCounterProposal(token: string, caseId: number, note: string): Promise<ClashCaseItem> {
  const res = await fetch(`${getApiBase()}/clash/cases/${caseId}/send-back`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ note }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Send back failed");
  }
  return res.json();
}

export async function hodOverrideCase(
  token: string,
  caseId: number,
  payload: { slot_id?: number; custom_at?: string; note: string }
): Promise<ClashCaseItem> {
  const res = await fetch(`${getApiBase()}/clash/cases/${caseId}/override`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "HOD override failed");
  }
  return res.json();
}

export async function completeClashCase(token: string, caseId: number): Promise<ClashCaseItem> {
  const res = await fetch(`${getApiBase()}/clash/cases/${caseId}/complete`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to mark complete");
  }
  return res.json();
}

export async function getHODOverview(token: string): Promise<HODOverview> {
  const res = await fetch(`${getApiBase()}/clash/hod/overview`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to fetch HOD overview");
  return res.json();
}

export async function getReferenceStudents(token: string, q?: string): Promise<ReferenceStudent[]> {
  const query = q ? `?q=${encodeURIComponent(q)}` : "";
  const res = await fetch(`${getApiBase()}/clash/reference/students${query}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to fetch students");
  return res.json();
}

export async function getReferenceOfferings(token: string): Promise<ReferenceOffering[]> {
  const res = await fetch(`${getApiBase()}/clash/reference/offerings`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to fetch course offerings");
  return res.json();
}

export async function getNotifications(token: string): Promise<NotificationItem[]> {
  const res = await fetch(`${getApiBase()}/clash/notifications`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to fetch notifications");
  return res.json();
}

export async function markNotificationRead(token: string, notifId: number) {
  const res = await fetch(`${getApiBase()}/clash/notifications/${notifId}/read`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  return res.json();
}

export async function markAllNotificationsRead(token: string) {
  const res = await fetch(`${getApiBase()}/clash/notifications/read-all`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  return res.json();
}

