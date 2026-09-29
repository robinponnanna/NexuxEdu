"use client";

import React, { useEffect, useState, useRef, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import {
  Radio,
  Navigation,
  CheckCircle2,
  AlertTriangle,
  Wifi,
  WifiOff,
  Clock,
  Shield,
  Send,
  Bus,
  MapPin,
  RefreshCw,
  Compass,
} from "lucide-react";

interface BusSessionMetadata {
  valid: boolean;
  token: string;
  busId: number;
  busNumber: string;
  routeName: string;
  driverName: string;
  driverPhone: string;
  expiresAt: string;
  active: boolean;
  latestLatitude?: number;
  latestLongitude?: number;
}

function DriverTrackContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";

  const [metadata, setMetadata] = useState<BusSessionMetadata | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [wsConnected, setWsConnected] = useState<boolean>(false);
  const [gpsActive, setGpsActive] = useState<boolean>(false);
  const [gpsError, setGpsError] = useState<string | null>(null);

  const [currentPosition, setCurrentPosition] = useState<{
    latitude: number;
    longitude: number;
    accuracy: number;
    timestamp: number;
    speed?: number | null;
  } | null>(null);

  const [packetsSent, setPacketsSent] = useState<number>(0);
  const [lastSentTime, setLastSentTime] = useState<number | null>(null);
  const [isPaused, setIsPaused] = useState<boolean>(false);
  const [isSimulating, setIsSimulating] = useState<boolean>(false);

  const wsRef = useRef<WebSocket | null>(null);
  const watchIdRef = useRef<number | null>(null);
  const lastSendTimestampRef = useRef<number>(0);
  const simulationIntervalRef = useRef<any>(null);

  const MIN_INTERVAL_MS = 2000; // Throttle requirement: 2 seconds

  // 1. Validate session token with backend API
  useEffect(() => {
    if (!token) {
      setError("Missing tracking token. Please access this page using an authorized administrative link.");
      setLoading(false);
      return;
    }

    let isMounted = true;
    async function validate() {
      try {
        setLoading(true);
        // Direct call or proxied call
        const apiBase =
          window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
            ? "http://127.0.0.1:8000/api/tracking"
            : "/api/tracking";

        const res = await fetch(`${apiBase}/sessions/validate?token=${encodeURIComponent(token)}`);
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || `Session invalid or expired (HTTP ${res.status})`);
        }
        const data = await res.json();
        if (isMounted) {
          setMetadata(data);
          setError(null);
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || "Failed to validate tracking session.");
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    validate();
    return () => {
      isMounted = false;
    };
  }, [token]);

  // 2. Establish WebSocket connection to /ws?token=...
  useEffect(() => {
    if (!metadata || !token || error) return;

    let isCancelled = false;
    let reconnectTimeout: any = null;

    function connectWs() {
      if (isCancelled) return;

      try {
        const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
        let hostPart = window.location.host;
        if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
          hostPart = `${window.location.hostname}:8000`;
        }
        const wsUrl = `${proto}//${hostPart}/ws?token=${encodeURIComponent(token)}`;

        const socket = new WebSocket(wsUrl);
        wsRef.current = socket;

        socket.onopen = () => {
          if (isCancelled) return;
          setWsConnected(true);
        };

        socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === "location_ack") {
              // Location acknowledged by server
            }
          } catch (e) {
            // ignore
          }
        };

        socket.onclose = () => {
          if (!isCancelled) {
            setWsConnected(false);
            reconnectTimeout = setTimeout(connectWs, 3000);
          }
        };

        socket.onerror = () => {
          if (!isCancelled) {
            setWsConnected(false);
          }
        };
      } catch (err) {
        console.error("WS error:", err);
      }
    }

    connectWs();

    return () => {
      isCancelled = true;
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [metadata, token, error]);

  // 3. Helper to send throttled location packet
  const sendLocationPacket = (lat: number, lng: number, accuracy: number, timestamp: number, speed?: number | null) => {
    const now = Date.now();
    if (now - lastSendTimestampRef.current < MIN_INTERVAL_MS) {
      return; // Throttled to 2 seconds
    }
    lastSendTimestampRef.current = now;

    const payload = {
      type: "location",
      latitude: parseFloat(lat.toFixed(6)),
      longitude: parseFloat(lng.toFixed(6)),
      accuracy: parseFloat(accuracy.toFixed(1)),
      timestamp: timestamp || now,
    };

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN && !isPaused) {
      try {
        wsRef.current.send(JSON.stringify(payload));
        setPacketsSent((prev) => prev + 1);
        setLastSentTime(now);
      } catch (err) {
        console.error("Failed to send location packet over WS:", err);
      }
    }

    setCurrentPosition({
      latitude: lat,
      longitude: lng,
      accuracy,
      timestamp: timestamp || now,
      speed,
    });
  };

  // 4. Start Hardware Geolocation Watcher
  useEffect(() => {
    if (!metadata || !wsConnected || isPaused || isSimulating) {
      if (watchIdRef.current !== null && navigator.geolocation) {
        navigator.geolocation.clearWatch(watchIdRef.current);
        watchIdRef.current = null;
      }
      setGpsActive(false);
      return;
    }

    if (!navigator.geolocation) {
      setGpsError("Geolocation is not supported by your mobile browser.");
      return;
    }

    setGpsError(null);

    const geoOptions: PositionOptions = {
      enableHighAccuracy: true,
      maximumAge: 0,
      timeout: 10000,
    };

    const handleSuccess = (pos: GeolocationPosition) => {
      setGpsActive(true);
      setGpsError(null);
      sendLocationPacket(
        pos.coords.latitude,
        pos.coords.longitude,
        pos.coords.accuracy,
        pos.timestamp,
        pos.coords.speed
      );
    };

    const handleError = (err: GeolocationPositionError) => {
      setGpsActive(false);
      if (err.code === 1) {
        setGpsError("Location access denied. Please grant GPS permission in your browser settings.");
      } else if (err.code === 2) {
        setGpsError("GPS position unavailable. Ensure device location is turned on.");
      } else if (err.code === 3) {
        setGpsError("GPS signal request timed out. Retrying...");
      } else {
        setGpsError(err.message || "Failed to acquire GPS fix.");
      }
    };

    const watchId = navigator.geolocation.watchPosition(handleSuccess, handleError, geoOptions);
    watchIdRef.current = watchId;

    return () => {
      if (watchIdRef.current !== null && navigator.geolocation) {
        navigator.geolocation.clearWatch(watchIdRef.current);
        watchIdRef.current = null;
      }
    };
  }, [metadata, wsConnected, isPaused, isSimulating]);

  // 5. Desktop Simulation Mode (for testing without moving)
  useEffect(() => {
    if (!isSimulating || !wsConnected || isPaused) {
      if (simulationIntervalRef.current) {
        clearInterval(simulationIntervalRef.current);
        simulationIntervalRef.current = null;
      }
      return;
    }

    let lat = currentPosition?.latitude || metadata?.latestLatitude || 28.6139;
    let lng = currentPosition?.longitude || metadata?.latestLongitude || 77.209;
    let step = 0;

    simulationIntervalRef.current = setInterval(() => {
      step += 1;
      // Slight movement
      lat += (Math.random() - 0.48) * 0.0003;
      lng += (Math.random() - 0.48) * 0.0003;
      sendLocationPacket(lat, lng, 8.5 + Math.random() * 4, Date.now(), 32.5);
    }, MIN_INTERVAL_MS);

    return () => {
      if (simulationIntervalRef.current) {
        clearInterval(simulationIntervalRef.current);
        simulationIntervalRef.current = null;
      }
    };
  }, [isSimulating, wsConnected, isPaused, metadata]);

  // Loading state
  if (loading) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background: "#090D16",
          color: "#F8FAFC",
          fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
          padding: "20px",
        }}
      >
        <div
          style={{
            width: "56px",
            height: "56px",
            borderRadius: "50%",
            border: "3px solid rgba(99, 102, 241, 0.2)",
            borderTopColor: "#6366F1",
            animation: "spin 1s linear infinite",
            marginBottom: "20px",
          }}
        />
        <h2 style={{ fontSize: "1.2rem", fontWeight: 600 }}>Verifying Tracking Session...</h2>
        <p style={{ color: "#94A3B8", fontSize: "0.85rem", marginTop: "6px" }}>Connecting to NexusEdu Fleet Security</p>
        <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  // Error state
  if (error || !metadata) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#090D16",
          color: "#F8FAFC",
          fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
          padding: "24px",
        }}
      >
        <div
          style={{
            maxWidth: "460px",
            width: "100%",
            background: "#131A29",
            border: "1px solid #EF4444",
            borderRadius: "16px",
            padding: "28px",
            textAlign: "center",
            boxShadow: "0 10px 40px rgba(239, 68, 68, 0.15)",
          }}
        >
          <div
            style={{
              width: "56px",
              height: "56px",
              background: "rgba(239, 68, 68, 0.15)",
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 16px",
              color: "#EF4444",
            }}
          >
            <AlertTriangle size={28} />
          </div>
          <h2 style={{ fontSize: "1.3rem", fontWeight: 700, color: "#F8FAFC", marginBottom: "10px" }}>
            Session Authorization Denied
          </h2>
          <p style={{ color: "#94A3B8", fontSize: "0.9rem", lineHeight: 1.5, marginBottom: "20px" }}>{error}</p>
          <div
            style={{
              background: "#090D16",
              borderRadius: "8px",
              padding: "12px",
              fontSize: "0.78rem",
              color: "#64748B",
              fontFamily: "monospace",
            }}
          >
            Security Note: Live telematics sessions require active cryptographic signatures generated by campus dispatch.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "linear-gradient(180deg, #090D16 0%, #0D1322 100%)",
        color: "#F8FAFC",
        fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        padding: "16px",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
      }}
    >
      <div style={{ maxWidth: "480px", width: "100%", display: "flex", flexDirection: "column", gap: "16px" }}>
        {/* Top Header Card */}
        <div
          style={{
            background: "rgba(19, 26, 41, 0.9)",
            border: "1px solid rgba(255, 255, 255, 0.08)",
            borderRadius: "16px",
            padding: "20px",
            backdropFilter: "blur(12px)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <div
                style={{
                  background: "linear-gradient(135deg, #6366F1, #8B5CF6)",
                  padding: "8px",
                  borderRadius: "10px",
                  color: "#FFFFFF",
                }}
              >
                <Bus size={22} />
              </div>
              <div>
                <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "#FFFFFF" }}>{metadata.busNumber}</div>
                <div style={{ fontSize: "0.75rem", color: "#94A3B8" }}>{metadata.routeName}</div>
              </div>
            </div>

            {/* Live Connection Badge */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                padding: "6px 12px",
                borderRadius: "20px",
                background: wsConnected ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)",
                border: `1px solid ${wsConnected ? "rgba(16, 185, 129, 0.4)" : "rgba(239, 68, 68, 0.4)"}`,
                fontSize: "0.75rem",
                fontWeight: 600,
                color: wsConnected ? "#34D399" : "#F87171",
              }}
            >
              {wsConnected ? <Wifi size={14} /> : <WifiOff size={14} />}
              {wsConnected ? "SERVER CONNECTED" : "OFFLINE"}
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "8px",
              paddingTop: "12px",
              borderTop: "1px solid rgba(255, 255, 255, 0.06)",
              fontSize: "0.78rem",
              color: "#94A3B8",
            }}
          >
            <div>
              Driver: <strong style={{ color: "#F8FAFC" }}>{metadata.driverName}</strong>
            </div>
            <div style={{ textAlign: "right" }}>
              Interval: <strong style={{ color: "#F8FAFC" }}>2.0s Secure Stream</strong>
            </div>
          </div>
        </div>

        {/* Live Streaming Status Banner */}
        <div
          style={{
            background: isPaused
              ? "rgba(245, 158, 11, 0.12)"
              : gpsActive || isSimulating
              ? "rgba(16, 185, 129, 0.12)"
              : "rgba(59, 130, 246, 0.12)",
            border: `1px solid ${
              isPaused
                ? "rgba(245, 158, 11, 0.3)"
                : gpsActive || isSimulating
                ? "rgba(16, 185, 129, 0.3)"
                : "rgba(59, 130, 246, 0.3)"
            }`,
            borderRadius: "14px",
            padding: "16px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div
              style={{
                width: "12px",
                height: "12px",
                borderRadius: "50%",
                background: isPaused ? "#F59E0B" : gpsActive || isSimulating ? "#10B981" : "#3B82F6",
                boxShadow: `0 0 12px ${isPaused ? "#F59E0B" : gpsActive || isSimulating ? "#10B981" : "#3B82F6"}`,
                animation: isPaused ? "none" : "pulse 1.8s infinite",
              }}
            />
            <div>
              <div style={{ fontSize: "0.92rem", fontWeight: 700, color: "#FFFFFF" }}>
                {isPaused
                  ? "Streaming Suspended"
                  : gpsActive
                  ? "GPS Streaming Active"
                  : isSimulating
                  ? "Simulation Active (Desktop)"
                  : "Awaiting GPS Fix..."}
              </div>
              <div style={{ fontSize: "0.75rem", color: "#94A3B8" }}>
                {isPaused
                  ? "Tap Resume to stream coordinates"
                  : `Transmitted ${packetsSent} location updates`}
              </div>
            </div>
          </div>

          <button
            onClick={() => setIsPaused(!isPaused)}
            style={{
              padding: "8px 16px",
              borderRadius: "8px",
              background: isPaused ? "#10B981" : "rgba(255, 255, 255, 0.1)",
              color: "#FFFFFF",
              border: "none",
              fontSize: "0.8rem",
              fontWeight: 600,
              cursor: "pointer",
              outline: "none",
            }}
          >
            {isPaused ? "Resume" : "Pause"}
          </button>
        </div>

        {/* GPS Error Alert if any */}
        {gpsError && !isSimulating && (
          <div
            style={{
              background: "rgba(239, 68, 68, 0.12)",
              border: "1px solid rgba(239, 68, 68, 0.3)",
              borderRadius: "12px",
              padding: "12px 16px",
              display: "flex",
              alignItems: "flex-start",
              gap: "10px",
              fontSize: "0.82rem",
              color: "#FCA5A5",
            }}
          >
            <AlertTriangle size={18} style={{ flexShrink: 0, marginTop: "2px" }} />
            <div>
              <div style={{ fontWeight: 600 }}>Location Permission Required</div>
              <div>{gpsError}</div>
              <div style={{ marginTop: "6px" }}>
                <button
                  onClick={() => setIsSimulating(true)}
                  style={{
                    background: "rgba(239, 68, 68, 0.2)",
                    border: "1px solid rgba(239, 68, 68, 0.4)",
                    color: "#F8FAFC",
                    padding: "4px 8px",
                    borderRadius: "6px",
                    fontSize: "0.75rem",
                    cursor: "pointer",
                  }}
                >
                  Enable Simulator Mode (for testing)
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Telemetry Coordinates Card */}
        <div
          style={{
            background: "rgba(19, 26, 41, 0.9)",
            border: "1px solid rgba(255, 255, 255, 0.08)",
            borderRadius: "16px",
            padding: "20px",
          }}
        >
          <div style={{ fontSize: "0.8rem", color: "#94A3B8", fontWeight: 600, textTransform: "uppercase", marginBottom: "14px", letterSpacing: "0.5px" }}>
            Real-Time Vehicle Position
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px", marginBottom: "16px" }}>
            <div
              style={{
                background: "rgba(9, 13, 22, 0.7)",
                padding: "14px",
                borderRadius: "12px",
                border: "1px solid rgba(255, 255, 255, 0.05)",
              }}
            >
              <div style={{ fontSize: "0.72rem", color: "#64748B", marginBottom: "4px" }}>LATITUDE</div>
              <div style={{ fontSize: "1.2rem", fontWeight: 700, fontFamily: "monospace", color: "#60A5FA" }}>
                {currentPosition ? currentPosition.latitude.toFixed(6) : "—"}
              </div>
            </div>

            <div
              style={{
                background: "rgba(9, 13, 22, 0.7)",
                padding: "14px",
                borderRadius: "12px",
                border: "1px solid rgba(255, 255, 255, 0.05)",
              }}
            >
              <div style={{ fontSize: "0.72rem", color: "#64748B", marginBottom: "4px" }}>LONGITUDE</div>
              <div style={{ fontSize: "1.2rem", fontWeight: 700, fontFamily: "monospace", color: "#60A5FA" }}>
                {currentPosition ? currentPosition.longitude.toFixed(6) : "—"}
              </div>
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: "8px",
              paddingTop: "14px",
              borderTop: "1px solid rgba(255, 255, 255, 0.06)",
              textAlign: "center",
            }}
          >
            <div>
              <div style={{ fontSize: "0.7rem", color: "#64748B" }}>ACCURACY</div>
              <div
                style={{
                  fontSize: "0.95rem",
                  fontWeight: 700,
                  color:
                    currentPosition && currentPosition.accuracy < 15
                      ? "#34D399"
                      : currentPosition && currentPosition.accuracy < 50
                      ? "#FBBF24"
                      : "#94A3B8",
                }}
              >
                {currentPosition ? `±${Math.round(currentPosition.accuracy)}m` : "—"}
              </div>
            </div>

            <div>
              <div style={{ fontSize: "0.7rem", color: "#64748B" }}>PACKETS SENT</div>
              <div style={{ fontSize: "0.95rem", fontWeight: 700, color: "#F8FAFC" }}>{packetsSent}</div>
            </div>

            <div>
              <div style={{ fontSize: "0.7rem", color: "#64748B" }}>LAST SYNC</div>
              <div style={{ fontSize: "0.95rem", fontWeight: 700, color: "#F8FAFC" }}>
                {lastSentTime ? `${Math.round((Date.now() - lastSentTime) / 1000)}s ago` : "—"}
              </div>
            </div>
          </div>
        </div>

        {/* Controls and Desktop Simulator Toggle */}
        <div
          style={{
            background: "rgba(19, 26, 41, 0.6)",
            border: "1px solid rgba(255, 255, 255, 0.06)",
            borderRadius: "14px",
            padding: "16px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div>
            <div style={{ fontSize: "0.85rem", fontWeight: 600, color: "#F8FAFC" }}>Desktop Simulation Mode</div>
            <div style={{ fontSize: "0.72rem", color: "#94A3B8" }}>
              Simulates realistic GPS movement without physical device transit.
            </div>
          </div>
          <button
            onClick={() => setIsSimulating(!isSimulating)}
            style={{
              padding: "8px 14px",
              borderRadius: "8px",
              background: isSimulating ? "#8B5CF6" : "rgba(255, 255, 255, 0.08)",
              border: `1px solid ${isSimulating ? "#A78BFA" : "rgba(255, 255, 255, 0.15)"}`,
              color: "#FFFFFF",
              fontSize: "0.78rem",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {isSimulating ? "Active (Testing)" : "Start Simulator"}
          </button>
        </div>

        {/* Security watermark footer */}
        <div
          style={{
            textAlign: "center",
            fontSize: "0.72rem",
            color: "#64748B",
            marginTop: "12px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "6px",
          }}
        >
          <Shield size={13} />
          NexusEdu Fleet Intelligence • Hardware Bound Geolocation Guard
        </div>
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.5; transform: scale(1.15); }
        }
      `}</style>
    </div>
  );
}

export default function DriverTrackPage() {
  return (
    <Suspense
      fallback={
        <div
          style={{
            minHeight: "100vh",
            background: "#090D16",
            color: "#FFFFFF",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          Loading driver telemetry page...
        </div>
      }
    >
      <DriverTrackContent />
    </Suspense>
  );
}
