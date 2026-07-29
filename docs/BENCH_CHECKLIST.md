# Bench Verification Checklist

Use this checklist to track real hardware verification for Predictive Thermal
Guard. Record actual measurements in [`NOTES.md`](../NOTES.md); do not replace
measurements with assumed or generated values.

Allowed session states: `not_started`, `in_progress`, `done`, and `blocked`.

## Rules

- Only record measurements you actually took.
- If a step fails, record what failed and what you tried, not only the
  eventual fix.
- Do not ask ChatGPT to invent values for `NOTES.md`.
- Update each status as the physical work progresses.

## Equipment

- [ ] ESP32 DevKit and USB cable
- [ ] TCA9548A breakout
- [ ] One to four MLX90614 breakouts
- [ ] Multimeter
- [ ] Jumper wires and breadboard
- [ ] Laptop with PlatformIO and a serial monitor
- [ ] Reference thermometer
- [ ] Low-voltage safe heat source

Do not use mains-powered equipment or exposed mains wiring as the heat source.

## Session 1 — host bus and mux

**Status:** `not_started`

**Goal:** Confirm the ESP32 can see the TCA9548A on I2C before any sensors are
attached.

### Procedure

- [ ] Wire the ESP32 to the TCA9548A using the host-side table in
      [`hardware/WIRING.md`](../hardware/WIRING.md).
- [ ] Tie A0, A1, and A2 to GND so the mux address is `0x70`.
- [ ] Power the ESP32 over USB.
- [ ] Measure 3V3 to GND; expect approximately 3.3 V.
- [ ] Measure SDA to GND with the bus idle; expect approximately 3.3 V.
- [ ] Measure SCL to GND with the bus idle; expect approximately 3.3 V.
- [ ] Flash a basic Arduino I2C scanner.
- [ ] Confirm that the scanner reports a device at `0x70`.

### Record in `NOTES.md`

- [ ] Exact board names and revisions
- [ ] Measured 3.3 V rail voltage
- [ ] Whether address `0x70` was found
- [ ] SDA and SCL pull-up behaviour
- [ ] Problems encountered and attempted fixes

### If `0x70` is not found

- [ ] Check the breakout solder joints.
- [ ] Confirm that the breakout logic level matches the ESP32.
- [ ] Confirm that A0, A1, and A2 are grounded.

## Session 2 — first MLX90614

**Status:** `not_started`

**Depends on:** Session 1 completed

**Goal:** Confirm one real sensor gives plausible, cross-checkable readings
through the mux.

### Procedure

- [ ] Wire one MLX90614 to mux channel 0 using
      [`hardware/WIRING.md`](../hardware/WIRING.md).
- [ ] Flash [`firmware/src/main.cpp`](../firmware/src/main.cpp).
- [ ] Open the serial monitor.
- [ ] Confirm the boot log reports
      `MLX90614 ready on mux channel 0`.
- [ ] Point the sensor at a known surface.
- [ ] Check the same surface with the reference thermometer.
- [ ] Run the sensor for 10 minutes.
- [ ] Count every `read failed` line.

### Record in `NOTES.md`

- [ ] Ambient reading and room-temperature reference
- [ ] Object reading and reference-thermometer reading
- [ ] Difference between readings
- [ ] Target distance and field-of-view estimate
- [ ] Read-failure count over 10 minutes

MLX90614 accuracy can be approximately ±0.5 °C in ideal conditions, but
emissivity, distance, and target coverage can produce a larger difference.
Record the observed difference without hiding it.

## Session 3 — multiple sensors and MQTT

**Status:** `not_started`

**Depends on:** Session 2 completed

**Goal:** Confirm the mux switches correctly between sensors and that MQTT
delivery recovers from interruptions.

### Procedure

- [ ] Add a second MLX90614.
- [ ] Add third and fourth sensors if available.
- [ ] Start the local Mosquitto broker.
- [ ] Start a subscriber:

  ```bash
  mosquitto_sub -v -t 'thermal-fault-guard/+/temperature'
  ```

- [ ] Flash and run the firmware.
- [ ] Confirm every connected channel reports `ready`.
- [ ] Watch Serial and `mosquitto_sub` for at least five minutes.
- [ ] Briefly interrupt Wi-Fi and confirm publishing resumes.
- [ ] Stop and restart Mosquitto and confirm publishing resumes without a
      firmware restart.

### Record in `NOTES.md`

- [ ] Connected channels
- [ ] Measured publish interval
- [ ] Whether Serial and MQTT messages match
- [ ] Any `reading queue full` drops
- [ ] Wi-Fi reconnect result
- [ ] MQTT reconnect result

## Fault trial — end-to-end detection

**Status:** `not_started`

**Depends on:** Session 3 completed

**Goal:** Confirm that the rolling-average detector in
[`backend/monitor.py`](../backend/monitor.py) flags a real temperature change.

Use only a low-voltage, controlled heat source. Never test with exposed mains
wiring.

### Procedure

- [ ] Start the monitor:

  ```bash
  thermal-monitor --broker localhost --csv temperature_log.csv
  ```

- [ ] Hold one channel at a stable baseline for at least two minutes.
- [ ] Confirm that at least eight baseline samples have been collected.
- [ ] Introduce the heat source near the sensor.
- [ ] Watch for a `[FAULT]` line in the monitor output.
- [ ] Start the dashboard:

  ```bash
  thermal-dashboard --csv temperature_log.csv
  ```

- [ ] Confirm that the affected row turns red.
- [ ] Confirm that the fault is marked on the plot.

### Record in `NOTES.md`

- [ ] Baseline duration and mean temperature
- [ ] Heat source and approximate distance
- [ ] Threshold settings
- [ ] Temperature at which the detector flagged
- [ ] Time from heat introduction to fault indication
- [ ] False alerts before introducing heat

## After all sessions

- [ ] Replace every `Not tested yet` entry in `NOTES.md` with measured results
      or a documented unresolved problem.
- [ ] Update the README current-status section.
- [ ] Add the real
      [`hardware/photos/breadboard-overview.jpg`](../hardware/photos/README.md).
- [ ] Correct `hardware/WIRING.md` if the physical wiring differed.
- [ ] Correct the KiCad drawing if the physical wiring differed.
- [ ] Commit the measured results separately with an honest message such as:

  ```text
  bench: sessions 1-3 + fault trial completed, see NOTES.md
  ```

An unresolved failure should remain documented as an open problem rather than
being omitted.
