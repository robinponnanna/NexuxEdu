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
