"use client";

import React, { useState, useEffect } from "react";
import {
  HODOverview,
  ClashCaseItem,
  getHODOverview,
  hodOverrideCase,
  getClashCaseDetail,
  CaseTimelineEntry,
} from "@/lib/api";
import { StatusChip } from "./StatusChip";
import { TimelineView } from "./TimelineView";
import {
  ShieldAlert,
  Clock,
  AlertTriangle,
  RefreshCw,
  CheckCircle2,
  Users,
  Calendar,
  Layers,
  Sparkles,
  ArrowRight,
  X,
  Building,
  MapPin,
} from "lucide-react";

interface HODDashboardProps {
  token: string;
}

export const HODDashboard: React.FC<HODDashboardProps> = ({ token }) => {
  const [overview, setOverview] = useState<HODOverview | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Override Modal state
  const [selectedCase, setSelectedCase] = useState<ClashCaseItem | null>(null);
  const [overrideDecision, setOverrideDecision] = useState<"APPROVED" | "REJECTED">("APPROVED");
  const [overrideSlotId, setOverrideSlotId] = useState<number | null>(null);
  
  // Specific Datetime and Venue fields (replacing free-text string requirement)
  const [customDateTime, setCustomDateTime] = useState<string>("");
  const [customVenue, setCustomVenue] = useState<string>("");
  
  const [overrideNote, setOverrideNote] = useState<string>("");
  const [submittingOverride, setSubmittingOverride] = useState<boolean>(false);
  const [overrideError, setOverrideError] = useState<string | null>(null);

  // Timeline Modal state
  const [timelineCase, setTimelineCase] = useState<ClashCaseItem | null>(null);
  const [timelineEntries, setTimelineEntries] = useState<CaseTimelineEntry[]>([]);
  const [timelineLoading, setTimelineLoading] = useState<boolean>(false);

  const fetchOverview = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getHODOverview(token);
      setOverview(data);
    } catch (err: any) {
      setError(err?.message || "Failed to load HOD department overview");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchOverview();
    }
  }, [token]);

  const handleOpenTimeline = async (c: ClashCaseItem) => {
    setTimelineCase(c);
    setTimelineLoading(true);
    try {
      const res = await getClashCaseDetail(token, c.id);
      setTimelineEntries(res.timeline || []);
    } catch (e: any) {
      console.error("Failed to load timeline", e);
    } finally {
      setTimelineLoading(false);
    }
  };

  const handleOpenOverride = (c: ClashCaseItem) => {
    setSelectedCase(c);
    setOverrideDecision("APPROVED");
    setOverrideSlotId(c.suggested_retake_assessment_id || null);
    setCustomDateTime("");
    setCustomVenue("");
    setOverrideNote("");
    setOverrideError(null);
  };

  const handleExecuteOverride = async () => {
    if (!selectedCase) return;
    if (!overrideNote.trim()) {
      setOverrideError("HOD justification note is mandatory for override audit trail.");
      return;
    }

    if (overrideDecision === "APPROVED" && !overrideSlotId && !customDateTime) {
      setOverrideError("Please assign a slot or select a custom date & time.");
      return;
    }

    setSubmittingOverride(true);
    setOverrideError(null);
    try {
      // Build ISO string if custom date provided
      let formattedCustomAt: string | undefined = undefined;
      if (customDateTime) {
        formattedCustomAt = new Date(customDateTime).toISOString();
      }

      // Append venue to note if specified
      let finalNote = overrideNote.trim();
      if (customVenue.trim()) {
        finalNote = `${finalNote} [Venue: ${customVenue.trim()}]`;
      }

      await hodOverrideCase(token, selectedCase.id, {
        slot_id: overrideSlotId || undefined,
        custom_at: formattedCustomAt,
        note: finalNote,
      });
      setSelectedCase(null);
      await fetchOverview();
    } catch (err: any) {
      setOverrideError(err?.message || "Failed to execute HOD override");
    } finally {
      setSubmittingOverride(false);
    }
  };

  const totalCasesCount = overview?.total_cases ?? Object.values(overview?.counts_by_status || {}).reduce((a, b) => a + b, 0);
  const escalatedCount = overview?.counts_by_status?.["ESCALATED_TO_HOD"] ?? overview?.escalated_cases?.length ?? 0;
  const stuckCount = overview?.stuck_cases?.length ?? 0;
  const profPendingMap = overview?.pending_per_professor || overview?.per_professor_pending || {};

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "22px" }}>
      {/* Header Banner */}
      <div
        style={{
          background: "linear-gradient(135deg, rgba(220, 38, 38, 0.08) 0%, rgba(239, 68, 68, 0.02) 100%)",
          border: "1px solid rgba(239, 68, 68, 0.25)",
          borderRadius: "10px",
          padding: "20px 24px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
            <Building size={18} color="var(--color-danger)" />
            <span
              style={{
                fontSize: "0.72rem",
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.06em",
                color: "var(--color-danger)",
              }}
            >
              HOD EXECUTIVE GOVERNANCE
            </span>
            {overview?.department && (
              <span
                style={{
                  fontSize: "0.74rem",
                  background: "var(--surface-elevated)",
                  padding: "2px 8px",
                  borderRadius: "4px",
                  color: "var(--text-main)",
                  fontWeight: 600,
                  border: "1px solid var(--surface-border)",
                }}
              >
                Dept: {overview.department}
              </span>
            )}
          </div>
          <h2 style={{ fontSize: "1.35rem", fontWeight: 700, color: "var(--text-main)", margin: 0 }}>
            Department Clash Governance & Escalations
          </h2>
          <p style={{ fontSize: "0.82rem", color: "var(--text-muted)", marginTop: "4px", margin: 0 }}>
            Oversee escalated retake conflicts, resolve professor rejections, monitor stuck SLA workflows, and balance exam schedules.
          </p>
        </div>

        <button
          onClick={fetchOverview}
          disabled={loading}
          style={{
            background: "var(--surface-card)",
            border: "1px solid var(--surface-border)",
            borderRadius: "7px",
            padding: "8px 14px",
            color: "var(--text-main)",
            fontSize: "0.82rem",
            fontWeight: 600,
            cursor: loading ? "not-allowed" : "pointer",
            display: "flex",
            alignItems: "center",
            gap: "6px",
          }}
        >
          <RefreshCw size={14} className={loading ? "spin" : ""} />
          <span>Refresh</span>
        </button>
      </div>

      {error && (
        <div
          style={{
            background: "#FEF2F2",
            border: "1px solid #FECACA",
            borderRadius: "8px",
            padding: "12px 16px",
            color: "var(--color-danger)",
            fontSize: "0.84rem",
          }}
        >
          {error}
        </div>
      )}

      {/* KPI Stats Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "14px" }}>
        <div style={{ background: "var(--surface-card)", border: "1px solid var(--surface-border)", borderRadius: "8px", padding: "16px 18px" }}>
          <div style={{ fontSize: "0.72rem", color: "var(--text-dim)", fontWeight: 600, letterSpacing: "0.04em" }}>TOTAL CLASH CASES</div>
          <div className="font-mono" style={{ fontSize: "1.7rem", fontWeight: 700, color: "var(--text-main)", marginTop: "4px" }}>
            {totalCasesCount}
          </div>
          <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginTop: "4px" }}>Department-wide scope</div>
        </div>

        <div style={{ background: "var(--surface-card)", border: "1px solid rgba(239, 68, 68, 0.3)", borderRadius: "8px", padding: "16px 18px" }}>
          <div style={{ fontSize: "0.72rem", color: "var(--color-danger)", fontWeight: 700, letterSpacing: "0.04em" }}>ESCALATED TO HOD</div>
          <div className="font-mono" style={{ fontSize: "1.7rem", fontWeight: 700, color: "var(--color-danger)", marginTop: "4px" }}>
            {escalatedCount}
          </div>
          <div style={{ fontSize: "0.72rem", color: "var(--text-dim)", marginTop: "4px" }}>Awaiting executive override</div>
        </div>

        <div style={{ background: "var(--surface-card)", border: "1px solid rgba(245, 158, 11, 0.3)", borderRadius: "8px", padding: "16px 18px" }}>
          <div style={{ fontSize: "0.72rem", color: "var(--color-warning)", fontWeight: 700, letterSpacing: "0.04em" }}>STUCK CASES (&gt;48H)</div>
          <div className="font-mono" style={{ fontSize: "1.7rem", fontWeight: 700, color: "var(--color-warning)", marginTop: "4px" }}>
            {stuckCount}
          </div>
          <div style={{ fontSize: "0.72rem", color: "var(--text-dim)", marginTop: "4px" }}>Pending professor action</div>
        </div>

        <div style={{ background: "var(--surface-card)", border: "1px solid var(--surface-border)", borderRadius: "8px", padding: "16px 18px" }}>
          <div style={{ fontSize: "0.72rem", color: "var(--text-dim)", fontWeight: 600, letterSpacing: "0.04em" }}>FACULTY MEMBERS</div>
          <div className="font-mono" style={{ fontSize: "1.7rem", fontWeight: 700, color: "var(--text-main)", marginTop: "4px" }}>
            {Object.keys(profPendingMap).length}
          </div>
          <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginTop: "4px" }}>With active course offerings</div>
        </div>
      </div>

      {/* Escalated Cases Requiring Immediate Action */}
      <div style={{ background: "var(--surface-card)", border: "1px solid var(--surface-border)", borderRadius: "10px", padding: "20px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div
              style={{
                width: "32px",
                height: "32px",
                borderRadius: "6px",
                background: "rgba(239, 68, 68, 0.12)",
                color: "var(--color-danger)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <ShieldAlert size={18} />
            </div>
            <div>
              <h3 style={{ fontSize: "1.05rem", fontWeight: 700, color: "var(--text-main)", margin: 0 }}>
                Escalated Cases (HOD Action Required)
              </h3>
              <p style={{ fontSize: "0.76rem", color: "var(--text-dim)", margin: 0 }}>
                Cases rejected by course professors or automatically escalated under Section §6 rules.
              </p>
            </div>
          </div>
          <span
            style={{
              fontSize: "0.75rem",
              padding: "3px 8px",
              borderRadius: "4px",
              background: (overview?.escalated_cases?.length || 0) > 0 ? "rgba(239, 68, 68, 0.1)" : "var(--surface-elevated)",
              color: (overview?.escalated_cases?.length || 0) > 0 ? "var(--color-danger)" : "var(--text-dim)",
              fontWeight: 600,
            }}
          >
            {overview?.escalated_cases?.length || 0} Escalated
          </span>
        </div>

        {overview?.escalated_cases && overview.escalated_cases.length > 0 ? (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem", textAlign: "left" }}>
              <thead>
                <tr style={{ background: "var(--surface-elevated)", color: "var(--text-dim)", borderBottom: "1px solid var(--surface-border)" }}>
                  <th style={{ padding: "10px 12px" }}>CASE</th>
                  <th style={{ padding: "10px 12px" }}>STUDENT</th>
                  <th style={{ padding: "10px 12px" }}>COURSE / EXAM</th>
                  <th style={{ padding: "10px 12px" }}>EVENT</th>
                  <th style={{ padding: "10px 12px" }}>STATUS</th>
                  <th style={{ padding: "10px 12px" }}>LAST REASON</th>
                  <th style={{ padding: "10px 12px", textAlign: "right" }}>ACTIONS</th>
                </tr>
              </thead>
              <tbody>
                {overview.escalated_cases.map((c) => (
                  <tr key={c.id} style={{ borderBottom: "1px solid var(--surface-border-subtle)" }}>
                    <td className="font-mono" style={{ padding: "12px", fontWeight: 600, color: "var(--text-main)" }}>
                      #{c.id}
                    </td>
                    <td style={{ padding: "12px" }}>
                      <div style={{ fontWeight: 600, color: "var(--text-main)" }}>{c.student_name}</div>
                      <div style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>
                        {c.student_roll} • Sec {c.student_section || "A"}
                      </div>
                    </td>
                    <td style={{ padding: "12px" }}>
                      <div style={{ fontWeight: 600, color: "var(--text-main)" }}>
                        {c.course_code} — {c.subject}
                      </div>
                      <div style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>
                        {c.assessment_kind}
                      </div>
                    </td>
                    <td style={{ padding: "12px", color: "var(--text-muted)" }}>
                      {c.event_title}
                    </td>
                    <td style={{ padding: "12px" }}>
                      <StatusChip status={c.status} />
                    </td>
                    <td style={{ padding: "12px", maxWidth: "220px", color: "var(--color-danger)", fontSize: "0.75rem" }}>
                      {c.rejection_reason || "Professor rejected request."}
                    </td>
                    <td style={{ padding: "12px", textAlign: "right" }}>
                      <div style={{ display: "flex", gap: "6px", justifyContent: "flex-end" }}>
                        <button
                          onClick={() => handleOpenTimeline(c)}
                          style={{
                            background: "transparent",
                            border: "1px solid var(--surface-border)",
                            borderRadius: "5px",
                            padding: "5px 9px",
                            fontSize: "0.74rem",
                            color: "var(--text-muted)",
                            cursor: "pointer",
                          }}
                        >
                          Audit Log
                        </button>
                        <button
                          onClick={() => handleOpenOverride(c)}
                          style={{
                            background: "var(--color-danger)",
                            border: "none",
                            borderRadius: "5px",
                            padding: "5px 11px",
                            fontSize: "0.74rem",
                            fontWeight: 600,
                            color: "#FFFFFF",
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            gap: "4px",
                          }}
                        >
                          <ShieldAlert size={12} />
                          <span>Override</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{ padding: "26px", textAlign: "center", color: "var(--text-muted)", fontSize: "0.84rem" }}>
            <CheckCircle2 size={24} color="var(--color-success)" style={{ margin: "0 auto 8px auto", display: "block" }} />
            No cases currently escalated in {overview?.department || "this department"}. All professor requests are on track.
          </div>
        )}
      </div>

      {/* Stuck Cases (>48 Hours) Warning Section */}
      {overview?.stuck_cases && overview.stuck_cases.length > 0 && (
        <div
          style={{
            background: "rgba(245, 158, 11, 0.05)",
            border: "1px solid rgba(245, 158, 11, 0.3)",
            borderRadius: "10px",
            padding: "18px 20px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "12px" }}>
            <AlertTriangle size={18} color="var(--color-warning)" />
            <div>
              <h4 style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--color-warning)", margin: 0 }}>
                SLA Alert: {overview.stuck_cases.length} Case(s) Inactive for &gt;48 Hours
              </h4>
              <p style={{ fontSize: "0.75rem", color: "var(--text-dim)", margin: 0 }}>
                These cases are in REQUEST_FILED or COUNTER_PROPOSED state without timely resolution.
              </p>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "10px" }}>
            {overview.stuck_cases.map((sc) => (
              <div
                key={sc.id}
                style={{
                  background: "var(--surface-card)",
                  border: "1px solid var(--surface-border)",
                  borderRadius: "7px",
                  padding: "10px 14px",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <div>
                  <div style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--text-main)" }}>
                    #{sc.id} — {sc.student_name}
                  </div>
                  <div style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>
                    {sc.course_code} • Last updated {new Date(sc.updated_at).toLocaleDateString()}
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <StatusChip status={sc.status} />
                  <button
                    onClick={() => handleOpenOverride(sc)}
                    style={{
                      background: "var(--surface-elevated)",
                      border: "1px solid var(--surface-border)",
                      borderRadius: "4px",
                      padding: "4px 8px",
                      fontSize: "0.72rem",
                      color: "var(--text-main)",
                      cursor: "pointer",
                      fontWeight: 600,
                    }}
                  >
                    Intervene
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Professor Workload Distribution */}
      <div style={{ background: "var(--surface-card)", border: "1px solid var(--surface-border)", borderRadius: "10px", padding: "20px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "14px" }}>
          <Users size={17} color="var(--color-primary)" />
          <h3 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text-main)", margin: 0 }}>
            Pending Clash Workload by Faculty Member
          </h3>
        </div>

        {Object.keys(profPendingMap).length > 0 ? (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "12px" }}>
            {Object.entries(profPendingMap).map(([profName, count]) => {
              const pendingCount = Number(count) || 0;
              return (
                <div
                  key={profName}
                  style={{
                    background: "var(--surface-elevated)",
                    border: "1px solid var(--surface-border)",
                    borderRadius: "8px",
                    padding: "12px 14px",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <div>
                    <div style={{ fontSize: "0.84rem", fontWeight: 600, color: "var(--text-main)" }}>{profName}</div>
                    <div style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>Course Instructor</div>
                  </div>
                  <div
                    className="font-mono"
                    style={{
                      fontSize: "1.1rem",
                      fontWeight: 700,
                      color: pendingCount > 0 ? "var(--color-warning)" : "var(--color-success)",
                      padding: "2px 8px",
                      borderRadius: "4px",
                      background: "var(--surface-card)",
                      border: "1px solid var(--surface-border)",
                    }}
                  >
                    {pendingCount} pending
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div style={{ color: "var(--text-dim)", fontSize: "0.8rem" }}>No faculty workload registered yet.</div>
        )}
      </div>

      {/* HOD Override Modal */}
      {selectedCase && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0, 0, 0, 0.65)",
            backdropFilter: "blur(4px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "20px",
          }}
        >
          <div
            style={{
              background: "var(--surface-card)",
              border: "1px solid var(--surface-border)",
              borderRadius: "12px",
              padding: "24px",
              maxWidth: "520px",
              width: "100%",
              boxShadow: "var(--shadow-lg)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <ShieldAlert size={20} color="var(--color-danger)" />
                <h3 style={{ fontSize: "1.15rem", fontWeight: 700, color: "var(--text-main)", margin: 0 }}>
                  HOD Discretionary Override #{selectedCase.id}
                </h3>
              </div>
              <button
                onClick={() => setSelectedCase(null)}
                style={{ background: "transparent", border: "none", color: "var(--text-dim)", cursor: "pointer" }}
              >
                <X size={18} />
              </button>
            </div>

            <div
              style={{
                background: "var(--surface-elevated)",
                border: "1px solid var(--surface-border)",
                borderRadius: "8px",
                padding: "12px 14px",
                marginBottom: "16px",
                fontSize: "0.8rem",
              }}
            >
              <div>
                <strong>Student:</strong> {selectedCase.student_name} ({selectedCase.student_roll})
              </div>
              <div style={{ marginTop: "4px" }}>
                <strong>Course:</strong> {selectedCase.course_code} — {selectedCase.subject}
              </div>
              <div style={{ marginTop: "4px" }}>
                <strong>Event:</strong> {selectedCase.event_title}
              </div>
              <div style={{ marginTop: "4px", color: "var(--color-danger)" }}>
                <strong>Current Status:</strong> {selectedCase.status}
              </div>
            </div>

            {overrideError && (
              <div
                style={{
                  background: "#FEF2F2",
                  border: "1px solid #FECACA",
                  borderRadius: "6px",
                  padding: "8px 12px",
                  color: "var(--color-danger)",
                  fontSize: "0.78rem",
                  marginBottom: "12px",
                }}
              >
                {overrideError}
              </div>
            )}

            {/* Decision choice */}
            <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginBottom: "16px" }}>
              <div>
                <label style={{ fontSize: "0.78rem", fontWeight: 600, color: "var(--text-main)", display: "block", marginBottom: "6px" }}>
                  Override Decision:
                </label>
                <div style={{ display: "flex", gap: "8px" }}>
                  <button
                    type="button"
                    onClick={() => setOverrideDecision("APPROVED")}
                    style={{
                      flex: 1,
                      padding: "8px",
                      borderRadius: "6px",
                      border: "1px solid",
                      borderColor: overrideDecision === "APPROVED" ? "var(--color-success)" : "var(--surface-border)",
                      background: overrideDecision === "APPROVED" ? "rgba(16, 185, 129, 0.12)" : "var(--surface-elevated)",
                      color: overrideDecision === "APPROVED" ? "var(--color-success)" : "var(--text-muted)",
                      fontWeight: 600,
                      fontSize: "0.8rem",
                      cursor: "pointer",
                    }}
                  >
                    Force Approve Retake
                  </button>
                  <button
                    type="button"
                    onClick={() => setOverrideDecision("REJECTED")}
                    style={{
                      flex: 1,
                      padding: "8px",
                      borderRadius: "6px",
                      border: "1px solid",
                      borderColor: overrideDecision === "REJECTED" ? "var(--color-danger)" : "var(--surface-border)",
                      background: overrideDecision === "REJECTED" ? "rgba(239, 68, 68, 0.12)" : "var(--surface-elevated)",
                      color: overrideDecision === "REJECTED" ? "var(--color-danger)" : "var(--text-muted)",
                      fontWeight: 600,
                      fontSize: "0.8rem",
                      cursor: "pointer",
                    }}
                  >
                    Confirm Final Rejection
                  </button>
                </div>
              </div>

              {overrideDecision === "APPROVED" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                  {selectedCase.suggested_retake_info && (
                    <div
                      style={{
                        background: "var(--surface-elevated)",
                        border: "1px solid var(--surface-border)",
                        borderRadius: "6px",
                        padding: "8px 12px",
                        fontSize: "0.76rem",
                        color: "var(--text-main)",
                        display: "flex",
                        alignItems: "center",
                        gap: "8px",
                      }}
                    >
                      <Sparkles size={14} color="var(--color-primary)" />
                      <span>Sister Section Parallel Slot: {selectedCase.suggested_retake_info}</span>
                    </div>
                  )}

                  {/* Datetime Field */}
                  <div>
                    <label style={{ fontSize: "0.76rem", fontWeight: 600, color: "var(--text-main)", display: "flex", alignItems: "center", gap: "6px", marginBottom: "4px" }}>
                      <Calendar size={13} color="var(--text-dim)" />
                      <span>Rescheduled Date & Time:</span>
                    </label>
                    <input
                      type="datetime-local"
                      value={customDateTime}
                      onChange={(e) => setCustomDateTime(e.target.value)}
                      style={{
                        width: "100%",
                        padding: "8px 10px",
                        background: "var(--surface-dark)",
                        border: "1px solid var(--surface-border)",
                        borderRadius: "6px",
                        color: "var(--text-main)",
                        fontSize: "0.78rem",
                      }}
                    />
                  </div>

                  {/* Venue Field */}
                  <div>
                    <label style={{ fontSize: "0.76rem", fontWeight: 600, color: "var(--text-main)", display: "flex", alignItems: "center", gap: "6px", marginBottom: "4px" }}>
                      <MapPin size={13} color="var(--text-dim)" />
                      <span>Assigned Venue / Examination Hall:</span>
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Turing Hall 2, Room 402"
                      value={customVenue}
                      onChange={(e) => setCustomVenue(e.target.value)}
                      style={{
                        width: "100%",
                        padding: "8px 10px",
                        background: "var(--surface-dark)",
                        border: "1px solid var(--surface-border)",
                        borderRadius: "6px",
                        color: "var(--text-main)",
                        fontSize: "0.78rem",
                      }}
                    />
                  </div>
                </div>
              )}

              <div>
                <label style={{ fontSize: "0.78rem", fontWeight: 600, color: "var(--text-main)", display: "block", marginBottom: "6px" }}>
                  HOD Audit Justification Note (Mandatory):
                </label>
                <textarea
                  rows={3}
                  value={overrideNote}
                  onChange={(e) => setOverrideNote(e.target.value)}
                  placeholder="Detail the institutional justification for this override..."
                  style={{
                    width: "100%",
                    padding: "8px 10px",
                    background: "var(--surface-dark)",
                    border: "1px solid var(--surface-border)",
                    borderRadius: "6px",
                    color: "var(--text-main)",
                    fontSize: "0.78rem",
                    resize: "vertical",
                  }}
                />
              </div>
            </div>

            <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end" }}>
              <button
                type="button"
                onClick={() => setSelectedCase(null)}
                disabled={submittingOverride}
                style={{
                  background: "transparent",
                  border: "1px solid var(--surface-border)",
                  borderRadius: "6px",
                  padding: "8px 14px",
                  color: "var(--text-muted)",
                  fontSize: "0.8rem",
                  cursor: "pointer",
                }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleExecuteOverride}
                disabled={submittingOverride}
                style={{
                  background: overrideDecision === "APPROVED" ? "var(--color-success)" : "var(--color-danger)",
                  border: "none",
                  borderRadius: "6px",
                  padding: "8px 16px",
                  color: "#FFFFFF",
                  fontSize: "0.8rem",
                  fontWeight: 600,
                  cursor: submittingOverride ? "not-allowed" : "pointer",
                }}
              >
                {submittingOverride ? "Recording..." : `Confirm ${overrideDecision === "APPROVED" ? "Override Approval" : "Final Rejection"}`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Timeline Modal */}
      {timelineCase && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0, 0, 0, 0.65)",
            backdropFilter: "blur(4px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "20px",
          }}
        >
          <div
            style={{
              background: "var(--surface-card)",
              border: "1px solid var(--surface-border)",
              borderRadius: "12px",
              padding: "24px",
              maxWidth: "540px",
              width: "100%",
              maxHeight: "85vh",
              overflowY: "auto",
              boxShadow: "var(--shadow-lg)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <h3 style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--text-main)", margin: 0 }}>
                Case Audit Trail #{timelineCase.id}
              </h3>
              <button
                onClick={() => setTimelineCase(null)}
                style={{ background: "transparent", border: "none", color: "var(--text-dim)", cursor: "pointer" }}
              >
                <X size={18} />
              </button>
            </div>

            {timelineLoading ? (
              <div style={{ padding: "20px", textAlign: "center", color: "var(--text-muted)" }}>Loading audit events...</div>
            ) : (
              <TimelineView entries={timelineEntries} />
            )}
          </div>
        </div>
      )}
    </div>
  );
};
