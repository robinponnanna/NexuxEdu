"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { login, AuthSession } from "@/lib/api";
import {
  ShieldCheck,
  Lock,
  Mail,
  ArrowRight,
  Eye,
  EyeOff,
  GraduationCap,
  School,
  Users,
  Shield,
  Sparkles,
  AlertCircle,
} from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("student@campus.edu");
  const [password, setPassword] = useState("password123");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const demoAccounts = [
    {
      role: "student",
      email: "student@campus.edu",
      name: "Jane Doe",
      title: "Student (CS Sem 6)",
      icon: GraduationCap,
      color: "var(--color-student)",
    },
    {
      role: "faculty",
      email: "faculty@campus.edu",
      name: "Prof. Alan Turing",
      title: "Faculty (HOD, CS)",
      icon: School,
      color: "var(--color-faculty)",
    },
    {
      role: "parent",
      email: "parent@campus.edu",
      name: "Robert Doe",
      title: "Parent (Ward: Jane)",
      icon: Users,
      color: "var(--color-parent)",
    },
    {
      role: "admin",
      email: "admin@campus.edu",
      name: "Sarah Connor",
      title: "Campus Administrator",
      icon: Shield,
      color: "var(--color-admin)",
    },
  ];

  const handleLogin = async (e?: React.FormEvent, directEmail?: string) => {
    if (e) e.preventDefault();
    const loginEmail = directEmail || email;
    setIsLoading(true);
    setErrorMessage("");

    try {
      const session: AuthSession = await login(loginEmail, password);
      // Persist session in localStorage for automatic role recognition
      if (typeof window !== "undefined") {
        localStorage.setItem("omnicampus_session", JSON.stringify(session));
      }
      // Navigate to dashboard where role and rights are automatically applied
      router.push("/");
    } catch (err: any) {
      setErrorMessage(err.message || "Invalid credentials. Please verify your email and password.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectPreset = (presetEmail: string) => {
    setEmail(presetEmail);
    setPassword("password123");
    handleLogin(undefined, presetEmail);
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--surface-dark)",
        padding: "24px",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "440px",
          borderRadius: "14px",
          padding: "36px 32px",
          background: "var(--surface-card)",
          boxShadow: "var(--shadow-lg)",
          border: "1px solid var(--surface-border)",
        }}
      >
        {/* Brand Header */}
        <div style={{ textAlign: "center", marginBottom: "28px" }}>
          <div
            style={{
              width: "44px",
              height: "44px",
              borderRadius: "10px",
              background: "var(--surface-elevated)",
              border: "1px solid var(--surface-border)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 16px auto",
              color: "var(--color-primary)",
              boxShadow: "var(--shadow-sm)",
            }}
          >
            <ShieldCheck size={26} />
          </div>

          <h1 style={{ fontSize: "1.45rem", fontWeight: 700, color: "var(--text-main)", letterSpacing: "-0.02em" }}>
            OmniCampus <span style={{ color: "var(--color-primary)", fontWeight: 600 }}>ERP</span>
          </h1>
          <p style={{ fontSize: "0.82rem", color: "var(--text-muted)", marginTop: "4px" }}>
            Role-Based Academic Governance & SafeTransit
          </p>
        </div>

        {/* Error Notification */}
        {errorMessage && (
          <div
            style={{
              background: "rgba(248, 113, 113, 0.08)",
              border: "1px solid rgba(248, 113, 113, 0.25)",
              borderRadius: "7px",
              padding: "10px 14px",
              marginBottom: "18px",
              display: "flex",
              alignItems: "center",
              gap: "10px",
              color: "var(--color-danger)",
              fontSize: "0.8rem",
            }}
          >
            <AlertCircle size={15} />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {/* Email Field */}
          <div>
            <label style={{ display: "block", fontSize: "0.72rem", fontWeight: 600, color: "var(--text-dim)", marginBottom: "6px", letterSpacing: "0.04em" }}>
              INSTITUTIONAL EMAIL
            </label>
            <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
              <div style={{ position: "absolute", left: "14px", color: "var(--text-dim)" }}>
                <Mail size={15} />
              </div>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@campus.edu"
                style={{
                  width: "100%",
                  background: "var(--surface-elevated)",
                  border: "1px solid var(--surface-border)",
                  borderRadius: "7px",
                  padding: "11px 14px 11px 40px",
                  color: "var(--text-main)",
                  fontSize: "0.85rem",
                  outline: "none",
                  transition: "border-color 0.18s ease",
                }}
                onFocus={(e) => (e.target.style.borderColor = "var(--surface-border-focus)")}
                onBlur={(e) => (e.target.style.borderColor = "var(--surface-border)")}
              />
            </div>
          </div>

          {/* Password Field */}
          <div>
            <label style={{ display: "block", fontSize: "0.72rem", fontWeight: 600, color: "var(--text-dim)", marginBottom: "6px", letterSpacing: "0.04em" }}>
              SECURITY PASSWORD
            </label>
            <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
              <div style={{ position: "absolute", left: "14px", color: "var(--text-dim)" }}>
                <Lock size={15} />
              </div>
              <input
                type={showPassword ? "text" : "password"}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                style={{
                  width: "100%",
                  background: "var(--surface-elevated)",
                  border: "1px solid var(--surface-border)",
                  borderRadius: "7px",
                  padding: "11px 40px 11px 40px",
                  color: "var(--text-main)",
                  fontSize: "0.85rem",
                  outline: "none",
                  transition: "border-color 0.18s ease",
                }}
                onFocus={(e) => (e.target.style.borderColor = "var(--surface-border-focus)")}
                onBlur={(e) => (e.target.style.borderColor = "var(--surface-border)")}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                style={{
                  position: "absolute",
                  right: "12px",
                  background: "transparent",
                  border: "none",
                  color: "var(--text-dim)",
                  cursor: "pointer",
                }}
              >
                {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isLoading}
            style={{
              marginTop: "6px",
              background: "var(--text-main)",
              color: "#FFFFFF",
              border: "none",
              borderRadius: "7px",
              padding: "11px",
              fontSize: "0.88rem",
              fontWeight: 600,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "8px",
              boxShadow: "var(--shadow-sm)",
              transition: "opacity 0.15s ease",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.opacity = "0.9")}
            onMouseLeave={(e) => (e.currentTarget.style.opacity = "1")}
          >
            {isLoading ? (
              <span>Authenticating Claims...</span>
            ) : (
              <>
                <span>Sign In to Campus ERP</span>
                <ArrowRight size={15} />
              </>
            )}
          </button>
        </form>

        {/* Demo Roles Quick Auto-Fill */}
        <div style={{ marginTop: "24px", borderTop: "1px solid var(--surface-border)", paddingTop: "18px" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
            {demoAccounts.map((acc) => {
              const Icon = acc.icon;
              return (
                <button
                  key={acc.role}
                  type="button"
                  onClick={() => handleSelectPreset(acc.email)}
                  disabled={isLoading}
                  style={{
                    background: "var(--surface-elevated)",
                    border: "1px solid var(--surface-border)",
                    borderRadius: "7px",
                    padding: "9px 10px",
                    display: "flex",
                    alignItems: "center",
                    gap: "9px",
                    textAlign: "left",
                    cursor: "pointer",
                    transition: "all 0.15s ease",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = "var(--surface-border-focus)";
                    e.currentTarget.style.background = "var(--surface-hover)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = "var(--surface-border)";
                    e.currentTarget.style.background = "var(--surface-elevated)";
                  }}
                >
                  <div
                    style={{
                      width: "30px",
                      height: "30px",
                      borderRadius: "6px",
                      background: "var(--surface-card)",
                      border: "1px solid var(--surface-border)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: acc.color,
                      flexShrink: 0,
                      boxShadow: "var(--shadow-sm)",
                    }}
                  >
                    <Icon size={15} />
                  </div>
                  <div>
                    <div style={{ fontSize: "0.78rem", fontWeight: 600, color: "var(--text-main)" }}>
                      {acc.name}
                    </div>
                    <div style={{ fontSize: "0.66rem", color: acc.color, textTransform: "capitalize", fontWeight: 500 }}>
                      {acc.role}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
