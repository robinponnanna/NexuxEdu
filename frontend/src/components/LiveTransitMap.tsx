"use client";

import React, { useEffect, useRef, useState } from "react";
import "leaflet/dist/leaflet.css";
import { BusDetails, getTransitWebSocketUrl } from "@/lib/api";
import {
  Navigation,
  Gauge,
  Clock,
  MapPin,
  Wifi,
  Radio,
  Bell,
  X,
  ShieldCheck,
  Compass,
  Maximize2,
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
  const polylineRef = useRef<any>(null);
  const stopMarkersRef = useRef<any[]>([]);
  const geofenceCircleRef = useRef<any>(null);
  const tileLayerRef = useRef<any>(null);

  const [currentCoord, setCurrentCoord] = useState<{ lat: number; lng: number }>({
    lat: bus.current_lat,
    lng: bus.current_lng,
  });
  const [speed, setSpeed] = useState<number>(bus.speed_kmh || 35.0);
  const [status, setStatus] = useState<string>(bus.status || "Active");
  const [nextStop, setNextStop] = useState<string>(bus.stops?.[1]?.name || "Midtown Gate");
  const [etaMins, setEtaMins] = useState<number>(5);
  const [distanceKm, setDistanceKm] = useState<number>(1.2);
  const [isConnected, setIsConnected] = useState<boolean>(false);

  // 500m Geofencing Proximity State
  const [geofenceActive, setGeofenceActive] = useState<boolean>(false);
  const [distanceToRegStopM, setDistanceToRegStopM] = useState<number>(1200);
  const [registeredStopName, setRegisteredStopName] = useState<string>(
    bus.stops?.[1]?.name || "Midtown Gate"
  );
  const [alertDismissed, setAlertDismissed] = useState<boolean>(false);

  // Initialize Leaflet Map
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
      }

      // Initialize Leaflet map
      const map = L.map(mapContainerRef.current, {
        center: [bus.current_lat, bus.current_lng],
        zoom: 14,
        zoomControl: false,
        attributionControl: true,
      });

      L.control.zoom({ position: "bottomright" }).addTo(map);

      // Exclusively use Standard OpenStreetMap Cartography
      const tileLayer = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19,
        subdomains: ["a", "b", "c"],
      }).addTo(map);
      tileLayerRef.current = tileLayer;


      mapInstanceRef.current = map;

      // Draw Route Polyline
      if (bus.waypoints && bus.waypoints.length > 0) {
        const polyline = L.polyline(bus.waypoints as [number, number][], {
          color: "#4F46E5",
          weight: 4,
          opacity: 0.8,
          dashArray: "3, 6",
          lineJoin: "round",
        }).addTo(map);
        polylineRef.current = polyline;

        // Auto-fit bounds to display the whole route on initial render
        try {
          const bounds = L.latLngBounds(bus.waypoints as [number, number][]);
          map.fitBounds(bounds, { padding: [50, 50], maxZoom: 15 });
        } catch (e) {
          // ignore
        }
      }

      // Render Stop Markers & 500m Geofence Radius Perimeter
      if (bus.stops) {
        bus.stops.forEach((stop, i) => {
          const isRegisteredParentStop = i === 1; // Default registered stop

          // Draw the 500-meter translucent geofencing radius around registered parent stop
          if (isRegisteredParentStop) {
            const geofenceCircle = L.circle([stop.lat, stop.lng], {
              radius: 500, // 500 meters
              color: "#FBBF24",
              fillColor: "#FBBF24",
              fillOpacity: 0.08,
              weight: 1.5,
              dashArray: "4, 4",
            }).addTo(map);

            geofenceCircle.bindPopup(
              `<div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 12px; color: #0F172A; line-height: 1.4;">
                <strong style="color: #D97706;">🔔 500m Geofence Zone</strong><br/>
                Pickup Stop: <strong>${stop.name}</strong><br/>
                Arrival alerts trigger automatically when the bus enters this boundary.
              </div>`
            );
            geofenceCircleRef.current = geofenceCircle;
          }

          const stopIcon = L.divIcon({
            className: "custom-stop-marker",
            html: `
              <div style="
                background: ${isRegisteredParentStop ? "#D97706" : "#FFFFFF"};
                color: ${isRegisteredParentStop ? "#FFFFFF" : "#0F172A"};
                width: 24px;
                height: 24px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 10px;
                font-weight: 700;
                border: 1.5px solid ${isRegisteredParentStop ? "#F59E0B" : "#CBD5E1"};
                box-shadow: 0 2px 6px rgba(0,0,0,0.15);
              ">
                ${stop.sequence}
              </div>
            `,
            iconSize: [24, 24],
            iconAnchor: [12, 12],
          });

          const marker = L.marker([stop.lat, stop.lng], { icon: stopIcon })
            .bindPopup(
              `<div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 12px; color: #0F172A;">
                <strong>${stop.name}</strong> (Stop #${stop.sequence})<br/>
                ${
                  isRegisteredParentStop
                    ? "<span style='color: #D97706; font-weight: 600;'>⭐ Registered SafeTransit Pickup Stop</span>"
                    : "Scheduled Campus Transit Stop"
                }
              </div>`
            )
            .addTo(map);
          stopMarkersRef.current.push(marker);
        });
      }

      // Custom animated Bus Beacon marker
      const busIcon = L.divIcon({
        className: "custom-bus-icon",
        html: `
          <div style="position: relative; width: 44px; height: 44px; display: flex; align-items: center; justify-content: center;">
            <div class="bus-beacon"></div>
            <div style="
              position: absolute;
              bottom: -18px;
              background: rgba(15, 23, 42, 0.95);
              color: #F8FAFC;
              padding: 2px 6px;
              border-radius: 4px;
              font-size: 10px;
              font-family: 'JetBrains Mono', monospace;
              font-weight: 700;
              white-space: nowrap;
              border: 1px solid rgba(245, 158, 11, 0.7);
              box-shadow: 0 2px 8px rgba(0,0,0,0.6);
            ">
              🚌 ${bus.bus_number}
            </div>
          </div>
        `,
        iconSize: [44, 44],
        iconAnchor: [22, 22],
      });

      const busMarker = L.marker([bus.current_lat, bus.current_lng], { icon: busIcon })
        .bindPopup(
          `<div style="font-family: sans-serif; font-size: 12px; color: #0F172A;">
            <strong>${bus.bus_number}</strong> (${bus.route_name})<br/>
            Driver: ${bus.driver_name} (${bus.driver_phone})<br/>
            Live Speed: ${bus.speed_kmh} km/h
          </div>`
        )
        .addTo(map);
      busMarkerRef.current = busMarker;

      // Crucial Leaflet Fix: Invalidate map size to prevent gray/unrendered tiles
      setTimeout(() => {
        if (mapInstanceRef.current) {
          mapInstanceRef.current.invalidateSize();
        }
      }, 200);

      setTimeout(() => {
        if (mapInstanceRef.current) {
          mapInstanceRef.current.invalidateSize();
        }
      }, 600);

      // Auto-recalculate size when container dimensions change
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
    };
  }, [bus.id]);


  // Connect to WebSocket for live 3-second telemetry streaming
  useEffect(() => {
    if (!token || !bus.id) return;

    let ws: WebSocket | null = null;
    let reconnectTimeout: any = null;
    let isCancelled = false;

    function connect() {
      if (isCancelled) return;
      try {
        const wsUrl = getTransitWebSocketUrl(bus.id, token);
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          if (!isCancelled) setIsConnected(true);
        };

        ws.onmessage = (event) => {
          if (isCancelled) return;
          try {
            const data = JSON.parse(event.data);
            if (data.lat && data.lng) {
              const newLat = parseFloat(data.lat);
              const newLng = parseFloat(data.lng);
              setCurrentCoord({ lat: newLat, lng: newLng });
              setSpeed(data.speed_kmh || 35.0);
              setStatus(data.status || "Active");
              if (data.next_stop) setNextStop(data.next_stop);
              if (data.next_stop_eta_mins) setEtaMins(data.next_stop_eta_mins);
              if (data.distance_to_stop_km) setDistanceKm(data.distance_to_stop_km);

              // 500m Geofence fields from backend
              if (data.geofence_active !== undefined) {
                setGeofenceActive(Boolean(data.geofence_active));
              }
              if (data.distance_to_registered_stop_m !== undefined) {
                setDistanceToRegStopM(data.distance_to_registered_stop_m);
              }
              if (data.registered_stop_name) {
                setRegisteredStopName(data.registered_stop_name);
              }

              // Smoothly pan marker and canvas
              if (busMarkerRef.current) {
                busMarkerRef.current.setLatLng([newLat, newLng]);
              }
            }
          } catch (e) {
            console.error("Failed to parse telemetry packet", e);
          }
        };

        ws.onclose = () => {
          if (!isCancelled) {
            setIsConnected(false);
            reconnectTimeout = setTimeout(connect, 3000);
          }
        };

        ws.onerror = () => {
          if (!isCancelled) setIsConnected(false);
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
    if (mapInstanceRef.current) {
      mapInstanceRef.current.panTo([currentCoord.lat, currentCoord.lng], {
        animate: true,
        duration: 0.8,
      });
      mapInstanceRef.current.setZoom(15);
    }
  };

  // Zoom to full route extent
  const handleFitRoute = () => {
    if (mapInstanceRef.current && bus.waypoints && bus.waypoints.length > 0) {
      import("leaflet").then(({ default: L }) => {
        const bounds = L.latLngBounds(bus.waypoints as [number, number][]);
        mapInstanceRef.current.fitBounds(bounds, { padding: [50, 50], maxZoom: 15 });
      });
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

      {/* ================= MAP CONTROLS OVERLAY (BOTTOM-LEFT) ================= */}
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
        <button
          type="button"
          onClick={handleRecenter}
          style={{
            background: "var(--surface-card)",
            color: "var(--text-main)",
            border: "1px solid var(--surface-border)",
            borderRadius: "8px",
            padding: "8px 12px",
            fontSize: "0.78rem",
            fontWeight: 600,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "6px",
            boxShadow: "var(--shadow-md)",
          }}
          title="Center on Live Bus"
        >
          <Compass size={14} color="var(--color-primary)" />
          <span>Center Bus</span>
        </button>

        <button
          type="button"
          onClick={handleFitRoute}
          style={{
            background: "var(--surface-card)",
            color: "var(--text-main)",
            border: "1px solid var(--surface-border)",
            borderRadius: "8px",
            padding: "8px 12px",
            fontSize: "0.78rem",
            fontWeight: 600,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "6px",
            boxShadow: "var(--shadow-md)",
          }}
          title="View Full Route"
        >
          <Maximize2 size={14} color="var(--color-student)" />
          <span>Full Route</span>
        </button>
      </div>


      {/* ================= GEOFENCING 500M PROXIMITY ALERT TOAST BANNER ================= */}
      {geofenceActive && !alertDismissed && (
        <div
          style={{
            position: "absolute",
            top: "16px",
            right: "16px",
            zIndex: 1001,
            padding: "12px 16px",
            borderRadius: "10px",
            border: "1px solid #FDE68A",
            background: "rgba(255, 255, 255, 0.96)",
            backdropFilter: "blur(12px)",
            boxShadow: "0 8px 24px rgba(0, 0, 0, 0.08)",
            display: "flex",
            alignItems: "center",
            gap: "12px",
            maxWidth: "440px",
            animation: "slideIn 0.3s ease",
          }}
        >
          <div
            style={{
              width: "32px",
              height: "32px",
              borderRadius: "8px",
              background: "#FFFBEB",
              border: "1px solid #FDE68A",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#D97706",
              flexShrink: 0,
            }}
          >
            <Bell size={16} />
          </div>

          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "#D97706", fontWeight: 700, fontSize: "0.76rem", letterSpacing: "0.03em" }}>
              <Radio size={12} className="animate-pulse" />
              <span>500M PROXIMITY ALERT</span>
            </div>
            <div style={{ fontSize: "0.8rem", color: "var(--text-main)", marginTop: "2px", lineHeight: 1.4 }}>
              <strong>{bus.bus_number}</strong> entered the pickup perimeter of <em>{registeredStopName}</em>.
            </div>
            <div style={{ fontSize: "0.72rem", color: "var(--text-dim)", marginTop: "3px" }}>
              Distance: <span className="font-mono" style={{ color: "#D97706", fontWeight: 600 }}>{distanceToRegStopM}m</span> • ETA: ~{etaMins} mins
            </div>
          </div>

          <button
            type="button"
            onClick={() => setAlertDismissed(true)}
            style={{
              background: "transparent",
              border: "none",
              color: "var(--text-dim)",
              cursor: "pointer",
              padding: "4px",
              borderRadius: "4px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transition: "color 0.15s ease",
            }}
            title="Dismiss Alert"
          >
            <X size={16} />
          </button>
        </div>
      )}

      {/* ================= TELEMETRY HUD OVERLAY (TOP-LEFT) ================= */}
      <div
        style={{
          position: "absolute",
          top: "16px",
          left: "16px",
          zIndex: 1000,
          padding: "14px 16px",
          borderRadius: "10px",
          background: "rgba(255, 255, 255, 0.96)",
          backdropFilter: "blur(12px)",
          border: "1px solid var(--surface-border)",
          display: "flex",
          flexDirection: "column",
          gap: "10px",
          minWidth: "260px",
          boxShadow: "0 8px 24px rgba(0, 0, 0, 0.08)",
        }}
      >
        {/* Header line */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid var(--surface-border)", paddingBottom: "8px" }}>
          <div>
            <div style={{ fontSize: "0.92rem", fontWeight: 700, color: "var(--text-main)", display: "flex", alignItems: "center", gap: "6px" }}>
              <Navigation size={15} color="var(--text-muted)" />
              <span>{bus.bus_number}</span>
            </div>
            <div style={{ fontSize: "0.72rem", color: "var(--text-dim)", marginTop: "1px" }}>
              {bus.route_name}
            </div>
          </div>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "5px",
              fontSize: "0.68rem",
              fontWeight: 600,
              padding: "3px 8px",
              borderRadius: "6px",
              background: isConnected ? "#ECFDF5" : "#FFFBEB",
              color: isConnected ? "#059669" : "#D97706",
              border: `1px solid ${isConnected ? "#A7F3D0" : "#FDE68A"}`,
            }}
          >
            <Wifi size={11} />
            <span>{isConnected ? "LIVE (3s)" : "CONNECTING"}</span>
          </div>
        </div>

        {/* Telemetry Stats Grid */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
          <div style={{ background: "var(--surface-elevated)", border: "1px solid var(--surface-border)", padding: "7px 10px", borderRadius: "6px" }}>
            <div style={{ fontSize: "0.65rem", color: "var(--text-dim)", display: "flex", alignItems: "center", gap: "4px" }}>
              <Gauge size={11} /> Velocity
            </div>
            <div className="font-mono" style={{ fontSize: "1.05rem", fontWeight: 700, color: "var(--text-main)", marginTop: "2px" }}>
              {speed} <span style={{ fontSize: "0.7rem", fontWeight: 400, color: "var(--text-dim)" }}>km/h</span>
            </div>
          </div>

          <div style={{ background: "var(--surface-elevated)", border: "1px solid var(--surface-border)", padding: "7px 10px", borderRadius: "6px" }}>
            <div style={{ fontSize: "0.65rem", color: "var(--text-dim)", display: "flex", alignItems: "center", gap: "4px" }}>
              <Clock size={11} /> Next Stop
            </div>
            <div className="font-mono" style={{ fontSize: "1.05rem", fontWeight: 700, color: "var(--text-main)", marginTop: "2px" }}>
              ~{etaMins} <span style={{ fontSize: "0.7rem", fontWeight: 400, color: "var(--text-dim)" }}>min</span>
            </div>
          </div>
        </div>

        {/* Stop Info & Geofencing Status */}
        <div style={{ background: "var(--surface-elevated)", border: "1px solid var(--surface-border)", padding: "8px 10px", borderRadius: "6px", display: "flex", flexDirection: "column", gap: "4px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "0.74rem", color: "var(--text-muted)" }}>
            <MapPin size={13} color="var(--text-dim)" />
            <span>Target: <strong style={{ color: "var(--text-main)" }}>{nextStop}</strong></span>
          </div>
          <div style={{ fontSize: "0.7rem", color: "var(--text-dim)", paddingLeft: "19px" }}>
            Distance: <span className="font-mono" style={{ color: "var(--text-main)" }}>{distanceKm} km</span>
          </div>

          {/* 500m Geofence Indicator Badge */}
          <div
            style={{
              marginTop: "4px",
              padding: "4px 8px",
              borderRadius: "4px",
              fontSize: "0.68rem",
              fontWeight: 600,
              display: "flex",
              alignItems: "center",
              gap: "5px",
              background: geofenceActive ? "#FFFBEB" : "#FFFFFF",
              color: geofenceActive ? "#D97706" : "var(--text-dim)",
              border: `1px solid ${geofenceActive ? "#FDE68A" : "var(--surface-border)"}`,
            }}
          >
            <ShieldCheck size={12} color={geofenceActive ? "#D97706" : "var(--text-dim)"} />
            <span>
              {geofenceActive
                ? `Active: ${distanceToRegStopM}m to ${registeredStopName}`
                : `Armed (${distanceToRegStopM}m away)`}
            </span>
          </div>
        </div>

        {/* Driver info */}
        <div style={{ fontSize: "0.68rem", color: "var(--text-dim)", display: "flex", justifyContent: "space-between", paddingTop: "2px" }}>
          <span>Driver: <span style={{ color: "var(--text-muted)" }}>{bus.driver_name}</span></span>
          <span className="font-mono" style={{ color: "var(--text-dim)" }}>{bus.driver_phone}</span>
        </div>
      </div>
    </div>
  );
};
