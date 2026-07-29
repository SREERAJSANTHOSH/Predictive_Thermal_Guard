# Bench Verification Guide — closing the "not tested yet" gap

This is a step-by-step guide for actually running the bench sessions in
`NOTES.md` and filling them in with real measurements, not placeholders. Do
these in order — each session assumes the previous one passed. Write results
straight into `NOTES.md` as you go, including anything that goes wrong.

Don't ask ChatGPT to fill in `NOTES.md` for you. This file only exists to be
useful if the numbers in it are real.

Use the [bench checklist](BENCH_CHECKLIST.md) to track session status without
inventing measurements.

---

## Before you start

Equipment needed:

- ESP32 DevKit + USB cable
- TCA9548A breakout
- At least 1 MLX90614 breakout (2+ if you want to test channel switching)
- Multimeter
- Jumper wires, breadboard
- Laptop with PlatformIO and a serial monitor
- A second known-good thermometer (phone IR thermometer, lab thermometer,
  anything you can cross-check against) for Bench Session 2
- A low-voltage, safe heat source for the fault trial (soldering iron held at
  a distance, a resistor under light load, a cup of hot water — NOT mains
  equipment)

---

## Bench Session 1 — host bus and mux

**Goal:** confirm the ESP32 can see the TCA9548A on the I2C bus before any
sensors are attached.

1. Wire ESP32 ↔ TCA9548A per `hardware/WIRING.md` (host side table only).
   Tie A0/A1/A2 to GND so the mux address is `0x70`.
2. Power the ESP32 over USB.
3. **Multimeter check first, before trusting any code:**
   - Measure 3V3 pin to GND → should read close to 3.3 V
   - Measure SDA and SCL to GND with the bus idle → should read close to 3.3 V
     (pulled high); if they read 0 V, your pull-ups aren't working
4. Flash a minimal I2C scanner sketch (ask ChatGPT for a standard Arduino I2C
   scanner if you don't have one saved — this one's generic enough that
   asking for it isn't a shortcut, it's a normal utility) and confirm it
   reports a device at `0x70`.
5. Record in `NOTES.md`:
   - Exact board names/revisions
   - Measured 3.3 V rail voltage
   - Whether `0x70` was found
   - Measured (or estimated from datasheet) SDA/SCL pull-up behavior
   - Anything that didn't work on the first try — wrong pin, address
     collision, reversed cable, whatever actually happened

If `0x70` isn't found: check solder joints on the breakout, confirm 3V3 vs 5V
logic level matches your ESP32 board, confirm A0/A1/A2 are actually grounded.
Write down what you tried, not just the eventual fix.

---

## Bench Session 2 — first MLX90614

**Goal:** confirm one real sensor gives sane, cross-checkable readings through
the mux.

1. Wire one MLX90614 to mux channel 0 per `hardware/WIRING.md`.
2. Flash the actual project firmware (`firmware/src/main.cpp`), open the
   serial monitor.
3. Confirm the boot log reports "MLX90614 ready on mux channel 0."
4. Point the sensor at a known surface (your hand, a wall, a cup of water)
   and simultaneously check the same spot with your reference thermometer.
5. Let it run for 10 minutes and count any `read failed` lines in the serial
   log.
6. Record in `NOTES.md`:
   - Sensor's ambient reading vs. room temperature (sanity check)
   - Sensor's object reading vs. your reference thermometer reading, and the
     difference between them
   - Target distance and rough field-of-view estimate
   - Read failure count over the 10 minutes
   - Note: MLX90614 accuracy is typically ±0.5°C in ideal conditions but
     depends heavily on emissivity and distance — don't expect a perfect
     match to the reference, just a plausible one (a few °C off due to
     emissivity mismatch is normal and worth writing down, not hiding)

---

## Bench Session 3 — multiple sensors and MQTT

**Goal:** confirm the mux correctly switches between multiple sensors and
that MQTT delivery is reliable.

1. Add a second (and third/fourth, if available) MLX90614 on the remaining
   mux channels.
2. Start Mosquitto locally, then in a separate terminal:

   ```bash
   mosquitto_sub -v -t 'thermal-fault-guard/+/temperature'
   ```

3. Flash and run the firmware, confirm all connected channels report "ready"
   at boot.
4. Watch both the serial monitor and the `mosquitto_sub` output for at least
   5 minutes.
5. Record in `NOTES.md`:
   - Which channels were connected
   - Measured publish interval (should be close to 1s per sensor)
   - Whether messages appeared correctly in `mosquitto_sub`, matching the
     serial log
   - Any "reading queue full" drops printed over Serial
   - Test Wi-Fi reconnect: turn your router off/on or move the ESP32 out of
     range briefly, confirm it reconnects and resumes publishing
   - Test MQTT reconnect: stop and restart the Mosquitto broker while the
     ESP32 is running, confirm it reconnects without a firmware restart

---

## Fault trial

**Goal:** confirm the rolling-average detector in `backend/monitor.py`
actually flags a real temperature change end-to-end.

Safety: use a low-voltage, controlled heat source only. Do not point sensors
at mains-powered equipment or exposed wiring for this test.

1. Start the monitor:

   ```bash
   thermal-monitor --broker localhost --csv temperature_log.csv
   ```

2. Let one channel sit at a stable baseline for at least 2 minutes (needs 8+
   samples before the detector will flag anything, per the default
   `--minimum-samples`).
3. Introduce your heat source near that sensor and watch for a `[FAULT]` line
   in the monitor output.
4. Open the dashboard in another terminal and confirm the row turns red and a
   red cross appears on the plot.
5. Record in `NOTES.md`:
   - Baseline duration and mean temperature before the trial
   - Heat source used and approximate distance
   - Threshold settings used (default: 8°C deviation or 85°C absolute)
   - Temperature at which it actually flagged
   - Time from heat introduction to flag appearing
   - Any false alerts before the heat was introduced

---

## After all sessions

Once all four sessions have real entries (no more "Not tested yet"):

1. Update the README's "Current status" section — change "to be completed on
   the actual hardware" to reflect what's actually been verified.
2. Add the real photo: `hardware/photos/breadboard-overview.jpg`, replacing
   the placeholder note.
3. If anything in `hardware/WIRING.md` or the KiCad drawing turned out to be
   wrong once you actually wired it, fix the docs to match reality — a
   corrected diagram is more credible than a first-draft one that happens to
   be right.
4. Commit with an honest message, e.g. `"bench: sessions 1-3 + fault trial
   completed, see NOTES.md"` — keep it as its own commit, not folded into a
   docs cleanup, so the history shows real verification work happened.

If something in a session fails and you can't resolve it, that's fine to
leave in `NOTES.md` as an open problem — an honestly documented failure is
worth more than a suspiciously clean success on every step.
