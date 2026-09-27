"use client";

import React from "react";
import { AlertCircle, CheckCircle2, AlertTriangle } from "lucide-react";

export interface SubjectAttendance {
  id: number;
  subject: string;
  attended_classes: number;
  total_classes: number;
  attendance_pct: number;
}

interface AttendanceCardProps {
  record: SubjectAttendance;
}

export const AttendanceCard: React.FC<AttendanceCardProps> = ({ record }) => {
  const pct = record.attendance_pct;

  // Minimal status color scheme (High contrast on white)
  let statusColor = "var(--color-success)";
  let statusText = "Safe Standing";
  let statusIcon = CheckCircle2;
  let bgTint = "#ECFDF5";
  let borderTint = "#A7F3D0";

  if (pct < 75.0) {
    statusColor = "var(--color-danger)";
    statusText = "Debarment Risk (< 75%)";
    statusIcon = AlertCircle;
    bgTint = "#FEF2F2";
    borderTint = "#FECACA";
  } else if (pct < 85.0) {
    statusColor = "var(--color-warning)";
    statusText = "Attention Required";
    statusIcon = AlertTriangle;
    bgTint = "#FFFBEB";
    borderTint = "#FDE68A";
  }

  const StatusIcon = statusIcon;

  // SVG circular ring calculation
  const radius = 36;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (pct / 100) * circumference;

  return (
    <div
      style={{
        background: "var(--surface-card)",
        border: "1px solid var(--surface-border)",
        borderRadius: "10px",
        padding: "18px 20px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "16px",
        boxShadow: "var(--shadow-sm)",
        transition: "border-color 0.18s ease, transform 0.18s ease",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = "var(--surface-border-focus)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = "var(--surface-border)";
      }}
    >
      {/* Subject & Class Counts */}
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: "0.95rem", fontWeight: 600, color: "var(--text-main)", marginBottom: "5px" }}>
          {record.subject}
        </div>

        <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "10px" }}>
          Classes Attended: <strong className="font-mono" style={{ color: "var(--text-main)", fontWeight: 600 }}>{record.attended_classes}</strong> / {record.total_classes}
        </div>

        {/* Minimal Pill Badge */}
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "5px",
            padding: "3px 8px",
            borderRadius: "5px",
            background: bgTint,
            color: statusColor,
            fontSize: "0.72rem",
            fontWeight: 600,
            border: `1px solid ${borderTint}`,
          }}
        >
          <StatusIcon size={12} />
          <span>{statusText}</span>
        </div>
      </div>

      {/* Circular Progress Ring */}
      <div style={{ position: "relative", width: "84px", height: "84px", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <svg width="84" height="84" style={{ transform: "rotate(-90deg)" }}>
          {/* Background circle */}
          <circle
            cx="42"
            cy="42"
            r={radius}
            stroke="var(--surface-border)"
            strokeWidth="5"
            fill="transparent"
          />
          {/* Animated active progress circle */}
          <circle
            cx="42"
            cy="42"
            r={radius}
            stroke={statusColor}
            strokeWidth="5"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            fill="transparent"
            style={{ transition: "stroke-dashoffset 0.8s ease" }}
          />
        </svg>

        {/* Centered Percentage */}
        <div
          style={{
            position: "absolute",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <span className="font-mono" style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text-main)" }}>
            {pct}%
          </span>
        </div>
      </div>
    </div>
  );
};

