# Predictive Thermal Guard API

FastAPI service for HTTP and MQTT telemetry ingestion, SQLite persistence,
thermal-frame hotspot extraction, adaptive anomaly detection, cause-labelled
alerts, and live WebSocket updates.

This service detects anomalies. It does not currently forecast future
temperatures.

Run from this directory:

```bash
pip install -e '.[dev]'
uvicorn thermal_guard.main:app --reload
```

The OpenAPI interface is available at `http://localhost:8000/docs`.
