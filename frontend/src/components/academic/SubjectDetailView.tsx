"use client";

import React, { useState } from "react";
import {
  ArrowLeft,
  BookOpen,
  AlertTriangle,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Clock,
  Layers,
  Sparkles,
  ChevronDown,
  ChevronUp,
  FileText,
} from "lucide-react";
import {
  SubjectMarksDetailResponse,
  SubjectAssessmentDetail,
  SubjectModuleMarksDetail,
} from "@/lib/api";

interface SubjectDetailViewProps {
  detail: SubjectMarksDetailResponse;
  onBack: () => void;
  onStudyModule: (moduleId: number) => void;
}

export const SubjectDetailView: React.FC<SubjectDetailViewProps> = ({
  detail,
  onBack,
  onStudyModule,
}) => {
  const [expandedAssessmentId, setExpandedAssessmentId] = useState<number | null>(null);

  const subject = detail.subject;
  const weakest = detail.weakest_module;
  const strongest = detail.strongest_module;

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

  const statusStyle = getStatusBadge(detail.status);
  const StatusIcon = statusStyle.icon;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "22px" }}>
      {/* Top Header Navigation */}
      <div
        style={{
          background: "var(--surface-card)",
          border: "1px solid var(--surface-border)",
          borderRadius: "10px",
          padding: "20px 26px",
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "16px",
          boxShadow: "var(--shadow-sm)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <button
            type="button"
            onClick={onBack}
            style={{
              background: "var(--surface-elevated)",
              border: "1px solid var(--surface-border)",
              borderRadius: "8px",
              padding: "8px 12px",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "6px",
              fontSize: "0.82rem",
              fontWeight: 600,
              color: "var(--text-main)",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-hover)")}
            onMouseLeave={(e) => (e.currentTarget.style.background = "var(--surface-elevated)")}
          >
            <ArrowLeft size={16} />
            <span>All Courses</span>
          </button>

          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span
                style={{
                  fontSize: "0.72rem",
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                  padding: "2px 8px",
                  borderRadius: "4px",
                  background: "var(--surface-elevated)",
                  color: "var(--text-dim)",
                  border: "1px solid var(--surface-border)",
                }}
              >
                {subject.code}
              </span>
              <span style={{ fontSize: "0.8rem", color: "var(--text-dim)" }}>
                {subject.department} • Semester {subject.semester} • {subject.credits} Credits
              </span>
            </div>
            <h1 style={{ fontSize: "1.45rem", fontWeight: 700, color: "var(--text-main)", marginTop: "4px" }}>
              {subject.name}
            </h1>
          </div>
        </div>

        {/* Overall Score Badge */}
        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: "0.72rem", color: "var(--text-dim)", fontWeight: 600, textTransform: "uppercase" }}>
              Course Standing
            </div>
            <div className="font-mono" style={{ fontSize: "1.6rem", fontWeight: 700, color: statusStyle.color }}>
              {detail.percentage.toFixed(1)}%
            </div>
            <div style={{ fontSize: "0.74rem", color: "var(--text-dim)" }}>
              {detail.total_marks_obtained} / {detail.total_marks_available} Marks
            </div>
          </div>

          <div
            style={{
              padding: "6px 12px",
              borderRadius: "20px",
              background: statusStyle.bg,
              border: `1px solid ${statusStyle.border}`,
              color: statusStyle.color,
              fontSize: "0.78rem",
              fontWeight: 700,
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <StatusIcon size={14} />
            <span>{detail.status}</span>
          </div>
        </div>
      </div>

      {/* ================= HERO DIAGNOSIS: WEAKEST MODULE CALLOUT ================= */}
      {weakest && (
        <div
          style={{
            background: "#FEF2F2",
            border: "1px solid #FECACA",
            borderLeft: "5px solid var(--color-danger)",
            borderRadius: "10px",
            padding: "20px 24px",
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "18px",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <div style={{ display: "flex", alignItems: "flex-start", gap: "14px", maxWidth: "680px" }}>
            <div
              style={{
                width: "40px",
                height: "40px",
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
                    letterSpacing: "0.05em",
                    color: "var(--color-danger)",
                  }}
                >
                  Diagnostic Priority · Needs Attention
                </span>
                <span style={{ fontSize: "0.74rem", color: "var(--text-dim)" }}>
                  Lowest Course Outcome Score
                </span>
              </div>
              <h2 style={{ fontSize: "1.15rem", fontWeight: 700, color: "var(--text-main)", marginTop: "2px" }}>
                {weakest.co_code}: {weakest.title}
              </h2>
              <p style={{ fontSize: "0.82rem", color: "var(--text-muted)", marginTop: "4px" }}>
                Score: <strong>{weakest.percentage.toFixed(1)}%</strong> ({weakest.marks_obtained} / {weakest.marks_available} marks).
                Reviewing study notes and micro-lessons for this module will significantly boost your end-term performance.
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={() => onStudyModule(weakest.id)}
            style={{
              background: "var(--color-primary)",
              color: "#FFFFFF",
              border: "none",
              borderRadius: "8px",
              padding: "10px 20px",
              fontSize: "0.85rem",
              fontWeight: 700,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "8px",
              boxShadow: "var(--shadow-sm)",
              whiteSpace: "nowrap",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.opacity = "0.9")}
            onMouseLeave={(e) => (e.currentTarget.style.opacity = "1")}
          >
            <BookOpen size={16} />
            <span>Study This Module</span>
          </button>
        </div>
      )}

      {/* ================= GRID: CO/MODULES & ASSESSMENTS ================= */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))", gap: "20px" }}>
        
        {/* Course Outcomes / Module Breakdown */}
        <div
          style={{
            background: "var(--surface-card)",
            border: "1px solid var(--surface-border)",
            borderRadius: "10px",
            padding: "20px 24px",
            boxShadow: "var(--shadow-sm)",
            display: "flex",
            flexDirection: "column",
            gap: "16px",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <h2 style={{ fontSize: "1.05rem", fontWeight: 700, color: "var(--text-main)", display: "flex", alignItems: "center", gap: "8px" }}>
                <Layers size={17} color="var(--color-student)" />
                <span>Course Outcomes (CO) Performance</span>
              </h2>
              <p style={{ fontSize: "0.78rem", color: "var(--text-dim)", marginTop: "2px" }}>
                Granular mastery tracking across all 5 syllabus modules
              </p>
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {detail.modules.map((mod: SubjectModuleMarksDetail) => {
              const mStyle = getStatusBadge(mod.status);
              const isWeakest = weakest?.id === mod.id;
              const isStrongest = strongest?.id === mod.id;

              return (
                <div
                  key={mod.id}
                  style={{
                    background: isWeakest ? "#FFFBFB" : "var(--surface-elevated)",
                    border: "1px solid",
                    borderColor: isWeakest ? "#FECACA" : "var(--surface-border)",
                    borderRadius: "8px",
                    padding: "14px 16px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "8px",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <span style={{ fontSize: "0.72rem", fontWeight: 700, color: "var(--color-student)" }}>
                          {mod.co_code}
                        </span>
                        <span style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--text-main)" }}>
                          {mod.title}
                        </span>
                        {isWeakest && (
                          <span
                            style={{
                              fontSize: "0.65rem",
                              fontWeight: 700,
                              background: "#FEF2F2",
                              color: "var(--color-danger)",
                              border: "1px solid #FECACA",
                              padding: "1px 6px",
                              borderRadius: "10px",
                              textTransform: "uppercase",
                            }}
                          >
                            Weakest Area
                          </span>
                        )}
                        {isStrongest && (
                          <span
                            style={{
                              fontSize: "0.65rem",
                              fontWeight: 700,
                              background: "#ECFDF5",
                              color: "var(--color-success)",
                              border: "1px solid #A7F3D0",
                              padding: "1px 6px",
                              borderRadius: "10px",
                              textTransform: "uppercase",
                            }}
                          >
                            Strongest
                          </span>
                        )}
                      </div>
                      {mod.description && (
                        <p style={{ fontSize: "0.76rem", color: "var(--text-muted)", marginTop: "3px", lineHeight: 1.3 }}>
                          {mod.description}
                        </p>
                      )}
                    </div>

                    <div style={{ textAlign: "right", minWidth: "80px" }}>
                      <span className="font-mono" style={{ fontSize: "0.95rem", fontWeight: 700, color: mStyle.color }}>
                        {mod.percentage.toFixed(1)}%
                      </span>
                      <div style={{ fontSize: "0.7rem", color: "var(--text-dim)" }}>
                        {mod.marks_obtained} / {mod.marks_available}
                      </div>
                    </div>
                  </div>

                  {/* Progress Bar */}
                  <div style={{ width: "100%", height: "6px", background: "var(--surface-border)", borderRadius: "3px", overflow: "hidden" }}>
                    <div
                      style={{
                        height: "100%",
                        width: `${Math.min(100, mod.percentage)}%`,
                        background: mStyle.color,
                        borderRadius: "3px",
                      }}
                    />
                  </div>

                  {/* Module Action CTA */}
                  <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "2px" }}>
                    <button
                      type="button"
                      onClick={() => onStudyModule(mod.id)}
                      style={{
                        background: "transparent",
                        border: "none",
                        color: "var(--color-student)",
                        fontSize: "0.76rem",
                        fontWeight: 600,
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        gap: "4px",
                        padding: "2px 4px",
                      }}
                    >
                      <BookOpen size={12} />
                      <span>Study Module Notes →</span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Assessment Breakdown Table */}
        <div
          style={{
            background: "var(--surface-card)",
            border: "1px solid var(--surface-border)",
            borderRadius: "10px",
            padding: "20px 24px",
            boxShadow: "var(--shadow-sm)",
            display: "flex",
            flexDirection: "column",
            gap: "16px",
          }}
        >
          <div>
            <h2 style={{ fontSize: "1.05rem", fontWeight: 700, color: "var(--text-main)", display: "flex", alignItems: "center", gap: "8px" }}>
              <FileText size={17} color="var(--color-faculty)" />
              <span>Continuous & Term Assessment Scores</span>
            </h2>
            <p style={{ fontSize: "0.78rem", color: "var(--text-dim)", marginTop: "2px" }}>
              Breakdown across CA1..CA3, Midterm, and Endterm examinations
            </p>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {detail.assessments.map((a: SubjectAssessmentDetail) => {
              const aStatus = getStatusBadge(a.percentage >= 75 ? "Strong" : a.percentage >= 60 ? "Developing" : "Needs Support");
              const isExpanded = expandedAssessmentId === a.id;

              return (
                <div
                  key={a.id}
                  style={{
                    background: "var(--surface-elevated)",
                    border: "1px solid var(--surface-border)",
                    borderRadius: "8px",
                    overflow: "hidden",
                  }}
                >
                  <div
                    onClick={() => setExpandedAssessmentId(isExpanded ? null : a.id)}
                    style={{
                      padding: "12px 16px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      cursor: "pointer",
                    }}
                  >
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span
                          style={{
                            fontSize: "0.72rem",
                            fontWeight: 700,
                            padding: "2px 6px",
                            borderRadius: "4px",
                            background: "var(--surface-card)",
                            border: "1px solid var(--surface-border)",
                            color: "var(--text-main)",
                          }}
                        >
                          {a.category}
                        </span>
                        <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--text-main)" }}>
                          {a.name}
                        </span>
                      </div>
                      <div style={{ fontSize: "0.72rem", color: "var(--text-dim)", marginTop: "2px" }}>
                        Weightage: {a.weightage_pct}% {a.assessment_date ? `• Date: ${a.assessment_date}` : ""}
                      </div>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                      <div style={{ textAlign: "right" }}>
                        <span className="font-mono" style={{ fontSize: "0.95rem", fontWeight: 700, color: aStatus.color }}>
                          {a.marks_obtained} / {a.max_marks}
                        </span>
                        <div style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>
                          {a.percentage.toFixed(1)}%
                        </div>
                      </div>
                      {isExpanded ? <ChevronUp size={16} color="var(--text-dim)" /> : <ChevronDown size={16} color="var(--text-dim)" />}
                    </div>
                  </div>

                  {/* Expanded Question Breakdown */}
                  {isExpanded && a.questions && a.questions.length > 0 && (
                    <div
                      style={{
                        padding: "10px 16px 14px 16px",
                        background: "var(--surface-card)",
                        borderTop: "1px solid var(--surface-border)",
                        display: "flex",
                        flexDirection: "column",
                        gap: "6px",
                      }}
                    >
                      <div style={{ fontSize: "0.72rem", fontWeight: 700, color: "var(--text-dim)", textTransform: "uppercase" }}>
                        Question Analysis
                      </div>
                      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(120px, 1fr))", gap: "8px" }}>
                        {a.questions.map((q, qIdx) => (
                          <div
                            key={q.question_id || qIdx}
                            style={{
                              background: "var(--surface-elevated)",
                              padding: "6px 10px",
                              borderRadius: "6px",
                              border: "1px solid var(--surface-border)",
                              fontSize: "0.75rem",
                            }}
                          >
                            <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-dim)", fontSize: "0.7rem" }}>
                              <span>{q.question_label}</span>
                              <span style={{ color: "var(--color-student)", fontWeight: 600 }}>{q.co_code}</span>
                            </div>
                            <div style={{ fontWeight: 700, color: "var(--text-main)", marginTop: "2px" }}>
                              {q.marks_obtained} / {q.max_marks}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
