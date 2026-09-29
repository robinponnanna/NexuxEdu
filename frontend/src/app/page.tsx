"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import { Header } from "@/components/Header";
import { Sidebar, NavTab } from "@/components/Sidebar";
import { AttendanceCard, SubjectAttendance } from "@/components/AttendanceCard";
import { ChatDrawer } from "@/components/ChatDrawer";
import {
  login,
  getDashboard,
  getBuses,
  UserProfile,
  BusDetails,
  getAuditLogs,
  getFacultyClassAttendance,
  FacultyAttendanceRosterResponse,
  FacultyStudentAttendance,
} from "@/lib/api";
import {
  GraduationCap,
  Bus,
  ShieldCheck,
  AlertTriangle,
  BookOpen,
  Calendar,
  Layers,
  ArrowRight,
  ShieldAlert,
  Clock,
  CheckCircle,
  Search,
  Filter,
  Users,
  CheckCircle2,
  AlertCircle,
  FileSpreadsheet,
  Download,
  Mail,
  UserCheck,
  RefreshCw,
} from "lucide-react";

// Dynamically import Leaflet Map to avoid SSR window errors
const LiveTransitMap = dynamic(
  () => import("@/components/LiveTransitMap").then((mod) => mod.LiveTransitMap),
  {
    ssr: false,
    loading: () => (
      <div
        style={{
          minHeight: "560px",
          background: "var(--surface-card)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "var(--text-muted)",
        }}
      >
        Loading Live Transit Map...
      </div>
    ),
  }
);

// Fallback initial data to guarantee instantaneous interactivity
const DEMO_PROFILES: Record<string, UserProfile> = {
  "student@campus.edu": {
    id: 5,
    public_id: "student-uuid",
    name: "Jane Doe",
    email: "student@campus.edu",
    role: "student",
    department: "Computer Science",
    student_id: 1,
    bus_id: 1,
  },
  "faculty@campus.edu": {
    id: 2,
    public_id: "faculty-uuid",
    name: "Prof. Alan Turing",
    email: "faculty@campus.edu",
    role: "faculty",
    department: "Computer Science",
  },
  "parent@campus.edu": {
    id: 4,
    public_id: "parent-uuid",
    name: "Robert Doe",
    email: "parent@campus.edu",
    role: "parent",
    ward_id: 1,
    bus_id: 1,
  },
  "admin@campus.edu": {
    id: 1,
    public_id: "admin-uuid",
    name: "Sarah Connor",
    email: "admin@campus.edu",
    role: "admin",
  },
};

const DEFAULT_BUSES: BusDetails[] = [
  {
    id: 1,
    bus_number: "BUS-001",
    route_name: "Route North-4 (Civic Express)",
    driver_name: "Driver Dave #1",
    driver_phone: "+91-9876543001",
    current_lat: 28.6139,
    current_lng: 77.209,
    speed_kmh: 38.0,
    status: "Active",
    stops: [
      { name: "Terminal Stop 1", lat: 28.6139, lng: 77.209, sequence: 1 },
      { name: "Midtown Gate 1", lat: 28.6189, lng: 77.216, sequence: 2 },
      { name: "Civic Center 1", lat: 28.6259, lng: 77.219, sequence: 3 },
      { name: "Campus Main Arch 1", lat: 28.6139, lng: 77.209, sequence: 4 },
    ],
    waypoints: [
      [28.6139, 77.209],
      [28.6189, 77.216],
      [28.6259, 77.219],
      [28.6289, 77.212],
      [28.6219, 77.204],
      [28.6139, 77.209],
    ],
  },
  {
    id: 2,
    bus_number: "BUS-002",
    route_name: "Route South-1 (Metro Link)",
    driver_name: "Captain Raj #2",
    driver_phone: "+91-9876543002",
    current_lat: 28.62,
    current_lng: 77.215,
    speed_kmh: 34.5,
    status: "Active",
    stops: [
      { name: "Terminal Stop 2", lat: 28.62, lng: 77.215, sequence: 1 },
      { name: "Midtown Gate 2", lat: 28.625, lng: 77.222, sequence: 2 },
      { name: "Civic Center 2", lat: 28.632, lng: 77.225, sequence: 3 },
      { name: "Campus Main Arch 2", lat: 28.62, lng: 77.215, sequence: 4 },
    ],
    waypoints: [
      [28.62, 77.215],
      [28.625, 77.222],
      [28.632, 77.225],
      [28.62, 77.215],
    ],
  },
];

const DEFAULT_ATTENDANCE: SubjectAttendance[] = [
  { id: 1, subject: "Operating Systems", attended_classes: 35, total_classes: 40, attendance_pct: 87.5 },
  { id: 2, subject: "Database Management Systems", attended_classes: 37, total_classes: 40, attendance_pct: 92.5 },
  { id: 3, subject: "Computer Networks", attended_classes: 31, total_classes: 40, attendance_pct: 77.5 },
  { id: 4, subject: "Theory of Computation", attended_classes: 28, total_classes: 40, attendance_pct: 70.0 },
];

const DEFAULT_FACULTY_ROSTER: FacultyAttendanceRosterResponse = {
  department: "Computer Science",
  selected_subject: "Operating Systems",
  selected_section: "All Sections",
  classes: [
    { code: "CS-301", name: "Operating Systems" },
    { code: "CS-302", name: "Database Management Systems" },
    { code: "CS-303", name: "Computer Networks" },
  ],
  sections: ["All Sections", "Section A", "Section B"],
  summary: {
    total_students: 8,
    class_avg_pct: 80.9,
    safe_count: 4,
    attention_count: 1,
    debarment_risk_count: 3,
  },
  students: [
    {
      student_id: 3,
      roll_number: "CS-2023-015",
      name: "Rahul Sharma",
      email: "rahul@campus.edu",
      section: "Section A",
      semester: 6,
      subject: "Operating Systems",
      attended_classes: 38,
      total_classes: 40,
      attendance_pct: 95.0,
      status: "Safe",
    },
    {
      student_id: 4,
      roll_number: "CS-2023-031",
      name: "Anita Desai",
      email: "anita@campus.edu",
      section: "Section A",
      semester: 6,
      subject: "Operating Systems",
      attended_classes: 26,
      total_classes: 40,
      attendance_pct: 65.0,
      status: "Debarment Risk",
    },
    {
      student_id: 1,
      roll_number: "CS-2023-042",
      name: "Jane Doe",
      email: "student@campus.edu",
      section: "Section A",
      semester: 6,
      subject: "Operating Systems",
      attended_classes: 35,
      total_classes: 40,
      attendance_pct: 87.5,
      status: "Safe",
    },
    {
      student_id: 2,
      roll_number: "CS-2023-088",
      name: "Alex Smith",
      email: "alex@campus.edu",
      section: "Section A",
      semester: 6,
      subject: "Operating Systems",
      attended_classes: 28,
      total_classes: 40,
      attendance_pct: 70.0,
      status: "Debarment Risk",
    },
    {
      student_id: 5,
      roll_number: "CS-2023-102",
      name: "Emily Watson",
      email: "emily@campus.edu",
      section: "Section B",
      semester: 6,
      subject: "Operating Systems",
      attended_classes: 39,
      total_classes: 40,
      attendance_pct: 97.5,
      status: "Safe",
    },
    {
      student_id: 6,
      roll_number: "CS-2023-118",
      name: "Michael Chen",
      email: "michael@campus.edu",
      section: "Section B",
      semester: 6,
      subject: "Operating Systems",
      attended_classes: 27,
      total_classes: 40,
      attendance_pct: 67.5,
      status: "Debarment Risk",
    },
    {
      student_id: 7,
      roll_number: "CS-2023-134",
      name: "Sophia Patel",
      email: "sophia@campus.edu",
      section: "Section B",
      semester: 6,
      subject: "Operating Systems",
      attended_classes: 34,
      total_classes: 40,
      attendance_pct: 85.0,
      status: "Safe",
    },
    {
      student_id: 8,
      roll_number: "CS-2023-159",
      name: "David Miller",
      email: "david@campus.edu",
      section: "Section B",
      semester: 6,
      subject: "Operating Systems",
      attended_classes: 32,
      total_classes: 40,
      attendance_pct: 80.0,
      status: "Attention",
    },
  ],
};

