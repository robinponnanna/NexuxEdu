"use client";

import React, { useState, useEffect } from "react";
import { ClashCaseItem, getClashCases, getClashCaseDetail } from "@/lib/api";
import { StatusChip } from "./StatusChip";
import { TimelineView } from "./TimelineView";
import {
  Calendar,
  Clock,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  MapPin,
  RefreshCw,
  Info,
} from "lucide-react";

interface StudentClashesProps {
  token: string;
}

export const StudentClashes: React.FC<StudentClashesProps> = ({ token }) => {
  const [cases, setCases] = useState<ClashCaseItem[]>([]);
  const [expandedCaseId, setExpandedCaseId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchCases = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getClashCases(token);
      setCases(data);
      if (data.length > 0 && !expandedCaseId) {
        setExpandedCaseId(data[0].id);
      }
    } catch (e: any) {
      setError(e.message || "Failed to load clashes");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCases();
  }, [token]);

  const handleToggleExpand = async (id: number) => {
    if (expandedCaseId === id) {
      setExpandedCaseId(null);
    } else {
      setExpandedCaseId(id);
      // Fetch fresh detail with timeline
      try {
        const detail = await getClashCaseDetail(token, id);
        setCases((prev) => prev.map((c) => (c.id === id ? detail : c)));
      } catch (e) {
        console.error(e);
      }
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Top Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2 style={{ fontSize: "1.4rem", fontWeight: 700, color: "var(--text-main)" }}>
            My Exam Clashes & Rescheduling Status
          </h2>
          <p style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
            Real-time tracking of institutional event clashes and automated makeup examination approvals.
          </p>
        </div>

        <button
          onClick={fetchCases}
          disabled={loading}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            background: "var(--surface-elevated)",
            border: "1px solid var(--surface-border)",
            borderRadius: "6px",
            padding: "8px 12px",
            fontSize: "0.8rem",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          <RefreshCw size={13} className={loading ? "spin" : ""} />
          Refresh
        </button>
      </div>

      {error && (
        <div
          style={{
            padding: "12px 16px",
            background: "#FEF2F2",
            border: "1px solid #FCA5A5",
            borderRadius: "8px",
            color: "#991B1B",
            fontSize: "0.85rem",
          }}
        >
          {error}
        </div>
      )}

      {cases.length === 0 ? (
        <div
          style={{
            padding: "48px 20px",
            textAlign: "center",
            background: "var(--surface-card)",
            border: "1px solid var(--surface-border)",
            borderRadius: "12px",
            color: "var(--text-muted)",
          }}
        >
          <CheckCircle2 size={36} style={{ color: "var(--color-faculty)", opacity: 0.8, marginBottom: "10px" }} />
          <h3 style={{ fontSize: "1.05rem", fontWeight: 700, color: "var(--text-main)" }}>
            No Exam Clashes Found
          </h3>
          <p style={{ fontSize: "0.85rem", marginTop: "4px" }}>
            You do not have any conflicting examinations with registered institutional events.
          </p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {cases.map((c) => {
            const isExpanded = expandedCaseId === c.id;

            return (
              <div
                key={c.id}
                style={{
                  background: "var(--surface-card)",
                  border: "1px solid",
                  borderColor: isExpanded ? "var(--surface-border-focus)" : "var(--surface-border)",
                  borderRadius: "12px",
                  overflow: "hidden",
                  boxShadow: "var(--shadow-sm)",
                  transition: "border-color 0.15s ease",
                }}
              >
                {/* Header Row */}
                <div
                  onClick={() => handleToggleExpand(c.id)}
                  style={{
                    padding: "16px 20px",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    cursor: "pointer",
                    background: isExpanded ? "var(--surface-elevated)" : "var(--surface-card)",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
                    <div
                      style={{
                        width: "40px",
                        height: "40px",
                        borderRadius: "10px",
                        background: "rgba(2, 132, 199, 0.1)",
                        color: "var(--color-student)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontWeight: 700,
                        fontSize: "0.85rem",
                      }}
                    >
                      {c.course_code.split("-")[0] || "EX"}
                    </div>

                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span style={{ fontWeight: 700, fontSize: "0.95rem", color: "var(--text-main)" }}>
                          {c.subject} ({c.course_code})
                        </span>
                        <StatusChip status={c.status} size="sm" />
                      </div>
                      <div
                        style={{
                          fontSize: "0.78rem",
                          color: "var(--text-muted)",
                          display: "flex",
                          gap: "12px",
                          marginTop: "3px",
                        }}
                      >
                        <span>Exam: {c.assessment_kind}</span>
                        <span>•</span>
                        <span>Event: {c.event_title}</span>
                      </div>
                    </div>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                    {isExpanded ? <ChevronUp size={18} color="var(--text-dim)" /> : <ChevronDown size={18} color="var(--text-dim)" />}
                  </div>
                </div>

                {/* Expanded Details & Timeline */}
                {isExpanded && (
                  <div
                    style={{
                      padding: "20px",
                      borderTop: "1px solid var(--surface-border)",
                      display: "flex",
                      flexDirection: "column",
                      gap: "20px",
                    }}
                  >
                    {/* Information summary cards */}
                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns: "1fr 1fr",
                        gap: "16px",
                      }}
                    >
                      {/* Original Clash Box */}
                      <div
                        style={{
                          background: "#FEF2F2",
                          border: "1px solid #FCA5A5",
                          borderRadius: "8px",
                          padding: "12px 14px",
                        }}
                      >
                        <div style={{ fontSize: "0.72rem", fontWeight: 700, color: "#991B1B", textTransform: "uppercase" }}>
                          Conflicting Exam
                        </div>
                        <div style={{ fontSize: "0.88rem", fontWeight: 600, color: "#7F1D1D", marginTop: "4px" }}>
                          {c.assessment_kind}
                        </div>
                        <div style={{ fontSize: "0.78rem", color: "#991B1B", marginTop: "2px" }}>
                          Instructor: {c.faculty_name || "Course Faculty"}
                        </div>
                      </div>

                      {/* Rescheduled Slot Box */}
                      <div
                        style={{
                          background: c.status === "APPROVED" || c.status === "COMPLETED" ? "#F0FDF4" : "var(--surface-elevated)",
                          border: "1px solid",
                          borderColor: c.status === "APPROVED" || c.status === "COMPLETED" ? "#86EFAC" : "var(--surface-border)",
                          borderRadius: "8px",
                          padding: "12px 14px",
                        }}
                      >
                        <div
                          style={{
                            fontSize: "0.72rem",
                            fontWeight: 700,
                            color: c.status === "APPROVED" ? "#166534" : "var(--text-dim)",
                            textTransform: "uppercase",
                          }}
                        >
                          {c.status === "APPROVED" || c.status === "COMPLETED" ? "Approved Retake Slot" : "Recommended Slot"}
                        </div>
                        <div
                          style={{
                            fontSize: "0.88rem",
                            fontWeight: 600,
                            color: c.status === "APPROVED" ? "#14532D" : "var(--text-main)",
                            marginTop: "4px",
                          }}
                        >
                          {c.retake_info || c.suggested_retake_info || "Under review by instructor"}
                        </div>
                        {c.retake_note && (
                          <div style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginTop: "4px" }}>
                            <strong>Note:</strong> {c.retake_note}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Timeline */}
                    <div>
                      <div
                        style={{
                          fontSize: "0.75rem",
                          fontWeight: 700,
                          textTransform: "uppercase",
                          letterSpacing: "0.05em",
                          color: "var(--text-dim)",
                          marginBottom: "12px",
                        }}
                      >
                        Lifecycle Timeline & Approvals
                      </div>
                      <TimelineView timeline={c.timeline} />
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
