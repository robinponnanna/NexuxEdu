"use client";

import React, { useEffect, useRef, useState } from "react";
import "leaflet/dist/leaflet.css";
import { BusDetails, getTransitWebSocketUrl, getUnifiedWebSocketUrl, getBusById } from "@/lib/api";
import {
  Navigation,
  Gauge,
  Wifi,
  Radio,
  Compass,
  Crosshair,
  Activity,
  Layers,
  Trash2,
  Smartphone,
  SmartphoneNfc,
} from "lucide-react";

interface LiveTransitMapProps {
  bus: BusDetails;
  token: string;
  userRole: string;
}

export const LiveTransitMap: React.FC<LiveTransitMapProps> = ({ bus, token, userRole }) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const busMarkerRef = useRef<any>(null);
  const accuracyCircleRef = useRef<any>(null);
  const trailPolylineRef = useRef<any>(null);
  const trailPointsRef = useRef<[number, number][]>([]);

  // Driver connection & location state
  const isInitiallyConnected = Boolean(bus.driver_connected);
  const hasValidCoords = Boolean(
    isInitiallyConnected &&
    bus.current_lat !== undefined &&
    bus.current_lat !== null &&
    bus.current_lng !== undefined &&
    bus.current_lng !== null &&
    !isNaN(bus.current_lat) &&
    !isNaN(bus.current_lng)
  );

  const [driverConnected, setDriverConnected] = useState<boolean>(isInitiallyConnected);
  const [currentCoord, setCurrentCoord] = useState<{ lat: number; lng: number } | null>(
    hasValidCoords ? { lat: bus.current_lat!, lng: bus.current_lng! } : null
  );
  const [speed, setSpeed] = useState<number>(bus.speed_kmh || 0.0);
  const [status, setStatus] = useState<string>(bus.status || "Active");
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [accuracy, setAccuracy] = useState<number | null>(null);
  const [autoFollow, setAutoFollow] = useState<boolean>(true);
  const [lastUpdateAgo, setLastUpdateAgo] = useState<number>(0);
  const [totalUpdatesReceived, setTotalUpdatesReceived] = useState<number>(0);

  const autoFollowRef = useRef<boolean>(true);
  const lastUpdateTimestampRef = useRef<number>(Date.now());

  useEffect(() => {
    autoFollowRef.current = autoFollow;
  }, [autoFollow]);

  // Sync state when bus prop changes
  useEffect(() => {
    const conn = Boolean(bus.driver_connected);
    setDriverConnected(conn);
    if (!conn) {
      setCurrentCoord(null);
      setSpeed(0.0);
      if (busMarkerRef.current && mapInstanceRef.current) {
        mapInstanceRef.current.removeLayer(busMarkerRef.current);
        busMarkerRef.current = null;
      }
      if (accuracyCircleRef.current && mapInstanceRef.current) {
        mapInstanceRef.current.removeLayer(accuracyCircleRef.current);
        accuracyCircleRef.current = null;
      }
    } else if (bus.current_lat && bus.current_lng) {
      setCurrentCoord({ lat: bus.current_lat, lng: bus.current_lng });
      setSpeed(bus.speed_kmh || 0.0);
    }
  }, [bus.id, bus.driver_connected, bus.current_lat, bus.current_lng, bus.speed_kmh]);

  // Heartbeat timer to show seconds since last refresh
  useEffect(() => {
    const timer = setInterval(() => {
      const elapsed = Math.floor((Date.now() - lastUpdateTimestampRef.current) / 1000);
      setLastUpdateAgo(elapsed);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Central position updater that refreshes marker, accuracy circle, breadcrumb trail, HUD, and camera
  const updateBusPosition = (
    newLat: number,
    newLng: number,
    newSpeed?: number,
    newAcc?: number,
    isDriver?: boolean
  ) => {
    if (isNaN(newLat) || isNaN(newLng)) return;

    setDriverConnected(true);
    setCurrentCoord({ lat: newLat, lng: newLng });
    if (newSpeed !== undefined && !isNaN(newSpeed)) setSpeed(newSpeed);
    if (newAcc !== undefined && !isNaN(newAcc)) setAccuracy(newAcc);
    lastUpdateTimestampRef.current = Date.now();
    setLastUpdateAgo(0);
    setTotalUpdatesReceived((prev) => prev + 1);

    const map = mapInstanceRef.current;
    if (!map) return;

    import("leaflet").then((LModule) => {
      const L = LModule.default || LModule;

      // 1. Update or create live vehicle marker
      if (busMarkerRef.current) {
        busMarkerRef.current.setLatLng([newLat, newLng]);
        busMarkerRef.current.setPopupContent(`
          <div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 12px; color: #0F172A; line-height: 1.4;">
            <div style="font-weight: 700; color: #0F172A; font-size: 13px;">🚌 ${bus.bus_number}</div>
            <div style="color: #64748B; font-size: 11px; margin-bottom: 4px;">${bus.route_name}</div>
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; padding: 4px 6px; border-radius: 4px; font-family: monospace; font-size: 11px; color: #0284C7; font-weight: 600;">
              ${newLat.toFixed(6)}° N, ${newLng.toFixed(6)}° E
            </div>
            <div style="margin-top: 4px; font-size: 11px; color: #334155;">
              Speed: <strong>${(newSpeed || 0).toFixed(1)} km/h</strong> • Precision: ±${Math.round(newAcc || 4)}m
            </div>
          </div>
        `);
      } else {
        const busIcon = L.divIcon({
          className: "custom-bus-icon",
          html: `
            <div style="position: relative; width: 44px; height: 44px; display: flex; align-items: center; justify-content: center;">
              <div class="bus-beacon"></div>
              <div style="
                position: absolute;
                bottom: -18px;
                background: #FFFFFF;
                color: #0F172A;
                padding: 2px 7px;
                border-radius: 4px;
                font-size: 10px;
                font-family: 'JetBrains Mono', monospace;
                font-weight: 700;
                white-space: nowrap;
                border: 1.5px solid #0F172A;
                box-shadow: 0 2px 8px rgba(0,0,0,0.15);
              ">
                🚌 ${bus.bus_number}
              </div>
            </div>
          `,
          iconSize: [44, 44],
          iconAnchor: [22, 22],
        });

        const newMarker = L.marker([newLat, newLng], { icon: busIcon })
          .bindPopup(`
            <div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 12px; color: #0F172A;">
              <strong>${bus.bus_number}</strong> (${bus.route_name})<br/>
              Driver: ${bus.driver_name}<br/>
              Lat: ${newLat.toFixed(6)}, Lng: ${newLng.toFixed(6)}
            </div>
          `)
          .addTo(map);

        busMarkerRef.current = newMarker;

        // First fix zoom-in
        map.setView([newLat, newLng], 16, { animate: true });
      }

      // 2. Update or create GPS accuracy circle
      const accRadius = newAcc !== undefined && !isNaN(newAcc) ? newAcc : 10;
      if (accuracyCircleRef.current) {
        accuracyCircleRef.current.setLatLng([newLat, newLng]);
        accuracyCircleRef.current.setRadius(accRadius);
      } else {
        accuracyCircleRef.current = L.circle([newLat, newLng], {
          radius: accRadius,
          color: "#16A34A",
          weight: 1.5,
          fillColor: "#16A34A",
          fillOpacity: 0.12,
        }).addTo(map);
      }

      // 3. Update dynamic real-time breadcrumb trail (traces exact path driven by device)
      trailPointsRef.current.push([newLat, newLng]);
      if (trailPointsRef.current.length > 500) {
        trailPointsRef.current.shift();
      }

      if (trailPolylineRef.current) {
        trailPolylineRef.current.setLatLngs(trailPointsRef.current);
      } else {
        trailPolylineRef.current = L.polyline(trailPointsRef.current, {
          color: "#0284C7",
          weight: 4,
          opacity: 0.85,
          lineJoin: "round",
        }).addTo(map);
      }

      // 4. Auto-follow camera: smoothly pan to keep moving device in center
      if (autoFollowRef.current) {
        map.panTo([newLat, newLng], { animate: true, duration: 1.0 });
      }
    });
  };

  // Remove marker and accuracy circle when disconnected
  const handleDeviceDisconnected = () => {
    setDriverConnected(false);
    setCurrentCoord(null);
    setSpeed(0.0);
    if (busMarkerRef.current && mapInstanceRef.current) {
      mapInstanceRef.current.removeLayer(busMarkerRef.current);
      busMarkerRef.current = null;
    }
    if (accuracyCircleRef.current && mapInstanceRef.current) {
      mapInstanceRef.current.removeLayer(accuracyCircleRef.current);
      accuracyCircleRef.current = null;
    }
  };

  // Initialize Leaflet Map (Zero Static Points: Clean white cartography)
  useEffect(() => {
    if (typeof window === "undefined" || !mapContainerRef.current) return;

    let isMounted = true;
    let resizeObserver: ResizeObserver | null = null;

    async function setupMap() {
      const L = (await import("leaflet")).default;

      if (!mapContainerRef.current || !isMounted) return;

      // Clean up previous instance if any
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
        busMarkerRef.current = null;
        accuracyCircleRef.current = null;
        trailPolylineRef.current = null;
        trailPointsRef.current = [];
      }

      // Determine initial center
      const initialCenter: [number, number] =
        bus.driver_connected && bus.current_lat && bus.current_lng
          ? [bus.current_lat, bus.current_lng]
          : [20.5937, 78.9629]; // Clean overview

      const initialZoom = bus.driver_connected && bus.current_lat && bus.current_lng ? 15 : 5;

      const map = L.map(mapContainerRef.current, {
        center: initialCenter,
        zoom: initialZoom,
        zoomControl: false,
        attributionControl: true,
      });

      L.control.zoom({ position: "bottomright" }).addTo(map);

      // Clean OpenStreetMap Layer (Standard White Cartography)
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19,
        subdomains: ["a", "b", "c"],
      }).addTo(map);

      mapInstanceRef.current = map;

      // If driver is currently active with coordinates, place marker
      if (bus.driver_connected && bus.current_lat && bus.current_lng) {
        const busIcon = L.divIcon({
          className: "custom-bus-icon",
          html: `
            <div style="position: relative; width: 44px; height: 44px; display: flex; align-items: center; justify-content: center;">
              <div class="bus-beacon"></div>
              <div style="
                position: absolute;
                bottom: -18px;
                background: #FFFFFF;
                color: #0F172A;
                padding: 2px 7px;
                border-radius: 4px;
                font-size: 10px;
                font-family: 'JetBrains Mono', monospace;
                font-weight: 700;
                white-space: nowrap;
                border: 1.5px solid #0F172A;
                box-shadow: 0 2px 8px rgba(0,0,0,0.15);
              ">
                🚌 ${bus.bus_number}
              </div>
            </div>
          `,
          iconSize: [44, 44],
          iconAnchor: [22, 22],
        });

        const marker = L.marker([bus.current_lat, bus.current_lng], { icon: busIcon })
          .bindPopup(`
            <div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 12px; color: #0F172A;">
              <strong>${bus.bus_number}</strong> (${bus.route_name})<br/>
              Live Speed: ${bus.speed_kmh || 0} km/h
            </div>
          `)
          .addTo(map);

        busMarkerRef.current = marker;
        trailPointsRef.current = [[bus.current_lat, bus.current_lng]];

        trailPolylineRef.current = L.polyline(trailPointsRef.current, {
          color: "#0284C7",
          weight: 4,
          opacity: 0.85,
          lineJoin: "round",
        }).addTo(map);

        accuracyCircleRef.current = L.circle([bus.current_lat, bus.current_lng], {
          radius: 12,
          color: "#16A34A",
          weight: 1.5,
          fillColor: "#16A34A",
          fillOpacity: 0.12,
        }).addTo(map);
      }

      // Invalidate map size
      setTimeout(() => {
        if (mapInstanceRef.current) {
          mapInstanceRef.current.invalidateSize();
        }
      }, 250);

      if (mapContainerRef.current) {
        resizeObserver = new ResizeObserver(() => {
          if (mapInstanceRef.current) {
            mapInstanceRef.current.invalidateSize();
          }
        });
        resizeObserver.observe(mapContainerRef.current);
      }
    }

    setupMap();

    return () => {
      isMounted = false;
      if (resizeObserver) resizeObserver.disconnect();
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
      busMarkerRef.current = null;
      accuracyCircleRef.current = null;
      trailPolylineRef.current = null;
      trailPointsRef.current = [];
    };
  }, [bus.id]);

  // 2-second continuous polling refresh to guarantee updates every 2000ms
  useEffect(() => {
    if (!token || !bus.id) return;
    let isCancelled = false;

    const interval = setInterval(async () => {
      if (isCancelled) return;
      try {
        const latest = await getBusById(token, bus.id);
        if (latest && !isCancelled) {
          if (latest.driver_connected) {
            if (latest.current_lat !== undefined && latest.current_lat !== null &&
                latest.current_lng !== undefined && latest.current_lng !== null) {
              updateBusPosition(latest.current_lat, latest.current_lng, latest.speed_kmh, undefined, true);
            }
          } else {
            handleDeviceDisconnected();
          }
        }
      } catch (e) {
        // ignore polling error
      }
    }, 2000);

    return () => {
      isCancelled = true;
      clearInterval(interval);
    };
  }, [bus.id, token]);

  // Connect to WebSocket for real-time telemetry streaming from driver
  useEffect(() => {
    if (!token || !bus.id) return;

    let ws: WebSocket | null = null;
    let reconnectTimeout: any = null;
    let isCancelled = false;

    function connect() {
      if (isCancelled) return;
      try {
        const wsUrl = getUnifiedWebSocketUrl(token);
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          if (!isCancelled) setIsConnected(true);
        };

        const handleWsMessage = (event: MessageEvent) => {
          if (isCancelled) return;
          try {
            const data = JSON.parse(event.data);
            const targetBusId = data.busId || data.bus_id || bus.id;

            // Handle driver connection / status updates
            if (data.type === "driver-status-update" && targetBusId === bus.id) {
              if (data.driverConnected) {
                setDriverConnected(true);
              } else {
                handleDeviceDisconnected();
              }
              return;
            }

            const lat = data.latitude !== undefined ? data.latitude : data.lat;
            const lng = data.longitude !== undefined ? data.longitude : data.lng;

            if (lat !== undefined && lng !== undefined && targetBusId === bus.id) {
              const newLat = parseFloat(lat);
              const newLng = parseFloat(lng);
              const spd = data.speed_kmh !== undefined ? data.speed_kmh : data.speed;
              const acc = data.accuracy !== undefined ? data.accuracy : undefined;

              updateBusPosition(newLat, newLng, spd, acc, data.driverConnected);

              if (data.status) setStatus(data.status);
            }
          } catch (e) {
            console.error("Failed to parse telemetry packet", e);
          }
        };

        ws.onmessage = handleWsMessage;

        ws.onclose = () => {
          if (!isCancelled) {
            setIsConnected(false);
            reconnectTimeout = setTimeout(connect, 3000);
          }
        };

        ws.onerror = () => {
          if (!isCancelled) {
            try {
              if (ws) ws.close();
              const fallbackUrl = getTransitWebSocketUrl(bus.id, token);
              const fallbackWs = new WebSocket(fallbackUrl);
              fallbackWs.onmessage = handleWsMessage;
              fallbackWs.onopen = () => setIsConnected(true);
              fallbackWs.onclose = () => setIsConnected(false);
              ws = fallbackWs;
            } catch (fallbackErr) {
              setIsConnected(false);
            }
          }
        };
      } catch (err) {
        console.error("WebSocket connection failure", err);
      }
    }

    connect();

    return () => {
      isCancelled = true;
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (ws) ws.close();
    };
  }, [bus.id, token]);

  // Center map on moving bus
  const handleRecenter = () => {
    if (mapInstanceRef.current && currentCoord) {
      mapInstanceRef.current.panTo([currentCoord.lat, currentCoord.lng], {
        animate: true,
        duration: 0.8,
      });
      mapInstanceRef.current.setZoom(16);
    }
  };

  // Clear live breadcrumb trail
  const handleClearTrail = () => {
    trailPointsRef.current = currentCoord ? [[currentCoord.lat, currentCoord.lng]] : [];
    if (trailPolylineRef.current) {
      trailPolylineRef.current.setLatLngs(trailPointsRef.current);
    }
  };

  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        height: "100%",
        minHeight: "540px",
        borderRadius: "14px",
        overflow: "hidden",
        border: "1px solid var(--surface-border)",
        background: "#FFFFFF",
      }}
    >
      {/* Leaflet Map Canvas */}
      <div
        ref={mapContainerRef}
        style={{
          width: "100%",
          height: "100%",
          minHeight: "540px",
          zIndex: 1,
        }}
      />

      {/* ================= AWAITING LIVE DRIVER SIGNAL OVERLAY (WHITE THEME) ================= */}
      {!driverConnected && (
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            zIndex: 1000,
            background: "rgba(255, 255, 255, 0.95)",
            backdropFilter: "blur(14px)",
            border: "1px solid #E2E8F0",
            borderRadius: "14px",
            padding: "24px 28px",
            color: "#0F172A",
            textAlign: "center",
            maxWidth: "460px",
            boxShadow: "0 20px 40px rgba(0, 0, 0, 0.08)",
          }}
        >
          <div
            style={{
              width: "48px",
              height: "48px",
              borderRadius: "50%",
              background: "#F1F5F9",
              border: "1px solid #E2E8F0",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 14px",
              color: "#64748B",
            }}
          >
            <Smartphone size={24} />
          </div>
          <h3 style={{ fontSize: "1.1rem", fontWeight: 700, marginBottom: "8px", color: "#0F172A" }}>
            No Device is Connected
          </h3>
          <p style={{ fontSize: "0.84rem", color: "#64748B", lineHeight: 1.5, marginBottom: "16px" }}>
            To track <strong>{bus.bus_number}</strong>, open the driver link on a smartphone and tap <strong>"Start Live GPS Tracking"</strong>. Once connected, live coordinates will instantly refresh on this map every 2 seconds.
          </p>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              background: "#F8FAFC",
              color: "#475569",
              border: "1px solid #E2E8F0",
              padding: "6px 14px",
              borderRadius: "6px",
              fontSize: "0.75rem",
              fontWeight: 600,
            }}
          >
            <Radio size={13} className="animate-pulse" color="#0284C7" />
            <span>Listening for device on WebSocket room bus:{bus.id}</span>
          </div>
        </div>
      )}

      {/* ================= MAP CONTROLS OVERLAY (BOTTOM-LEFT - WHITE THEME) ================= */}
      <div
        style={{
          position: "absolute",
          bottom: "20px",
          left: "20px",
          zIndex: 1000,
          display: "flex",
          gap: "8px",
        }}
      >
        {driverConnected && currentCoord && (
          <button
            type="button"
            onClick={handleRecenter}
            style={{
              background: "#FFFFFF",
              color: "#0F172A",
              border: "1px solid #E2E8F0",
              borderRadius: "8px",
              padding: "8px 12px",
              fontSize: "0.78rem",
              fontWeight: 600,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "6px",
              boxShadow: "0 4px 12px rgba(0, 0, 0, 0.06)",
            }}
            title="Center on Live Bus"
          >
            <Compass size={14} color="#0284C7" />
            <span>Center Device</span>
          </button>
        )}

        <button
          type="button"
          onClick={() => setAutoFollow(!autoFollow)}
          style={{
            background: autoFollow ? "#ECFDF5" : "#FFFFFF",
            color: autoFollow ? "#059669" : "#0F172A",
            border: autoFollow ? "1px solid #A7F3D0" : "1px solid #E2E8F0",
            borderRadius: "8px",
            padding: "8px 12px",
            fontSize: "0.78rem",
            fontWeight: 600,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "6px",
            boxShadow: "0 4px 12px rgba(0, 0, 0, 0.06)",
          }}
          title="Auto-Follow Moving Bus Camera"
        >
          <Crosshair size={14} color={autoFollow ? "#059669" : "#64748B"} />
          <span>Auto-Follow: {autoFollow ? "ON" : "OFF"}</span>
        </button>

        {trailPointsRef.current.length > 1 && (
          <button
            type="button"
            onClick={handleClearTrail}
            style={{
              background: "#FFFFFF",
              color: "#64748B",
              border: "1px solid #E2E8F0",
              borderRadius: "8px",
              padding: "8px 12px",
              fontSize: "0.78rem",
              fontWeight: 600,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "6px",
              boxShadow: "0 4px 12px rgba(0, 0, 0, 0.06)",
            }}
            title="Reset Live Breadcrumb Trail"
          >
            <Trash2 size={13} />
            <span>Reset Path</span>
          </button>
        )}
      </div>

      {/* ================= REAL-TIME TELEMETRY HUD OVERLAY (TOP-LEFT - WHITE THEME) ================= */}
      <div
        style={{
          position: "absolute",
          top: "16px",
          left: "16px",
          zIndex: 1000,
          padding: "16px",
          borderRadius: "12px",
          background: "#FFFFFF",
          border: "1px solid #E2E8F0",
          display: "flex",
          flexDirection: "column",
          gap: "10px",
          minWidth: "290px",
          boxShadow: "0 10px 25px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -4px rgba(0, 0, 0, 0.03)",
          color: "#0F172A",
        }}
      >
        {/* Header line */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid #E2E8F0", paddingBottom: "10px" }}>
          <div>
            <div style={{ fontSize: "0.96rem", fontWeight: 700, color: "#0F172A", display: "flex", alignItems: "center", gap: "6px" }}>
              <Navigation size={15} color="#0284C7" />
              <span>{bus.bus_number}</span>
            </div>
            <div style={{ fontSize: "0.72rem", color: "#64748B", marginTop: "1px" }}>
              {bus.route_name}
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "4px" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "5px",
                fontSize: "0.68rem",
                fontWeight: 600,
                padding: "3px 8px",
                borderRadius: "6px",
                background: isConnected ? "#F0FDF4" : "#FFFBEB",
                color: isConnected ? "#16A34A" : "#D97706",
                border: `1px solid ${isConnected ? "#BBF7D0" : "#FDE68A"}`,
              }}
            >
              <Wifi size={11} />
              <span>{isConnected ? "WS LIVE" : "CONNECTING"}</span>
            </div>

            {driverConnected ? (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "4px",
                  fontSize: "0.65rem",
                  fontWeight: 700,
                  padding: "3px 7px",
                  borderRadius: "4px",
                  background: "#ECFDF5",
                  color: "#059669",
                  border: "1px solid #A7F3D0",
                }}
              >
                <Radio size={10} className="animate-pulse" />
                <span>STREAMING (2s)</span>
              </div>
            ) : (
              <div
                style={{
                  fontSize: "0.65rem",
                  fontWeight: 600,
                  padding: "2px 6px",
                  borderRadius: "4px",
                  background: "#F1F5F9",
                  color: "#64748B",
                  border: "1px solid #E2E8F0",
                }}
              >
                DISCONNECTED
              </div>
            )}
          </div>
        </div>

        {/* ================= LOCATION COORDINATES SMALL WINDOW ================= */}
        <div
          style={{
            background: "#F8FAFC",
            border: "1px solid #E2E8F0",
            padding: "10px 12px",
            borderRadius: "8px",
            display: "flex",
            flexDirection: "column",
            gap: "4px",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "0.65rem", color: "#64748B", textTransform: "uppercase", fontWeight: 700, letterSpacing: "0.03em" }}>
              Location Coordinates
            </span>
            {driverConnected && currentCoord && (
              <span style={{ fontSize: "0.65rem", color: "#16A34A", fontWeight: 700, display: "flex", alignItems: "center", gap: "4px" }}>
                <Activity size={10} className="animate-pulse" />
                {lastUpdateAgo === 0 ? "Just now" : `${lastUpdateAgo}s ago`}
              </span>
            )}
          </div>

          {/* EXACT REQUIRED LOGIC: If no device sending its location, say 'No Device is Connected' */}
          {!driverConnected || !currentCoord ? (
            <div style={{ padding: "4px 0" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "6px", margin: "2px 0 3px" }}>
                <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#94A3B8" }}></span>
                <span style={{ fontSize: "0.92rem", fontWeight: 700, color: "#0F172A" }}>
                  No Device is Connected
                </span>
              </div>
              <div style={{ fontSize: "0.72rem", color: "#64748B" }}>
                Awaiting GPS signal from driver phone
              </div>
            </div>
          ) : (
            <div style={{ padding: "2px 0" }}>
              <div className="font-mono" style={{ fontSize: "0.90rem", fontWeight: 700, color: "#0284C7", letterSpacing: "0.02em" }}>
                {currentCoord.lat.toFixed(6)}° N, {currentCoord.lng.toFixed(6)}° E
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.68rem", color: "#64748B", marginTop: "3px" }}>
                <span>Precision: <strong style={{ color: "#16A34A" }}>±{accuracy ? Math.round(accuracy) : 4}m</strong></span>
                <span style={{ color: "#059669", fontWeight: 600 }}>Refreshing every 2s</span>
              </div>
            </div>
          )}
        </div>

        {/* Telemetry Stats Grid (White Theme) */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
          <div style={{ background: "#F8FAFC", border: "1px solid #E2E8F0", padding: "7px 10px", borderRadius: "6px" }}>
            <div style={{ fontSize: "0.65rem", color: "#64748B", display: "flex", alignItems: "center", gap: "4px" }}>
              <Gauge size={11} /> Speed
            </div>
            <div className="font-mono" style={{ fontSize: "1.05rem", fontWeight: 700, color: "#0F172A", marginTop: "2px" }}>
              {driverConnected ? speed.toFixed(1) : "—"} <span style={{ fontSize: "0.7rem", fontWeight: 400, color: "#64748B" }}>km/h</span>
            </div>
          </div>

          <div style={{ background: "#F8FAFC", border: "1px solid #E2E8F0", padding: "7px 10px", borderRadius: "6px" }}>
            <div style={{ fontSize: "0.65rem", color: "#64748B", display: "flex", alignItems: "center", gap: "4px" }}>
              <Layers size={11} /> Path Updates
            </div>
            <div className="font-mono" style={{ fontSize: "1.05rem", fontWeight: 700, color: "#0F172A", marginTop: "2px" }}>
              {driverConnected ? trailPointsRef.current.length : 0} <span style={{ fontSize: "0.7rem", fontWeight: 400, color: "#64748B" }}>ticks</span>
            </div>
          </div>
        </div>

        {/* Driver contact line */}
        <div style={{ fontSize: "0.68rem", color: "#64748B", display: "flex", justifyContent: "space-between", paddingTop: "2px" }}>
          <span>Driver: <strong style={{ color: "#334155" }}>{bus.driver_name}</strong></span>
          <span className="font-mono" style={{ color: "#64748B" }}>{bus.driver_phone}</span>
        </div>
      </div>
    </div>
  );
};
