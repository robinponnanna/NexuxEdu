"use client";

import React from "react";

export type ClashStatus =
  | "DETECTED"
  | "REQUEST_FILED"
  | "COUNTER_PROPOSED"
  | "REJECTED"
  | "ESCALATED_TO_HOD"
  | "APPROVED"
  | "COMPLETED";

interface StatusChipProps {
  status: string;
  size?: "sm" | "md";
}

export const StatusChip: React.FC<StatusChipProps> = ({ status, size = "md" }) => {
  const normalized = (status || "").toUpperCase();

  const getStyle = (): { bg: string; color: string; border: string; label: string } => {
    switch (normalized) {
      case "DETECTED":
        return {
          bg: "#FEF2F2",
          color: "#991B1B",
          border: "#FCA5A5",
          label: "Clash Detected",
        };
      case "REQUEST_FILED":
        return {
          bg: "#EFF6FF",
          color: "#1E40AF",
          border: "#93C5FD",
          label: "Request Filed",
        };
      case "COUNTER_PROPOSED":
        return {
          bg: "#FFFBEB",
          color: "#92400E",
          border: "#FCD34D",
          label: "Counter Proposed",
        };
      case "REJECTED":
        return {
          bg: "#FFF1F2",
          color: "#9F1239",
          border: "#FDA4AF",
          label: "Rejected",
        };
      case "ESCALATED_TO_HOD":
        return {
          bg: "#FAF5FF",
          color: "#6B21A8",
          border: "#D8B4FE",
          label: "Escalated to HOD",
        };
      case "APPROVED":
        return {
          bg: "#F0FDF4",
          color: "#166534",
          border: "#86EFAC",
          label: "Approved",
        };
      case "COMPLETED":
        return {
          bg: "#F8FAFC",
          color: "#334155",
          border: "#CBD5E1",
          label: "Completed",
        };
      default:
        return {
          bg: "#F1F5F9",
          color: "#475569",
          border: "#E2E8F0",
          label: status,
        };
    }
  };

  const config = getStyle();
  const padding = size === "sm" ? "2px 8px" : "4px 10px";
  const fontSize = size === "sm" ? "0.68rem" : "0.75rem";

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "5px",
        padding,
        fontSize,
        fontWeight: 600,
        borderRadius: "9999px",
        background: config.bg,
        color: config.color,
        border: `1px solid ${config.border}`,
        whiteSpace: "nowrap",
      }}
    >
      <span
        style={{
          width: size === "sm" ? "5px" : "6px",
          height: size === "sm" ? "5px" : "6px",
          borderRadius: "50%",
          background: config.color,
        }}
      />
      {config.label}
    </span>
  );
};
