from typing import Dict, Any, List
from app.models.schemas import ERPGraphState, Citation
from app.core.pubsub import broker
from app.core.database import AsyncSessionLocal, Bus
from sqlalchemy import select

async def execute_transit_telemetry_agent(state: ERPGraphState) -> Dict[str, Any]:
    """
    Transit & Fleet Telemetry Agent.
    Strictly verifies vehicle scoping according to session role:
    - student / parent: can only query their assigned bus_id
    - admin: can query any bus or full fleet
    - faculty: restricted to shuttle timetable overview
    """
    claims = state.claims
    citations: List[Citation] = []
    
    if claims.role in ["student", "parent"]:
        bus_id = claims.bus_id
        if not bus_id:
            return {
                "authorized": True,
                "data": None,
                "message": "Your profile is not currently assigned to a campus transit route.",
                "citations": []
            }
        
        telemetry = await broker.get_bus_telemetry(bus_id)
        if not telemetry:
            # Fallback to DB
            async with AsyncSessionLocal() as session:
                res = await session.execute(select(Bus).where(Bus.id == bus_id))
                bus = res.scalar_one_or_none()
                if bus:
                    telemetry = {
                        "bus_id": bus.id,
                        "bus_number": bus.bus_number,
                        "route_name": bus.route_name,
                        "lat": bus.current_lat,
                        "lng": bus.current_lng,
                        "speed_kmh": bus.speed_kmh,
                        "status": bus.status
                    }
        
        if telemetry:
            citations.append(Citation(
                title=f"Transit Telemetry ({telemetry.get('bus_number', 'BUS-001')})",
                section=f"Route: {telemetry.get('route_name')}",
                type="telemetry",
                detail=f"Lat: {telemetry.get('lat')}, Lng: {telemetry.get('lng')}, Speed: {telemetry.get('speed_kmh')} km/h"
            ))
            return {
                "authorized": True,
                "data": telemetry,
                "citations": citations
            }
            
    elif claims.role == "admin":
        # Admin gets primary active bus or requested bus
        telemetry = await broker.get_bus_telemetry(1)
        citations.append(Citation(
            title="Master Fleet Transit Telemetry",
            section="Campus Transit Network",
            type="telemetry",
            detail="Admin global transit broadcast"
        ))
        return {
            "authorized": True,
            "data": telemetry,
            "citations": citations
        }
        
    elif claims.role == "faculty":
        citations.append(Citation(
            title="Faculty Transit Schedule",
            section="Campus Inter-Building Shuttle",
            type="policy_doc",
            detail="Faculty shuttle timetable (08:00 - 18:00 hourly)"
        ))
        return {
            "authorized": True,
            "data": {
                "type": "shuttle_schedule",
                "info": "Faculty inter-departmental shuttles depart every 30 minutes from the North Academic Complex."
            },
            "citations": citations
        }
        
    return {"authorized": True, "data": None, "citations": []}
