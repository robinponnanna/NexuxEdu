"use client";

import React, { useState, useEffect } from "react";
import {
  EventItem,
  EventDetailItem,
  ClashCaseItem,
  ReferenceStudent,
  getEvents,
  createEvent,
  getEventDetail,
  addEventParticipants,
  manualDetectClashes,
  fileClashCasesBulk,
  getReferenceStudents,
} from "@/lib/api";
import { StatusChip } from "./StatusChip";
import { TimelineView } from "./TimelineView";
import {
  Calendar,
  Plus,
  Users,
  AlertTriangle,
  RefreshCw,
  Send,
  Search,
  CheckSquare,
  Square,
  X,
  Clock,
  ChevronRight,
  Info,
} from "lucide-react";

interface AdminEventManagementProps {
  token: string;
}

export const AdminEventManagement: React.FC<AdminEventManagementProps> = ({ token }) => {
  const [events, setEvents] = useState<EventItem[]>([]);
  const [selectedEventId, setSelectedEventId] = useState<number | null>(null);
  const [eventDetail, setEventDetail] = useState<EventDetailItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Create event modal state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [startAt, setStartAt] = useState("");
  const [endAt, setEndAt] = useState("");

  // Participant picker state
  const [showPicker, setShowPicker] = useState(false);
  const [students, setStudents] = useState<ReferenceStudent[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedStudentIds, setSelectedStudentIds] = useState<number[]>([]);

  // Bulk case filing selection
  const [selectedCaseIds, setSelectedCaseIds] = useState<number[]>([]);

  // Timeline drill-down drawer
  const [activeTimelineCase, setActiveTimelineCase] = useState<ClashCaseItem | null>(null);

  const loadEvents = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getEvents(token);
      setEvents(data);
      if (data.length > 0 && !selectedEventId) {
        setSelectedEventId(data[0].id);
      }
    } catch (e: any) {
      setError(e.message || "Failed to load events");
    } finally {
      setLoading(false);
    }
  };

  const loadEventDetail = async (id: number) => {
    try {
      const detail = await getEventDetail(token, id);
      setEventDetail(detail);
      setSelectedCaseIds([]);
    } catch (e: any) {
      setError(e.message || "Failed to load event details");
    }
  };

  useEffect(() => {
    loadEvents();
  }, [token]);

  useEffect(() => {
    if (selectedEventId) {
      loadEventDetail(selectedEventId);
    }
  }, [selectedEventId]);

  // Load students for participant picker
  useEffect(() => {
    if (showPicker) {
      getReferenceStudents(token, searchQuery).then(setStudents).catch(console.error);
    }
  }, [showPicker, searchQuery]);

  const handleCreateEvent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title || !startAt || !endAt) return;
    setActionLoading(true);
    setError(null);
    try {
      // Ensure ISO format with Z
      const startIso = new Date(startAt).toISOString();
      const endIso = new Date(endAt).toISOString();
      const created = await createEvent(token, {
        title,
        description,
        start_at: startIso,
        end_at: endIso,
      });
      setShowCreateModal(false);
      setTitle("");
      setDescription("");
      setStartAt("");
      setEndAt("");
      await loadEvents();
      setSelectedEventId(created.id);
      setSuccessMsg(`Event "${created.title}" created successfully.`);
    } catch (e: any) {
      setError(e.message || "Failed to create event");
    } finally {
      setActionLoading(false);
    }
  };

  const handleAddParticipants = async () => {
    if (!selectedEventId || selectedStudentIds.length === 0) return;
    setActionLoading(true);
    setError(null);
    try {
      const res = await addEventParticipants(token, selectedEventId, selectedStudentIds);
      setShowPicker(false);
      setSelectedStudentIds([]);
      await loadEventDetail(selectedEventId);
      await loadEvents();
      setSuccessMsg(res.message);
    } catch (e: any) {
      setError(e.message || "Failed to add participants");
    } finally {
      setActionLoading(false);
    }
  };

  const handleManualDetect = async () => {
    if (!selectedEventId) return;
    setActionLoading(true);
    try {
      await manualDetectClashes(token, selectedEventId);
      await loadEventDetail(selectedEventId);
      setSuccessMsg("Clash detection scan completed.");
    } catch (e: any) {
      setError(e.message || "Detection failed");
    } finally {
      setActionLoading(false);
    }
  };

  const handleBulkFile = async () => {
    if (selectedCaseIds.length === 0) return;
    setActionLoading(true);
    setError(null);
    try {
      await fileClashCasesBulk(token, selectedCaseIds);
      if (selectedEventId) await loadEventDetail(selectedEventId);
      setSelectedCaseIds([]);
      setSuccessMsg(`Successfully filed ${selectedCaseIds.length} clash reschedule requests.`);
    } catch (e: any) {
      setError(e.message || "Bulk file failed");
    } finally {
      setActionLoading(false);
    }
  };

  const toggleSelectCase = (id: number) => {
    setSelectedCaseIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const detectedCases = eventDetail?.clashes.filter((c) => c.status === "DETECTED") || [];
  const allDetectedSelected =
    detectedCases.length > 0 && detectedCases.every((c) => selectedCaseIds.includes(c.id));

  const toggleSelectAllDetected = () => {
    if (allDetectedSelected) {
      setSelectedCaseIds((prev) =>
        prev.filter((id) => !detectedCases.some((c) => c.id === id))
      );
    } else {
      const idsToAdd = detectedCases.map((c) => c.id);
      setSelectedCaseIds((prev) => Array.from(new Set([...prev, ...idsToAdd])));
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Top Action Bar */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "12px",
        }}
      >
        <div>
          <h2 style={{ fontSize: "1.4rem", fontWeight: 700, color: "var(--text-main)" }}>
            Institutional Events & Exam Clashes
          </h2>
          <p style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
            Manage campus events, schedule participant cohorts, and dispatch automated clash reschedule workflows.
          </p>
        </div>

        <button
          onClick={() => setShowCreateModal(true)}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            background: "var(--color-primary)",
            color: "#FFFFFF",
            border: "none",
            borderRadius: "8px",
            padding: "9px 16px",
            fontWeight: 600,
            fontSize: "0.85rem",
            cursor: "pointer",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <Plus size={16} />
          Create Event
        </button>
      </div>

      {/* Alert Notices */}
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
          <button
            onClick={() => setError(null)}
            style={{ background: "none", border: "none", color: "#991B1B", cursor: "pointer" }}
          >
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
          <button
            onClick={() => setSuccessMsg(null)}
            style={{ background: "none", border: "none", color: "#166534", cursor: "pointer" }}
          >
            <X size={16} />
          </button>
        </div>
      )}

      {/* Main Grid: Events List on Left, Event Workspace on Right */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "300px 1fr",
          gap: "20px",
          alignItems: "start",
        }}
      >
        {/* Events Selector Column */}
        <div
          style={{
            background: "var(--surface-card)",
            border: "1px solid var(--surface-border)",
            borderRadius: "12px",
            padding: "16px",
            display: "flex",
            flexDirection: "column",
            gap: "10px",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <div
            style={{
              fontSize: "0.75rem",
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              color: "var(--text-dim)",
              marginBottom: "4px",
            }}
          >
            Registered Events ({events.length})
          </div>

          {events.length === 0 ? (
            <p style={{ fontSize: "0.82rem", color: "var(--text-muted)", padding: "12px 0" }}>
              No events found. Click "Create Event" above.
            </p>
          ) : (
            events.map((ev) => {
              const isSelected = ev.id === selectedEventId;
              const startDate = new Date(ev.start_at).toLocaleDateString([], {
                month: "short",
                day: "numeric",
              });

              return (
                <div
                  key={ev.id}
                  onClick={() => setSelectedEventId(ev.id)}
                  style={{
                    padding: "12px",
                    borderRadius: "8px",
                    border: "1px solid",
                    borderColor: isSelected ? "var(--color-primary)" : "var(--surface-border)",
                    background: isSelected ? "var(--surface-elevated)" : "var(--surface-card)",
                    cursor: "pointer",
                    transition: "all 0.15s ease",
                  }}
                >
                  <div
                    style={{
                      fontWeight: 700,
                      fontSize: "0.88rem",
                      color: "var(--text-main)",
                      marginBottom: "4px",
                    }}
                  >
                    {ev.title}
                  </div>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      fontSize: "0.75rem",
                      color: "var(--text-dim)",
                    }}
                  >
                    <span>{startDate}</span>
                    <div style={{ display: "flex", gap: "8px" }}>
                      <span>{ev.participants_count || 0} pts</span>
                      {(ev.clashes_count ?? 0) > 0 && (
                        <span style={{ color: "var(--color-danger)", fontWeight: 700 }}>
                          {ev.clashes_count} clashes
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Selected Event Details & Clash Management */}
        {eventDetail ? (
          <div
            style={{
              background: "var(--surface-card)",
              border: "1px solid var(--surface-border)",
              borderRadius: "12px",
              padding: "20px",
              display: "flex",
              flexDirection: "column",
              gap: "20px",
              boxShadow: "var(--shadow-sm)",
            }}
          >
            {/* Header info */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                flexWrap: "wrap",
                gap: "12px",
                borderBottom: "1px solid var(--surface-border)",
                paddingBottom: "16px",
              }}
            >
              <div>
                <h3 style={{ fontSize: "1.2rem", fontWeight: 700, color: "var(--text-main)" }}>
                  {eventDetail.title}
                </h3>
                <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", margin: "4px 0" }}>
                  {eventDetail.description || "No description provided."}
                </p>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "12px",
                    fontSize: "0.78rem",
                    color: "var(--text-dim)",
                    marginTop: "6px",
                  }}
                >
                  <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                    <Calendar size={13} />
                    {new Date(eventDetail.start_at).toLocaleString([], {
                      month: "short",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}{" "}
                    -{" "}
                    {new Date(eventDetail.end_at).toLocaleString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                  <span>•</span>
                  <span>{eventDetail.participants_count || 0} enrolled participants</span>
                </div>
              </div>

              {/* Action Buttons */}
              <div style={{ display: "flex", gap: "8px" }}>
                <button
                  onClick={() => setShowPicker(true)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    background: "var(--surface-elevated)",
                    color: "var(--text-main)",
                    border: "1px solid var(--surface-border)",
                    borderRadius: "6px",
                    padding: "7px 12px",
                    fontSize: "0.8rem",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  <Users size={14} />
                  Add Participants
                </button>

                <button
                  onClick={handleManualDetect}
                  disabled={actionLoading}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    background: "var(--surface-elevated)",
                    color: "var(--text-main)",
                    border: "1px solid var(--surface-border)",
                    borderRadius: "6px",
                    padding: "7px 12px",
                    fontSize: "0.8rem",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  <RefreshCw size={14} className={actionLoading ? "spin" : ""} />
                  Re-scan Clashes
                </button>
              </div>
            </div>

            {/* Clashes Table Header & Bulk Actions */}
            <div>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: "12px",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <h4 style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--text-main)" }}>
                    Detected Assessment Clashes ({eventDetail.clashes.length})
                  </h4>
                  {detectedCases.length > 0 && (
                    <span
                      style={{
                        background: "#FEF2F2",
                        color: "#991B1B",
                        padding: "2px 8px",
                        borderRadius: "9999px",
                        fontSize: "0.72rem",
                        fontWeight: 700,
                      }}
                    >
                      {detectedCases.length} Pending Filing
                    </span>
                  )}
                </div>

                {detectedCases.length > 0 && (
                  <button
                    onClick={handleBulkFile}
                    disabled={selectedCaseIds.length === 0 || actionLoading}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                      background:
                        selectedCaseIds.length > 0 ? "var(--color-student)" : "var(--surface-border)",
                      color: "#FFFFFF",
                      border: "none",
                      borderRadius: "6px",
                      padding: "6px 12px",
                      fontSize: "0.78rem",
                      fontWeight: 600,
                      cursor: selectedCaseIds.length > 0 ? "pointer" : "not-allowed",
                      transition: "all 0.15s ease",
                    }}
                  >
                    <Send size={13} />
                    File Selected Requests ({selectedCaseIds.length})
                  </button>
                )}
              </div>

              {eventDetail.clashes.length === 0 ? (
                <div
                  style={{
                    padding: "36px 20px",
                    textAlign: "center",
                    background: "var(--surface-elevated)",
                    borderRadius: "8px",
                    border: "1px dashed var(--surface-border)",
                    color: "var(--text-muted)",
                    fontSize: "0.85rem",
                  }}
                >
                  <AlertTriangle size={24} style={{ opacity: 0.4, marginBottom: "6px" }} />
                  <p>No assessment clashes detected for this event.</p>
                  <p style={{ fontSize: "0.78rem", color: "var(--text-dim)", marginTop: "4px" }}>
                    Add student participants from Section A to trigger clash detection.
                  </p>
                </div>
              ) : (
                <div
                  style={{
                    border: "1px solid var(--surface-border)",
                    borderRadius: "8px",
                    overflow: "hidden",
                  }}
                >
                  <table
                    style={{
                      width: "100%",
                      borderCollapse: "collapse",
                      fontSize: "0.8rem",
                      textAlign: "left",
                    }}
                  >
                    <thead>
                      <tr
                        style={{
                          background: "var(--surface-elevated)",
                          borderBottom: "1px solid var(--surface-border)",
                          color: "var(--text-dim)",
                          fontSize: "0.72rem",
                          textTransform: "uppercase",
                          letterSpacing: "0.04em",
                        }}
                      >
                        <th style={{ padding: "10px 12px", width: "36px" }}>
                          {detectedCases.length > 0 && (
                            <button
                              onClick={toggleSelectAllDetected}
                              style={{ background: "none", border: "none", cursor: "pointer", padding: 0 }}
                            >
                              {allDetectedSelected ? (
                                <CheckSquare size={16} color="var(--color-primary)" />
                              ) : (
                                <Square size={16} color="var(--text-dim)" />
                              )}
                            </button>
                          )}
                        </th>
                        <th style={{ padding: "10px 12px" }}>Student</th>
                        <th style={{ padding: "10px 12px" }}>Clashing Exam</th>
                        <th style={{ padding: "10px 12px" }}>Suggested Retake Slot</th>
                        <th style={{ padding: "10px 12px" }}>Status</th>
                        <th style={{ padding: "10px 12px", textAlign: "right" }}>Timeline</th>
                      </tr>
                    </thead>
                    <tbody>
                      {eventDetail.clashes.map((c) => {
                        const isSelectable = c.status === "DETECTED";
                        const isSelected = selectedCaseIds.includes(c.id);

                        return (
                          <tr
                            key={c.id}
                            style={{
                              borderBottom: "1px solid var(--surface-border-subtle)",
                              background: isSelected ? "rgba(239, 246, 255, 0.4)" : "var(--surface-card)",
                            }}
                          >
                            <td style={{ padding: "10px 12px" }}>
                              {isSelectable && (
                                <button
                                  onClick={() => toggleSelectCase(c.id)}
                                  style={{ background: "none", border: "none", cursor: "pointer", padding: 0 }}
                                >
                                  {isSelected ? (
                                    <CheckSquare size={16} color="var(--color-primary)" />
                                  ) : (
                                    <Square size={16} color="var(--text-dim)" />
                                  )}
                                </button>
                              )}
                            </td>
                            <td style={{ padding: "10px 12px" }}>
                              <div style={{ fontWeight: 600, color: "var(--text-main)" }}>
                                {c.student_name}
                              </div>
                              <div style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>
                                {c.student_roll} • {c.student_section || "Sec A"}
                              </div>
                            </td>
                            <td style={{ padding: "10px 12px" }}>
                              <div style={{ fontWeight: 600, color: "var(--text-main)" }}>
                                {c.subject} ({c.course_code})
                              </div>
                              <div style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>
                                {c.assessment_kind} • {c.faculty_name || "Faculty"}
                              </div>
                            </td>
                            <td style={{ padding: "10px 12px" }}>
                              {c.suggested_retake_info ? (
                                <div style={{ color: "var(--color-faculty)", fontWeight: 600 }}>
                                  {c.suggested_retake_info}
                                </div>
                              ) : (
                                <div style={{ color: "var(--text-dim)", fontStyle: "italic" }}>
                                  No sister section slot (Custom slot required)
                                </div>
                              )}
                            </td>
                            <td style={{ padding: "10px 12px" }}>
                              <StatusChip status={c.status} size="sm" />
                            </td>
                            <td style={{ padding: "10px 12px", textAlign: "right" }}>
                              <button
                                onClick={() => setActiveTimelineCase(c)}
                                style={{
                                  background: "none",
                                  border: "none",
                                  color: "var(--color-primary)",
                                  fontWeight: 600,
                                  cursor: "pointer",
                                  fontSize: "0.75rem",
                                  display: "inline-flex",
                                  alignItems: "center",
                                  gap: "3px",
                                }}
                              >
                                View Log <ChevronRight size={13} />
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div
            style={{
              padding: "40px",
              textAlign: "center",
              background: "var(--surface-card)",
              border: "1px solid var(--surface-border)",
              borderRadius: "12px",
              color: "var(--text-muted)",
            }}
          >
            Select an event on the left to inspect its clash cases.
          </div>
        )}
      </div>

      {/* Create Event Modal */}
      {showCreateModal && (
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
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "16px",
              }}
            >
              <h3 style={{ fontSize: "1.15rem", fontWeight: 700, color: "var(--text-main)" }}>
                Create Institutional Event
              </h3>
              <button
                onClick={() => setShowCreateModal(false)}
                style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-dim)" }}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleCreateEvent} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 600, marginBottom: "4px" }}>
                  Event Title *
                </label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Smart Campus Hackathon 2026"
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: "6px",
                    border: "1px solid var(--surface-border-focus)",
                    fontSize: "0.85rem",
                  }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 600, marginBottom: "4px" }}>
                  Description
                </label>
                <textarea
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Inter-college technical competition..."
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: "6px",
                    border: "1px solid var(--surface-border-focus)",
                    fontSize: "0.85rem",
                    fontFamily: "inherit",
                  }}
                />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 600, marginBottom: "4px" }}>
                    Start Date & Time *
                  </label>
                  <input
                    type="datetime-local"
                    required
                    value={startAt}
                    onChange={(e) => setStartAt(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "8px 10px",
                      borderRadius: "6px",
                      border: "1px solid var(--surface-border-focus)",
                      fontSize: "0.82rem",
                    }}
                  />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 600, marginBottom: "4px" }}>
                    End Date & Time *
                  </label>
                  <input
                    type="datetime-local"
                    required
                    value={endAt}
                    onChange={(e) => setEndAt(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "8px 10px",
                      borderRadius: "6px",
                      border: "1px solid var(--surface-border-focus)",
                      fontSize: "0.82rem",
                    }}
                  />
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "10px" }}>
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
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
                    background: "var(--color-primary)",
                    color: "#FFFFFF",
                    border: "none",
                    borderRadius: "6px",
                    fontSize: "0.82rem",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  {actionLoading ? "Creating..." : "Save Event"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Participant Picker Modal */}
      {showPicker && (
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
              width: "560px",
              maxHeight: "620px",
              background: "var(--surface-card)",
              border: "1px solid var(--surface-border)",
              borderRadius: "12px",
              padding: "24px",
              boxShadow: "var(--shadow-lg)",
              display: "flex",
              flexDirection: "column",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "16px",
              }}
            >
              <div>
                <h3 style={{ fontSize: "1.15rem", fontWeight: 700, color: "var(--text-main)" }}>
                  Enroll Students in Event
                </h3>
                <p style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                  Enrolling students will automatically execute clash detection against their examination schedules.
                </p>
              </div>
              <button
                onClick={() => setShowPicker(false)}
                style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-dim)" }}
              >
                <X size={18} />
              </button>
            </div>

            <div style={{ position: "relative", marginBottom: "12px" }}>
              <Search
                size={14}
                style={{ position: "absolute", left: "10px", top: "11px", color: "var(--text-dim)" }}
              />
              <input
                type="text"
                placeholder="Search by student name or roll number..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  width: "100%",
                  padding: "8px 12px 8px 32px",
                  borderRadius: "6px",
                  border: "1px solid var(--surface-border-focus)",
                  fontSize: "0.82rem",
                }}
              />
            </div>

            <div
              style={{
                flex: 1,
                overflowY: "auto",
                border: "1px solid var(--surface-border)",
                borderRadius: "8px",
                maxHeight: "320px",
              }}
            >
              {students.length === 0 ? (
                <div style={{ padding: "20px", textAlign: "center", color: "var(--text-muted)", fontSize: "0.82rem" }}>
                  No students found.
                </div>
              ) : (
                students.map((s) => {
                  const isChecked = selectedStudentIds.includes(s.id);
                  return (
                    <div
                      key={s.id}
                      onClick={() =>
                        setSelectedStudentIds((prev) =>
                          isChecked ? prev.filter((id) => id !== s.id) : [...prev, s.id]
                        )
                      }
                      style={{
                        padding: "10px 14px",
                        borderBottom: "1px solid var(--surface-border-subtle)",
                        display: "flex",
                        alignItems: "center",
                        gap: "12px",
                        cursor: "pointer",
                        background: isChecked ? "rgba(239, 246, 255, 0.4)" : "var(--surface-card)",
                      }}
                    >
                      {isChecked ? (
                        <CheckSquare size={16} color="var(--color-primary)" />
                      ) : (
                        <Square size={16} color="var(--text-dim)" />
                      )}
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 600, fontSize: "0.85rem", color: "var(--text-main)" }}>
                          {s.name}
                        </div>
                        <div style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>
                          {s.roll_number} • {s.department} • {s.section}
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginTop: "16px",
              }}
            >
              <span style={{ fontSize: "0.8rem", color: "var(--text-dim)" }}>
                {selectedStudentIds.length} student(s) selected
              </span>

              <div style={{ display: "flex", gap: "8px" }}>
                <button
                  onClick={() => setShowPicker(false)}
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
                  onClick={handleAddParticipants}
                  disabled={selectedStudentIds.length === 0 || actionLoading}
                  style={{
                    padding: "8px 16px",
                    background: "var(--color-primary)",
                    color: "#FFFFFF",
                    border: "none",
                    borderRadius: "6px",
                    fontSize: "0.82rem",
                    fontWeight: 600,
                    cursor: selectedStudentIds.length > 0 ? "pointer" : "not-allowed",
                  }}
                >
                  {actionLoading ? "Enrolling & Scanning..." : "Add & Scan Clashes"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Timeline Drill-Down Drawer */}
      {activeTimelineCase && (
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
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                borderBottom: "1px solid var(--surface-border)",
                paddingBottom: "14px",
                marginBottom: "16px",
              }}
            >
              <div>
                <h3 style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--text-main)" }}>
                  Case Audit Log & History
                </h3>
                <p style={{ fontSize: "0.78rem", color: "var(--text-dim)" }}>
                  Case #{activeTimelineCase.id} • {activeTimelineCase.student_name}
                </p>
              </div>
              <button
                onClick={() => setActiveTimelineCase(null)}
                style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-dim)" }}
              >
                <X size={18} />
              </button>
            </div>

            <div
              style={{
                background: "var(--surface-elevated)",
                border: "1px solid var(--surface-border)",
                borderRadius: "8px",
                padding: "12px",
                marginBottom: "16px",
              }}
            >
              <div style={{ fontWeight: 600, fontSize: "0.85rem", color: "var(--text-main)" }}>
                {activeTimelineCase.subject} ({activeTimelineCase.assessment_kind})
              </div>
              <div style={{ fontSize: "0.78rem", color: "var(--text-dim)", marginTop: "4px" }}>
                Current Status: <StatusChip status={activeTimelineCase.status} size="sm" />
              </div>
              {activeTimelineCase.rejection_reason && (
                <div style={{ fontSize: "0.78rem", color: "var(--color-danger)", marginTop: "6px" }}>
                  <strong>Rejection Reason:</strong> {activeTimelineCase.rejection_reason}
                </div>
              )}
            </div>

            <TimelineView timeline={activeTimelineCase.timeline} />
          </div>
        </div>
      )}
    </div>
  );
};
