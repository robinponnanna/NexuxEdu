import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import init_db
from app.services.seed_data import seed_database_if_empty
from app.services.seed_academic_data import seed_academic_support_data
from app.services.transit_simulator import transit_simulator
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.transit import router as transit_router, handle_transit_websocket
from app.api.erp import router as erp_router
from app.api.student_academic import router as student_academic_router
from app.api.tracking import router as tracking_router, handle_unified_websocket
from fastapi import WebSocket, Query
from fastapi.responses import HTMLResponse
from typing import Optional
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Database tables and seed demo records
    await init_db()
    await seed_database_if_empty()
    await seed_academic_support_data()
    # Start live transit telemetry simulator
    await transit_simulator.start()
    yield
    # Shutdown: Stop transit simulator
    await transit_simulator.stop()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Next-Gen Smart Campus ERP with RBAC-Grounded AI & Live Transit Telemetry",
    lifespan=lifespan
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(chat_router, prefix=settings.API_V1_STR)
app.include_router(transit_router, prefix=settings.API_V1_STR)
app.include_router(erp_router, prefix=settings.API_V1_STR)
app.include_router(student_academic_router, prefix=settings.API_V1_STR)
# Mount Tracking Router under both /api and /api/v1 for universal routing
app.include_router(tracking_router, prefix="/api")
app.include_router(tracking_router, prefix=settings.API_V1_STR)

# Top-level unified WebSocket endpoint at /ws?token=...
@app.websocket("/ws")
async def ws_unified_endpoint(websocket: WebSocket, token: Optional[str] = Query(None)):
    await handle_unified_websocket(websocket, token)

# Top-level WebSocket alias as specified in SYSTEM_DESIGN: /ws/transit/{bus_id}
@app.websocket("/ws/transit/{bus_id}")
async def ws_transit_alias(websocket: WebSocket, bus_id: int, token: Optional[str] = Query(None)):
    await handle_transit_websocket(websocket, bus_id, token)

# Standalone driver tracking page served directly on backend port
@app.get("/track", response_class=HTMLResponse)
async def serve_driver_track_page():
    track_file = os.path.join(os.path.dirname(__file__), "..", "static", "track.html")
    if os.path.exists(track_file):
        with open(track_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Driver Tracking Portal</h1><p>Static track.html file not found.</p>", status_code=404)

@app.get("/health")
@app.get(f"{settings.API_V1_STR}/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION
    }

