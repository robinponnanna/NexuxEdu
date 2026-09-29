import uuid
import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from app.core.database import AsyncSessionLocal, TrackingSession, Bus, BusAssignment, Student, Parent, User
from app.core.config import settings
from app.core.security import decode_access_token
from app.api.auth import get_current_user_claims
from app.models.schemas import UserSecurityClaims

router = APIRouter(prefix="/tracking", tags=["Tracking & Fleet Intelligence"])

class CreateSessionRequest(BaseModel):
    busId: Optional[int] = Field(None, description="Bus ID to track")
    bus_id: Optional[int] = Field(None, description="Bus ID alias")
    ttlMinutes: Optional[int] = Field(1440, description="Session time-to-live in minutes (default 24h)")
    ttl_minutes: Optional[int] = Field(None, description="TTL minutes alias")

    def get_bus_id(self) -> int:
        bid = self.busId if self.busId is not None else self.bus_id
        if bid is None:
            raise ValueError("busId or bus_id is required")
        return bid

    def get_ttl_minutes(self) -> int:
        if self.ttl_minutes is not None:
            return self.ttl_minutes
        if self.ttlMinutes is not None:
            return self.ttlMinutes
        return 1440

class CreateSessionResponse(BaseModel):
    token: str
    trackingUrl: str
    expiresAt: str
    busId: int
    busNumber: Optional[str] = None
    routeName: Optional[str] = None

@router.post("/sessions", response_model=CreateSessionResponse)
async def create_tracking_session(
    payload: CreateSessionRequest,
    claims: Optional[UserSecurityClaims] = Depends(get_current_user_claims)
):
    """
    Admin generates a real-time driver tracking session link.
    """
    # RBAC check: only admin can generate tracking sessions
    if claims and claims.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only administrators can generate vehicle tracking links."
        )

    try:
        bus_id = payload.get_bus_id()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    ttl_minutes = payload.get_ttl_minutes()

    async with AsyncSessionLocal() as session:
        # Validate that bus exists
        res = await session.execute(select(Bus).where(Bus.id == bus_id))
        bus = res.scalar_one_or_none()
        if not bus:
            raise HTTPException(status_code=404, detail=f"Bus with ID {bus_id} not found.")

        # Deactivate any previous active sessions for this bus (optional, keeps it clean)
        # or leave multiple active
        token = str(uuid.uuid4())
        now = datetime.datetime.utcnow()
        expires_at = now + datetime.timedelta(minutes=ttl_minutes)

        tracking_session = TrackingSession(
            token=token,
            bus_id=bus_id,
            created_at=now,
            expires_at=expires_at,
            active=1,
            latest_latitude=bus.current_lat,
            latest_longitude=bus.current_lng,
            latest_accuracy=10.0,
            latest_timestamp=int(now.timestamp() * 1000)
        )
        session.add(tracking_session)
        await session.commit()

        base_url = (settings.PUBLIC_BASE_URL or "http://localhost:3000").rstrip("/")
        tracking_url = f"{base_url}/track?token={token}"

        return CreateSessionResponse(
            token=token,
            trackingUrl=tracking_url,
            expiresAt=expires_at.isoformat() + "Z",
            busId=bus.id,
            busNumber=bus.bus_number,
            routeName=bus.route_name
        )

async def _validate_token_internal(token: str):
    if not token:
        raise HTTPException(status_code=400, detail="Tracking token is required.")

    async with AsyncSessionLocal() as session:
        stmt = (
            select(TrackingSession, Bus)
            .join(Bus, TrackingSession.bus_id == Bus.id)
            .where(
                TrackingSession.token == token,
                TrackingSession.active == 1
            )
        )
        res = await session.execute(stmt)
        record = res.first()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid tracking token or session has been terminated."
            )

        ts, bus = record
        now = datetime.datetime.utcnow()
        if ts.expires_at < now:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="This tracking session has expired. Please request a new link from campus administration."
            )

        return {
            "valid": True,
            "token": ts.token,
            "busId": bus.id,
            "busNumber": bus.bus_number,
            "routeName": bus.route_name,
            "driverName": bus.driver_name,
            "driverPhone": bus.driver_phone,
            "expiresAt": ts.expires_at.isoformat() + "Z",
            "active": bool(ts.active),
            "latestLatitude": ts.latest_latitude or bus.current_lat,
            "latestLongitude": ts.latest_longitude or bus.current_lng
        }

