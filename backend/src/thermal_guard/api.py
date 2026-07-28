"""FastAPI route definitions."""

from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect

from .models import (
    Alert,
    DashboardSnapshot,
    DeviceSummary,
    DeviceTelemetry,
    SensorReading,
    ThermalFrame,
)
from .realtime import LiveHub
from .service import ThermalGuardService

router = APIRouter()


def get_service(request: Request) -> ThermalGuardService:
    return cast(ThermalGuardService, request.app.state.service)


def get_hub(request: Request) -> LiveHub:
    return cast(LiveHub, request.app.state.hub)


Service = Annotated[ThermalGuardService, Depends(get_service)]


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "predictive-thermal-guard"}


@router.post("/api/v1/readings", response_model=Alert | None)
async def ingest_reading(reading: SensorReading, service: Service) -> Alert | None:
    return await service.ingest_reading(reading)


@router.post("/api/v1/telemetry", response_model=list[Alert])
async def ingest_telemetry(telemetry: DeviceTelemetry, service: Service) -> list[Alert]:
    return await service.ingest_telemetry(telemetry)


@router.post("/api/v1/frames", response_model=Alert | None)
async def ingest_frame(frame: ThermalFrame, service: Service) -> Alert | None:
    return await service.ingest_frame(frame)


@router.get("/api/v1/devices", response_model=list[DeviceSummary])
def list_devices(service: Service) -> list[DeviceSummary]:
    return service.repository.list_devices()


@router.get("/api/v1/alerts", response_model=list[Alert])
def list_alerts(service: Service, limit: int = 50) -> list[Alert]:
    return service.repository.list_alerts(limit=min(max(limit, 1), 200))


@router.get("/api/v1/dashboard", response_model=DashboardSnapshot)
def dashboard(service: Service) -> DashboardSnapshot:
    return service.dashboard()


@router.websocket("/ws/live")
async def live(websocket: WebSocket) -> None:
    hub: LiveHub = websocket.app.state.hub
    service: ThermalGuardService = websocket.app.state.service
    await hub.connect(websocket)
    await websocket.send_json(service.dashboard().model_dump(mode="json"))
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        hub.disconnect(websocket)
