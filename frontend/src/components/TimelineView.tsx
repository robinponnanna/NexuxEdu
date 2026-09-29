"use client";

import React from "react";
import { CaseTimelineEntry } from "@/lib/api";
import { StatusChip } from "./StatusChip";
import { Clock, User } from "lucide-react";

interface TimelineViewProps {
  timeline?: CaseTimelineEntry[];
}

export const TimelineView: React.FC<TimelineViewProps> = ({ timeline = [] }) => {
  if (!timeline || timeline.length === 0) {
    return (
      <div
        style={{
          padding: "20px",
          textAlign: "center",
          color: "var(--text-muted)",
          fontSize: "0.85rem",
        }}
      >
        No historical timeline entries recorded for this case.
      </div>
    );
  }

  const sorted = [...timeline].sort(
    (a, b) => new Date(a.at).getTime() - new Date(b.at).getTime()
  );

  return (
    <div style={{ position: "relative", padding: "10px 0 10px 16px" }}>
      {/* Vertical Track Line */}
      <div
        style={{
          position: "absolute",
          top: "16px",
          bottom: "16px",
          left: "26px",
          width: "2px",
          background: "var(--surface-border)",
        }}
      />

      <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
        {sorted.map((item, index) => {
          const isLatest = index === sorted.length - 1;
          const formattedDate = new Date(item.at).toLocaleString(undefined, {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
          });

          return (
            <div
              key={item.id}
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: "14px",
                position: "relative",
              }}
            >
              {/* Node indicator */}
              <div
                style={{
                  width: "22px",
                  height: "22px",
                  borderRadius: "50%",
                  background: isLatest ? "var(--color-primary)" : "var(--surface-card)",
                  border: `2px solid ${isLatest ? "var(--color-primary)" : "var(--surface-border-focus)"}`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  zIndex: 2,
                  marginTop: "2px",
                  boxShadow: isLatest ? "0 0 0 3px rgba(15, 23, 42, 0.1)" : "none",
                }}
              >
                <div
                  style={{
                    width: "6px",
                    height: "6px",
                    borderRadius: "50%",
                    background: isLatest ? "#FFFFFF" : "var(--text-dim)",
                  }}
                />
              </div>

              {/* Content Card */}
              <div
                style={{
                  flex: 1,
                  background: isLatest ? "var(--surface-elevated)" : "var(--surface-card)",
                  border: `1px solid ${isLatest ? "var(--surface-border-focus)" : "var(--surface-border)"}`,
                  borderRadius: "10px",
                  padding: "12px 14px",
                  boxShadow: "var(--shadow-sm)",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    flexWrap: "wrap",
                    gap: "8px",
                    marginBottom: "6px",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <StatusChip status={item.to_status} size="sm" />
                    {item.from_status && (
                      <span
                        style={{
                          fontSize: "0.75rem",
                          color: "var(--text-dim)",
                        }}
                      >
                        (from {item.from_status})
                      </span>
                    )}
                  </div>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "4px",
                      fontSize: "0.75rem",
                      color: "var(--text-dim)",
                    }}
                  >
                    <Clock size={12} />
                    <span>{formattedDate}</span>
                  </div>
                </div>

                {item.note && (
                  <p
                    style={{
                      fontSize: "0.85rem",
                      color: "var(--text-main)",
                      margin: "6px 0 8px 0",
                      lineHeight: 1.45,
                    }}
                  >
                    {item.note}
                  </p>
                )}

                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    fontSize: "0.75rem",
                    color: "var(--text-muted)",
                  }}
                >
                  <User size={12} />
                  <span>
                    {item.actor_name || "System"}{" "}
                    <span style={{ color: "var(--text-dim)" }}>
                      ({item.actor_role})
                    </span>
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