@router.get("/sessions/validate")
async def validate_tracking_session_query(token: Optional[str] = Query(None)):
    """
    Validates a tracking session token via query parameter ?token=...
    """
    if not token:
        raise HTTPException(status_code=400, detail="Tracking token query parameter is required.")
    return await _validate_token_internal(token)

@router.get("/sessions/{token}")
async def validate_tracking_session_path(token: str):
    """
    Validates a tracking session token via path parameter /sessions/{token}
    """
    return await _validate_token_internal(token)

@router.get("/user-assigned-buses")
async def get_user_assigned_buses(claims: UserSecurityClaims = Depends(get_current_user_claims)):
    """
    Returns the list of bus IDs assigned to the authenticated user.
    Admins receive all active bus IDs.
    """
    async with AsyncSessionLocal() as session:
        if claims.role == "admin":
            res = await session.execute(select(Bus.id))
            bus_ids = [r[0] for r in res.all()]
            return {"role": claims.role, "busIds": bus_ids}

        # Query bus_assignments
        res = await session.execute(
            select(BusAssignment.bus_id)
            .where(BusAssignment.user_id == claims.user_id, BusAssignment.active == 1)
        )
        assigned_ids = [r[0] for r in res.all()]

        # If student and bus_id is in claims, ensure it's included
        if claims.bus_id and claims.bus_id not in assigned_ids:
            assigned_ids.append(claims.bus_id)

        # If parent, check ward's bus
        if claims.role == "parent" and claims.ward_id:
            student_res = await session.execute(
                select(Student.bus_id).where(Student.id == claims.ward_id)
            )
            ward_bus = student_res.scalar_one_or_none()
            if ward_bus and ward_bus not in assigned_ids:
                assigned_ids.append(ward_bus)

        return {"role": claims.role, "busIds": assigned_ids}

from fastapi import WebSocket, WebSocketDisconnect
from app.core.pubsub import broker
import json
import asyncio

