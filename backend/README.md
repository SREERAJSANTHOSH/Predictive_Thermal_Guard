# Predictive Thermal Guard API

FastAPI service for HTTP and MQTT telemetry ingestion, SQLite persistence,
thermal-frame hotspot extraction, adaptive anomaly detection, alerts, and live
WebSocket updates.

Run from this directory:

```bash
pip install -e '.[dev]'
uvicorn thermal_guard.main:app --reload
```

The OpenAPI interface is available at `http://localhost:8000/docs`.
