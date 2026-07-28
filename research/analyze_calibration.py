#!/usr/bin/env python3
"""Summarize paired reference and infrared calibration readings."""

from __future__ import annotations

import argparse
import csv
import math
import statistics
from pathlib import Path


def load_errors(path: Path) -> list[float]:
    errors: list[float] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"reference_c", "sensor_c"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            missing = sorted(required.difference(reader.fieldnames or []))
            raise ValueError(f"missing CSV columns: {', '.join(missing)}")

        for line_number, row in enumerate(reader, start=2):
            try:
                reference = float(row["reference_c"])
                sensor = float(row["sensor_c"])
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"line {line_number} has a non-numeric paired reading"
                ) from error
            if not (math.isfinite(reference) and math.isfinite(sensor)):
                raise ValueError(f"line {line_number} has a non-finite reading")
            errors.append(sensor - reference)

    if not errors:
        raise ValueError("CSV contains no paired readings")
    return errors


def summarize(errors: list[float]) -> dict[str, float | int]:
    count = len(errors)
    return {
        "count": count,
        "bias_c": statistics.fmean(errors),
        "mae_c": statistics.fmean(abs(error) for error in errors),
        "rmse_c": math.sqrt(statistics.fmean(error * error for error in errors)),
        "standard_deviation_c": statistics.stdev(errors) if count > 1 else 0.0,
        "maximum_absolute_error_c": max(abs(error) for error in errors),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Calculate error metrics from calibration CSV data."
    )
    parser.add_argument("csv_file", type=Path)
    args = parser.parse_args()

    metrics = summarize(load_errors(args.csv_file))
    for name, value in metrics.items():
        print(f"{name}: {value if isinstance(value, int) else f'{value:.4f}'}")


if __name__ == "__main__":
    main()
