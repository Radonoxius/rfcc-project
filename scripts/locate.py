#!/usr/bin/env python3
"""Track receiver position from magnitude samples using the paper's interval algorithm.

Input: a CSV with a `magnitude_ohm` column, one sample per acquisition.
Calibration: one C-generated curve CSV with the same termination/receiver parameters.
"""
import csv, bisect, math, sys

def load(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) < 2:
        raise ValueError(f"{path}: calibration needs at least two samples")
    x = [float(r["x_cells"]) for r in rows]
    z = [float(r["magnitude_ohm"]) for r in rows]
    if any(not math.isfinite(v) for v in x + z):
        raise ValueError(f"{path}: calibration values must be finite")
    if any(right <= left for left, right in zip(x, x[1:])):
        raise ValueError(f"{path}: x_cells must be strictly increasing")
    return x, z

def main(calibration, measurements):
    x, z = load(calibration)
    with open(measurements, newline="") as f: samples = [float(r["magnitude_ohm"]) for r in csv.DictReader(f)]
    previous = None
    previous_delta_sign = 0
    interval = math.floor(x[0])
    last_interval = math.floor(x[-1])
    for k, measured in enumerate(samples):
        if not math.isfinite(measured):
            raise ValueError(f"measurement {k} is not finite")
        lo, hi = max(float(interval), x[0]), min(float(interval + 1), x[-1])
        if previous is not None:
            delta = measured - previous
            delta_sign = (delta > 0) - (delta < 0)
            if (delta_sign and previous_delta_sign and delta_sign != previous_delta_sign
                    and interval < last_interval):
                interval += 1
            if delta_sign:
                previous_delta_sign = delta_sign
            lo, hi = max(float(interval), x[0]), min(float(interval + 1), x[-1])
        a, b = bisect.bisect_left(x, lo), bisect.bisect_right(x, hi)
        if a == b:
            raise ValueError(f"{calibration}: no calibration samples in interval [{lo}, {hi}]")
        idx = min(range(a, b), key=lambda q: abs(z[q] - measured))
        print(f"{k},{measured:.9g},{x[idx]:.9g},{abs(z[idx]-measured):.9g}")
        previous = measured

if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(f"usage: {sys.argv[0]} calibration.csv measurements.csv")
    main(*sys.argv[1:])
