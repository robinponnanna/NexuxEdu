import asyncio
import websockets
import json
import datetime
import urllib.request

async def test_multi_tick():
    # 1. Login as admin
    login_req = urllib.request.Request(
        "http://127.0.0.1:8000/api/v1/auth/login",
        data=json.dumps({"email": "admin@campus.edu", "password": "password123"}).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(login_req) as resp:
        admin_tok = json.loads(resp.read().decode())["access_token"]

    # 2. Create tracking session
    sess_req = urllib.request.Request(
        "http://127.0.0.1:8000/api/tracking/sessions",
        data=json.dumps({"busId": 1, "ttlMinutes": 60}).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {admin_tok}"}
    )
    with urllib.request.urlopen(sess_req) as resp:
        session_info = json.loads(resp.read().decode())
        driver_token = session_info["token"]

    print(f"Tracking session established: token={driver_token}")

    # 3. Connect driver and admin WebSocket clients
    driver_ws = await websockets.connect(f"ws://127.0.0.1:8000/ws?token={driver_token}")
    admin_ws = await websockets.connect(f"ws://127.0.0.1:8000/ws?token={admin_tok}")

    ack_d = await driver_ws.recv()
    ack_a = json.loads(await admin_ws.recv())
    buses_count = len(ack_a.get("subscribedBuses", []))

    # Drain initial state messages
    for _ in range(buses_count):
        await admin_ws.recv()

    print("Initial connections ready. Beginning 2-second location transmission...")

    base_lat, base_lng = 28.6185, 77.2148
    for i in range(3):
        cur_lat = round(base_lat + i * 0.0005, 6)
        cur_lng = round(base_lng + i * 0.0005, 6)
        spd = 30.0 + i * 4.0
        print(f"\n[Tick {i+1}] Driver transmitting: lat={cur_lat}, lng={cur_lng}, speed={spd} km/h...")
        await driver_ws.send(json.dumps({
            "type": "location",
            "latitude": cur_lat,
            "longitude": cur_lng,
            "accuracy": 3.8,
            "speed_kmh": spd,
            "timestamp": int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)
        }))
        d_ack = await driver_ws.recv()
        print(f"  [Driver ACK received]: status={json.loads(d_ack).get('status')}")

        received = False
        while True:
            msg = json.loads(await asyncio.wait_for(admin_ws.recv(), timeout=3.0))
            if msg.get("type") == "bus-location-update" and msg.get("busId") == 1 and msg.get("latitude") == cur_lat:
                print(f"  [Admin Leaflet Map received]: lat={msg.get('latitude')}, lng={msg.get('longitude')}, speed={msg.get('speed_kmh')} km/h, accuracy={msg.get('accuracy')}m")
                received = True
                break
        assert received, f"Admin did not receive tick {i+1}"
        await asyncio.sleep(2)

    await driver_ws.close()
    await admin_ws.close()
    print("\n🎉 ALL 2-SECOND TICKS RECEIVED AND CONFIRMED BY LEAFLET MAP!")

if __name__ == "__main__":
    asyncio.run(test_multi_tick())