async def handle_unified_websocket(websocket: WebSocket, token: Optional[str]):
    """
    Unified WebSocket endpoint at /ws?token=...:
    1. Driver mode: Validates tracking session token, accepts location packets,
       updates database, and broadcasts bus-location-update to room bus:<busId>.
    2. ERP User mode: Validates JWT session claims, finds user's assigned buses
       from bus_assignments, automatically joins rooms bus:<busId>, and streams
       live location updates.
    """
    await websocket.accept()

    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing authentication or tracking token")
        return

    # Check 1: Driver tracking session token
    async with AsyncSessionLocal() as session:
        stmt = (
            select(TrackingSession, Bus)
            .join(Bus, TrackingSession.bus_id == Bus.id)
            .where(TrackingSession.token == token, TrackingSession.active == 1)
        )
        res = await session.execute(stmt)
        record = res.first()

    if record:
        ts, bus = record
        now = datetime.datetime.utcnow()
        if ts.expires_at < now:
            await websocket.send_json({"error": "Tracking session has expired", "code": "SESSION_EXPIRED"})
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Tracking session expired")
            return

        bus_id = bus.id
        ts_id = ts.id

        # Send initial confirmation to driver
        await websocket.send_json({
            "type": "connection_ack",
            "role": "driver",
            "busId": bus_id,
            "busNumber": bus.bus_number,
            "routeName": bus.route_name,
            "status": "ready"
        })

        try:
            while True:
                data = await websocket.receive_json()
                msg_type = data.get("type")

                if msg_type == "location":
                    latitude = float(data.get("latitude"))
                    longitude = float(data.get("longitude"))
                    accuracy = float(data.get("accuracy", 10.0))
                    timestamp = data.get("timestamp") or int(datetime.datetime.utcnow().timestamp() * 1000)

                    # Update database
                    async with AsyncSessionLocal() as db:
                        # Update Bus
                        b_res = await db.execute(select(Bus).where(Bus.id == bus_id))
                        b = b_res.scalar_one_or_none()
                        if b:
                            b.current_lat = latitude
                            b.current_lng = longitude
                            b.last_updated = datetime.datetime.utcnow()

                        # Update TrackingSession
                        ts_res = await db.execute(select(TrackingSession).where(TrackingSession.id == ts_id))
                        cur_ts = ts_res.scalar_one_or_none()
                        if cur_ts:
                            cur_ts.latest_latitude = latitude
                            cur_ts.latest_longitude = longitude
                            cur_ts.latest_accuracy = accuracy
                            cur_ts.latest_timestamp = int(timestamp)
                        await db.commit()

                    # Real-time broadcast to room bus:<busId> and channel:bus:<busId>
                    broadcast_payload = {
                        "type": "bus-location-update",
                        "busId": bus_id,
                        "latitude": latitude,
                        "longitude": longitude,
                        "accuracy": accuracy,
                        "timestamp": timestamp,
                        "status": "Active"
                    }
                    await broker.broadcast_bus_location(bus_id, broadcast_payload)

                    # Send acknowledgment back to driver
                    await websocket.send_json({
                        "type": "location_ack",
                        "timestamp": timestamp,
                        "status": "recorded"
                    })
                elif msg_type == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": int(datetime.datetime.utcnow().timestamp() * 1000)
                    })
        except WebSocketDisconnect:
            pass
        except Exception as e:
            print(f"Driver WebSocket error for bus {bus_id}: {e}")
        return

    # Check 2: ERP User JWT Token
    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid authentication or tracking token")
        return

    user_role = payload.get("role")
    user_id = payload.get("user_id")

    assigned_bus_ids = []
    async with AsyncSessionLocal() as session:
        if user_role == "admin":
            b_res = await session.execute(select(Bus.id))
            assigned_bus_ids = [r[0] for r in b_res.all()]
        else:
            ba_res = await session.execute(
                select(BusAssignment.bus_id).where(BusAssignment.user_id == user_id, BusAssignment.active == 1)
            )
            assigned_bus_ids = [r[0] for r in ba_res.all()]

            if payload.get("bus_id") and payload.get("bus_id") not in assigned_bus_ids:
                assigned_bus_ids.append(payload.get("bus_id"))

            if user_role == "parent" and payload.get("ward_id"):
                w_res = await session.execute(select(Student.bus_id).where(Student.id == payload.get("ward_id")))
                ward_bus = w_res.scalar_one_or_none()
                if ward_bus and ward_bus not in assigned_bus_ids:
                    assigned_bus_ids.append(ward_bus)

    # Acknowledge user connection and subscribed buses
    await websocket.send_json({
        "type": "connection_ack",
        "role": user_role,
        "subscribedBuses": assigned_bus_ids
    })

    # Send current known state for each assigned bus immediately
    for bid in assigned_bus_ids:
        cur_state = await broker.get_bus_telemetry(bid)
        if cur_state:
            await websocket.send_json({
                "type": "bus-location-update",
                "busId": bid,
                "latitude": cur_state.get("lat"),
                "longitude": cur_state.get("lng"),
                "speed_kmh": cur_state.get("speed_kmh", 0.0),
                "status": cur_state.get("status", "Active"),
                **cur_state
            })

    # Subscribe to rooms bus:<busId> using a shared queue
    shared_queue = asyncio.Queue(maxsize=200)
    for bid in assigned_bus_ids:
        await broker.subscribe(f"bus:{bid}", queue=shared_queue)

    async def forward_stream():
        try:
            while True:
                msg = await shared_queue.get()
                if isinstance(msg, str):
                    await websocket.send_text(msg)
                else:
                    await websocket.send_json(msg)
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    async def client_listener():
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        except Exception:
            pass

    forward_task = asyncio.create_task(forward_stream())
    listener_task = asyncio.create_task(client_listener())

    done, pending = await asyncio.wait(
        [forward_task, listener_task],
        return_when=asyncio.FIRST_COMPLETED
    )

    for task in pending:
        task.cancel()

    for bid in assigned_bus_ids:
        await broker.unsubscribe(f"bus:{bid}", shared_queue)
