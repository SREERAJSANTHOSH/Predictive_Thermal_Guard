from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from datetime import timezone
from pathlib import Path

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt5 import QtCore, QtGui, QtWidgets

from desktop.csv_source import LoggedReading, latest_per_sensor, load_readings


def format_temperature(value: float | None) -> str:
    return "--" if value is None else f"{value:.2f} C"


class ThermalDashboard(QtWidgets.QMainWindow):
    def __init__(self, csv_path: Path) -> None:
        super().__init__()
        self.csv_path = csv_path
        self.setWindowTitle("Thermal Fault Guard")
        self.resize(1050, 720)

        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)

        heading = QtWidgets.QLabel("Live thermal channels")
        heading.setStyleSheet("font-size: 20px; font-weight: 600;")
        layout.addWidget(heading)

        self.table = QtWidgets.QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            [
                "Device",
                "Channel",
                "Object",
                "Ambient",
                "Baseline",
                "Deviation",
                "Status",
                "Updated (UTC)",
            ]
        )
        self.table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.table, stretch=2)

        self.figure = Figure(figsize=(8, 4), tight_layout=True)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.axes = self.figure.add_subplot(111)
        layout.addWidget(self.canvas, stretch=3)

        self.setCentralWidget(central)
        self.statusBar().showMessage(f"Waiting for {self.csv_path}")

        self.refresh_timer = QtCore.QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh)
        self.refresh_timer.start(750)
        self.refresh()

    def refresh(self) -> None:
        readings = load_readings(self.csv_path)
        if not readings:
            self.statusBar().showMessage(f"Waiting for {self.csv_path}")
            return

        self._update_table(list(latest_per_sensor(readings).values()))
        self._update_plot(readings)
        self.statusBar().showMessage(
            f"Loaded {len(readings)} samples from {self.csv_path}"
        )

    def _update_table(self, latest: list[LoggedReading]) -> None:
        latest.sort(key=lambda item: item.sensor_key)
        self.table.setRowCount(len(latest))

        for row_index, reading in enumerate(latest):
            deviation = (
                "--"
                if reading.deviation_c is None
                else f"{reading.deviation_c:+.2f} C"
            )
            values = [
                reading.device_id,
                str(reading.channel),
                format_temperature(reading.temp_c),
                format_temperature(reading.ambient_c),
                format_temperature(reading.baseline_c),
                deviation,
                "FAULT" if reading.abnormal else "NORMAL",
                reading.timestamp.astimezone(timezone.utc).strftime("%H:%M:%S"),
            ]
            for column_index, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                item.setToolTip(reading.reason)
                if reading.abnormal:
                    item.setBackground(QtGui.QColor("#b71c1c"))
                    item.setForeground(QtGui.QColor("#ffffff"))
                self.table.setItem(row_index, column_index, item)

    def _update_plot(self, readings: list[LoggedReading]) -> None:
        history: dict[tuple[str, int], list[LoggedReading]] = defaultdict(list)
        for reading in readings:
            history[reading.sensor_key].append(reading)

        self.axes.clear()
        for (device_id, channel), samples in sorted(history.items()):
            visible = samples[-120:]
            self.axes.plot(
                range(len(visible)),
                [sample.temp_c for sample in visible],
                label=f"{device_id} / CH{channel}",
                linewidth=1.6,
            )
            fault_x = [
                index for index, sample in enumerate(visible) if sample.abnormal
            ]
            if fault_x:
                self.axes.scatter(
                    fault_x,
                    [visible[index].temp_c for index in fault_x],
                    color="#b71c1c",
                    marker="x",
                    s=55,
                    zorder=3,
                )

        self.axes.set_title("Object temperature history")
        self.axes.set_xlabel("Recent samples")
        self.axes.set_ylabel("Temperature (C)")
        self.axes.grid(True, alpha=0.25)
        self.axes.legend(loc="upper left", fontsize="small")
        self.canvas.draw_idle()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Open the PyQt dashboard.")
    parser.add_argument("--csv", type=Path, default=Path("temperature_log.csv"))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    application = QtWidgets.QApplication(sys.argv)
    window = ThermalDashboard(args.csv)
    window.show()
    raise SystemExit(application.exec())


if __name__ == "__main__":
    main()
