"use client";

import { useEffect, useMemo, useState } from "react";

type Reading = {
  sensor_id: string;
  temperature_c: number;
};

type Alert = {
  id: string;
  sensor_id: string;
  severity: "warning" | "critical";
  temperature_c: number;
  threshold_c: number;
  message: string;
  created_at: string;
};

type Snapshot = {
  device_count: number;
  online_count: number;
  warning_count: number;
  uptime_percent: number;
  latest_readings: Reading[];
  alerts: Alert[];
  frame?: {
    width: number;
    height: number;
    pixels_c: number[];
  };
};

const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

const trend = {
  L1: [38, 39, 39, 40, 41, 40, 42, 43, 44, 45, 45.6],
  L2: [46, 48, 49, 50, 52, 56, 60, 65, 66, 74, 78.4],
  L3: [41, 42, 42, 41, 43, 44, 46, 45, 48, 49, 47.8],
};

const demoFrame = createThermalFrame(24, 16);

const fallbackSnapshot: Snapshot = {
  device_count: 12,
  online_count: 12,
  warning_count: 2,
  uptime_percent: 99.4,
  latest_readings: [
    { sensor_id: "L1", temperature_c: 45.6 },
    { sensor_id: "L2", temperature_c: 78.4 },
    { sensor_id: "L3", temperature_c: 47.8 },
  ],
  alerts: [
    {
      id: "demo-alert",
      sensor_id: "L2",
      severity: "warning",
      temperature_c: 78.4,
      threshold_c: 70,
      message: "Phase L2 hotspot",
      created_at: "2026-07-28T10:18:02Z",
    },
  ],
  frame: { width: 24, height: 16, pixels_c: demoFrame },
};

function createThermalFrame(width: number, height: number): number[] {
  return Array.from({ length: width * height }, (_, index) => {
    const x = index % width;
    const y = Math.floor(index / width);
    const base = 28 + y * 0.65 + Math.sin(x * 0.72) * 2.8;
    const phase1 = 14 * Math.exp(-((x - 6) ** 2 + (y - 8) ** 2) / 18);
    const phase2 = 46 * Math.exp(-((x - 12) ** 2 + (y - 7) ** 2) / 13);
    const phase3 = 18 * Math.exp(-((x - 18) ** 2 + (y - 9) ** 2) / 20);
    return Number((base + phase1 + phase2 + phase3).toFixed(1));
  });
}

function thermalColor(value: number): string {
  const stops = [
    [20, [8, 32, 88]],
    [35, [0, 135, 180]],
    [50, [55, 190, 118]],
    [65, [247, 205, 45]],
    [80, [255, 91, 35]],
    [100, [255, 246, 218]],
  ] as const;
  for (let index = 1; index < stops.length; index += 1) {
    const [upperValue, upperColor] = stops[index];
    const [lowerValue, lowerColor] = stops[index - 1];
    if (value <= upperValue) {
      const ratio = Math.max(
        0,
        Math.min(1, (value - lowerValue) / (upperValue - lowerValue)),
      );
      const rgb = lowerColor.map((channel, colorIndex) =>
        Math.round(
          channel + (upperColor[colorIndex] - channel) * ratio,
        ),
      );
      return `rgb(${rgb.join(",")})`;
    }
  }
  return "rgb(255,246,218)";
}

function Sparkline({
  values,
  color,
}: {
  values: number[];
  color: string;
}) {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const points = values
    .map((value, index) => {
      const x = (index / (values.length - 1)) * 100;
      const y = 30 - ((value - min) / Math.max(1, max - min)) * 24;
      return `${x},${y}`;
    })
    .join(" ");
  return (
    <svg
      className="sparkline"
      viewBox="0 0 100 32"
      role="img"
      aria-label="Recent metric trend"
    >
      <polyline points={points} fill="none" stroke={color} strokeWidth="2" />
    </svg>
  );
}

function MetricCard({
  label,
  value,
  detail,
  kind,
  series,
}: {
  label: string;
  value: string;
  detail: string;
  kind: "device" | "warning" | "uptime";
  series: number[];
}) {
  const color = kind === "warning" ? "#f6a63b" : "#2dd4d7";
  return (
    <article className={`metric-card metric-${kind}`}>
      <div className="metric-symbol" aria-hidden="true">
        {kind === "device" ? "▰" : kind === "warning" ? "△" : "✓"}
      </div>
      <div>
        <strong>{value}</strong>
        <span>{label}</span>
      </div>
      <div className="metric-trend">
        <Sparkline values={series} color={color} />
        <small>{detail}</small>
      </div>
    </article>
  );
}