export default function HomePage() {
  const router = useRouter();
  const [token, setToken] = useState<string>("");
  const [user, setUser] = useState<UserProfile>(DEMO_PROFILES["student@campus.edu"]);
  const [activeTab, setActiveTab] = useState<NavTab>("dashboard");
  const [dashboardData, setDashboardData] = useState<any>({
    role: "student",
    name: "Jane Doe",
    department: "Computer Science",
    overall_attendance_pct: 81.9,
    assigned_bus_id: 1,
    semester: 6,
    attendance_records: DEFAULT_ATTENDANCE,
  });
  const [buses, setBuses] = useState<BusDetails[]>(DEFAULT_BUSES);
  const [selectedBusId, setSelectedBusId] = useState<number>(1);
  const [auditLogs, setAuditLogs] = useState<any[]>([
    {
      id: 1,
      role: "student",
      event_type: "EVENT_PRIVILEGE_PROBE",
      details: "User role 'student' attempted unauthorized access to structured records. Query: 'Show all faculty salaries in Computer Science'",
      timestamp: new Date().toISOString(),
    },
  ]);
  const [isChatOpen, setIsChatOpen] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isAuthChecked, setIsAuthChecked] = useState<boolean>(false);

  // Faculty Class Attendance Roster State
  const [facultyRoster, setFacultyRoster] = useState<FacultyAttendanceRosterResponse>(DEFAULT_FACULTY_ROSTER);
  const [selectedSubject, setSelectedSubject] = useState<string>("Operating Systems");
  const [selectedSection, setSelectedSection] = useState<string>("All Sections");
  const [selectedStatusFilter, setSelectedStatusFilter] = useState<"all" | "Safe" | "Attention" | "Debarment Risk">("all");
  const [studentSearchQuery, setStudentSearchQuery] = useState<string>("");
  const [isFacultyRosterLoading, setIsFacultyRosterLoading] = useState<boolean>(false);
  const [noticeToast, setNoticeToast] = useState<string | null>(null);

  // Fetch live metrics based on user role and token
  const loadRoleData = async (authToken: string, currentUser: UserProfile) => {
    try {
      // 1. Fetch dashboard metrics
      const dash = await getDashboard(authToken).catch(() => null);
      if (dash) {
        setDashboardData(dash);
      }

      // 2. Fetch transit routes
      const busList = await getBuses(authToken).catch(() => []);
      if (busList && busList.length > 0) {
        setBuses(busList);
      }

      // 3. If admin, fetch security audit logs
      if (currentUser.role === "admin") {
        const logs = await getAuditLogs(authToken).catch(() => []);
        if (logs && logs.length > 0) {
          setAuditLogs(logs);
        }
      }

      // 4. If faculty, fetch class and sections attendance roster
      if (currentUser.role === "faculty") {
        const roster = await getFacultyClassAttendance(authToken, selectedSubject, selectedSection).catch(() => null);
        if (roster) {
          setFacultyRoster(roster);
        }
      }
    } catch (err) {
      console.warn("Data loading fallback to local cache:", err);
    }
  };

  const handleSubjectOrSectionChange = async (subject: string, section: string) => {
    setSelectedSubject(subject);
    setSelectedSection(section);
    if (!token || user?.role !== "faculty") return;
    setIsFacultyRosterLoading(true);
    try {
      const roster = await getFacultyClassAttendance(token, subject, section);
      setFacultyRoster(roster);
    } catch (e) {
      console.warn("Failed to load faculty roster:", e);
    } finally {
      setIsFacultyRosterLoading(false);
    }
  };

  const handleSendNotice = (studentName: string) => {
    setNoticeToast(`Attendance advisory notification & email dispatched to ${studentName} and parent.`);
    setTimeout(() => setNoticeToast(null), 3500);
  };

  // Check login session on mount to automatically determine role & rights
  useEffect(() => {
    if (typeof window !== "undefined") {
      const savedSession = localStorage.getItem("nexusedu_session") || localStorage.getItem("omnicampus_session");
      if (savedSession) {
        try {
          const session = JSON.parse(savedSession);
          if (session && session.token && session.user) {
            setToken(session.token);
            setUser(session.user);
            if (session.user.bus_id) {
              setSelectedBusId(session.user.bus_id);
            }
            setIsAuthChecked(true);
            loadRoleData(session.token, session.user);
            return;
          }
        } catch (e) {
          console.error("Failed to parse session", e);
        }
      }
      // If not logged in, redirect to the login page
      router.push("/login");
    }
  }, [router]);

  // Authenticate user & grant corresponding rights
  const authenticateUser = async (email: string) => {
    setIsLoading(true);

    try {
      const session = await login(email, "password123");
      setToken(session.token);
      setUser(session.user);
      if (typeof window !== "undefined") {
        localStorage.setItem("nexusedu_session", JSON.stringify(session));
        localStorage.setItem("omnicampus_session", JSON.stringify(session));
      }
      if (session.user.bus_id) {
        setSelectedBusId(session.user.bus_id);
      }

      // Automatically enforce role rights for active tab
      if (session.user.role !== "admin" && activeTab === "audits") {
        setActiveTab("dashboard");
      }
      if (session.user.role === "faculty" && activeTab === "transit") {
        setActiveTab("dashboard");
      }

      await loadRoleData(session.token, session.user);
    } catch (err) {
      console.warn("API handshake fallback to verified local profile:", err);
      const localProfile = DEMO_PROFILES[email] || DEMO_PROFILES["student@campus.edu"];
      setUser(localProfile);
      if (localProfile.bus_id) setSelectedBusId(localProfile.bus_id);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRoleSwitch = (email: string) => {
    authenticateUser(email);
  };

  const handleLogout = () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("omnicampus_session");
    }
    router.push("/login");
  };

  const selectedBus = buses.find((b) => b.id === selectedBusId) || buses[0] || DEFAULT_BUSES[0];

  if (!isAuthChecked) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background: "var(--surface-dark)",
          color: "var(--text-main)",
          gap: "16px",
        }}
      >
        <div
          style={{
            width: "44px",
            height: "44px",
            borderRadius: "10px",
            background: "var(--surface-elevated)",
            border: "1px solid var(--surface-border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "var(--color-primary)",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <ShieldCheck size={24} />
        </div>
        <div style={{ fontSize: "0.95rem", fontWeight: 600, color: "var(--text-main)" }}>
          Verifying NexusEdu Security Claims...
        </div>
        <div style={{ fontSize: "0.78rem", color: "var(--text-dim)" }}>
          Applying zero-trust role bounds & RBAC permissions
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", background: "var(--surface-dark)" }}>
      {/* Header with profile icon and hover role display */}
      <Header user={user} onLogout={handleLogout} />

      {/* Main Layout Container */}
      <div style={{ display: "flex", flex: 1 }}>
        {/* Sidebar */}
        <Sidebar
          user={user}
          activeTab={activeTab}
          onSelectTab={(tab) => setActiveTab(tab)}
          onOpenChat={() => setIsChatOpen(true)}
        />

        {/* Content View Area */}
        <main style={{ flex: 1, padding: "28px 36px", overflowY: "auto", maxWidth: "1400px" }}>
          {/* Top Banner / Role Orientation */}
          <div
            style={{
              background: "var(--surface-card)",
              border: "1px solid var(--surface-border)",
              borderRadius: "10px",
              padding: "22px 26px",
              marginBottom: "24px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              boxShadow: "var(--shadow-sm)",
            }}
          >
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
                <span
                  style={{
                    fontSize: "0.7rem",
                    fontWeight: 600,
                    letterSpacing: "0.06em",
                    textTransform: "uppercase",
                    padding: "2px 7px",
                    borderRadius: "4px",
                    background: "var(--surface-elevated)",
                    color: "var(--text-muted)",
                    border: "1px solid var(--surface-border-subtle)",
                  }}
                >
                  WORKSPACE
                </span>
                <span style={{ fontSize: "0.8rem", color: "var(--text-dim)" }}>
                  Role: <strong style={{ color: "var(--text-main)", textTransform: "capitalize", fontWeight: 600 }}>{user?.role}</strong> • User ID: #{user?.id || 1}
                </span>
              </div>
              <h1 style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--text-main)", letterSpacing: "-0.02em" }}>
                Welcome, {user?.name || "NexusEdu User"}
              </h1>
              <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginTop: "4px" }}>
                {user?.role === "student" && "Track course attendance, exam eligibility thresholds, and your assigned transit shuttle."}
                {user?.role === "parent" && "Real-time child commute telematics, geofence alerts, and verified ward attendance."}
                {user?.role === "faculty" && "Manage department lecture rosters, submit grading keys, and review teaching schedules."}
                {user?.role === "admin" && "Master fleet telemetry, cross-department governance, and zero-trust security audit logs."}
              </p>
            </div>

            <div style={{ display: "flex", gap: "12px" }}>
              <button
                type="button"
                onClick={() => setIsChatOpen(true)}
                style={{
                  background: "var(--text-main)",
                  color: "#FFFFFF",
                  border: "none",
                  borderRadius: "7px",
                  padding: "9px 16px",
                  fontSize: "0.84rem",
                  fontWeight: 600,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "7px",
                  boxShadow: "var(--shadow-sm)",
                  userSelect: "none",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.opacity = "0.9")}
                onMouseLeave={(e) => (e.currentTarget.style.opacity = "1")}
              >
                <span>Ask AI Assistant</span>
                <ArrowRight size={15} />
              </button>
            </div>
          </div>

          {/* ===================== TAB: DASHBOARD ===================== */}
          {activeTab === "dashboard" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
              {/* KPI Cards Row */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "16px" }}>
                {user?.role === "student" || user?.role === "parent" ? (
                  <>
                    {/* Overall Attendance KPI */}
                    <div style={{ background: "var(--surface-card)", border: "1px solid var(--surface-border)", borderRadius: "10px", padding: "18px 20px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                        <span style={{ fontSize: "0.75rem", color: "var(--text-dim)", fontWeight: 600, letterSpacing: "0.04em" }}>OVERALL ATTENDANCE</span>
                        <GraduationCap size={18} color="var(--color-student)" />
                      </div>
                      <div className="font-mono" style={{ fontSize: "1.85rem", fontWeight: 700, color: (dashboardData?.overall_attendance_pct ?? 81.9) >= 75 ? "var(--color-success)" : "var(--color-danger)" }}>
                        {dashboardData?.overall_attendance_pct ?? 81.9}%
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginTop: "6px", display: "flex", alignItems: "center", gap: "5px" }}>
                        <CheckCircle size={13} color="var(--color-success)" />
                        <span>Examination Threshold: 75.0%</span>
                      </div>
                    </div>

                    {/* Assigned Bus Status */}
                    <div style={{ background: "var(--surface-card)", border: "1px solid var(--surface-border)", borderRadius: "10px", padding: "18px 20px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                        <span style={{ fontSize: "0.75rem", color: "var(--text-dim)", fontWeight: 600, letterSpacing: "0.04em" }}>ASSIGNED VEHICLE</span>
                        <Bus size={18} color="var(--color-parent)" />
                      </div>
                      <div className="font-mono" style={{ fontSize: "1.35rem", fontWeight: 700, color: "var(--text-main)" }}>
                        {selectedBus?.bus_number || "BUS-001"}
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "6px" }}>
                        Route: <strong style={{ color: "var(--text-main)" }}>{selectedBus?.route_name || "Route North-4"}</strong>
                      </div>
                    </div>

                    {/* Academic Standing */}
                    <div style={{ background: "var(--surface-card)", border: "1px solid var(--surface-border)", borderRadius: "10px", padding: "18px 20px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                        <span style={{ fontSize: "0.75rem", color: "var(--text-dim)", fontWeight: 600, letterSpacing: "0.04em" }}>ACADEMIC STANDING</span>
                        <Layers size={18} color="var(--color-faculty)" />
                      </div>
                      <div style={{ fontSize: "1.35rem", fontWeight: 700, color: "var(--text-main)" }}>
                        Semester 6
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginTop: "6px" }}>
                        Dept: {user?.department || "Computer Science"}
                      </div>
                    </div>
                  </>
                ) : user?.role === "faculty" ? (
                  <>
                    <div style={{ background: "var(--surface-card)", border: "1px solid var(--surface-border)", borderRadius: "10px", padding: "18px 20px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                        <span style={{ fontSize: "0.75rem", color: "var(--text-dim)", fontWeight: 600, letterSpacing: "0.04em" }}>ACTIVE COURSES</span>
                        <BookOpen size={18} color="var(--color-faculty)" />
                      </div>
                      <div className="font-mono" style={{ fontSize: "1.85rem", fontWeight: 700, color: "var(--text-main)" }}>
                        3
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "6px" }}>
                        OS, DBMS & Networks
                      </div>
                    </div>

                    <div style={{ background: "var(--surface-card)", border: "1px solid var(--surface-border)", borderRadius: "10px", padding: "18px 20px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                        <span style={{ fontSize: "0.75rem", color: "var(--text-dim)", fontWeight: 600, letterSpacing: "0.04em" }}>TOTAL STUDENTS</span>
                        <GraduationCap size={18} color="var(--color-student)" />
                      </div>
                      <div className="font-mono" style={{ fontSize: "1.85rem", fontWeight: 700, color: "var(--text-main)" }}>
                        {facultyRoster?.summary?.total_students || 8}
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "6px" }}>
                        Sec A (4) • Sec B (4)
                      </div>
                    </div>

                    <div style={{ background: "var(--surface-card)", border: "1px solid var(--surface-border)", borderRadius: "10px", padding: "18px 20px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                        <span style={{ fontSize: "0.75rem", color: "var(--text-dim)", fontWeight: 600, letterSpacing: "0.04em" }}>CLASS ATTENDANCE</span>
                        <UserCheck size={18} color="var(--color-success)" />
                      </div>
                      <div className="font-mono" style={{ fontSize: "1.85rem", fontWeight: 700, color: "var(--color-main)" }}>
                        {facultyRoster?.summary?.class_avg_pct || 80.9}%
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "var(--color-danger)", marginTop: "6px", display: "flex", alignItems: "center", gap: "4px" }}>
                        <AlertCircle size={13} color="var(--color-danger)" />
                        <span>{facultyRoster?.summary?.debarment_risk_count || 3} at debarment risk (&lt;75%)</span>
                      </div>
                    </div>
                  </>
                ) : (
                  <>
                    <div style={{ background: "var(--surface-card)", border: "1px solid var(--surface-border)", borderRadius: "10px", padding: "18px 20px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                        <span style={{ fontSize: "0.75rem", color: "var(--text-dim)", fontWeight: 600, letterSpacing: "0.04em" }}>TOTAL USERS</span>
                        <GraduationCap size={18} color="var(--color-admin)" />
                      </div>
                      <div className="font-mono" style={{ fontSize: "1.85rem", fontWeight: 700, color: "var(--text-main)" }}>
                        {dashboardData?.total_users || 6}
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "6px" }}>
                        RBAC Accounts
                      </div>
                    </div>

                    <div style={{ background: "var(--surface-card)", border: "1px solid var(--surface-border)", borderRadius: "10px", padding: "18px 20px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                        <span style={{ fontSize: "0.75rem", color: "var(--text-dim)", fontWeight: 600, letterSpacing: "0.04em" }}>ACTIVE FLEET</span>
                        <Bus size={18} color="var(--color-parent)" />
                      </div>
                      <div className="font-mono" style={{ fontSize: "1.85rem", fontWeight: 700, color: "var(--text-main)" }}>
                        {dashboardData?.active_buses || 20}
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "6px" }}>
                        3s Live GPS Streams
                      </div>
                    </div>

                    <div style={{ background: "var(--surface-card)", border: "1px solid var(--surface-border)", borderRadius: "10px", padding: "18px 20px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                        <span style={{ fontSize: "0.75rem", color: "var(--text-dim)", fontWeight: 600, letterSpacing: "0.04em" }}>SECURITY AUDITS</span>
                        <ShieldAlert size={18} color="var(--color-danger)" />
                      </div>
                      <div className="font-mono" style={{ fontSize: "1.85rem", fontWeight: 700, color: "var(--color-danger)" }}>
                        {auditLogs.length}
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "6px" }}>
                        Zero-Trust Intercepts
                      </div>
                    </div>
                  </>
                )}
              </div>

              {/* Attendance Grid Preview (for student & parent) */}
              {(user?.role === "student" || user?.role === "parent") && (
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
                    <h2 style={{ fontSize: "1.1rem", fontWeight: 600, color: "var(--text-main)" }}>
                      Subject Attendance Health Indicators
                    </h2>
                    <button
                      type="button"
                      onClick={() => setActiveTab("attendance")}
                      style={{ background: "transparent", border: "none", color: "var(--color-primary)", cursor: "pointer", fontSize: "0.82rem", fontWeight: 500 }}
                    >
                      View All Courses →
                    </button>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "14px" }}>
                    {(dashboardData?.attendance_records || DEFAULT_ATTENDANCE).map((rec: SubjectAttendance) => (
                      <AttendanceCard key={rec.id} record={rec} />
                    ))}
                  </div>
                </div>
              )}

              {/* Faculty Section Health & Roster Preview (for faculty) */}
              {user?.role === "faculty" && (
                <div style={{ background: "var(--surface-card)", borderRadius: "10px", border: "1px solid var(--surface-border)", padding: "20px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                    <div>
                      <h2 style={{ fontSize: "1.1rem", fontWeight: 600, color: "var(--text-main)", display: "flex", alignItems: "center", gap: "8px" }}>
                        <Users size={18} color="var(--color-faculty)" />
                        <span>Class & Sections Attendance Intelligence — {selectedSubject}</span>
                      </h2>
                      <p style={{ fontSize: "0.78rem", color: "var(--text-dim)", marginTop: "2px" }}>
                        Real-time student attendance monitoring across Section A and Section B under §4.2 invariants.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setActiveTab("attendance")}
                      style={{
                        background: "var(--surface-elevated)",
                        border: "1px solid var(--surface-border)",
                        color: "var(--text-main)",
                        borderRadius: "6px",
                        padding: "7px 14px",
                        cursor: "pointer",
                        fontSize: "0.82rem",
                        fontWeight: 600,
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-hover)")}
                      onMouseLeave={(e) => (e.currentTarget.style.background = "var(--surface-elevated)")}
                    >
                      <span>Open Full Class Roster</span>
                      <ArrowRight size={14} />
                    </button>
                  </div>

                  {/* Section Breakdown Mini Cards */}
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "14px", marginBottom: "16px" }}>
                    <div style={{ background: "var(--surface-elevated)", border: "1px solid var(--surface-border)", borderRadius: "8px", padding: "14px 16px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                        <span style={{ fontSize: "0.82rem", fontWeight: 700, color: "var(--text-main)" }}>SECTION A</span>
                        <span style={{ fontSize: "0.72rem", background: "var(--surface-border)", padding: "2px 6px", borderRadius: "4px", color: "var(--text-muted)" }}>Semester 6</span>
                      </div>
                      <div style={{ display: "flex", alignItems: "baseline", gap: "8px" }}>
                        <span className="font-mono" style={{ fontSize: "1.4rem", fontWeight: 700, color: "var(--text-main)" }}>4</span>
                        <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Enrolled Students</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem", marginTop: "10px", paddingTop: "8px", borderTop: "1px solid var(--surface-border)" }}>
                        <span style={{ color: "var(--text-dim)" }}>Average: <strong>79.4%</strong></span>
                        <span style={{ color: "var(--color-danger)", fontWeight: 600 }}>2 At Risk (&lt;75%)</span>
                      </div>
                    </div>

                    <div style={{ background: "var(--surface-elevated)", border: "1px solid var(--surface-border)", borderRadius: "8px", padding: "14px 16px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                        <span style={{ fontSize: "0.82rem", fontWeight: 700, color: "var(--text-main)" }}>SECTION B</span>
                        <span style={{ fontSize: "0.72rem", background: "var(--surface-border)", padding: "2px 6px", borderRadius: "4px", color: "var(--text-muted)" }}>Semester 6</span>
                      </div>
                      <div style={{ display: "flex", alignItems: "baseline", gap: "8px" }}>
                        <span className="font-mono" style={{ fontSize: "1.4rem", fontWeight: 700, color: "var(--text-main)" }}>4</span>
                        <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Enrolled Students</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem", marginTop: "10px", paddingTop: "8px", borderTop: "1px solid var(--surface-border)" }}>
                        <span style={{ color: "var(--text-dim)" }}>Average: <strong>82.5%</strong></span>
                        <span style={{ color: "var(--color-danger)", fontWeight: 600 }}>1 At Risk (&lt;75%)</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ===================== TAB: LIVE TRANSIT ===================== */}
          {activeTab === "transit" && selectedBus && (
            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              {/* Route Selector Bar */}
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", background: "var(--surface-card)", padding: "12px 18px", borderRadius: "8px", border: "1px solid var(--surface-border)" }}>
                <div>
                  <div style={{ fontSize: "0.9rem", fontWeight: 600, color: "var(--text-main)" }}>
                    Selected Vehicle: {selectedBus.bus_number} ({selectedBus.route_name})
                  </div>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>
                    Driver: {selectedBus.driver_name} • Phone: {selectedBus.driver_phone}
                  </div>
                </div>

                {user?.role === "admin" && (
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <span style={{ fontSize: "0.78rem", color: "var(--text-dim)", fontWeight: 500 }}>ROUTE (ADMIN):</span>
                    <select
                      value={selectedBusId}
                      onChange={(e) => setSelectedBusId(Number(e.target.value))}
                      style={{
                        background: "var(--surface-dark)",
                        color: "var(--text-main)",
                        border: "1px solid var(--surface-border)",
                        padding: "6px 10px",
                        borderRadius: "6px",
                        fontSize: "0.82rem",
                        cursor: "pointer",
                        outline: "none",
                      }}
                    >
                      {buses.map((b) => (
                        <option key={b.id} value={b.id}>
                          {b.bus_number} — {b.route_name}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>

              {/* Map Canvas */}
              <div style={{ height: "620px" }}>
                <LiveTransitMap bus={selectedBus} token={token} userRole={user?.role || "student"} />
              </div>
            </div>
          )}

          {/* ===================== TAB: ATTENDANCE TRACKER / FACULTY CLASS ROSTER ===================== */}
          {activeTab === "attendance" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
              {/* Toast notice banner */}
              {noticeToast && (
                <div
                  style={{
                    background: "#F0FDF4",
                    border: "1px solid #BBF7D0",
                    borderLeft: "4px solid var(--color-success)",
                    borderRadius: "8px",
                    padding: "12px 16px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    fontSize: "0.84rem",
                    color: "var(--color-success)",
                    fontWeight: 500,
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <CheckCircle2 size={16} />
                    <span>{noticeToast}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setNoticeToast(null)}
                    style={{ background: "transparent", border: "none", color: "var(--color-success)", cursor: "pointer", fontSize: "0.8rem", fontWeight: 600 }}
                  >
                    ✕
                  </button>
                </div>
              )}

              {/* Branch based on role: Faculty vs Student/Parent */}
              {user?.role === "faculty" ? (
                <>
                  {/* Faculty Roster Header & Controls */}
                  <div
                    style={{
                      background: "var(--surface-card)",
                      border: "1px solid var(--surface-border)",
                      borderRadius: "10px",
                      padding: "20px",
                      display: "flex",
                      flexDirection: "column",
                      gap: "18px",
                    }}
                  >
                    {/* Top Row: Title, Course selector, and Refresh */}
                    <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: "16px" }}>
                      <div>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <span style={{ fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase", padding: "2px 7px", borderRadius: "4px", background: "var(--surface-elevated)", color: "var(--color-faculty)", border: "1px solid var(--surface-border)" }}>
                            FACULTY COMMAND CENTER
                          </span>
                          <span style={{ fontSize: "0.78rem", color: "var(--text-dim)" }}>
                            Department of Computer Science
                          </span>
                        </div>
                        <h2 style={{ fontSize: "1.35rem", fontWeight: 700, color: "var(--text-main)", marginTop: "4px" }}>
                          Class & Section Attendance Roster
                        </h2>
                        <p style={{ fontSize: "0.82rem", color: "var(--text-muted)", marginTop: "2px" }}>
                          Inspect section rosters, analyze attendance distributions, and enforce examination debarment thresholds (§4.2).
                        </p>
                      </div>

                      {/* Course Selector Buttons */}
                      <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "8px" }}>
                        {(facultyRoster?.classes || DEFAULT_FACULTY_ROSTER.classes).map((cls) => {
                          const isSelected = selectedSubject === cls.name;
                          return (
                            <button
                              key={cls.code}
                              type="button"
                              onClick={() => handleSubjectOrSectionChange(cls.name, selectedSection)}
                              style={{
                                padding: "7px 13px",
                                borderRadius: "7px",
                                fontSize: "0.82rem",
                                fontWeight: 600,
                                cursor: "pointer",
                                transition: "all 0.15s ease",
                                border: isSelected ? "1px solid var(--text-main)" : "1px solid var(--surface-border)",
                                background: isSelected ? "var(--text-main)" : "var(--surface-card)",
                                color: isSelected ? "#FFFFFF" : "var(--text-main)",
                              }}
                            >
                              {cls.name} ({cls.code})
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    {/* Filter & Search Bar */}
                    <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: "14px", paddingTop: "14px", borderTop: "1px solid var(--surface-border)" }}>
                      {/* Section Tabs */}
                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <span style={{ fontSize: "0.75rem", color: "var(--text-dim)", fontWeight: 600, marginRight: "4px" }}>
                          SECTION:
                        </span>
                        {["All Sections", "Section A", "Section B"].map((sec) => {
                          const isSelected = selectedSection === sec;
                          const studentCount = sec === "All Sections" ? 8 : 4;
                          return (
                            <button
                              key={sec}
                              type="button"
                              onClick={() => handleSubjectOrSectionChange(selectedSubject, sec)}
                              style={{
                                padding: "5px 12px",
                                borderRadius: "6px",
                                fontSize: "0.78rem",
                                fontWeight: 600,
                                cursor: "pointer",
                                border: isSelected ? "1px solid var(--color-primary)" : "1px solid var(--surface-border)",
                                background: isSelected ? "var(--surface-elevated)" : "transparent",
                                color: isSelected ? "var(--color-primary)" : "var(--text-muted)",
                                display: "flex",
                                alignItems: "center",
                                gap: "6px",
                              }}
                            >
                              <span>{sec}</span>
                              <span
                                style={{
                                  fontSize: "0.68rem",
                                  padding: "1px 5px",
                                  borderRadius: "10px",
                                  background: isSelected ? "var(--color-primary)" : "var(--surface-border)",
                                  color: isSelected ? "#FFFFFF" : "var(--text-muted)",
                                }}
                              >
                                {studentCount}
                              </span>
                            </button>
                          );
                        })}
                      </div>

                      {/* Search & Status Filters */}
                      <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "10px", flexGrow: 1, maxWidth: "560px", justifyContent: "flex-end" }}>
                        {/* Search Input */}
                        <div style={{ position: "relative", minWidth: "220px", flexGrow: 1 }}>
                          <Search
                            size={14}
                            color="var(--text-dim)"
                            style={{ position: "absolute", left: "10px", top: "50%", transform: "translateY(-50%)" }}
                          />
                          <input
                            type="text"
                            placeholder="Search by student, roll number, or section..."
                            value={studentSearchQuery}
                            onChange={(e) => setStudentSearchQuery(e.target.value)}
                            style={{
                              width: "100%",
                              padding: "6px 12px 6px 30px",
                              borderRadius: "6px",
                              border: "1px solid var(--surface-border)",
                              background: "var(--surface-dark)",
                              color: "var(--text-main)",
                              fontSize: "0.8rem",
                              outline: "none",
                            }}
                          />
                          {studentSearchQuery && (
                            <button
                              type="button"
                              onClick={() => setStudentSearchQuery("")}
                              style={{
                                position: "absolute",
                                right: "8px",
                                top: "50%",
                                transform: "translateY(-50%)",
                                background: "transparent",
                                border: "none",
                                color: "var(--text-dim)",
                                cursor: "pointer",
                                fontSize: "0.75rem",
                              }}
                            >
                              ✕
                            </button>
                          )}
                        </div>

                        {/* Status Filter */}
                        <select
                          value={selectedStatusFilter}
                          onChange={(e) => setSelectedStatusFilter(e.target.value as any)}
                          style={{
                            padding: "6px 10px",
                            borderRadius: "6px",
                            border: "1px solid var(--surface-border)",
                            background: "var(--surface-dark)",
                            color: "var(--text-main)",
                            fontSize: "0.8rem",
                            outline: "none",
                            cursor: "pointer",
                          }}
                        >
                          <option value="all">All Eligibility Statuses</option>
                          <option value="Safe">Safe Standing (≥85%)</option>
                          <option value="Attention">Attention Required (75-84%)</option>
                          <option value="Debarment Risk">Debarment Risk (&lt;75%)</option>
                        </select>
                      </div>
                    </div>
                  </div>

                  {/* Summary Metric KPI Cards */}
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: "14px" }}>
                    <div style={{ background: "var(--surface-card)", border: "1px solid var(--surface-border)", borderRadius: "8px", padding: "14px 18px" }}>
                      <div style={{ fontSize: "0.72rem", color: "var(--text-dim)", fontWeight: 600, letterSpacing: "0.04em", textTransform: "uppercase" }}>
                        ENROLLED STUDENTS
                      </div>
                      <div className="font-mono" style={{ fontSize: "1.65rem", fontWeight: 700, color: "var(--text-main)", marginTop: "4px" }}>
                        {facultyRoster?.summary?.total_students || 8}
                      </div>
                      <div style={{ fontSize: "0.74rem", color: "var(--text-muted)", marginTop: "4px" }}>
                        {selectedSection} in {selectedSubject}
                      </div>
                    </div>

                    <div style={{ background: "var(--surface-card)", border: "1px solid var(--surface-border)", borderRadius: "8px", padding: "14px 18px" }}>
                      <div style={{ fontSize: "0.72rem", color: "var(--text-dim)", fontWeight: 600, letterSpacing: "0.04em", textTransform: "uppercase" }}>
                        CLASS AVERAGE ATTENDANCE
                      </div>
                      <div className="font-mono" style={{ fontSize: "1.65rem", fontWeight: 700, color: (facultyRoster?.summary?.class_avg_pct || 80.9) >= 75 ? "var(--color-success)" : "var(--color-danger)", marginTop: "4px" }}>
                        {facultyRoster?.summary?.class_avg_pct || 80.9}%
                      </div>
                      <div style={{ fontSize: "0.74rem", color: "var(--text-muted)", marginTop: "4px" }}>
                        Target Threshold: ≥75.0%
                      </div>
                    </div>

                    <div style={{ background: "var(--surface-card)", border: "1px solid var(--surface-border)", borderRadius: "8px", padding: "14px 18px" }}>
                      <div style={{ fontSize: "0.72rem", color: "var(--text-dim)", fontWeight: 600, letterSpacing: "0.04em", textTransform: "uppercase" }}>
                        SAFE STANDING (≥85%)
                      </div>
                      <div className="font-mono" style={{ fontSize: "1.65rem", fontWeight: 700, color: "var(--color-success)", marginTop: "4px" }}>
                        {facultyRoster?.summary?.safe_count || 4}
                      </div>
                      <div style={{ fontSize: "0.74rem", color: "var(--color-success)", marginTop: "4px" }}>
                        Full examination clearance
                      </div>
                    </div>

                    <div style={{ background: "var(--surface-card)", border: "1px solid var(--surface-border)", borderRadius: "8px", padding: "14px 18px" }}>
                      <div style={{ fontSize: "0.72rem", color: "var(--text-dim)", fontWeight: 600, letterSpacing: "0.04em", textTransform: "uppercase" }}>
                        DEBARMENT WARNING (&lt;75%)
                      </div>
                      <div className="font-mono" style={{ fontSize: "1.65rem", fontWeight: 700, color: "var(--color-danger)", marginTop: "4px" }}>
                        {facultyRoster?.summary?.debarment_risk_count || 3}
                      </div>
                      <div style={{ fontSize: "0.74rem", color: "var(--color-danger)", marginTop: "4px" }}>
                        Ineligible for hall tickets
                      </div>
                    </div>
                  </div>

                  {/* Debarment Advisory Callout */}
                  {(facultyRoster?.summary?.debarment_risk_count || 0) > 0 && (
                    <div
                      style={{
                        background: "#FEF2F2",
                        border: "1px solid #FECACA",
                        borderLeft: "4px solid var(--color-danger)",
                        borderRadius: "8px",
                        padding: "14px 18px",
                        display: "flex",
                        alignItems: "flex-start",
                        gap: "12px",
                      }}
                    >
                      <AlertTriangle size={20} color="var(--color-danger)" style={{ flexShrink: 0, marginTop: "2px" }} />
                      <div>
                        <div style={{ fontSize: "0.88rem", fontWeight: 700, color: "var(--color-danger)" }}>
                          Examination Debarment Advisory (§4.2 Invariant)
                        </div>
                        <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "3px", lineHeight: 1.45 }}>
                          {facultyRoster?.summary?.debarment_risk_count} student(s) in {selectedSection} have fallen strictly below 75.0% in <strong>{selectedSubject}</strong>. Faculty may review lecture attendance logs or send formal advisory notices to students and registered parent contacts.
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Attendance Roster Table */}
                  <div
                    style={{
                      background: "var(--surface-card)",
                      border: "1px solid var(--surface-border)",
                      borderRadius: "10px",
                      overflow: "hidden",
                    }}
                  >
                    <div style={{ padding: "14px 18px", borderBottom: "1px solid var(--surface-border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div style={{ fontSize: "0.9rem", fontWeight: 700, color: "var(--text-main)" }}>
                        Enrolled Students Roster ({selectedSection})
                      </div>
                      <div style={{ fontSize: "0.76rem", color: "var(--text-dim)" }}>
                        Total 40 lectures scheduled • Showing filtered records
                      </div>
                    </div>

                    <div style={{ overflowX: "auto" }}>
                      <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "0.84rem" }}>
                        <thead>
                          <tr style={{ background: "var(--surface-dark)", borderBottom: "1px solid var(--surface-border)" }}>
                            <th style={{ padding: "12px 18px", color: "var(--text-dim)", fontWeight: 600, fontSize: "0.72rem", textTransform: "uppercase" }}>Student Name & Roll No</th>
                            <th style={{ padding: "12px 14px", color: "var(--text-dim)", fontWeight: 600, fontSize: "0.72rem", textTransform: "uppercase" }}>Section</th>
                            <th style={{ padding: "12px 14px", color: "var(--text-dim)", fontWeight: 600, fontSize: "0.72rem", textTransform: "uppercase" }}>Semester</th>
                            <th style={{ padding: "12px 14px", color: "var(--text-dim)", fontWeight: 600, fontSize: "0.72rem", textTransform: "uppercase" }}>Lectures Attended</th>
                            <th style={{ padding: "12px 14px", color: "var(--text-dim)", fontWeight: 600, fontSize: "0.72rem", textTransform: "uppercase" }}>Attendance Rate</th>
                            <th style={{ padding: "12px 14px", color: "var(--text-dim)", fontWeight: 600, fontSize: "0.72rem", textTransform: "uppercase" }}>Exam Eligibility</th>
                            <th style={{ padding: "12px 18px", color: "var(--text-dim)", fontWeight: 600, fontSize: "0.72rem", textTransform: "uppercase", textAlign: "right" }}>Action</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(() => {
                            const rawList = facultyRoster?.students || DEFAULT_FACULTY_ROSTER.students;
                            const filteredList = rawList.filter((st) => {
                              if (selectedStatusFilter !== "all" && st.status !== selectedStatusFilter) {
                                return false;
                              }
                              if (studentSearchQuery.trim()) {
                                const q = studentSearchQuery.toLowerCase();
                                const matchName = st.name.toLowerCase().includes(q);
                                const matchRoll = st.roll_number.toLowerCase().includes(q);
                                const matchEmail = st.email.toLowerCase().includes(q);
                                const matchSection = st.section.toLowerCase().includes(q);
                                if (!matchName && !matchRoll && !matchEmail && !matchSection) return false;
                              }
                              return true;
                            });

                            if (filteredList.length === 0) {
                              return (
                                <tr>
                                  <td colSpan={7} style={{ padding: "40px 18px", textAlign: "center", color: "var(--text-dim)" }}>
                                    <AlertCircle size={28} color="var(--text-dim)" style={{ margin: "0 auto 8px auto", opacity: 0.5 }} />
                                    <div style={{ fontWeight: 600 }}>No students matched the selected search or filter.</div>
                                    <button
                                      type="button"
                                      onClick={() => {
                                        setStudentSearchQuery("");
                                        setSelectedStatusFilter("all");
                                      }}
                                      style={{
                                        marginTop: "10px",
                                        background: "var(--surface-elevated)",
                                        border: "1px solid var(--surface-border)",
                                        padding: "5px 12px",
                                        borderRadius: "6px",
                                        color: "var(--color-primary)",
                                        fontSize: "0.78rem",
                                        cursor: "pointer",
                                      }}
                                    >
                                      Reset Filters
                                    </button>
                                  </td>
                                </tr>
                              );
                            }

                            return filteredList.map((st) => {
                              const isSafe = st.status === "Safe";
                              const isAttention = st.status === "Attention";
                              const isDebarment = st.status === "Debarment Risk";

                              const statusBg = isSafe ? "#ECFDF5" : isAttention ? "#FFFBEB" : "#FEF2F2";
                              const statusColor = isSafe ? "var(--color-success)" : isAttention ? "var(--color-warning)" : "var(--color-danger)";
                              const statusBorder = isSafe ? "#A7F3D0" : isAttention ? "#FDE68A" : "#FECACA";

                              return (
                                <tr
                                  key={st.student_id}
                                  style={{
                                    borderBottom: "1px solid var(--surface-border)",
                                    transition: "background 0.15s ease",
                                  }}
                                  onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-elevated)")}
                                  onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                                >
                                  {/* Student Name & Roll */}
                                  <td style={{ padding: "14px 18px" }}>
                                    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                                      <div
                                        style={{
                                          width: "32px",
                                          height: "32px",
                                          borderRadius: "50%",
                                          background: isSafe ? "#ECFDF5" : isAttention ? "#FFFBEB" : "#FEF2F2",
                                          color: statusColor,
                                          fontWeight: 700,
                                          fontSize: "0.75rem",
                                          display: "flex",
                                          alignItems: "center",
                                          justifyContent: "center",
                                          border: `1px solid ${statusBorder}`,
                                          flexShrink: 0,
                                        }}
                                      >
                                        {st.name.split(" ").map((n) => n[0]).join("").slice(0, 2)}
                                      </div>
                                      <div>
                                        <div style={{ fontWeight: 600, color: "var(--text-main)" }}>{st.name}</div>
                                        <div className="font-mono" style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>
                                          {st.roll_number} • {st.email}
                                        </div>
                                      </div>
                                    </div>
                                  </td>

                                  {/* Section */}
                                  <td style={{ padding: "14px 14px" }}>
                                    <span
                                      style={{
                                        fontSize: "0.72rem",
                                        fontWeight: 600,
                                        padding: "3px 8px",
                                        borderRadius: "4px",
                                        background: "var(--surface-elevated)",
                                        border: "1px solid var(--surface-border)",
                                        color: "var(--text-main)",
                                      }}
                                    >
                                      {st.section}
                                    </span>
                                  </td>

                                  {/* Semester */}
                                  <td style={{ padding: "14px 14px", color: "var(--text-muted)" }}>
                                    Semester {st.semester}
                                  </td>

                                  {/* Lectures Attended */}
                                  <td style={{ padding: "14px 14px" }}>
                                    <span className="font-mono" style={{ fontWeight: 600, color: "var(--text-main)" }}>
                                      {st.attended_classes}
                                    </span>
                                    <span style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}> / {st.total_classes} lectures</span>
                                  </td>

                                  {/* Attendance Rate */}
                                  <td style={{ padding: "14px 14px", minWidth: "140px" }}>
                                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "4px" }}>
                                      <span className="font-mono" style={{ fontWeight: 700, fontSize: "0.85rem", color: statusColor }}>
                                        {st.attendance_pct.toFixed(1)}%
                                      </span>
                                    </div>
                                    <div style={{ width: "100%", height: "5px", background: "var(--surface-border)", borderRadius: "3px", overflow: "hidden" }}>
                                      <div
                                        style={{
                                          width: `${Math.min(st.attendance_pct, 100)}%`,
                                          height: "100%",
                                          background: statusColor,
                                          borderRadius: "3px",
                                        }}
                                      />
                                    </div>
                                  </td>

                                  {/* Exam Eligibility Badge */}
                                  <td style={{ padding: "14px 14px" }}>
                                    <span
                                      style={{
                                        display: "inline-flex",
                                        alignItems: "center",
                                        gap: "4px",
                                        fontSize: "0.72rem",
                                        fontWeight: 600,
                                        padding: "3px 8px",
                                        borderRadius: "4px",
                                        background: statusBg,
                                        color: statusColor,
                                        border: `1px solid ${statusBorder}`,
                                      }}
                                    >
                                      {isSafe && <CheckCircle2 size={12} />}
                                      {isAttention && <Clock size={12} />}
                                      {isDebarment && <AlertTriangle size={12} />}
                                      <span>{st.status}</span>
                                    </span>
                                  </td>

                                  {/* Action */}
                                  <td style={{ padding: "14px 18px", textAlign: "right" }}>
                                    <button
                                      type="button"
                                      onClick={() => handleSendNotice(st.name)}
                                      style={{
                                        padding: "4px 9px",
                                        borderRadius: "5px",
                                        fontSize: "0.74rem",
                                        fontWeight: 500,
                                        cursor: "pointer",
                                        background: isDebarment ? "var(--color-danger)" : "var(--surface-elevated)",
                                        color: isDebarment ? "#FFFFFF" : "var(--text-main)",
                                        border: isDebarment ? "none" : "1px solid var(--surface-border)",
                                        display: "inline-flex",
                                        alignItems: "center",
                                        gap: "4px",
                                      }}
                                      onMouseEnter={(e) => {
                                        if (!isDebarment) e.currentTarget.style.background = "var(--surface-hover)";
                                      }}
                                      onMouseLeave={(e) => {
                                        if (!isDebarment) e.currentTarget.style.background = "var(--surface-elevated)";
                                      }}
                                    >
                                      <Mail size={12} />
                                      <span>{isDebarment ? "Debarment Notice" : "Send Advisory"}</span>
                                    </button>
                                  </td>
                                </tr>
                              );
                            });
                          })()}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </>
              ) : (
                /* Student & Parent Personal Attendance View */
                <>
                  {/* Debarment Warning Notification Box */}
                  <div
                    style={{
                      background: "#FEF2F2",
                      border: "1px solid #FECACA",
                      borderLeft: "3px solid var(--color-danger)",
                      borderRadius: "8px",
                      padding: "14px 18px",
                      display: "flex",
                      alignItems: "center",
                      gap: "12px",
                    }}
                  >
                    <AlertTriangle size={20} color="var(--color-danger)" />
                    <div>
                      <div style={{ fontSize: "0.9rem", fontWeight: 600, color: "var(--color-danger)" }}>
                        University Attendance Policy Invariant (§4.2)
                      </div>
                      <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "2px" }}>
                        Students must maintain $\ge 75\%$ in each subject. Any course below 75% incurs an automated examination debarment warning.
                      </div>
                    </div>
                  </div>

                  {/* Cards Grid */}
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: "16px" }}>
                    {(dashboardData?.attendance_records || DEFAULT_ATTENDANCE).map((rec: SubjectAttendance) => (
                      <AttendanceCard key={rec.id} record={rec} />
                    ))}
                  </div>
                </>
              )}
            </div>
          )}

          {/* ===================== TAB: POLICIES ===================== */}
          {activeTab === "policies" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
              <div>
                <h2 style={{ fontSize: "1.2rem", fontWeight: 700, color: "var(--text-main)" }}>
                  Institutional Regulations & Vector Documents
                </h2>
                <p style={{ fontSize: "0.82rem", color: "var(--text-dim)", marginTop: "2px" }}>
                  Policy documents pre-filtered by zero-trust role claims (`allowed_roles`).
                </p>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                <div style={{ background: "var(--surface-card)", border: "1px solid var(--surface-border)", borderRadius: "10px", padding: "18px 20px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                    <div style={{ fontSize: "0.98rem", fontWeight: 600, color: "var(--text-main)" }}>
                      Academic Regulations 2026 §4.2: Attendance Requirements & Examination Eligibility
                    </div>
                    <span style={{ fontSize: "0.7rem", background: "#ECFDF5", color: "var(--color-success)", padding: "2px 7px", borderRadius: "4px", fontWeight: 600, border: "1px solid #A7F3D0" }}>
                      PUBLIC
                    </span>
                  </div>
                  <p style={{ fontSize: "0.84rem", color: "var(--text-muted)", lineHeight: 1.5 }}>
                    Every enrolled student must maintain a minimum attendance threshold of 75% in each registered course to be eligible to appear for the end-semester final university examinations. Students falling between 65% and 74% due to verified medical emergencies may apply for condonation through the Dean of Academic Affairs.
                  </p>
                </div>

                <div style={{ background: "var(--surface-card)", border: "1px solid var(--surface-border)", borderRadius: "10px", padding: "18px 20px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                    <div style={{ fontSize: "0.98rem", fontWeight: 600, color: "var(--text-main)" }}>
                      Examination Code & Grading Policy 2026 (§7.1)
                    </div>
                    <span style={{ fontSize: "0.7rem", background: "#ECFDF5", color: "var(--color-success)", padding: "2px 7px", borderRadius: "4px", fontWeight: 600, border: "1px solid #A7F3D0" }}>
                      PUBLIC
                    </span>
                  </div>
                  <p style={{ fontSize: "0.84rem", color: "var(--text-muted)", lineHeight: 1.5 }}>
                    The grading framework follows a standard 10-point scale: A+ (90-100%), A (80-89%), B (70-79%), C (60-69%), and F (&lt;60%). Course evaluations are distributed as: Continuous Internal Evaluation (CIE) comprising midterms (30%) and quizzes/assignments (20%), and Semester End Examination (SEE) weighing 50%.
                  </p>
                </div>

                <div style={{ background: "var(--surface-card)", border: "1px solid var(--surface-border)", borderRadius: "10px", padding: "18px 20px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                    <div style={{ fontSize: "0.98rem", fontWeight: 600, color: "var(--text-main)" }}>
                      SafeTransit Fleet & Student Commute Guidelines (§11.3)
                    </div>
                    <span style={{ fontSize: "0.7rem", background: "#ECFDF5", color: "var(--color-success)", padding: "2px 7px", borderRadius: "4px", fontWeight: 600, border: "1px solid #A7F3D0" }}>
                      PUBLIC
                    </span>
                  </div>
                  <p style={{ fontSize: "0.84rem", color: "var(--text-muted)", lineHeight: 1.5 }}>
                    SafeTransit operates daily from 07:00 to 19:30 across 20 designated regional routes. Bus tracking is streamed via real-time telemetry markers. RFID boarding confirmation alerts are dispatched to registered parent contacts upon stop arrival.
                  </p>
                </div>

                {/* Faculty Restricted Document */}
                <div style={{ background: "var(--surface-card)", border: "1px solid #FDE68A", borderRadius: "10px", padding: "18px 20px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                    <div style={{ fontSize: "0.98rem", fontWeight: 600, color: "var(--color-warning)" }}>
                      Faculty Compensation & Research Grant Discretionary Fund Guidelines (§18.4)
                    </div>
                    <span style={{ fontSize: "0.7rem", background: "#FFFBEB", color: "var(--color-warning)", padding: "2px 7px", borderRadius: "4px", fontWeight: 600, border: "1px solid #FDE68A" }}>
                      FACULTY, ADMIN ONLY
                    </span>
                  </div>
                  <p style={{ fontSize: "0.84rem", color: "var(--text-muted)", lineHeight: 1.5 }}>
                    CONFIDENTIAL / RESTRICTED ACCESS: Faculty annual compensation consists of base academic scale, departmental chair stipends, and research publication incentives. (Attempting to query this as a student or parent triggers the zero-trust firewall refusal).
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* ===================== TAB: SECURITY AUDITS (ADMIN ONLY) ===================== */}
          {activeTab === "audits" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <ShieldAlert size={20} color="var(--color-danger)" />
                <h2 style={{ fontSize: "1.2rem", fontWeight: 700, color: "var(--text-main)" }}>
                  Zero-Trust Privilege Probe & Security Logs
                </h2>
              </div>
              <p style={{ fontSize: "0.82rem", color: "var(--text-dim)" }}>
                Real-time security events captured whenever unauthorized cross-role queries occur.
              </p>

              <div style={{ background: "var(--surface-card)", border: "1px solid var(--surface-border)", borderRadius: "10px", overflow: "hidden" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "0.82rem" }}>
                  <thead>
                    <tr style={{ background: "var(--surface-elevated)", color: "var(--text-dim)", borderBottom: "1px solid var(--surface-border)" }}>
                      <th style={{ padding: "10px 14px" }}>EVENT ID</th>
                      <th style={{ padding: "10px 14px" }}>ROLE</th>
                      <th style={{ padding: "10px 14px" }}>EVENT TYPE</th>
                      <th style={{ padding: "10px 14px" }}>DETAILS</th>
                      <th style={{ padding: "10px 14px" }}>TIMESTAMP</th>
                    </tr>
                  </thead>
                  <tbody>
                    {auditLogs.length > 0 ? (
                      auditLogs.map((log) => (
                        <tr key={log.id} style={{ borderBottom: "1px solid var(--surface-border-subtle)" }}>
                          <td className="font-mono" style={{ padding: "11px 14px", color: "var(--text-dim)" }}>
                            #{log.id}
                          </td>
                          <td style={{ padding: "11px 14px" }}>
                            <span style={{ padding: "2px 7px", borderRadius: "4px", fontSize: "0.7rem", fontWeight: 600, background: "#FEF2F2", color: "var(--color-danger)", border: "1px solid #FECACA" }}>
                              {log.role.toUpperCase()}
                            </span>
                          </td>
                          <td className="font-mono" style={{ padding: "11px 14px", color: "var(--color-warning)" }}>
                            {log.event_type}
                          </td>
                          <td style={{ padding: "11px 14px", color: "var(--text-main)" }}>
                            {log.details}
                          </td>
                          <td className="font-mono" style={{ padding: "11px 14px", color: "var(--text-dim)", fontSize: "0.72rem" }}>
                            {new Date(log.timestamp).toLocaleString()}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={5} style={{ padding: "24px", textAlign: "center", color: "var(--text-muted)" }}>
                          No privilege violations logged yet. Try querying restricted faculty compensation in the AI Assistant to trigger an intercept!
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Floating RBAC Chat Drawer */}
      <ChatDrawer
        token={token}
        userRole={user?.role || "student"}
        isOpen={isChatOpen}
        onToggle={() => setIsChatOpen(!isChatOpen)}
      />
    </div>
  );
}
