import asyncio
import json
import urllib.request
import websockets
import datetime

BASE_HTTP = "http://127.0.0.1:8000"
BASE_WS = "ws://127.0.0.1:8000"

async def test_entire_tracking_pipeline():
    print("==================================================")
    print("STEP 1: Admin Authentication")
    print("==================================================")
    # 1. Login as Admin
    login_req = urllib.request.Request(
        f"{BASE_HTTP}/api/v1/auth/login",
        data=json.dumps({"email": "admin@campus.edu", "password": "password123"}).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(login_req) as resp:
        login_data = json.loads(resp.read().decode())
        admin_token = login_data["access_token"]
        print(f"✓ Admin Logged In: {login_data['user']['name']} ({login_data['user']['role']})")

    # 1b. Login as Student (Jane Doe, assigned to Bus 1)
    student_req = urllib.request.Request(
        f"{BASE_HTTP}/api/v1/auth/login",
        data=json.dumps({"email": "student@campus.edu", "password": "password123"}).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(student_req) as resp:
        student_data = json.loads(resp.read().decode())
        student_token = student_data["access_token"]
        print(f"✓ Student Logged In: {student_data['user']['name']} (bus_id={student_data['user'].get('bus_id')})")

    print("\n==================================================")
    print("STEP 2: Admin Link Generation (POST /api/tracking/sessions)")
    print("==================================================")
    create_session_req = urllib.request.Request(
        f"{BASE_HTTP}/api/tracking/sessions",
        data=json.dumps({"busId": 1, "ttlMinutes": 1440}).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {admin_token}"
        }
    )
    with urllib.request.urlopen(create_session_req) as resp:
        session_data = json.loads(resp.read().decode())
        driver_token = session_data["token"]
        tracking_url = session_data["trackingUrl"]
        print(f"✓ Tracking Session Created!")
        print(f"  - Token: {driver_token}")
        print(f"  - Bus: {session_data['busNumber']} (ID: {session_data['busId']})")
        print(f"  - Tracking URL: {tracking_url}")
        print(f"  - Expires At: {session_data['expiresAt']}")

    print("\n==================================================")
    print("STEP 3: Public Token Validation (GET /api/tracking/sessions/validate)")
    print("==================================================")
    validate_req = urllib.request.Request(
        f"{BASE_HTTP}/api/tracking/sessions/validate?token={driver_token}"
    )
    with urllib.request.urlopen(validate_req) as resp:
        validation_data = json.loads(resp.read().decode())
        assert validation_data["valid"] is True
        print(f"✓ Session Token Validated: Bus {validation_data['busNumber']} on {validation_data['routeName']}")

    print("\n==================================================")
    print("STEP 4: Real-time WebSocket Ingestion & User Subscriptions")
    print("==================================================")

    # Connect Student WebSocket to /ws?token=<student_token>
    student_ws_url = f"{BASE_WS}/ws?token={student_token}"
    driver_ws_url = f"{BASE_WS}/ws?token={driver_token}"

    print("Connecting Student WebSocket...")
    async with websockets.connect(student_ws_url) as student_ws:
        student_ack = json.loads(await student_ws.recv())
        print(f"✓ Student WebSocket connected: {student_ack}")

        # Connect Driver WebSocket to /ws?token=<driver_token>
        print("Connecting Driver WebSocket...")
        async with websockets.connect(driver_ws_url) as driver_ws:
            driver_ack = json.loads(await driver_ws.recv())
            print(f"✓ Driver WebSocket connected: {driver_ack}")

            # Driver sends GPS location update
            test_lat = 28.618521
            test_lng = 77.214892
            test_time = int(datetime.datetime.utcnow().timestamp() * 1000)

            location_payload = {
                "type": "location",
                "latitude": test_lat,
                "longitude": test_lng,
                "accuracy": 9.2,
                "timestamp": test_time
            }

            print(f"Driver sending location: lat={test_lat}, lng={test_lng}...")
            await driver_ws.send(json.dumps(location_payload))

            # Driver receives ack
            driver_resp = json.loads(await driver_ws.recv())
            print(f"✓ Driver received acknowledgment: {driver_resp}")

            # Student receives broadcast update in room bus:1
            print("Listening for Student broadcast...")
            broadcast_received = False
            # Read messages until we get bus-location-update for test coord
            for _ in range(5):
                msg = json.loads(await asyncio.wait_for(student_ws.recv(), timeout=5.0))
                if msg.get("type") == "bus-location-update" and msg.get("latitude") is not None:
                    if abs(float(msg.get("latitude")) - test_lat) < 0.0001:
                        broadcast_received = True
                        print("✓ Student successfully received real-time bus-location-update event!")
                        break

            assert broadcast_received, "Student did not receive real-time bus-location-update!"

    print("\n==================================================")
    print("🎉 ALL TESTS PASSED! REAL-TIME BUS TRACKING FULLY OPERATIONAL!")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(test_entire_tracking_pipeline())
