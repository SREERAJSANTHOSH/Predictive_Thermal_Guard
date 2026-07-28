# Results status

## Verified software evidence

The current continuous-integration workflow checks:

| Layer | Check | Status at version 0.2 preparation |
|---|---|---|
| Backend | Ruff lint | Automated in CI |
| Backend | Strict Mypy | Automated in CI |
| Backend | Pytest with coverage | Automated in CI |
| Dashboard | ESLint and TypeScript | Automated in CI |
| Dashboard | Thermal utility tests | Automated in CI |
| Dashboard | Next.js production build | Automated in CI |
| Firmware | PlatformIO ESP32 build | Automated in CI |

The status for a release should link to that release's GitHub Actions run.

## Hardware results

No calibrated hardware dataset is committed yet.

| Metric | Absolute detector | Adaptive + absolute detector |
|---|---:|---:|
| Sensor MAE | Pending | Pending |
| Sensor RMSE | Pending | Pending |
| Precision | Pending | Pending |
| Recall | Pending | Pending |
| F1 score | Pending | Pending |
| Mean detection delay | Pending | Pending |
| False alarms per hour | Pending | Pending |
| Unique packet delivery | Pending | Pending |
| 95th-percentile latency | Pending | Pending |

Do not replace `Pending` values with dashboard fixtures or simulator output.
The 78.4 °C hotspot and other demo values exist only to exercise the interface.
