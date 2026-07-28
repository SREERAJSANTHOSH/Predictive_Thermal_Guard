# Research method

## Question

Can a three-point infrared node identify abnormal heating earlier than an
absolute temperature limit alone while maintaining an acceptable false-alarm
rate?

## Hypotheses

- After installation-specific correction, mean absolute error will remain
  within 2 °C from 30–100 °C on the laboratory target.
- A sustained 10 °C rise above a stable baseline will be detected within ten
  one-second samples.
- Combining the adaptive detector with fixed limits will improve detection of
  moderate heating without an unacceptable increase in false alarms.

These are targets to test, not completed results.

## Apparatus

- ESP32 development board
- TCA9548A I²C multiplexer
- three MLX90614 sensors with model suffix recorded
- adjustable mount with distance and angle markings
- high-emissivity reference tape
- regulated low-voltage heater or resistive test fixture
- contact reference sensor with documented uncertainty
- Wi-Fi access point, MQTT broker, and API host

Use an isolated low-voltage fixture for student experiments. Work on energized
mains equipment requires institutional approval, suitable PPE, and qualified
supervision.

## Variables

| Type | Variables |
|---|---|
| Independent | target temperature, heating profile, distance, angle, surface treatment, network interruption |
| Dependent | error, repeatability, detection delay, false alarms, missed detections, delivery ratio, latency |
| Controlled | mount, sample interval, target area, supply voltage, firmware commit, detector settings |

## Calibration procedure

1. Record the firmware commit, sensor model, target surface, distance, angle,
   ambient temperature, and reference-instrument uncertainty.
2. Position each sensor so the target fills its field of view.
3. Stabilize the target at 30, 40, 50, 60, 70, 80, 90, and 100 °C.
4. At each point, collect at least 30 paired reference and infrared readings.
5. Repeat the sequence three times, remounting the sensors between runs.
6. Repeat selected temperatures at different distances and viewing angles.
7. Store unmodified CSV files under `research/data/raw/`.

For error \(e_i=T_{sensor,i}-T_{reference,i}\), report:

\[
MAE = \frac{1}{N}\sum |e_i|
\]

\[
RMSE = \sqrt{\frac{1}{N}\sum e_i^2}
\]

Also report bias, standard deviation, and maximum absolute error. Do not report
only the best run.

## Detector comparison

Replay the same recorded sequences through:

1. the absolute 70/85 °C detector; and
2. the adaptive-plus-absolute detector.

Evaluate stable noise, single-sample outliers, +5 °C and +10 °C steps, gradual
ramps, normal load cycles, and sustained threshold crossings. Define the
ground-truth fault interval before calculating results. Report precision,
recall, F1 score, false alarms per hour, and detection delay.

Select parameters with one dataset and report final performance on a separate
dataset.

## Communication test

Before testing delivery, add `boot_id` and `sequence_number` to the telemetry
envelope and implement local buffering plus server-side deduplication. Generate
3,600 records per condition:

- stable Wi-Fi;
- 30-second Wi-Fi interruptions;
- unavailable MQTT broker;
- unavailable HTTP API; and
- backend restart during acquisition.

Report the ratio of unique stored records to generated records and the median,
95th-percentile, and maximum acquisition-to-storage latency.

## Long-duration test

Run the system for at least 24 hours under a stable thermal condition. Record
sensor failures, reconnections, missing and duplicate sequence numbers, device
restarts, database growth, dashboard reconnections, and false alerts.

## Reproducibility rule

Every reported table or chart must identify its raw file, analysis command,
firmware commit, backend commit, and detector settings. Simulation may be used
to test code paths, but it must be labelled and kept separate from physical
measurements.
