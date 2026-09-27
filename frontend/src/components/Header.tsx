"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { UserProfile } from "@/lib/api";
import {
  ShieldCheck,
  User,
  GraduationCap,
  School,
  Users,
  Shield,
  LogOut,
  ChevronDown,
  Lock,
  Mail,
  Building,
} from "lucide-react";

interface HeaderProps {
  user: UserProfile | null;
  onSwitchRole?: (email: string) => void;
  onLogout?: () => void;
  isLoading?: boolean;
}

export const Header: React.FC<HeaderProps> = ({ user, onLogout }) => {
  const router = useRouter();
  const [isHovered, setIsHovered] = useState(false);

  const getRoleBadgeClass = (role?: string) => {
    switch (role) {
      case "student":
        return "badge-student";
      case "faculty":
        return "badge-faculty";
      case "parent":
        return "badge-parent";
      case "admin":
        return "badge-admin";
      default:
        return "badge-student";
    }
  };

  const getRoleColor = (role?: string) => {
    switch (role) {
      case "student":
        return "var(--color-student)";
      case "faculty":
        return "var(--color-faculty)";
      case "parent":
        return "var(--color-parent)";
      case "admin":
        return "var(--color-admin)";
      default:
        return "var(--color-primary)";
    }
  };

  const handleSignOut = () => {
    if (onLogout) {
      onLogout();
    } else {
      if (typeof window !== "undefined") {
        localStorage.removeItem("omnicampus_session");
      }
      router.push("/login");
    }
  };

  return (
    <header
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "14px 28px",
        background: "var(--surface-dark)",
        borderBottom: "1px solid var(--surface-border)",
        position: "sticky",
        top: 0,
        zIndex: 100,
      }}
    >
      {/* Brand & Title */}
      <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
        <div
          onClick={() => router.push("/")}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            fontWeight: 700,
            fontSize: "1.15rem",
            letterSpacing: "-0.02em",
            cursor: "pointer",
          }}
        >
          <div
            style={{
              width: "34px",
              height: "34px",
              borderRadius: "8px",
              background: "var(--surface-elevated)",
              border: "1px solid var(--surface-border)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--color-primary)",
              boxShadow: "var(--shadow-sm)",
            }}
          >
            <ShieldCheck size={20} />
          </div>
          <span style={{ color: "var(--text-main)", fontWeight: 700 }}>
            OmniCampus <span style={{ color: "var(--color-primary)", fontWeight: 600 }}>ERP</span>
          </span>
        </div>
      </div>

      {/* Top Right Profile Section with Hover Role Display */}
      <div style={{ display: "flex", alignItems: "center", gap: "18px" }}>
        {user && (
          <div
            id="user-profile-container"
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
            style={{
              position: "relative",
            }}
          >
            {/* Clickable/Hoverable Trigger */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                cursor: "pointer",
                padding: "6px 12px",
                borderRadius: "8px",
                border: "1px solid",
                borderColor: isHovered ? "var(--surface-border-focus)" : "transparent",
                background: isHovered ? "var(--surface-elevated)" : "transparent",
                transition: "all 0.2s ease",
              }}
            >
              {/* Profile Icon */}
              <div
                style={{
                  width: "34px",
                  height: "34px",
                  borderRadius: "50%",
                  background: "var(--surface-elevated)",
                  border: "1px solid var(--surface-border)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "var(--text-main)",
                  fontWeight: 600,
                  fontSize: "0.85rem",
                  flexShrink: 0,
                }}
              >
                <User size={16} color="var(--text-muted)" />
              </div>

              {/* Name & Role Text */}
              <div style={{ textAlign: "left" }}>
                <div
                  id="header-user-name"
                  style={{
                    fontSize: "0.85rem",
                    fontWeight: 600,
                    color: "var(--text-main)",
                    display: "flex",
                    alignItems: "center",
                    gap: "5px",
                  }}
                >
                  <span>{user.name}</span>
                  <ChevronDown
                    size={13}
                    color="var(--text-dim)"
                    style={{
                      transform: isHovered ? "rotate(180deg)" : "rotate(0deg)",
                      transition: "transform 0.2s ease",
                    }}
                  />
                </div>
                <div style={{ fontSize: "0.7rem", color: "var(--text-dim)", fontWeight: 500 }}>
                  Role: <span style={{ color: getRoleColor(user.role), fontWeight: 600, textTransform: "capitalize" }}>{user.role}</span>
                </div>
              </div>
            </div>

            {/* Hover Tooltip / Floating Profile Card */}
            {isHovered && (
              <div
                id="role-hover-card"
                style={{
                  position: "absolute",
                  top: "calc(100% + 8px)",
                  right: 0,
                  width: "320px",
                  background: "var(--surface-card)",
                  backdropFilter: "blur(20px)",
                  border: "1px solid var(--surface-border)",
                  borderRadius: "12px",
                  padding: "16px 18px",
                  boxShadow: "var(--shadow-lg)",
                  zIndex: 200,
                  animation: "fadeIn 0.15s ease-out",
                }}
              >
                {/* Header with Role Title */}
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    paddingBottom: "12px",
                    borderBottom: "1px solid var(--surface-border)",
                    marginBottom: "12px",
                  }}
                >
                  <div>
                    <div style={{ fontSize: "0.68rem", color: "var(--text-dim)", textTransform: "uppercase", fontWeight: 600, letterSpacing: "0.05em" }}>
                      AUTHENTICATED ROLE
                    </div>
                    <div
                      id="hover-role-display"
                      style={{
                        fontSize: "0.98rem",
                        fontWeight: 700,
                        color: getRoleColor(user.role),
                        letterSpacing: "0.02em",
                        textTransform: "uppercase",
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                        marginTop: "2px",
                      }}
                    >
                      <Lock size={14} />
                      <span>{user.role}</span>
                    </div>
                  </div>

                  <span
                    className={getRoleBadgeClass(user.role)}
                    style={{
                      padding: "3px 8px",
                      borderRadius: "6px",
                      fontSize: "0.68rem",
                      fontWeight: 600,
                      textTransform: "uppercase",
                    }}
                  >
                    Active
                  </span>
                </div>

                {/* User Identity Details */}
                <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginBottom: "12px", fontSize: "0.8rem" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--text-main)" }}>
                    <Mail size={13} color="var(--text-dim)" />
                    <span className="font-mono" style={{ fontSize: "0.76rem" }}>{user.email}</span>
                  </div>

                  {user.department && (
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--text-muted)" }}>
                      <Building size={13} color="var(--text-dim)" />
                      <span>Dept: {user.department}</span>
                    </div>
                  )}

                  {user.role === "parent" && (
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--color-parent)" }}>
                      <Users size={13} />
                      <span>Ward: Jane Doe (Student ID #1)</span>
                    </div>
                  )}

                  {user.bus_id && (
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--text-muted)" }}>
                      <span style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>Assigned Vehicle:</span>
                      <strong style={{ color: "var(--text-main)" }}>BUS-00{user.bus_id}</strong>
                    </div>
                  )}
                </div>

                {/* Actions Footer */}
                <div style={{ display: "flex", gap: "8px", paddingTop: "6px", borderTop: "1px solid var(--surface-border)" }}>
                  <button
                    type="button"
                    onClick={handleSignOut}
                    style={{
                      flex: 1,
                      background: "#FEF2F2",
                      border: "1px solid #FECACA",
                      borderRadius: "6px",
                      padding: "8px 12px",
                      color: "var(--color-danger)",
                      fontSize: "0.78rem",
                      fontWeight: 600,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: "6px",
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = "#FEE2E2")}
                    onMouseLeave={(e) => (e.currentTarget.style.background = "#FEF2F2")}
                  >
                    <LogOut size={13} />
                    <span>Sign Out</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => router.push("/login")}
                    style={{
                      flex: 1,
                      background: "var(--surface-elevated)",
                      border: "1px solid var(--surface-border)",
                      borderRadius: "6px",
                      padding: "8px 12px",
                      color: "var(--text-main)",
                      fontSize: "0.78rem",
                      fontWeight: 500,
                      cursor: "pointer",
                      textAlign: "center",
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-hover)")}
                    onMouseLeave={(e) => (e.currentTarget.style.background = "var(--surface-elevated)")}
                  >
                    Switch User
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </header>
  );
};

