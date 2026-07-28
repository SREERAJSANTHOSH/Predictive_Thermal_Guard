# Hardware revision A

This revision uses ready-made modules so the firmware can be proved on a
breadboard before a custom PCB is laid out:

- ESP32 DevKit
- TCA9548A I2C multiplexer breakout
- two to four MLX90614 breakout boards

The checked-in KiCad schematic is a module-level interconnect drawing. It
records the nets used on the bench without pretending that a custom PCB has
already been fabricated. Open `kicad/ThermalFaultGuard.sch` in KiCad and save
it in the current KiCad format if prompted.

## Design points

- The ESP32 host bus runs at 100 kHz on GPIO21/GPIO22.
- All MLX90614 boards retain their default `0x5A` address. The TCA9548A
  isolates the identical addresses on channels 0 to 3.
- The TCA9548A address pins A0, A1, and A2 are tied low, giving address
  `0x70`.
- Sensor power is 3.3 V. Confirm the voltage requirements of the exact
  breakout board before connecting it; breakout designs are not identical.
- Many TCA9548A and MLX90614 breakouts already fit I2C pull-ups. Measure the
  effective pull-up resistance before adding R2/R3, because parallel pull-ups
  can make it unnecessarily low.
- Keep each downstream I2C pair short on the breadboard. Put a 100 nF bypass
  capacitor beside each sensor connector and a 10 uF bulk capacitor beside
  the multiplexer module.

## Before power-up

1. Check 3.3 V to ground resistance with power removed.
2. Power the ESP32 without sensors and confirm a stable 3.3 V rail.
3. Fit the TCA9548A and scan for `0x70`.
4. Add one sensor on channel 0 and confirm `0x5A` after selecting the channel.
5. Add the remaining sensors one at a time.

Record the measured rail voltage, detected channels, cable lengths, and any
read errors in the repository's `NOTES.md`.

