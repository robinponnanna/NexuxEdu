"use client";

import React, { useState, useEffect } from "react";
import {
  ClashCaseItem,
  getClashCases,
  professorDecideCases,
} from "@/lib/api";
import { StatusChip } from "./StatusChip";
import { TimelineView } from "./TimelineView";
import {
  Calendar,
  CheckCircle2,
  Clock,
  MessageSquare,
  AlertOctagon,
  ChevronRight,
  X,
  Send,
  Layers,
  CheckSquare,
  Square,
} from "lucide-react";

interface ProfessorRescheduleProps {
  token: string;
}

export const ProfessorReschedule: React.FC<ProfessorRescheduleProps> = ({ token }) => {
  const [cases, setCases] = useState<ClashCaseItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Decision Modal State
  const [selectedCaseIds, setSelectedCaseIds] = useState<number[]>([]);
  const [showDecisionModal, setShowDecisionModal] = useState(false);
  const [decisionType, setDecisionType] = useState<"approve" | "counter" | "reject">("approve");
  const [customDateTime, setCustomDateTime] = useState("");
  const [decisionNote, setDecisionNote] = useState("");
  const [rejectionReason, setRejectionReason] = useState("");

  // Timeline Modal
  const [timelineCase, setTimelineCase] = useState<ClashCaseItem | null>(null);

  const fetchCases = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getClashCases(token);
      setCases(data);
    } catch (e: any) {
      setError(e.message || "Failed to load reschedule requests");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCases();
  }, [token]);

  // Group pending cases by Assessment
  const pendingCases = cases.filter((c) => c.status === "REQUEST_FILED");
  const completedOrOtherCases = cases.filter((c) => c.status !== "REQUEST_FILED");

  // Group by assessment_id
  const groupedPending: Record<number, { title: string; cases: ClashCaseItem[] }> = {};
  pendingCases.forEach((c) => {
    if (!groupedPending[c.assessment_id]) {
      groupedPending[c.assessment_id] = {
        title: `${c.subject} (${c.course_code}) - ${c.assessment_kind}`,
        cases: [],
      };
    }
    groupedPending[c.assessment_id].cases.push(c);
  });

  const toggleSelect = (id: number) => {
    setSelectedCaseIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  const handleOpenDecisionModal = (type: "approve" | "counter" | "reject", caseId?: number) => {
    if (caseId) {
      setSelectedCaseIds([caseId]);
    }
    setDecisionType(type);
    setCustomDateTime("");
    setDecisionNote("");
    setRejectionReason("");
    setShowDecisionModal(true);
  };

  const handleSubmitDecision = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedCaseIds.length === 0) return;

    if (decisionType === "reject" && !rejectionReason.trim()) {
      setError("Rejection reason is required.");
      return;
    }

    if (decisionType === "counter" && !customDateTime) {
      setError("Proposed alternative datetime is required for counter proposals.");
      return;
    }

    setActionLoading(true);
    setError(null);
    try {
      const customIso = customDateTime ? new Date(customDateTime).toISOString() : undefined;
      await professorDecideCases(token, {
        case_ids: selectedCaseIds,
        decision: decisionType,
        custom_at: customIso,
        note: decisionNote || undefined,
        rejection_reason: rejectionReason || undefined,
      });

      setShowDecisionModal(false);
      setSelectedCaseIds([]);
      await fetchCases();
      setSuccessMsg(
        decisionType === "reject"
          ? "Case(s) rejected and automatically escalated to Head of Department."
          : `Reschedule requests ${decisionType}d successfully.`
      );
    } catch (e: any) {
      setError(e.message || "Failed to submit decision");
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Top Banner */}
      <div>
        <h2 style={{ fontSize: "1.4rem", fontWeight: 700, color: "var(--text-main)" }}>
          Faculty Examination Reschedule Requests
        </h2>
        <p style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
          Review institutional event clash reschedule requests filed for your courses. Confirm suggested sister section slots, offer counter proposals, or submit documented rejections.
        </p>
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
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <span>{error}</span>
          <button onClick={() => setError(null)} style={{ background: "none", border: "none", cursor: "pointer", color: "#991B1B" }}>
            <X size={16} />
          </button>
        </div>
      )}

      {successMsg && (
        <div
          style={{
            padding: "12px 16px",
            background: "#F0FDF4",
            border: "1px solid #86EFAC",
            borderRadius: "8px",
            color: "#166534",
            fontSize: "0.85rem",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <span>{successMsg}</span>
          <button onClick={() => setSuccessMsg(null)} style={{ background: "none", border: "none", cursor: "pointer", color: "#166534" }}>
            <X size={16} />
          </button>
        </div>
      )}

      {/* Pending Reschedule Requests Section */}
      <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <h3 style={{ fontSize: "1.05rem", fontWeight: 700, color: "var(--text-main)" }}>
            Pending Action Required ({pendingCases.length})
          </h3>

          {selectedCaseIds.length > 0 && (
            <div style={{ display: "flex", gap: "8px" }}>
              <button
                onClick={() => handleOpenDecisionModal("approve")}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  background: "var(--color-faculty)",
                  color: "#FFFFFF",
                  border: "none",
                  borderRadius: "6px",
                  padding: "7px 12px",
                  fontSize: "0.8rem",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                <CheckCircle2 size={14} />
                Approve Selected ({selectedCaseIds.length})
              </button>
              <button
                onClick={() => handleOpenDecisionModal("counter")}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  background: "var(--color-parent)",
                  color: "#FFFFFF",
                  border: "none",
                  borderRadius: "6px",
                  padding: "7px 12px",
                  fontSize: "0.8rem",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                <MessageSquare size={14} />
                Counter Propose
              </button>
              <button
                onClick={() => handleOpenDecisionModal("reject")}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  background: "var(--color-danger)",
                  color: "#FFFFFF",
                  border: "none",
                  borderRadius: "6px",
                  padding: "7px 12px",
                  fontSize: "0.8rem",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                <AlertOctagon size={14} />
                Reject
              </button>
            </div>
          )}
        </div>

        {Object.keys(groupedPending).length === 0 ? (
          <div
            style={{
              padding: "40px",
              textAlign: "center",
              background: "var(--surface-card)",
              border: "1px solid var(--surface-border)",
              borderRadius: "12px",
              color: "var(--text-muted)",
              fontSize: "0.88rem",
            }}
          >
            <CheckCircle2 size={28} style={{ color: "var(--color-faculty)", opacity: 0.6, marginBottom: "8px" }} />
            <p style={{ fontWeight: 600 }}>All caught up! No pending reschedule requests.</p>
          </div>
        ) : (
          Object.entries(groupedPending).map(([assId, group]) => {
            const allSelectedInGroup = group.cases.every((c) => selectedCaseIds.includes(c.id));

            const toggleGroupSelection = () => {
              if (allSelectedInGroup) {
                setSelectedCaseIds((prev) => prev.filter((id) => !group.cases.some((c) => c.id === id)));
              } else {
                const idsToAdd = group.cases.map((c) => c.id);
                setSelectedCaseIds((prev) => Array.from(new Set([...prev, ...idsToAdd])));
              }
            };

            return (
              <div
                key={assId}
                style={{
                  background: "var(--surface-card)",
                  border: "1px solid var(--surface-border)",
                  borderRadius: "12px",
                  overflow: "hidden",
                  boxShadow: "var(--shadow-sm)",
                }}
              >
                <div
                  style={{
                    padding: "12px 16px",
                    background: "var(--surface-elevated)",
                    borderBottom: "1px solid var(--surface-border)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <button
                      onClick={toggleGroupSelection}
                      style={{ background: "none", border: "none", cursor: "pointer", padding: 0 }}
                    >
                      {allSelectedInGroup ? (
                        <CheckSquare size={16} color="var(--color-primary)" />
                      ) : (
                        <Square size={16} color="var(--text-dim)" />
                      )}
                    </button>
                    <span style={{ fontWeight: 700, fontSize: "0.9rem", color: "var(--text-main)" }}>
                      {group.title}
                    </span>
                    <span
                      style={{
                        background: "var(--color-primary-subtle)",
                        color: "var(--color-primary)",
                        padding: "2px 8px",
                        borderRadius: "9999px",
                        fontSize: "0.72rem",
                        fontWeight: 600,
                      }}
                    >
                      {group.cases.length} student(s)
                    </span>
                  </div>
                </div>

                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8rem", textAlign: "left" }}>
                  <thead>
                    <tr
                      style={{
                        borderBottom: "1px solid var(--surface-border)",
                        color: "var(--text-dim)",
                        fontSize: "0.72rem",
                        textTransform: "uppercase",
                      }}
                    >
                      <th style={{ padding: "10px 14px", width: "36px" }}></th>
                      <th style={{ padding: "10px 14px" }}>Student</th>
                      <th style={{ padding: "10px 14px" }}>Event Window</th>
                      <th style={{ padding: "10px 14px" }}>System Recommendation</th>
                      <th style={{ padding: "10px 14px", textAlign: "right" }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {group.cases.map((c) => {
                      const isSelected = selectedCaseIds.includes(c.id);
                      return (
                        <tr
                          key={c.id}
                          style={{
                            borderBottom: "1px solid var(--surface-border-subtle)",
                            background: isSelected ? "rgba(239, 246, 255, 0.4)" : "var(--surface-card)",
                          }}
                        >
                          <td style={{ padding: "10px 14px" }}>
                            <button
                              onClick={() => toggleSelect(c.id)}
                              style={{ background: "none", border: "none", cursor: "pointer", padding: 0 }}
                            >
                              {isSelected ? (
                                <CheckSquare size={16} color="var(--color-primary)" />
                              ) : (
                                <Square size={16} color="var(--text-dim)" />
                              )}
                            </button>
                          </td>
                          <td style={{ padding: "10px 14px" }}>
                            <div style={{ fontWeight: 600, color: "var(--text-main)" }}>{c.student_name}</div>
                            <div style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>
                              {c.student_roll} • {c.student_section || "Section A"}
                            </div>
                          </td>
                          <td style={{ padding: "10px 14px" }}>
                            <div style={{ color: "var(--text-main)" }}>{c.event_title}</div>
                          </td>
                          <td style={{ padding: "10px 14px" }}>
                            {c.suggested_retake_info ? (
                              <div style={{ color: "var(--color-faculty)", fontWeight: 600 }}>
                                {c.suggested_retake_info}
                              </div>
                            ) : (
                              <span style={{ color: "var(--text-dim)", fontStyle: "italic" }}>
                                Single Section (Assign Custom Slot)
                              </span>
                            )}
                          </td>
                          <td style={{ padding: "10px 14px", textAlign: "right" }}>
                            <div style={{ display: "flex", gap: "6px", justifyContent: "flex-end" }}>
                              <button
                                onClick={() => handleOpenDecisionModal("approve", c.id)}
                                style={{
                                  background: "#F0FDF4",
                                  color: "#166534",
                                  border: "1px solid #86EFAC",
                                  borderRadius: "4px",
                                  padding: "4px 8px",
                                  fontSize: "0.72rem",
                                  fontWeight: 600,
                                  cursor: "pointer",
                                }}
                              >
                                Approve
                              </button>
                              <button
                                onClick={() => handleOpenDecisionModal("counter", c.id)}
                                style={{
                                  background: "#FFFBEB",
                                  color: "#92400E",
                                  border: "1px solid #FCD34D",
                                  borderRadius: "4px",
                                  padding: "4px 8px",
                                  fontSize: "0.72rem",
                                  fontWeight: 600,
                                  cursor: "pointer",
                                }}
                              >
                                Counter
                              </button>
                              <button
                                onClick={() => handleOpenDecisionModal("reject", c.id)}
                                style={{
                                  background: "#FEF2F2",
                                  color: "#991B1B",
                                  border: "1px solid #FCA5A5",
                                  borderRadius: "4px",
                                  padding: "4px 8px",
                                  fontSize: "0.72rem",
                                  fontWeight: 600,
                                  cursor: "pointer",
                                }}
                              >
                                Reject
                              </button>
                              <button
                                onClick={() => setTimelineCase(c)}
                                style={{
                                  background: "none",
                                  border: "none",
                                  color: "var(--text-dim)",
                                  cursor: "pointer",
                                  padding: "4px",
                                }}
                                title="View History"
                              >
                                <ChevronRight size={14} />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            );
          })
        )}
      </div>

      {/* Decision Modal */}
      {showDecisionModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(15, 23, 42, 0.4)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
          }}
        >
          <div
            style={{
              width: "480px",
              background: "var(--surface-card)",
              border: "1px solid var(--surface-border)",
              borderRadius: "12px",
              padding: "24px",
              boxShadow: "var(--shadow-lg)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
              <h3 style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--text-main)" }}>
                {decisionType === "approve"
                  ? "Approve Reschedule"
                  : decisionType === "counter"
                  ? "Propose Alternative Counter-Slot"
                  : "Reject Reschedule Request"}
              </h3>
              <button onClick={() => setShowDecisionModal(false)} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-dim)" }}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSubmitDecision} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div style={{ fontSize: "0.82rem", color: "var(--text-muted)" }}>
                Applying action to <strong>{selectedCaseIds.length}</strong> selected case(s).
              </div>

              {decisionType === "approve" && (
                <div>
                  <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 600, marginBottom: "4px" }}>
                    Alternative Date & Time (Optional if using suggested slot)
                  </label>
                  <input
                    type="datetime-local"
                    value={customDateTime}
                    onChange={(e) => setCustomDateTime(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "8px 10px",
                      borderRadius: "6px",
                      border: "1px solid var(--surface-border-focus)",
                      fontSize: "0.82rem",
                    }}
                  />
                  <span style={{ fontSize: "0.72rem", color: "var(--text-dim)", display: "block", marginTop: "3px" }}>
                    Leave blank to automatically accept the system-recommended sister section slot.
                  </span>
                </div>
              )}

              {decisionType === "counter" && (
                <div>
                  <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 600, marginBottom: "4px" }}>
                    Counter Proposed Datetime *
                  </label>
                  <input
                    type="datetime-local"
                    required
                    value={customDateTime}
                    onChange={(e) => setCustomDateTime(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "8px 10px",
                      borderRadius: "6px",
                      border: "1px solid var(--surface-border-focus)",
                      fontSize: "0.82rem",
                    }}
                  />
                </div>
              )}

              {decisionType === "reject" ? (
                <div>
                  <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 600, marginBottom: "4px" }}>
                    Mandatory Rejection Justification *
                  </label>
                  <textarea
                    rows={3}
                    required
                    value={rejectionReason}
                    onChange={(e) => setRejectionReason(e.target.value)}
                    placeholder="Provide justification per syllabus and departmental policy..."
                    style={{
                      width: "100%",
                      padding: "8px 10px",
                      borderRadius: "6px",
                      border: "1px solid var(--surface-border-focus)",
                      fontSize: "0.82rem",
                      fontFamily: "inherit",
                    }}
                  />
                  <span style={{ fontSize: "0.72rem", color: "var(--color-danger)", display: "block", marginTop: "4px" }}>
                    Notice: Rejecting this request automatically escalates it to the Head of Department for administrative review.
                  </span>
                </div>
              ) : (
                <div>
                  <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 600, marginBottom: "4px" }}>
                    Instructor Note (Optional)
                  </label>
                  <textarea
                    rows={2}
                    value={decisionNote}
                    onChange={(e) => setDecisionNote(e.target.value)}
                    placeholder="Instructions for venue, materials, or confirmation..."
                    style={{
                      width: "100%",
                      padding: "8px 10px",
                      borderRadius: "6px",
                      border: "1px solid var(--surface-border-focus)",
                      fontSize: "0.82rem",
                      fontFamily: "inherit",
                    }}
                  />
                </div>
              )}

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "8px" }}>
                <button
                  type="button"
                  onClick={() => setShowDecisionModal(false)}
                  style={{
                    padding: "8px 14px",
                    background: "var(--surface-elevated)",
                    border: "1px solid var(--surface-border)",
                    borderRadius: "6px",
                    fontSize: "0.82rem",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  style={{
                    padding: "8px 16px",
                    background:
                      decisionType === "reject"
                        ? "var(--color-danger)"
                        : decisionType === "counter"
                        ? "var(--color-parent)"
                        : "var(--color-faculty)",
                    color: "#FFFFFF",
                    border: "none",
                    borderRadius: "6px",
                    fontSize: "0.82rem",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  {actionLoading ? "Submitting..." : "Confirm Decision"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* History / Timeline Modal */}
      {timelineCase && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(15, 23, 42, 0.4)",
            display: "flex",
            justifyContent: "flex-end",
            zIndex: 1000,
          }}
        >
          <div
            style={{
              width: "480px",
              background: "var(--surface-card)",
              height: "100%",
              boxShadow: "var(--shadow-lg)",
              display: "flex",
              flexDirection: "column",
              padding: "24px",
              overflowY: "auto",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--surface-border)", paddingBottom: "12px", marginBottom: "16px" }}>
              <h3 style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--text-main)" }}>
                Case Timeline & Log
              </h3>
              <button onClick={() => setTimelineCase(null)} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-dim)" }}>
                <X size={18} />
              </button>
            </div>

            <div style={{ background: "var(--surface-elevated)", padding: "12px", borderRadius: "8px", border: "1px solid var(--surface-border)", marginBottom: "16px" }}>
              <div style={{ fontWeight: 600, fontSize: "0.85rem" }}>{timelineCase.student_name} ({timelineCase.student_roll})</div>
              <div style={{ fontSize: "0.78rem", color: "var(--text-dim)", marginTop: "4px" }}>
                Course: {timelineCase.subject} • Status: <StatusChip status={timelineCase.status} size="sm" />
              </div>
            </div>

            <TimelineView timeline={timelineCase.timeline} />
          </div>
        </div>
      )}
    </div>
  );
};
