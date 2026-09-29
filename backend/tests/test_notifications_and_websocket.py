import pytest
import asyncio
from fastapi import FastAPI, WebSocket
from httpx import AsyncClient, ASGITransport
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.pubsub import broker
from app.core.security import create_access_token
from app.core.notifications import NotificationCollector
from app.api.clash import handle_notifications_websocket, router as clash_router

ws_app = FastAPI()
ws_app.include_router(clash_router, prefix="/api/v1")

@ws_app.websocket("/ws/notifications")
async def route_ws_notifications(websocket: WebSocket, token: str = None, as_admin: bool = False):
    await handle_notifications_websocket(websocket, token, as_admin)

@pytest.mark.asyncio
async def test_notification_collector_rollback_guarantee():
    """
    Amendment 2: A rolled-back transition must never produce a live notification.
    Broker pushes must happen strictly AFTER a successful commit.
    """
    collector = NotificationCollector()
    channel = "channel:user:999"

    # Subscribe a listener to the channel
    queue = await broker.subscribe(channel)

    try:
        # Simulate a transaction with pending notifications
        collector.queue_publish(channel, {"type": "TEST_ALERT", "title": "Simulated Alert"})
        assert len(collector._pending) == 1

        # Simulate a database failure / rollback:
        # When transaction fails, collector.clear() is called instead of flush()
        collector.clear()
        assert len(collector._pending) == 0

        # Assert zero messages delivered to subscriber
        assert queue.empty() is True

        # Now simulate a successful commit and flush
        collector.queue_publish(channel, {"type": "COMMITTED_ALERT", "title": "Real Notification"})
        flushed_count = await collector.flush()
        assert flushed_count == 1

        # Assert message is now delivered
        assert not queue.empty()
        delivered = await queue.get()
        assert "COMMITTED_ALERT" in delivered

    finally:
        await broker.unsubscribe(channel, queue)

def test_websocket_auth_and_channel_isolation():
    """
    Amendment 7: WebSocket channel must be derived from verified JWT, never client input.
    Only admins may subscribe to the admin channel.
    """
    client = TestClient(ws_app)

    # 1. Missing token -> WS_1008_POLICY_VIOLATION
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/ws/notifications") as ws:
            ws.receive_json()
    assert exc.value.code == 1008

    # 2. Invalid token -> WS_1008_POLICY_VIOLATION
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/ws/notifications?token=invalid_jwt_token") as ws:
            ws.receive_json()
    assert exc.value.code == 1008

    # 3. Valid Student token connects and gets channel:user:{id}
    student_token = create_access_token({"sub": "student@nexusedu.com", "user_id": 42, "role": "student"})
    with client.websocket_connect(f"/ws/notifications?token={student_token}") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "CONNECTED"
        assert msg["channel"] == "channel:user:42"
        assert msg["user_id"] == 42
        assert msg["role"] == "student"

    # 4. Student attempting as_admin=true -> Rejected / Closed with 1008
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/ws/notifications?token={student_token}&as_admin=true") as ws:
            ws.receive_json()
            ws.receive_json()
    assert exc.value.code == 1008

    # 5. Admin connecting with as_admin=true -> Allowed to join channel:admin
    admin_token = create_access_token({"sub": "admin@nexusedu.com", "user_id": 1, "role": "admin"})
    with client.websocket_connect(f"/ws/notifications?token={admin_token}&as_admin=true") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "CONNECTED"
        assert msg["channel"] == "channel:admin"
        assert msg["user_id"] == 1
        assert msg["role"] == "admin"
