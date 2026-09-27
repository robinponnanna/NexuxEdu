import asyncio
import json
import math
import random
import datetime
from sqlalchemy import select
from app.core.database import AsyncSessionLocal, Bus
from app.core.pubsub import broker
from app.core.config import settings

class TransitSimulator:
    """
    Simulates real-time vehicular GPS movement for the 20 campus buses.
    Executes the mathematical waypoint progression equation:
    P(t) = (1 - alpha)*P_k + alpha*P_{k+1} + N(0, sigma^2)
    and broadcasts telemetry updates over Pub/Sub at 3-second intervals.
    """
    def __init__(self):
        self._running = False
        self._task: asyncio.Task = None
        self._bus_states = {}  # bus_id -> {waypoint_idx, progress_alpha, waypoints, stops, speed}

    async def initialize(self):
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Bus))
            buses = result.scalars().all()
            for bus in buses:
                waypoints = json.loads(bus.waypoints_json) if bus.waypoints_json else []
                stops = json.loads(bus.stops_json) if bus.stops_json else []
                if not waypoints:
                    waypoints = [[bus.current_lat, bus.current_lng]]
                self._bus_states[bus.id] = {
                    "bus_number": bus.bus_number,
                    "route_name": bus.route_name,
                    "driver_name": bus.driver_name,
                    "waypoints": waypoints,
                    "stops": stops,
                    "current_idx": 0,
                    "alpha": 0.0,
                    "speed_kmh": bus.speed_kmh or 35.0,
                    "status": bus.status or "Active",
                    "lat": bus.current_lat,
                    "lng": bus.current_lng
                }
                # Initial cache write
                await broker.set_bus_telemetry(bus.id, {
                    "bus_id": bus.id,
                    "bus_number": bus.bus_number,
                    "route_name": bus.route_name,
                    "driver_name": bus.driver_name,
                    "lat": bus.current_lat,
                    "lng": bus.current_lng,
                    "speed_kmh": bus.speed_kmh,
                    "status": bus.status,
                    "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                    "next_stop": stops[1]["name"] if len(stops) > 1 else "Campus Central",
                    "next_stop_eta_mins": 5,
                    "distance_to_stop_km": 1.2
                })

    async def start(self):
        if self._running:
            return
        self._running = True
        await self.initialize()
        self._task = asyncio.create_task(self._simulation_loop())
        print("Transit Simulator started: 20 buses transmitting at 3-second intervals.")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        print("Transit Simulator stopped.")

    async def _simulation_loop(self):
        sigma = 0.00003  # Realistic GPS jitter standard deviation
        delta_alpha = 0.08 # Progression increment per 3s tick

        while self._running:
            try:
                await asyncio.sleep(settings.TELEMETRY_INTERVAL_SECONDS)
                now_str = datetime.datetime.utcnow().isoformat() + "Z"

                for bus_id, state in self._bus_states.items():
                    waypoints = state["waypoints"]
                    if len(waypoints) < 2:
                        continue

                    idx = state["current_idx"]
                    next_idx = (idx + 1) % len(waypoints)

                    p_k = waypoints[idx]
                    p_k1 = waypoints[next_idx]

                    # Update progression alpha
                    state["alpha"] += delta_alpha
                    if state["alpha"] >= 1.0:
                        state["alpha"] = 0.0
                        state["current_idx"] = next_idx
                        idx = next_idx
                        next_idx = (idx + 1) % len(waypoints)
                        p_k = waypoints[idx]
                        p_k1 = waypoints[next_idx]

                    alpha = state["alpha"]
                    # Interpolation + Gaussian jitter N(0, sigma^2)
                    jitter_lat = random.gauss(0, sigma)
                    jitter_lng = random.gauss(0, sigma)

                    sim_lat = round((1.0 - alpha) * p_k[0] + alpha * p_k1[0] + jitter_lat, 6)
                    sim_lng = round((1.0 - alpha) * p_k[1] + alpha * p_k1[1] + jitter_lng, 6)

                    # Dynamic speed variation
                    speed_delta = random.uniform(-1.5, 1.5)
                    sim_speed = max(18.0, min(55.0, round(state["speed_kmh"] + speed_delta, 1)))

                    state["lat"] = sim_lat
                    state["lng"] = sim_lng
                    state["speed_kmh"] = sim_speed

                    stops = state["stops"]
                    next_stop_name = stops[(idx + 1) % len(stops)]["name"] if stops else "Main Gate"
                    
                    # Registered parent pickup stop (Stop sequence 2: "Midtown Gate")
                    registered_stop = stops[1] if len(stops) > 1 else (stops[0] if stops else None)
                    geofence_active = False
                    dist_to_registered_km = 1.2
                    dist_to_registered_m = 1200
                    
                    if registered_stop:
                        # Geodesic Haversine calculation
                        r_lat = registered_stop["lat"]
                        r_lng = registered_stop["lng"]
                        dlat = math.radians(r_lat - sim_lat)
                        dlng = math.radians(r_lng - sim_lng)
                        a = math.sin(dlat / 2)**2 + math.cos(math.radians(sim_lat)) * math.cos(math.radians(r_lat)) * math.sin(dlng / 2)**2
                        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
                        dist_to_registered_km = round(6371.0 * c, 3)
                        dist_to_registered_m = int(dist_to_registered_km * 1000)
                        
                        # 500-meter proximity threshold
                        geofence_active = dist_to_registered_m <= 500

                    eta_mins = max(1, int(dist_to_registered_km * 3.5))

                    telemetry_payload = {
                        "bus_id": bus_id,
                        "bus_number": state["bus_number"],
                        "route_name": state["route_name"],
                        "driver_name": state["driver_name"],
                        "lat": sim_lat,
                        "lng": sim_lng,
                        "speed_kmh": sim_speed,
                        "status": state["status"],
                        "timestamp": now_str,
                        "next_stop": next_stop_name,
                        "next_stop_eta_mins": eta_mins,
                        "distance_to_stop_km": dist_to_registered_km,
                        "geofence_active": geofence_active,
                        "geofence_radius_meters": 500,
                        "registered_stop_name": registered_stop["name"] if registered_stop else "Campus Gate",
                        "distance_to_registered_stop_m": dist_to_registered_m
                    }

                    # Publish to Redis/Broker
                    await broker.set_bus_telemetry(bus_id, telemetry_payload)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in transit simulation loop: {e}")
                await asyncio.sleep(1)

transit_simulator = TransitSimulator()

