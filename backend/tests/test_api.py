from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ingests_generic_sensor_reading(client: TestClient) -> None:
    response = client.post(
        "/api/v1/readings",
        json={
            "device_id": "panel-a",
            "sensor_id": "L1",
            "temperature_c": 42.5,
        },
    )
    assert response.status_code == 200
    assert response.json() is None
    dashboard = client.get("/api/v1/dashboard").json()
    assert dashboard["device_count"] == 1
    assert dashboard["latest_readings"][0]["sensor_id"] == "L1"


def test_creates_alert_above_absolute_threshold(client: TestClient) -> None:
    response = client.post(
        "/api/v1/readings",
        json={
            "device_id": "panel-a",
            "sensor_id": "L2",
            "temperature_c": 78.4,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["severity"] == "warning"
    assert payload["sensor_id"] == "L2"


def test_rejects_malformed_frame(client: TestClient) -> None:
    response = client.post(
        "/api/v1/frames",
        json={
            "device_id": "camera-a",
            "width": 2,
            "height": 2,
            "pixels_c": [31.0, 32.0],
        },
    )
    assert response.status_code == 422


def test_ingests_thermal_camera_frame(client: TestClient) -> None:
    response = client.post(
        "/api/v1/frames",
        json={
            "device_id": "camera-a",
            "camera_id": "mlx90640",
            "width": 2,
            "height": 2,
            "pixels_c": [31.0, 32.0, 91.5, 35.0],
        },
    )
    assert response.status_code == 200
    assert response.json()["severity"] == "critical"
    dashboard = client.get("/api/v1/dashboard").json()
    assert dashboard["frame"]["maximum_c"] == 91.5
    assert dashboard["frame"]["hotspot_x"] == 0
    assert dashboard["frame"]["hotspot_y"] == 1


def test_ingests_device_envelope(client: TestClient) -> None:
    response = client.post(
        "/api/v1/telemetry",
        json={
            "device_id": "esp32-panel",
            "firmware_version": "2.0.0",
            "uptime_s": 100,
            "rssi_dbm": -54,
            "readings": [
                {
                    "device_id": "esp32-panel",
                    "sensor_id": "L1",
                    "temperature_c": 40.1,
                },
                {
                    "device_id": "esp32-panel",
                    "sensor_id": "L2",
                    "temperature_c": 41.3,
                },
            ],
        },
    )
    assert response.status_code == 200
    assert response.json() == []
    devices = client.get("/api/v1/devices").json()
    assert devices[0]["firmware_version"] == "2.0.0"
