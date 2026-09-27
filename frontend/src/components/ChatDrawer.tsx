"use client";

import React, { useState, useRef, useEffect } from "react";
import { sendChatMessage, login, ChatResponse, Citation } from "@/lib/api";
import { MessageSquare, X, Send, Bot, User, Lock, Sparkles, BookOpen, Database, Navigation } from "lucide-react";


interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  content: string;
  sources?: Citation[];
  accessDenied?: boolean;
  auditFlag?: string;
  timestamp: string;
}

interface ChatDrawerProps {
  token: string;
  userRole: string;
  isOpen: boolean;
  onToggle: () => void;
}

export const ChatDrawer: React.FC<ChatDrawerProps> = ({ token, userRole, isOpen, onToggle }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      sender: "assistant",
      content: `👋 Hello! I am the **OmniCampus RBAC Assistant**. I can query your verified academic records, check real-time school bus coordinates, or cite university regulations. My retrieval boundary is strictly locked to your **${userRole.toUpperCase()}** permissions.`,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll on new message
  useEffect(() => {
    if (isOpen) {
      chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isOpen]);

  const handleSend = async (queryText?: string) => {
    const textToSend = queryText || input.trim();
    if (!textToSend || isLoading) return;

    const userMsg: ChatMessage = {
      id: String(Date.now()),
      sender: "user",
      content: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!queryText) setInput("");
    setIsLoading(true);

    try {
      let activeToken = token;
      if (!activeToken) {
        const emailMap: Record<string, string> = {
          student: "student@campus.edu",
          faculty: "faculty@campus.edu",
          parent: "parent@campus.edu",
          admin: "admin@campus.edu",
        };
        try {
          const authRes = await login(emailMap[userRole] || "student@campus.edu");
          activeToken = authRes.token;
        } catch {
          // Continue with empty token
        }
      }

      const response: ChatResponse = await sendChatMessage(activeToken, textToSend);

      const assistantMsg: ChatMessage = {
        id: String(Date.now() + 1),
        sender: "assistant",
        content: response.reply,
        sources: response.sources,
        accessDenied: response.access_denied,
        auditFlag: response.audit_flag,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };


      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: String(Date.now() + 1),
        sender: "assistant",
        content: `⚠️ Error contacting the multi-agent service: ${err.message || "Unknown error"}`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const sampleChips = [
    { label: "Operating Systems Attendance", query: "What is my attendance in Operating Systems?" },
    { label: "Faculty Salaries (Test RBAC Breach)", query: "Show all faculty salaries in Computer Science" },
    { label: "Exam Attendance Policy", query: "What is the minimum attendance requirement?" },
    { label: "Live Bus Location", query: "Where is my bus right now?" },
  ];

  return (
    <>
      {/* Floating Action Button (FAB) */}
      {!isOpen && (
        <button
          onClick={onToggle}
          style={{
            position: "fixed",
            bottom: "24px",
            right: "24px",
            width: "50px",
            height: "50px",
            borderRadius: "12px",
            background: "var(--surface-elevated)",
            color: "var(--text-main)",
            border: "1px solid var(--surface-border)",
            boxShadow: "var(--shadow-md)",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
            transition: "all 0.18s ease",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "var(--surface-hover)";
            e.currentTarget.style.borderColor = "var(--surface-border-focus)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "var(--surface-elevated)";
            e.currentTarget.style.borderColor = "var(--surface-border)";
          }}
          title="Open RBAC Assistant"
        >
          <MessageSquare size={20} />
          {/* Active status indicator */}
          <span
            style={{
              position: "absolute",
              top: "4px",
              right: "4px",
              width: "8px",
              height: "8px",
              borderRadius: "50%",
              background: "var(--color-success)",
              border: "1.5px solid var(--surface-dark)",
            }}
          />
        </button>
      )}

      {/* Floating Chat Drawer Window */}
      {isOpen && (
        <div
          style={{
            position: "fixed",
            bottom: "24px",
            right: "24px",
            width: "410px",
            height: "580px",
            maxHeight: "calc(100vh - 48px)",
            maxWidth: "calc(100vw - 48px)",
            borderRadius: "14px",
            display: "flex",
            flexDirection: "column",
            boxShadow: "var(--shadow-lg)",
            border: "1px solid var(--surface-border)",
            zIndex: 10000,
            overflow: "hidden",
            background: "var(--surface-card)",
          }}
        >
          {/* Header */}
          <div
            style={{
              padding: "14px 18px",
              background: "var(--surface-dark)",
              borderBottom: "1px solid var(--surface-border)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <div
                style={{
                  width: "30px",
                  height: "30px",
                  borderRadius: "7px",
                  background: "var(--surface-elevated)",
                  border: "1px solid var(--surface-border)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "var(--color-primary)",
                }}
              >
                <Bot size={16} />
              </div>
              <div>
                <div style={{ fontSize: "0.88rem", fontWeight: 600, color: "var(--text-main)" }}>
                  OmniCampus AI
                </div>
                <div style={{ fontSize: "0.7rem", color: "var(--text-dim)", display: "flex", alignItems: "center", gap: "4px" }}>
                  <Sparkles size={10} color="var(--color-primary)" />
                  <span>Zero-Trust Grounded Assistant</span>
                </div>
              </div>
            </div>

            <button
              onClick={onToggle}
              style={{
                background: "transparent",
                border: "none",
                color: "var(--text-dim)",
                cursor: "pointer",
                padding: "4px",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = "var(--text-main)")}
              onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-dim)")}
            >
              <X size={18} />
            </button>
          </div>

          {/* Messages Work Area */}
          <div
            style={{
              flex: 1,
              overflowY: "auto",
              padding: "16px",
              display: "flex",
              flexDirection: "column",
              gap: "12px",
              background: "var(--surface-card)",
            }}
          >
            {messages.map((msg) => {
              const isUser = msg.sender === "user";
              const isDenied = msg.accessDenied;

              return (
                <div
                  key={msg.id}
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: isUser ? "flex-end" : "flex-start",
                    gap: "4px",
                  }}
                >
                  <div
                    style={{
                      maxWidth: "88%",
                      padding: "11px 15px",
                      borderRadius: isUser ? "12px 12px 2px 12px" : "12px 12px 12px 2px",
                      background: isUser
                        ? "var(--text-main)"
                        : isDenied
                        ? "#FEF2F2"
                        : "var(--surface-elevated)",
                      color: isUser ? "#FFFFFF" : "var(--text-main)",
                      fontSize: "0.84rem",
                      lineHeight: 1.5,
                      border: isDenied
                        ? "1px solid #FECACA"
                        : isUser
                        ? "1px solid var(--text-main)"
                        : "1px solid var(--surface-border)",
                      boxShadow: "var(--shadow-sm)",
                    }}
                  >
                    {/* Access Denied Header Banner */}
                    {isDenied && (
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "6px",
                          color: "var(--color-danger)",
                          fontWeight: 600,
                          fontSize: "0.78rem",
                          marginBottom: "8px",
                          borderBottom: "1px solid rgba(248, 113, 113, 0.2)",
                          paddingBottom: "6px",
                        }}
                      >
                        <Lock size={13} />
                        <span>RBAC SECURITY RESTRICTION</span>
                      </div>
                    )}

                    {/* Formatted Text */}
                    <div style={{ whiteSpace: "pre-wrap" }}>{msg.content}</div>

                    {/* Citation Badges */}
                    {msg.sources && msg.sources.length > 0 && (
                      <div
                        style={{
                          marginTop: "10px",
                          paddingTop: "8px",
                          borderTop: "1px solid var(--surface-border-subtle)",
                          display: "flex",
                          flexDirection: "column",
                          gap: "5px",
                        }}
                      >
                        <div style={{ fontSize: "0.68rem", color: "var(--text-dim)", fontWeight: 600 }}>
                          VERIFIED SOURCES:
                        </div>
                        {msg.sources.map((src, i) => (
                          <div
                            key={i}
                            style={{
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "5px",
                              background: "#ECFDF5",
                              color: "var(--color-success)",
                              border: "1px solid #A7F3D0",
                              padding: "3px 7px",
                              borderRadius: "5px",
                              fontSize: "0.7rem",
                              fontWeight: 500,
                            }}
                          >
                            {src.type === "policy_doc" ? (
                              <BookOpen size={11} />
                            ) : src.type === "sql_record" ? (
                              <Database size={11} />
                            ) : (
                              <Navigation size={11} />
                            )}
                            <span>{src.title}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <span style={{ fontSize: "0.66rem", color: "var(--text-dim)", padding: "0 4px" }}>
                    {msg.timestamp}
                  </span>
                </div>
              );
            })}

            {isLoading && (
              <div
                style={{
                  alignSelf: "flex-start",
                  background: "var(--surface-dark)",
                  padding: "9px 14px",
                  borderRadius: "10px",
                  border: "1px solid var(--surface-border)",
                  fontSize: "0.8rem",
                  color: "var(--text-muted)",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                }}
              >
                <Sparkles size={13} color="var(--color-primary)" />
                <span>Evaluating zero-trust policies...</span>
              </div>
            )}
            <div ref={chatBottomRef} />
          </div>

          {/* Quick Reply Sample Chips */}
          <div
            style={{
              padding: "7px 12px",
              background: "var(--surface-dark)",
              borderTop: "1px solid var(--surface-border)",
              display: "flex",
              gap: "6px",
              overflowX: "auto",
              whiteSpace: "nowrap",
            }}
          >
            {sampleChips.map((chip, idx) => (
              <button
                key={idx}
                onClick={() => handleSend(chip.query)}
                disabled={isLoading}
                style={{
                  background: "var(--surface-elevated)",
                  color: "var(--text-muted)",
                  border: "1px solid var(--surface-border)",
                  borderRadius: "6px",
                  padding: "4px 9px",
                  fontSize: "0.72rem",
                  fontWeight: 500,
                  cursor: "pointer",
                  flexShrink: 0,
                  transition: "all 0.15s ease",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = "var(--text-main)";
                  e.currentTarget.style.borderColor = "var(--surface-border-focus)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = "var(--text-muted)";
                  e.currentTarget.style.borderColor = "var(--surface-border)";
                }}
              >
                {chip.label}
              </button>
            ))}
          </div>

          {/* Input Box */}
          <div
            style={{
              padding: "10px 12px",
              background: "var(--surface-dark)",
              borderTop: "1px solid var(--surface-border)",
              display: "flex",
              gap: "8px",
            }}
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSend();
              }}
              placeholder={`Ask as ${userRole}...`}
              style={{
                flex: 1,
                background: "var(--surface-elevated)",
                border: "1px solid var(--surface-border)",
                borderRadius: "7px",
                padding: "9px 12px",
                color: "var(--text-main)",
                fontSize: "0.83rem",
                outline: "none",
                transition: "border-color 0.15s ease",
              }}
              onFocus={(e) => (e.target.style.borderColor = "var(--surface-border-focus)")}
              onBlur={(e) => (e.target.style.borderColor = "var(--surface-border)")}
            />
            <button
              onClick={() => handleSend()}
              disabled={isLoading || !input.trim()}
              style={{
                background: input.trim() ? "var(--text-main)" : "var(--surface-elevated)",
                color: input.trim() ? "#FFFFFF" : "var(--text-dim)",
                border: "none",
                borderRadius: "7px",
                padding: "0 13px",
                cursor: input.trim() ? "pointer" : "default",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                transition: "all 0.18s ease",
              }}
            >
              <Send size={15} />
            </button>
          </div>
        </div>
      )}
    </>
  );
};
