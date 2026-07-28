# Engineering decisions

This file records decisions from the current research-oriented revision
onward. It is not a reconstruction of earlier activity.

## 2026-07-28 — Describe the implemented capability accurately

**Decision:** Call version 0.2 an adaptive thermal anomaly-monitoring prototype.

**Reason:** The backend compares observations with fixed limits and a recursive
baseline. No forecasting model or remaining-useful-life estimator is
implemented.

**Consequence:** The project name remains as the intended direction, while the
README and dashboard distinguish anomaly detection from prediction.

## 2026-07-28 — Preserve unknown values

**Decision:** Return `null` for uptime until heartbeat history exists.

**Reason:** A latest-seen timestamp cannot establish 30-day uptime.

**Consequence:** The dashboard displays `N/A` instead of a generated percentage.

## 2026-07-28 — Record alert cause

**Decision:** Store whether an alert was raised by an absolute warning,
absolute critical limit, or the adaptive detector.

**Reason:** An adaptive alert below 70 °C previously displayed 70 °C as if that
fixed threshold had been crossed.

**Consequence:** Each alert now carries its actual cause and an appropriate
comparison threshold.

## 2026-07-28 — Use standard Next.js tooling

**Decision:** Use the normal Next.js development, build, and start commands.

**Reason:** The dashboard does not require provider-specific workers,
authentication headers, or deployment manifests.

**Consequence:** The repository can be built locally or in Docker without
platform-specific scaffolding.

## 2026-07-28 — Treat demo values as interface fixtures

**Decision:** Keep deterministic demo data for offline UI testing, but label it
and exclude it from research results.

**Reason:** A useful interface preview must not be mistaken for measured
performance.

**Consequence:** Physical results remain pending until raw calibration and
fault-injection data are collected.