function HeatMap({
  frame,
}: {
  frame: NonNullable<Snapshot["frame"]>;
}) {
  const [selected, setSelected] = useState<number | null>(null);
  const hotspot = frame.pixels_c.reduce(
    (best, value, index) =>
      value > best.value ? { value, index } : best,
    { value: Number.NEGATIVE_INFINITY, index: 0 },
  );
  return (
    <div className="thermal-stage">
      <div
        className="thermal-grid"
        style={{
          gridTemplateColumns: `repeat(${frame.width}, minmax(0, 1fr))`,
        }}
        role="grid"
        aria-label="Live thermal camera frame"
      >
        {frame.pixels_c.map((value, index) => (
          <button
            className={`thermal-cell ${
              index === hotspot.index ? "hotspot" : ""
            }`}
            key={`${index}-${value}`}
            onClick={() => setSelected(index)}
            style={{ backgroundColor: thermalColor(value) }}
            aria-label={`Pixel ${index + 1}: ${value.toFixed(1)} degrees Celsius`}
            title={`${value.toFixed(1)}°C`}
          />
        ))}
      </div>
      <div className="phase-labels" aria-hidden="true">
        <span>L1</span>
        <span>L2</span>
        <span>L3</span>
      </div>
      <div className="hotspot-callout">
        <span>PHASE L2</span>
        <strong>
          {(selected === null
            ? hotspot.value
            : frame.pixels_c[selected]
          ).toFixed(1)}
          °C
        </strong>
      </div>
      <div className="thermal-legend" aria-label="Temperature scale">
        <span>100°</span>
        <i />
        <span>20°</span>
      </div>
    </div>
  );
}

function TrendChart({ latest }: { latest: Reading[] }) {
  const width = 760;
  const height = 190;
  const toPoints = (values: number[]) =>
    values
      .map((value, index) => {
        const x = 32 + (index / (values.length - 1)) * (width - 54);
        const y = height - 24 - ((value - 20) / 80) * (height - 44);
        return `${x},${y}`;
      })
      .join(" ");
  const colors = { L1: "#39d7d9", L2: "#ff7a45", L3: "#5da9ff" };
  return (
    <div className="chart-wrap">
      <svg
        className="trend-chart"
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label="One-hour temperature trend for phases L1, L2 and L3"
      >
        {[20, 40, 60, 80, 100].map((tick) => {
          const y = height - 24 - ((tick - 20) / 80) * (height - 44);
          return (
            <g key={tick}>
              <line x1="32" y1={y} x2={width - 22} y2={y} />
              <text x="3" y={y + 4}>
                {tick}
              </text>
            </g>
          );
        })}
        {(Object.keys(trend) as Array<keyof typeof trend>).map((phase) => (
          <polyline
            key={phase}
            points={toPoints(trend[phase])}
            fill="none"
            stroke={colors[phase]}
            strokeWidth={phase === "L2" ? "3" : "2"}
          />
        ))}
      </svg>
      <div className="chart-legend">
        {latest.map((reading) => (
          <span key={reading.sensor_id}>
            <i className={`legend-${reading.sensor_id.toLowerCase()}`} />
            {reading.sensor_id}
            <strong>{reading.temperature_c.toFixed(1)}°C</strong>
          </span>
        ))}
      </div>
    </div>
  );
}

