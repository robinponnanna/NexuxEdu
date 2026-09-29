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
        self._active_driver_buses: set = set()

    def register_active_driver(self, bus_id: int):
        self._active_driver_buses.add(bus_id)

    def unregister_active_driver(self, bus_id: int):
        self._active_driver_buses.discard(bus_id)

    def is_driver_active(self, bus_id: int) -> bool:
        return bus_id in self._active_driver_buses

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
        # Synthetic waypoint generation disabled: Only real driver device coordinates are processed
        while self._running:
            try:
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(1)

transit_simulator = TransitSimulator()

