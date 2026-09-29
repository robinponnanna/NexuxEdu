"use client";

import React, { useState, useEffect, useRef } from "react";
import { Bell, Check, CheckCheck, Clock, ShieldAlert } from "lucide-react";
import {
  NotificationItem,
  getNotifications,
  markNotificationRead,
  markAllNotificationsRead,
} from "@/lib/api";

interface NotificationBellProps {
  token: string | null;
}

export const NotificationBell: React.FC<NotificationBellProps> = ({ token }) => {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const fetchNotifs = async () => {
    if (!token) return;
    try {
      const items = await getNotifications(token);
      setNotifications(items);
    } catch {
      // Ignore polling errors gracefully
    }
  };

  // Poll every 10 seconds as specified in requirements
  useEffect(() => {
    if (!token) return;
    fetchNotifs();
    const interval = setInterval(fetchNotifs, 10000);
    return () => clearInterval(interval);
  }, [token]);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleMarkRead = async (id: number) => {
    if (!token) return;
    try {
      await markNotificationRead(token, id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
    } catch (e) {
      console.error(e);
    }
  };

  const handleMarkAllRead = async () => {
    if (!token) return;
    setLoading(true);
    try {
      await markAllNotificationsRead(token);
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  return (
    <div style={{ position: "relative" }} ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          position: "relative",
          background: isOpen ? "var(--surface-elevated)" : "transparent",
          border: "1px solid",
          borderColor: isOpen ? "var(--surface-border-focus)" : "transparent",
          borderRadius: "8px",
          padding: "8px",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "var(--text-main)",
          transition: "all 0.15s ease",
        }}
        aria-label="Notifications"
      >
        <Bell size={19} />
        {unreadCount > 0 && (
          <span
            style={{
              position: "absolute",
              top: "4px",
              right: "4px",
              background: "var(--color-danger)",
              color: "#FFFFFF",
              fontSize: "0.65rem",
              fontWeight: 700,
              borderRadius: "9999px",
              minWidth: "16px",
              height: "16px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "0 4px",
              boxShadow: "0 0 0 2px var(--surface-card)",
            }}
          >
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div
          style={{
            position: "absolute",
            top: "calc(100% + 8px)",
            right: "0",
            width: "360px",
            maxHeight: "480px",
            background: "var(--surface-card)",
            border: "1px solid var(--surface-border)",
            borderRadius: "12px",
            boxShadow: "var(--shadow-lg)",
            display: "flex",
            flexDirection: "column",
            zIndex: 1000,
            overflow: "hidden",
          }}
        >
          {/* Header */}
          <div
            style={{
              padding: "12px 16px",
              borderBottom: "1px solid var(--surface-border)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              background: "var(--surface-elevated)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ fontWeight: 700, fontSize: "0.88rem", color: "var(--text-main)" }}>
                Notifications
              </span>
              {unreadCount > 0 && (
                <span
                  style={{
                    background: "var(--color-primary-subtle)",
                    color: "var(--color-primary)",
                    padding: "2px 6px",
                    borderRadius: "9999px",
                    fontSize: "0.72rem",
                    fontWeight: 600,
                  }}
                >
                  {unreadCount} new
                </span>
              )}
            </div>

            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                disabled={loading}
                style={{
                  background: "none",
                  border: "none",
                  color: "var(--color-primary)",
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "4px",
                }}
              >
                <CheckCheck size={14} />
                Mark all read
              </button>
            )}
          </div>

          {/* List */}
          <div
            style={{
              overflowY: "auto",
              maxHeight: "400px",
              display: "flex",
              flexDirection: "column",
            }}
          >
            {notifications.length === 0 ? (
              <div
                style={{
                  padding: "40px 20px",
                  textAlign: "center",
                  color: "var(--text-muted)",
                  fontSize: "0.85rem",
                }}
              >
                <Bell size={28} style={{ opacity: 0.3, marginBottom: "8px" }} />
                <p>No notifications yet</p>
              </div>
            ) : (
              notifications.map((notif) => {
                const formattedDate = new Date(notif.created_at).toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                });

                return (
                  <div
                    key={notif.id}
                    onClick={() => !notif.is_read && handleMarkRead(notif.id)}
                    style={{
                      padding: "12px 16px",
                      borderBottom: "1px solid var(--surface-border-subtle)",
                      background: notif.is_read ? "var(--surface-card)" : "rgba(239, 246, 255, 0.4)",
                      cursor: notif.is_read ? "default" : "pointer",
                      display: "flex",
                      alignItems: "flex-start",
                      gap: "10px",
                      transition: "background 0.15s ease",
                    }}
                  >
                    <div
                      style={{
                        width: "8px",
                        height: "8px",
                        borderRadius: "50%",
                        background: notif.is_read ? "transparent" : "var(--color-student)",
                        marginTop: "5px",
                        flexShrink: 0,
                      }}
                    />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div
                        style={{
                          fontWeight: notif.is_read ? 600 : 700,
                          fontSize: "0.82rem",
                          color: "var(--text-main)",
                          marginBottom: "3px",
                        }}
                      >
                        {notif.title}
                      </div>
                      <div
                        style={{
                          fontSize: "0.78rem",
                          color: "var(--text-muted)",
                          lineHeight: 1.4,
                          marginBottom: "4px",
                        }}
                      >
                        {notif.body}
                      </div>
                      <div
                        style={{
                          fontSize: "0.7rem",
                          color: "var(--text-dim)",
                          display: "flex",
                          alignItems: "center",
                          gap: "3px",
                        }}
                      >
                        <Clock size={10} />
                        {formattedDate}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
};
