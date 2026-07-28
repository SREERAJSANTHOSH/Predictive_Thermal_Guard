# Breadboard bill of materials

| Ref. | Part | Qty. | Purpose / note |
|---|---|---:|---|
| A1 | ESP32 DevKit V1 or equivalent | 1 | 3.3 V MCU and Wi-Fi |
| A2 | TCA9548A breakout | 1 | Isolates four identical `0x5A` sensors |
| A3-A6 | MLX90614 breakout | 2-4 | Non-contact object and ambient temperature |
| C1-C4 | 100 nF ceramic capacitor | 4 | Local sensor bypass |
| C5 | 10 uF electrolytic or ceramic capacitor | 1 | Bulk bypass at mux board |
| R1 | 10 kΩ resistor | 1 | TCA9548A reset pull-up if absent on module |
| R2-R3 | 4.7 kΩ resistor | 0-2 | Host SDA/SCL pull-ups only if not fitted |
| — | Breadboard and jumper wire | 1 set | Prototype interconnect |
| — | USB cable and 5 V USB supply | 1 | Programming and power |

Part numbers are intentionally not locked to one breakout vendor. Before
assembly, compare the chosen module schematics for regulator, level shifter,
and pull-up differences.

