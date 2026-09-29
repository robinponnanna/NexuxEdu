"use client";

import React, { useState, useEffect } from "react";
import {
  GraduationCap,
  BookOpen,
  CheckCircle2,
  AlertTriangle,
  Clock,
  HelpCircle,
  Sparkles,
  ArrowRight,
  Filter,
  Layers,
  ChevronRight,
  Search,
  Loader2,
  AlertCircle,
  TrendingUp,
} from "lucide-react";
import {
  StudentMarksOverviewResponse,
  StudentSubjectSummary,
  getStudentMarksOverview,
} from "@/lib/api";

interface AcademicOverviewProps {
  token: string;
  onSelectSubject: (subjectId: number) => void;
  onStudyModuleDirect?: (subjectId: number, moduleId: number) => void;
}

export const AcademicOverview: React.FC<AcademicOverviewProps> = ({
  token,
  onSelectSubject,
  onStudyModuleDirect,
}) => {
  const [overview, setOverview] = useState<StudentMarksOverviewResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<"all" | "Strong" | "Developing" | "Needs Support">("all");
  const [semesterFilter, setSemesterFilter] = useState<number | undefined>(undefined);
  const [searchQuery, setSearchQuery] = useState<string>("");

  useEffect(() => {
    let isMounted = true;
    const loadOverview = async () => {
      setIsLoading(true);
      setErrorMessage(null);
      try {
        const data = await getStudentMarksOverview(token, semesterFilter, statusFilter);
        if (isMounted) setOverview(data);
      } catch (err: any) {
        if (isMounted) setErrorMessage(err.message || "Failed to load academic records.");
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    if (token) {
      loadOverview();
    }
    return () => {
      isMounted = false;
    };
  }, [token, statusFilter, semesterFilter]);

  const subjects = overview?.subjects || [];

  // Filter by local search query if typed
  const filteredSubjects = subjects.filter((s) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      s.code.toLowerCase().includes(q) ||
      s.name.toLowerCase().includes(q) ||
      s.department.toLowerCase().includes(q)
    );
  });

  // Calculate high-level status distribution counts
  const strongCount = subjects.filter((s) => s.status === "Strong").length;
  const developingCount = subjects.filter((s) => s.status === "Developing").length;
  const needsSupportCount = subjects.filter((s) => s.status === "Needs Support").length;

  // Find subject with lowest overall score or lowest module score
  const lowestModuleSubject = subjects
    .filter((s) => s.weakest_module)
    .sort((a, b) => (a.weakest_module!.percentage) - (b.weakest_module!.percentage))[0];

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "Strong":
        return {
          bg: "#ECFDF5",
          color: "var(--color-success)",
          border: "#A7F3D0",
          icon: CheckCircle2,
        };
      case "Developing":
        return {
          bg: "#FFFBEB",
          color: "var(--color-warning)",
          border: "#FDE68A",
          icon: Clock,
        };
      case "Needs Support":
        return {
          bg: "#FEF2F2",
          color: "var(--color-danger)",
          border: "#FECACA",
          icon: AlertTriangle,
        };
      default:
        return {
          bg: "var(--surface-elevated)",
          color: "var(--text-dim)",
          border: "var(--surface-border)",
          icon: HelpCircle,
        };
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Top Banner / Academic Orientation */}
      <div
        style={{
          background: "var(--surface-card)",
          border: "1px solid var(--surface-border)",
          borderRadius: "10px",
          padding: "22px 26px",
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "16px",
          boxShadow: "var(--shadow-sm)",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
            <span
              style={{
                fontSize: "0.7rem",
                fontWeight: 700,
                letterSpacing: "0.06em",
                textTransform: "uppercase",
                padding: "2px 7px",
                borderRadius: "4px",
                background: "#F0F9FF",
                color: "var(--color-student)",
                border: "1px solid #BAE6FD",
              }}
            >
              Academic Intelligence
            </span>
            <span style={{ fontSize: "0.8rem", color: "var(--text-dim)" }}>
              {overview?.student_name || "Jane Doe"} • Roll: {overview?.roll_number || "CS-2023-042"} • Semester {overview?.semester || 6}
            </span>
          </div>
          <h1 style={{ fontSize: "1.45rem", fontWeight: 700, color: "var(--text-main)", letterSpacing: "-0.01em" }}>
            Student Academic Support & Mastery
          </h1>
          <p style={{ fontSize: "0.84rem", color: "var(--text-muted)", marginTop: "4px" }}>
            Course outcome diagnostics, continuous assessment analytics, and grounded AI study micro-lessons.
          </p>
        </div>
      </div>

      {/* KPI Stats Row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px" }}>
        {/* Overall Academic Average */}
        <div style={{ background: "var(--surface-card)", border: "1px solid var(--surface-border)", borderRadius: "10px", padding: "18px 20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <span style={{ fontSize: "0.74rem", color: "var(--text-dim)", fontWeight: 700, letterSpacing: "0.04em", textTransform: "uppercase" }}>
              Overall Standing
            </span>
            <TrendingUp size={18} color="var(--color-student)" />
          </div>
          <div className="font-mono" style={{ fontSize: "1.85rem", fontWeight: 700, color: "var(--text-main)" }}>
            {overview?.overall_percentage != null ? `${overview.overall_percentage.toFixed(1)}%` : "—"}
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "6px" }}>
            Cumulative across {subjects.length || 6} enrolled subjects
          </div>
        </div>

        {/* Strong Courses */}
        <div style={{ background: "var(--surface-card)", border: "1px solid var(--surface-border)", borderRadius: "10px", padding: "18px 20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <span style={{ fontSize: "0.74rem", color: "var(--color-success)", fontWeight: 700, letterSpacing: "0.04em", textTransform: "uppercase" }}>
              Strong Mastery (≥75%)
            </span>
            <CheckCircle2 size={18} color="var(--color-success)" />
          </div>
          <div className="font-mono" style={{ fontSize: "1.85rem", fontWeight: 700, color: "var(--color-success)" }}>
            {strongCount}
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "6px" }}>
            High Course Outcome alignment
          </div>
        </div>

        {/* Developing Courses */}
        <div style={{ background: "var(--surface-card)", border: "1px solid var(--surface-border)", borderRadius: "10px", padding: "18px 20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <span style={{ fontSize: "0.74rem", color: "var(--color-warning)", fontWeight: 700, letterSpacing: "0.04em", textTransform: "uppercase" }}>
              Developing (60-74%)
            </span>
            <Clock size={18} color="var(--color-warning)" />
          </div>
          <div className="font-mono" style={{ fontSize: "1.85rem", fontWeight: 700, color: "var(--color-warning)" }}>
            {developingCount}
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "6px" }}>
            Recommended for targeted revision
          </div>
        </div>

        {/* Needs Support Courses */}
        <div style={{ background: "var(--surface-card)", border: "1px solid var(--surface-border)", borderRadius: "10px", padding: "18px 20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <span style={{ fontSize: "0.74rem", color: "var(--color-danger)", fontWeight: 700, letterSpacing: "0.04em", textTransform: "uppercase" }}>
              Needs Attention (&lt;60%)
            </span>
            <AlertTriangle size={18} color="var(--color-danger)" />
          </div>
          <div className="font-mono" style={{ fontSize: "1.85rem", fontWeight: 700, color: "var(--color-danger)" }}>
            {needsSupportCount}
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "6px" }}>
            Identified weak syllabus modules
          </div>
        </div>
      </div>

      {/* ================= HERO DIAGNOSIS CALLOUT ================= */}
      {lowestModuleSubject && lowestModuleSubject.weakest_module && (
        <div
          style={{
            background: "#FEF2F2",
            border: "1px solid #FECACA",
            borderLeft: "5px solid var(--color-danger)",
            borderRadius: "10px",
            padding: "18px 24px",
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "16px",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
            <div
              style={{
                width: "42px",
                height: "42px",
                borderRadius: "8px",
                background: "#FEE2E2",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--color-danger)",
                flexShrink: 0,
              }}
            >
              <AlertTriangle size={20} />
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span
                  style={{
                    fontSize: "0.7rem",
                    fontWeight: 700,
                    textTransform: "uppercase",
                    color: "var(--color-danger)",
                  }}
                >
                  Diagnostic Callout · Weakest Course Outcome
                </span>
                <span style={{ fontSize: "0.74rem", color: "var(--text-dim)" }}>
                  {lowestModuleSubject.code} — {lowestModuleSubject.name}
                </span>
              </div>
              <div style={{ fontSize: "1.05rem", fontWeight: 700, color: "var(--text-main)", marginTop: "2px" }}>
                {lowestModuleSubject.weakest_module.co_code}: {lowestModuleSubject.weakest_module.title} —{" "}
                <span style={{ color: "var(--color-danger)" }}>
                  {lowestModuleSubject.weakest_module.percentage.toFixed(1)}%
                </span>
              </div>
              <div style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginTop: "2px" }}>
                Score: {lowestModuleSubject.weakest_module.marks_obtained} / {lowestModuleSubject.weakest_module.marks_available} marks.
                Study notes and interactive AI explanations are available to remediate this concept.
              </div>
            </div>
          </div>

          <div style={{ display: "flex", gap: "10px" }}>
            <button
              type="button"
              onClick={() => onSelectSubject(lowestModuleSubject.id)}
              style={{
                background: "var(--color-primary)",
                color: "#FFFFFF",
                border: "none",
                borderRadius: "8px",
                padding: "9px 16px",
                fontSize: "0.82rem",
                fontWeight: 600,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "6px",
                boxShadow: "var(--shadow-sm)",
              }}
            >
              <BookOpen size={14} />
              <span>Review Subject & Notes</span>
            </button>
          </div>
        </div>
      )}

      {/* ================= MARKS EXPLORER & FILTERING ================= */}
      <div
        style={{
          background: "var(--surface-card)",
          border: "1px solid var(--surface-border)",
          borderRadius: "10px",
          padding: "20px 24px",
          boxShadow: "var(--shadow-sm)",
          display: "flex",
          flexDirection: "column",
          gap: "18px",
        }}
      >
        {/* Controls Header */}
        <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: "14px" }}>
          <div>
            <h2 style={{ fontSize: "1.15rem", fontWeight: 700, color: "var(--text-main)" }}>
              Enrolled Courses & Course Outcome Status
            </h2>
            <p style={{ fontSize: "0.78rem", color: "var(--text-dim)", marginTop: "2px" }}>
              Filter by mastery classification or search specific course titles.
            </p>
          </div>

          {/* Search Box */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                background: "var(--surface-elevated)",
                border: "1px solid var(--surface-border)",
                borderRadius: "6px",
                padding: "6px 10px",
                minWidth: "220px",
              }}
            >
              <Search size={14} color="var(--text-dim)" />
              <input
                type="text"
                placeholder="Search subject or code..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  border: "none",
                  background: "transparent",
                  outline: "none",
                  fontSize: "0.82rem",
                  color: "var(--text-main)",
                  width: "100%",
                }}
              />
            </div>
          </div>
        </div>

        {/* Filter Tabs Bar */}
        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "8px", paddingTop: "12px", borderTop: "1px solid var(--surface-border)" }}>
          <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-dim)", textTransform: "uppercase", marginRight: "4px" }}>
            Status Filter:
          </span>

          {(["all", "Strong", "Developing", "Needs Support"] as const).map((st) => {
            const isSelected = statusFilter === st;
            const count =
              st === "all"
                ? subjects.length
                : st === "Strong"
                ? strongCount
                : st === "Developing"
                ? developingCount
                : needsSupportCount;

            return (
              <button
                key={st}
                type="button"
                onClick={() => setStatusFilter(st)}
                style={{
                  padding: "6px 12px",
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
                <span>{st === "all" ? "All Subjects" : st}</span>
                <span
                  style={{
                    fontSize: "0.68rem",
                    padding: "1px 5px",
                    borderRadius: "10px",
                    background: isSelected ? "var(--color-primary)" : "var(--surface-border)",
                    color: isSelected ? "#FFFFFF" : "var(--text-muted)",
                  }}
                >
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        {/* Loading State */}
        {isLoading && (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "40px 0", gap: "10px", color: "var(--text-dim)" }}>
            <Loader2 size={20} className="animate-spin" />
            <span style={{ fontSize: "0.85rem" }}>Loading academic records from campus database...</span>
          </div>
        )}

        {/* Error State */}
        {errorMessage && !isLoading && (
          <div
            style={{
              background: "#FEF2F2",
              border: "1px solid #FECACA",
              borderRadius: "8px",
              padding: "14px 18px",
              color: "var(--color-danger)",
              fontSize: "0.85rem",
              display: "flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            <AlertCircle size={18} />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Subjects Grid */}
        {!isLoading && !errorMessage && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: "16px" }}>
            {filteredSubjects.map((sub: StudentSubjectSummary) => {
              const sBadge = getStatusBadge(sub.status);
              const SIcon = sBadge.icon;

              return (
                <div
                  key={sub.id}
                  style={{
                    background: "var(--surface-elevated)",
                    border: "1px solid var(--surface-border)",
                    borderRadius: "10px",
                    padding: "18px 20px",
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "space-between",
                    gap: "14px",
                    boxShadow: "var(--shadow-sm)",
                    transition: "all 0.15s ease",
                  }}
                >
                  <div>
                    {/* Header: Code, Title, Status */}
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
                      <div>
                        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                          <span
                            style={{
                              fontSize: "0.72rem",
                              fontWeight: 700,
                              color: "var(--text-dim)",
                              background: "var(--surface-card)",
                              padding: "2px 6px",
                              borderRadius: "4px",
                              border: "1px solid var(--surface-border)",
                            }}
                          >
                            {sub.code}
                          </span>
                          <span style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>
                            {sub.credits} Credits • Sem {sub.semester}
                          </span>
                        </div>
                        <h3 style={{ fontSize: "1.05rem", fontWeight: 700, color: "var(--text-main)", marginTop: "4px" }}>
                          {sub.name}
                        </h3>
                      </div>

                      <div
                        style={{
                          padding: "3px 8px",
                          borderRadius: "12px",
                          background: sBadge.bg,
                          border: `1px solid ${sBadge.border}`,
                          color: sBadge.color,
                          fontSize: "0.72rem",
                          fontWeight: 700,
                          display: "flex",
                          alignItems: "center",
                          gap: "4px",
                          whiteSpace: "nowrap",
                        }}
                      >
                        <SIcon size={12} />
                        <span>{sub.status}</span>
                      </div>
                    </div>

                    {/* Score Bar */}
                    <div style={{ margin: "10px 0" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem", marginBottom: "4px" }}>
                        <span style={{ color: "var(--text-dim)" }}>Marks: <strong>{sub.total_marks_obtained} / {sub.total_marks_available}</strong></span>
                        <span className="font-mono" style={{ fontWeight: 700, color: sBadge.color }}>
                          {sub.percentage.toFixed(1)}%
                        </span>
                      </div>
                      <div style={{ width: "100%", height: "6px", background: "var(--surface-border)", borderRadius: "3px", overflow: "hidden" }}>
                        <div
                          style={{
                            height: "100%",
                            width: `${Math.min(100, sub.percentage)}%`,
                            background: sBadge.color,
                            borderRadius: "3px",
                          }}
                        />
                      </div>
                    </div>

                    {/* Strongest / Weakest Module Chips */}
                    <div style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "0.74rem", marginTop: "8px" }}>
                      {sub.weakest_module && (
                        <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--text-muted)" }}>
                          <span style={{ fontWeight: 700, color: "var(--color-danger)" }}>Weakest:</span>
                          <span style={{ color: "var(--text-main)", fontWeight: 600 }}>
                            {sub.weakest_module.co_code} ({sub.weakest_module.percentage.toFixed(0)}%)
                          </span>
                          <span style={{ color: "var(--text-dim)" }}>— {sub.weakest_module.title}</span>
                        </div>
                      )}

                      {sub.strongest_module && (
                        <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--text-muted)" }}>
                          <span style={{ fontWeight: 700, color: "var(--color-success)" }}>Strongest:</span>
                          <span style={{ color: "var(--text-main)", fontWeight: 600 }}>
                            {sub.strongest_module.co_code} ({sub.strongest_module.percentage.toFixed(0)}%)
                          </span>
                          <span style={{ color: "var(--text-dim)" }}>— {sub.strongest_module.title}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Open Subject Details CTA */}
                  <div style={{ borderTop: "1px solid var(--surface-border)", paddingTop: "10px", display: "flex", justifyContent: "flex-end" }}>
                    <button
                      type="button"
                      onClick={() => onSelectSubject(sub.id)}
                      style={{
                        background: "var(--surface-card)",
                        border: "1px solid var(--surface-border)",
                        borderRadius: "6px",
                        padding: "6px 12px",
                        fontSize: "0.78rem",
                        fontWeight: 600,
                        color: "var(--text-main)",
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-hover)")}
                      onMouseLeave={(e) => (e.currentTarget.style.background = "var(--surface-card)")}
                    >
                      <span>View Analysis & Notes</span>
                      <ChevronRight size={14} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Empty Filter State */}
        {!isLoading && !errorMessage && filteredSubjects.length === 0 && (
          <div
            style={{
              textAlign: "center",
              padding: "40px 20px",
              background: "var(--surface-elevated)",
              borderRadius: "8px",
              border: "1px solid var(--surface-border)",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "8px",
            }}
          >
            <Layers size={28} color="var(--text-dim)" />
            <div style={{ color: "var(--text-main)", fontSize: "0.9rem", fontWeight: 600 }}>
              No subjects match the selected filter
            </div>
            <p style={{ color: "var(--text-muted)", fontSize: "0.78rem", maxWidth: "400px" }}>
              Try selecting a different status filter or clear your search keyword.
            </p>
            <button
              type="button"
              onClick={() => {
                setStatusFilter("all");
                setSearchQuery("");
              }}
              style={{
                marginTop: "6px",
                background: "var(--surface-card)",
                border: "1px solid var(--surface-border)",
                borderRadius: "6px",
                padding: "6px 14px",
                fontSize: "0.78rem",
                fontWeight: 600,
                color: "var(--color-primary)",
                cursor: "pointer",
              }}
            >
              Reset Filters
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
