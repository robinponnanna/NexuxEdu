import json
import asyncio
from typing import List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends, Query, status
from sqlalchemy import select
from app.core.database import AsyncSessionLocal, Bus
from app.core.pubsub import broker
from app.core.security import decode_access_token
from app.models.schemas import BusDetails, BusStop, UserSecurityClaims
from app.api.auth import get_current_user_claims

router = APIRouter(prefix="/transit", tags=["Transit & Fleet"])

@router.get("/buses", response_model=List[BusDetails])
async def list_buses(claims: UserSecurityClaims = Depends(get_current_user_claims)):
    """Returns list of active transit buses."""
    async with AsyncSessionLocal() as session:
        stmt = select(Bus)
        res = await session.execute(stmt)
        buses = res.scalars().all()
        
        results = []
        for b in buses:
            # Check latest telemetry from cache
            from app.services.transit_simulator import transit_simulator
            is_driver_active = transit_simulator.is_driver_active(b.id)
            telemetry = await broker.get_bus_telemetry(b.id)
            lat = telemetry.get("lat", b.current_lat) if (telemetry and is_driver_active) else (b.current_lat if is_driver_active else None)
            lng = telemetry.get("lng", b.current_lng) if (telemetry and is_driver_active) else (b.current_lng if is_driver_active else None)
            spd = telemetry.get("speed_kmh", b.speed_kmh) if (telemetry and is_driver_active) else 0.0
            st = telemetry.get("status", b.status) if telemetry else b.status
            
            stops = json.loads(b.stops_json) if b.stops_json else []
            waypoints = json.loads(b.waypoints_json) if b.waypoints_json else []
            
            results.append(BusDetails(
                id=b.id,
                bus_number=b.bus_number,
                route_name=b.route_name,
                driver_name=b.driver_name,
                driver_phone=b.driver_phone,
                current_lat=lat,
                current_lng=lng,
                speed_kmh=spd,
                status=st,
                driver_connected=is_driver_active,
                last_updated=b.last_updated.isoformat() if b.last_updated else None,
                stops=[BusStop(**s) for s in stops],
                waypoints=waypoints
            ))
        return results

@router.get("/buses/{bus_id}", response_model=BusDetails)
async def get_bus(bus_id: int, claims: UserSecurityClaims = Depends(get_current_user_claims)):
    """Returns details for a specific bus."""
    # RBAC check: Non-admins cannot inspect other buses if student/parent
    if claims.role in ["student", "parent"] and claims.bus_id and claims.bus_id != bus_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You may only track your assigned transport route."
        )
        
    async with AsyncSessionLocal() as session:
        stmt = select(Bus).where(Bus.id == bus_id)
        res = await session.execute(stmt)
        b = res.scalar_one_or_none()
        if not b:
            raise HTTPException(status_code=404, detail="Bus route not found.")
            
        from app.services.transit_simulator import transit_simulator
        is_driver_active = transit_simulator.is_driver_active(b.id)
        telemetry = await broker.get_bus_telemetry(b.id)
        lat = telemetry.get("lat", b.current_lat) if (telemetry and is_driver_active) else (b.current_lat if is_driver_active else None)
        lng = telemetry.get("lng", b.current_lng) if (telemetry and is_driver_active) else (b.current_lng if is_driver_active else None)
        spd = telemetry.get("speed_kmh", b.speed_kmh) if (telemetry and is_driver_active) else 0.0
        st = telemetry.get("status", b.status) if telemetry else b.status

        stops = json.loads(b.stops_json) if b.stops_json else []
        waypoints = json.loads(b.waypoints_json) if b.waypoints_json else []

        return BusDetails(
            id=b.id,
            bus_number=b.bus_number,
            route_name=b.route_name,
            driver_name=b.driver_name,
            driver_phone=b.driver_phone,
            current_lat=lat,
            current_lng=lng,
            speed_kmh=spd,
            status=st,
            driver_connected=is_driver_active,
            last_updated=b.last_updated.isoformat() if b.last_updated else None,
            stops=[BusStop(**s) for s in stops],
            waypoints=waypoints
        )

# WebSocket streaming endpoint
async def handle_transit_websocket(websocket: WebSocket, bus_id: int, token: Optional[str]):
    await websocket.accept()
    
    # 1. Authenticate Token
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing auth token")
        return
        
    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        return
        
    user_role = payload.get("role")
    user_bus_id = payload.get("bus_id")
    
    # 2. RBAC validation
    if user_role in ["student", "parent"] and user_bus_id and user_bus_id != bus_id:
        await websocket.send_json({
            "error": "Access Denied: You are not authorized to monitor this route."
        })
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized bus tracking")
        return

    # Send initial state immediately
    current_state = await broker.get_bus_telemetry(bus_id)
    if current_state:
        await websocket.send_json(current_state)

    # 3. Subscribe to real-time pub/sub stream
    queue = await broker.subscribe(f"channel:bus:{bus_id}")
    try:
        while True:
            # Wait for next telemetry update from background simulator
            raw_msg = await queue.get()
            if isinstance(raw_msg, str):
                data = json.loads(raw_msg)
            else:
                data = raw_msg
            await websocket.send_json(data)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket streaming error: {e}")
    finally:
        await broker.unsubscribe(f"channel:bus:{bus_id}", queue)

@router.websocket("/stream/{bus_id}")
async def transit_stream_route(websocket: WebSocket, bus_id: int, token: Optional[str] = Query(None)):
    await handle_transit_websocket(websocket, bus_id, token)
