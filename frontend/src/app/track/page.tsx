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
  const [isStarted, setIsStarted] = useState<boolean>(false);

  const wsRef = useRef<WebSocket | null>(null);
  const watchIdRef = useRef<number | null>(null);
  const lastSendTimestampRef = useRef<number>(0);
  const simulationIntervalRef = useRef<any>(null);
  const wakeLockRef = useRef<any>(null);

  const requestWakeLock = async () => {
    if (typeof window !== "undefined" && "wakeLock" in navigator) {
      try {
        wakeLockRef.current = await (navigator as any).wakeLock.request("screen");
      } catch (err) {}
    }
  };

  const releaseWakeLock = () => {
    if (wakeLockRef.current) {
      wakeLockRef.current.release().catch(() => {});
      wakeLockRef.current = null;
    }
  };

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
    if (!metadata || !wsConnected || isPaused || isSimulating || !isStarted) {
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
        setGpsError("Location access denied. Please grant GPS permission in your browser/device settings.");
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

    // 2-second continuous periodic fallback
    const intervalId = setInterval(() => {
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
          handleSuccess,
          () => {
            if (currentPosition) {
              sendLocationPacket(
                currentPosition.latitude,
                currentPosition.longitude,
                currentPosition.accuracy,
                Date.now(),
                currentPosition.speed
              );
            }
          },
          { enableHighAccuracy: true, maximumAge: 1500, timeout: 1800 }
        );
      } else if (currentPosition) {
        sendLocationPacket(
          currentPosition.latitude,
          currentPosition.longitude,
          currentPosition.accuracy,
          Date.now(),
          currentPosition.speed
        );
      }
    }, MIN_INTERVAL_MS);

    return () => {
      clearInterval(intervalId);
      if (watchIdRef.current !== null && navigator.geolocation) {
        navigator.geolocation.clearWatch(watchIdRef.current);
        watchIdRef.current = null;
      }
    };
  }, [metadata, wsConnected, isPaused, isSimulating, isStarted, currentPosition]);

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
          background: "#FFFFFF",
          color: "#0F172A",
          fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
          padding: "20px",
        }}
      >
        <div
          style={{
            width: "56px",
            height: "56px",
            borderRadius: "50%",
            border: "3px solid #E2E8F0",
            borderTopColor: "#0284C7",
            animation: "spin 1s linear infinite",
            marginBottom: "20px",
          }}
        />
        <h2 style={{ fontSize: "1.2rem", fontWeight: 700, color: "#0F172A" }}>Verifying Tracking Session...</h2>
        <p style={{ color: "#64748B", fontSize: "0.85rem", marginTop: "6px" }}>Connecting to NexusEdu Fleet Security</p>
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
          background: "#F8FAFC",
          color: "#0F172A",
          fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
          padding: "24px",
        }}
      >
        <div
          style={{
            maxWidth: "460px",
            width: "100%",
            background: "#FFFFFF",
            border: "1px solid #FECACA",
            borderRadius: "16px",
            padding: "28px",
            textAlign: "center",
            boxShadow: "0 10px 40px rgba(239, 68, 68, 0.08)",
          }}
        >
          <div
            style={{
              width: "56px",
              height: "56px",
              background: "#FEF2F2",
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 16px",
              color: "#DC2626",
            }}
          >
            <AlertTriangle size={28} />
          </div>
          <h2 style={{ fontSize: "1.3rem", fontWeight: 700, color: "#0F172A", marginBottom: "10px" }}>
            Session Authorization Denied
          </h2>
          <p style={{ color: "#64748B", fontSize: "0.9rem", lineHeight: 1.5, marginBottom: "20px" }}>{error}</p>
          <div
            style={{
              background: "#F8FAFC",
              border: "1px solid #E2E8F0",
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
        background: "#FFFFFF",
        color: "#0F172A",
        fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        padding: "24px 16px",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div style={{ maxWidth: "420px", width: "100%", display: "flex", flexDirection: "column", gap: "16px" }}>
        {/* Main Card with the 5 required details */}
        <div
          style={{
            background: "#FFFFFF",
            border: "1px solid #E2E8F0",
            borderRadius: "16px",
            padding: "24px",
            boxShadow: "0 10px 25px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -4px rgba(0, 0, 0, 0.02)",
            display: "flex",
            flexDirection: "column",
            gap: "18px",
          }}
        >
          {/* 1. BUS ID */}
          <div style={{ textAlign: "center", borderBottom: "1px solid #F1F5F9", paddingBottom: "16px" }}>
            <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "#64748B", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Bus ID
            </div>
            <div style={{ fontSize: "1.6rem", fontWeight: 800, color: "#0F172A", marginTop: "2px" }}>
              {metadata.busNumber}
            </div>
          </div>

          {/* 2. Speed in which the bus is moving */}
          <div
            style={{
              background: "#F8FAFC",
              border: "1px solid #E2E8F0",
              borderRadius: "12px",
              padding: "18px",
              textAlign: "center",
            }}
          >
            <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "#64748B", textTransform: "uppercase", letterSpacing: "0.04em" }}>
              Speed
            </div>
            <div className="font-mono" style={{ fontSize: "2.4rem", fontWeight: 800, color: "#0F172A", lineHeight: 1.1, marginTop: "4px" }}>
              {currentPosition?.speed !== null && currentPosition?.speed !== undefined
                ? (currentPosition.speed * 3.6).toFixed(1)
                : "0.0"}{" "}
              <span style={{ fontSize: "1rem", fontWeight: 600, color: "#64748B" }}>km/h</span>
            </div>
          </div>

          {/* 3 & 4. Latitude and Longitude */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
            <div
              style={{
                background: "#F8FAFC",
                border: "1px solid #E2E8F0",
                borderRadius: "12px",
                padding: "14px",
                textAlign: "center",
              }}
            >
              <div style={{ fontSize: "0.72rem", fontWeight: 700, color: "#64748B", textTransform: "uppercase" }}>
                Latitude
              </div>
              <div
                className="font-mono"
                style={{ fontSize: "1.1rem", fontWeight: 700, color: "#0284C7", marginTop: "4px" }}
              >
                {currentPosition ? currentPosition.latitude.toFixed(6) : "—"}
              </div>
            </div>

            <div
              style={{
                background: "#F8FAFC",
                border: "1px solid #E2E8F0",
                borderRadius: "12px",
                padding: "14px",
                textAlign: "center",
              }}
            >
              <div style={{ fontSize: "0.72rem", fontWeight: 700, color: "#64748B", textTransform: "uppercase" }}>
                Longitude
              </div>
              <div
                className="font-mono"
                style={{ fontSize: "1.1rem", fontWeight: 700, color: "#0284C7", marginTop: "4px" }}
              >
                {currentPosition ? currentPosition.longitude.toFixed(6) : "—"}
              </div>
            </div>
          </div>

          {/* 5. GPS Precision */}
          <div
            style={{
              background: "#F8FAFC",
              border: "1px solid #E2E8F0",
              borderRadius: "12px",
              padding: "14px",
              textAlign: "center",
            }}
          >
            <div style={{ fontSize: "0.72rem", fontWeight: 700, color: "#64748B", textTransform: "uppercase" }}>
              GPS Precision
            </div>
            <div
              style={{
                fontSize: "1.2rem",
                fontWeight: 700,
                color: currentPosition ? "#16A34A" : "#64748B",
                marginTop: "4px",
              }}
            >
              {currentPosition ? `±${Math.round(currentPosition.accuracy)}m` : "—"}
            </div>
          </div>
        </div>

        {/* Start / Stop GPS Tracking Action Button */}
        <button
          onClick={() => {
            if (isStarted) {
              releaseWakeLock();
              setIsStarted(false);
            } else {
              requestWakeLock();
              setIsStarted(true);
            }
          }}
          style={{
            width: "100%",
            padding: "16px 20px",
            borderRadius: "14px",
            border: "none",
            fontSize: "1rem",
            fontWeight: 700,
            cursor: "pointer",
            color: "#FFFFFF",
            background: isStarted
              ? "linear-gradient(135deg, #EF4444 0%, #DC2626 100%)"
              : "linear-gradient(135deg, #10B981 0%, #059669 100%)",
            boxShadow: isStarted
              ? "0 6px 20px rgba(239, 68, 68, 0.25)"
              : "0 6px 20px rgba(16, 185, 129, 0.25)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "10px",
            transition: "all 0.2s ease",
          }}
        >
          <Navigation size={18} />
          <span>{isStarted ? "STOP GPS TRACKING" : "START LIVE GPS TRACKING"}</span>
        </button>

        {/* Location Error Notice if any */}
        {gpsError && (
          <div
            style={{
              background: "#FEF2F2",
              border: "1px solid #FECACA",
              borderRadius: "12px",
              padding: "12px 16px",
              fontSize: "0.82rem",
              color: "#DC2626",
              textAlign: "center",
            }}
          >
            {gpsError}
          </div>
        )}
      </div>
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
            background: "#FFFFFF",
            color: "#0F172A",
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
