"use client";

import React from "react";
import { UserProfile } from "@/lib/api";
import { LayoutDashboard, Bus, UserCheck, ShieldAlert } from "lucide-react";

export type NavTab =
  | "dashboard"
  | "transit"
  | "attendance"
  | "policies"
  | "audits"
  | "events"
  | "reschedule"
  | "clashes"
  | "hod_dashboard";

interface SidebarProps {
  user: UserProfile | null;
  activeTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  onOpenChat: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ user, activeTab, onSelectTab }) => {
  const role = user?.role || "student";
  const isHOD = !!user?.is_hod;

  const navItems: { id: NavTab; label: string; icon: React.ComponentType<{ size: number; color?: string }>; visible: boolean }[] = [
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard, visible: true },
    { id: "events", label: "Event Clashes", icon: ShieldAlert, visible: role === "admin" },
    { id: "reschedule", label: "Retake Requests", icon: UserCheck, visible: role === "faculty" },
    { id: "hod_dashboard", label: "HOD Governance", icon: ShieldAlert, visible: role === "faculty" && isHOD },
    { id: "clashes", label: "My Clashes", icon: UserCheck, visible: role === "student" },
    { id: "transit", label: "Live Transit", icon: Bus, visible: role === "student" || role === "parent" || role === "admin" },
    { id: "attendance", label: role === "faculty" ? "Class Roster" : "Attendance Tracker", icon: UserCheck, visible: true },
    { id: "audits", label: "Security Audits", icon: ShieldAlert, visible: role === "admin" },
  ];

  return (
    <aside
      style={{
        width: "230px",
        minHeight: "calc(100vh - 61px)",
        background: "var(--surface-dark)",
        borderRight: "1px solid var(--surface-border)",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        padding: "20px 10px",
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
        <div
          style={{
            fontSize: "0.68rem",
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            color: "var(--text-dim)",
            padding: "0 12px 10px 12px",
          }}
        >
          Navigation
        </div>

        {navItems.filter((i) => i.visible).map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "11px",
                width: "100%",
                padding: "9px 12px",
                borderRadius: "7px",
                border: "1px solid",
                borderColor: isActive ? "var(--surface-border)" : "transparent",
                cursor: "pointer",
                background: isActive ? "var(--surface-elevated)" : "transparent",
                color: isActive ? "var(--text-main)" : "var(--text-muted)",
                fontWeight: isActive ? 600 : 400,
                fontSize: "0.85rem",
                textAlign: "left",
                transition: "all 0.15s ease",
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  e.currentTarget.style.background = "var(--surface-elevated)";
                  e.currentTarget.style.color = "var(--text-main)";
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  e.currentTarget.style.background = "transparent";
                  e.currentTarget.style.color = "var(--text-muted)";
                }
              }}
            >
              <Icon size={16} color={isActive ? "var(--color-primary)" : "var(--text-dim)"} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>
    </aside>
  );
};

