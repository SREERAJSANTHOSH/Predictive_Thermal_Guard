#!/usr/bin/env python3
"""Publish deterministic point readings and thermal frames to a running API."""

import argparse
import json
import math
import time
import urllib.request


def post(url: str, path: str, payload: dict[str, object]) -> None:
    request = urllib.request.Request(
        f"{url.rstrip('/')}{path}",
        data=json.dumps(payload).encode(),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        if response.status >= 300:
            raise RuntimeError(f"API returned {response.status}")


def frame(cycle: int, width: int = 24, height: int = 16) -> list[float]:
    pixels: list[float] = []
    for y in range(height):
        for x in range(width):
            base = 29 + y * 0.5 + math.sin((x + cycle) * 0.5)
            hotspot = 47 * math.exp(-((x - 12) ** 2 + (y - 7) ** 2) / 15)
            pixels.append(round(base + hotspot, 2))
    return pixels


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--cycles", type=int, default=120)
    parser.add_argument("--interval", type=float, default=1.0)
    args = parser.parse_args()

    for cycle in range(args.cycles):
        readings = [
            {
                "device_id": "EM-PANEL-1",
                "sensor_id": phase,
                "temperature_c": round(base + math.sin(cycle / 8) * 0.8, 2),
                "ambient_c": 29.0,
            }
            for phase, base in (("L1", 45.6), ("L2", 71 + cycle * 0.08), ("L3", 47.8))
        ]
        post(
            args.api,
            "/api/v1/telemetry",
            {
                "device_id": "EM-PANEL-1",
                "firmware_version": "simulator-0.2",
                "uptime_s": cycle,
                "rssi_dbm": -52,
                "readings": readings,
            },
        )
        post(
            args.api,
            "/api/v1/frames",
            {
                "device_id": "THERMAL-CAM-1",
                "camera_id": "simulated-camera",
                "width": 24,
                "height": 16,
                "pixels_c": frame(cycle),
            },
        )
        print(f"published cycle {cycle + 1}/{args.cycles}")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