export default function Home() {
  const [snapshot, setSnapshot] = useState<Snapshot>(fallbackSnapshot);
  const [mode, setMode] = useState<"demo" | "live">("demo");
  const [clock, setClock] = useState("10:24:36");

  useEffect(() => {
    const timer = window.setInterval(
      () => setClock(new Date().toLocaleTimeString()),
      1000,
    );
    let socket: WebSocket | undefined;

    const load = async () => {
      try {
        const response = await fetch(`${API_URL}/api/v1/dashboard`, {
          signal: AbortSignal.timeout(2500),
        });
        if (!response.ok) return;
        setSnapshot((await response.json()) as Snapshot);
        setMode("live");
      } catch {
        setMode("demo");
      }
    };

    void load();
    try {
      const socketUrl = API_URL.replace(/^http/, "ws");
      socket = new WebSocket(`${socketUrl}/ws/live`);
      socket.onmessage = (event) => {
        const next = JSON.parse(event.data) as Snapshot;
        if (next.latest_readings) {
          setSnapshot(next);
          setMode("live");
        }
      };
    } catch {}

    return () => {
      window.clearInterval(timer);
      socket?.close();
    };
  }, []);

  const primaryAlert = snapshot.alerts[0] ?? fallbackSnapshot.alerts[0];
  const frame = snapshot.frame ?? fallbackSnapshot.frame;
  const onlineLabel = useMemo(
    () =>
      snapshot.online_count === snapshot.device_count
        ? "All online"
        : `${snapshot.online_count} online`,
    [snapshot],
  );

  return (
    <main className="dashboard-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">T</span>
          <strong>PREDICTIVE THERMAL GUARD</strong>
          <span className={`live-state ${mode}`}>
            <i />
            {mode === "live" ? "LIVE" : "DEMO"}
          </span>
        </div>
        <div className="topbar-meta">
          <span>{clock}</span>
          <span>{new Date().toLocaleDateString()}</span>
          <button aria-label="Open system settings">⚙</button>
        </div>
      </header>

      <div className="dashboard-grid">
        <section className="metrics" aria-label="Fleet status">
          <MetricCard
            label="DEVICES"
            value={String(snapshot.device_count)}
            detail={onlineLabel}
            kind="device"
            series={[7, 8, 8, 9, 10, 10, 11, 12]}
          />
          <MetricCard
            label="WARNINGS"
            value={String(snapshot.warning_count)}
            detail="Last 24h"
            kind="warning"
            series={[1, 0, 1, 1, 0, 1, 2, 2]}
          />
          <MetricCard
            label="UPTIME"
            value={`${snapshot.uptime_percent.toFixed(1)}%`}
            detail="Last 30d"
            kind="uptime"
            series={[98, 99, 99, 98.7, 99.2, 99.4, 99.3, 99.4]}
          />
        </section>

        <section className="panel thermal-panel">
          <div className="panel-heading">
            <h1>LIVE THERMAL MAP</h1>
            <span>EM-PANEL-1 · updated {clock}</span>
          </div>
          {frame && <HeatMap frame={frame} />}
        </section>

        <aside className="side-stack">
          <section className="panel alert-panel">
            <div className="eyebrow">PRIORITIZED ALERT</div>
            <div className="alert-title">
              <span className="warning-icon">!</span>
              <div>
                <h2>{primaryAlert.message.toUpperCase()}</h2>
                <strong>{primaryAlert.temperature_c.toFixed(1)}°C</strong>
              </div>
              <span className="warning-badge">
                {primaryAlert.severity.toUpperCase()}
              </span>
            </div>
            <dl className="alert-facts">
              <div>
                <dt>Sensor</dt>
                <dd>{primaryAlert.sensor_id}</dd>
              </div>
              <div>
                <dt>Threshold</dt>
                <dd>&gt; {primaryAlert.threshold_c.toFixed(1)}°C</dd>
              </div>
              <div>
                <dt>Delta above limit</dt>
                <dd>
                  +
                  {(
                    primaryAlert.temperature_c - primaryAlert.threshold_c
                  ).toFixed(1)}
                  °C
                </dd>
              </div>
              <div>
                <dt>Predicted 30m trend</dt>
                <dd className="rising">Rising ↑</dd>
              </div>
            </dl>
            <p className="recommendation">
              Recommendation: isolate load and schedule inspection.
            </p>
          </section>

          <section className="panel connectivity">
            <div className="panel-heading">
              <h2>DEVICE CONNECTIVITY</h2>
            </div>
            <div className="protocol-mark">MQTT</div>
            <dl>
              <div>
                <dt>Status</dt>
                <dd className="connected">CONNECTED</dd>
              </div>
              <div>
                <dt>Broker</dt>
                <dd>mqtt://broker:1883</dd>
              </div>
              <div>
                <dt>HTTP API</dt>
                <dd>READY</dd>
              </div>
              <div>
                <dt>QoS / Keep alive</dt>
                <dd>1 / 60s</dd>
              </div>
            </dl>
          </section>
        </aside>

        <section className="panel trend-panel">
          <div className="panel-heading">
            <h2>TEMPERATURE TREND</h2>
            <div className="range-tabs" aria-label="Chart time range">
              <button className="active">1H</button>
              <button>6H</button>
              <button>24H</button>
              <button>7D</button>
            </div>
          </div>
          <TrendChart latest={snapshot.latest_readings} />
        </section>

        <section className="panel details-panel">
          <div className="panel-heading">
            <h2>DEVICE DETAILS</h2>
          </div>
          <dl>
            <div>
              <dt>Device ID</dt>
              <dd>EM-PANEL-1</dd>
            </div>
            <div>
              <dt>Location</dt>
              <dd>Electrical Room A</dd>
            </div>
            <div>
              <dt>Controller</dt>
              <dd>ESP32</dd>
            </div>
            <div>
              <dt>Sensors</dt>
              <dd>3 × MLX90614</dd>
            </div>
            <div>
              <dt>I²C multiplexer</dt>
              <dd>TCA9548A</dd>
            </div>
            <div>
              <dt>Sample rate</dt>
              <dd>1 second</dd>
            </div>
          </dl>
        </section>
      </div>
    </main>
  );
}
