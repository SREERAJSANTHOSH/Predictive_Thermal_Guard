"""Application factory and executable ASGI app."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .analytics import ThermalAnalyzer
from .api import router
from .config import Settings, get_settings
from .mqtt import MqttAdapter
from .realtime import LiveHub
from .service import ThermalGuardService
from .storage import Repository


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()
    hub = LiveHub()
    repository = Repository(resolved.database_path)
    analyzer = ThermalAnalyzer(resolved)
    service = ThermalGuardService(repository, analyzer, broadcaster=hub.broadcast)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        del app
        repository.initialize()
        adapter: MqttAdapter | None = None
        if resolved.mqtt_enabled:
            adapter = MqttAdapter(resolved, service, asyncio.get_running_loop())
            adapter.start()
        yield
        if adapter is not None:
            adapter.stop()

    app = FastAPI(
        title="Predictive Thermal Guard API",
        version="2.0.0",
        description="HTTP/MQTT telemetry, thermal analytics, alerts, and live updates.",
        lifespan=lifespan,
    )
    app.state.hub = hub
    app.state.service = service
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()
