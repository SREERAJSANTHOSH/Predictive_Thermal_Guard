EESchema Schematic File Version 4
LIBS:power
LIBS:device
LIBS:Connector_Generic
EELAYER 29 0
EELAYER END
$Descr A4 11693 8268
Sheet 1 1
Title "Thermal Fault Guard - Breadboard Interconnect"
Date "2026-07-28"
Rev "A"
Comp "SREERAJSANTHOSH"
Comment1 "ESP32 + TCA9548A + four MLX90614 breakout boards"
Comment2 "Module-level schematic; verify breakout pin order before assembly"
$EndDescr
$Comp
L Connector_Generic:Conn_01x04 J1
U 1 1 66000001
P 1900 2200
F 0 "J1" H 1818 2517 50  0000 C CNN
F 1 "ESP32_I2C" H 1818 2426 50 0000 C CNN
	1    1900 2200
	-1 0 0 -1
$EndComp
$Comp
L Connector_Generic:Conn_01x08 J2
U 1 1 66000002
P 4300 2400
F 0 "J2" H 4380 2392 50 0000 L CNN
F 1 "TCA9548A_HOST" H 4380 2301 50 0000 L CNN
	1    4300 2400
	1 0 0 -1
$EndComp
Wire Wire Line
	2100 2100 4100 2100
Wire Wire Line
	2100 2200 4100 2200
Wire Wire Line
	2100 2300 4100 2300
Wire Wire Line
	2100 2400 4100 2400
Text Label 2250 2100 0 50 ~ 0
+3V3
Text Label 2250 2200 0 50 ~ 0
GND
Text Label 2250 2300 0 50 ~ 0
SDA_GPIO21
Text Label 2250 2400 0 50 ~ 0
SCL_GPIO22
Wire Wire Line
	4100 2500 3850 2500
Wire Wire Line
	3850 2500 3850 2600
Wire Wire Line
	3850 2600 4100 2600
Wire Wire Line
	3850 2600 3850 2700
Wire Wire Line
	3850 2700 4100 2700
Connection ~ 3850 2600
Text Label 3650 2600 2 50 ~ 0
GND
Text Label 3900 2800 2 50 ~ 0
MUX_RST
$Comp
L Device:R R1
U 1 1 66000003
P 3500 3000
F 0 "R1" H 3570 3046 50 0000 L CNN
F 1 "10k" H 3570 2955 50 0000 L CNN
	1    3500 3000
	1 0 0 -1
$EndComp
Wire Wire Line
	3500 2850 3500 2800
Wire Wire Line
	3500 2800 4100 2800
Wire Wire Line
	3500 3150 3500 3250
Text Label 3500 3250 3 50 ~ 0
+3V3
$Comp
L Connector_Generic:Conn_01x04 J3
U 1 1 66000010
P 7000 1800
F 0 "J3" H 7080 1792 50 0000 L CNN
F 1 "MLX90614_CH0" H 7080 1701 50 0000 L CNN
	1    7000 1800
	1 0 0 -1
$EndComp
$Comp
L Connector_Generic:Conn_01x04 J4
U 1 1 66000011
P 7000 2900
F 0 "J4" H 7080 2892 50 0000 L CNN
F 1 "MLX90614_CH1" H 7080 2801 50 0000 L CNN
	1    7000 2900
	1 0 0 -1
$EndComp
$Comp
L Connector_Generic:Conn_01x04 J5
U 1 1 66000012
P 7000 4000
F 0 "J5" H 7080 3992 50 0000 L CNN
F 1 "MLX90614_CH2" H 7080 3901 50 0000 L CNN
	1    7000 4000
	1 0 0 -1
$EndComp
$Comp
L Connector_Generic:Conn_01x04 J6
U 1 1 66000013
P 7000 5100
F 0 "J6" H 7080 5092 50 0000 L CNN
F 1 "MLX90614_CH3" H 7080 5001 50 0000 L CNN
	1    7000 5100
	1 0 0 -1
$EndComp
Text Label 6800 1700 2 50 ~ 0
+3V3
Text Label 6800 1800 2 50 ~ 0
GND
Text Label 6800 1900 2 50 ~ 0
SD0
Text Label 6800 2000 2 50 ~ 0
SC0
Text Label 6800 2800 2 50 ~ 0
+3V3
Text Label 6800 2900 2 50 ~ 0
GND
Text Label 6800 3000 2 50 ~ 0
SD1
Text Label 6800 3100 2 50 ~ 0
SC1
Text Label 6800 3900 2 50 ~ 0
+3V3
Text Label 6800 4000 2 50 ~ 0
GND
Text Label 6800 4100 2 50 ~ 0
SD2
Text Label 6800 4200 2 50 ~ 0
SC2
Text Label 6800 5000 2 50 ~ 0
+3V3
Text Label 6800 5100 2 50 ~ 0
GND
Text Label 6800 5200 2 50 ~ 0
SD3
Text Label 6800 5300 2 50 ~ 0
SC3
$Comp
L Connector_Generic:Conn_01x08 J7
U 1 1 66000020
P 5500 3900
F 0 "J7" H 5418 4417 50 0000 C CNN
F 1 "TCA9548A_CH0_CH3" H 5418 4326 50 0000 C CNN
	1    5500 3900
	-1 0 0 -1
$EndComp
Text Label 5700 3600 0 50 ~ 0
SD0
Text Label 5700 3700 0 50 ~ 0
SC0
Text Label 5700 3800 0 50 ~ 0
SD1
Text Label 5700 3900 0 50 ~ 0
SC1
Text Label 5700 4000 0 50 ~ 0
SD2
Text Label 5700 4100 0 50 ~ 0
SC2
Text Label 5700 4200 0 50 ~ 0
SD3
Text Label 5700 4300 0 50 ~ 0
SC3
Text Notes 1550 1900 0 60 ~ 12
ESP32 DevKit header
Text Notes 3850 1900 0 60 ~ 12
TCA9548A breakout host header
Text Notes 6350 1450 0 60 ~ 12
Sensor breakout headers
Text Notes 1550 3700 0 50 ~ 0
J1 pin order: 3V3, GND, SDA/GPIO21, SCL/GPIO22
Text Notes 1550 3850 0 50 ~ 0
J2 pin order: VIN, GND, SDA, SCL, A0, A1, A2, RST
Text Notes 1550 4000 0 50 ~ 0
J3-J6 pin order: 3V3, GND, SDA, SCL
Text Notes 1550 4300 0 50 ~ 0
J7 pin order: SD0, SC0, SD1, SC1, SD2, SC2, SD3, SC3
$EndSCHEMATC
