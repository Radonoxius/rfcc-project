#!/usr/bin/env python3
"""Noise-aware sequential receiver position estimator using a particle filter."""

import argparse
import csv
import math
import random
import sys


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"{path}: missing CSV header")
        return reader.fieldnames, list(reader)


def calibration(path):
    fields, rows = read_rows(path)
    required = {"x_cells", "re_ohm", "im_ohm"}
    if not required.issubset(fields):
        raise ValueError(f"{path}: calibration needs x_cells,re_ohm,im_ohm columns")
    points = sorted((float(r["x_cells"]), float(r["re_ohm"]), float(r["im_ohm"])) for r in rows)
    if len(points) < 2 or any(not all(map(math.isfinite, p)) for p in points):
        raise ValueError(f"{path}: need at least two finite calibration rows")
    if any(points[k][0] <= points[k - 1][0] for k in range(1, len(points))):
        raise ValueError(f"{path}: x_cells values must be unique")
    return points


def interp(points, x):
    lo, hi = points[0][0], points[-1][0]
    x = min(hi, max(lo, x))
    left, right = 0, len(points) - 1
    while right - left > 1:
        mid = (left + right) // 2
        if points[mid][0] <= x:
            left = mid
        else:
            right = mid
    a, b = points[left], points[right]
    t = (x - a[0]) / (b[0] - a[0])
    return a[1] + t * (b[1] - a[1]), a[2] + t * (b[2] - a[2])


def systematic_resample(particles, weights, rng):
    n = len(particles)
    start = rng.random() / n
    out, cumulative, j = [], weights[0], 0
    for k in range(n):
        u = start + k / n
        while u > cumulative and j < n - 1:
            j += 1
            cumulative += weights[j]
        out.append(particles[j])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("calibration", help="resonator-array calibration CSV with x_cells,re_ohm,im_ohm")
    ap.add_argument("measurements", help="CSV with re_ohm,im_ohm measurement columns")
    ap.add_argument("--noise", type=float, default=0.03, help="complex-plane measurement noise sigma in ohms (default: 0.03)")
    ap.add_argument("--motion", type=float, default=0.08, help="per-sample motion prior sigma in coil pitches (default: 0.08)")
    ap.add_argument("--particles", type=int, default=2000, help="particle count (default: 2000)")
    ap.add_argument("--seed", type=int, default=1, help="random seed for reproducibility")
    args = ap.parse_args()
    if (not math.isfinite(args.noise) or not math.isfinite(args.motion) or
            args.noise <= 0 or args.motion < 0 or args.particles < 100):
        ap.error("noise must be positive, motion nonnegative, and particles at least 100")

    points = calibration(args.calibration)
    fields, rows = read_rows(args.measurements)
    if not {"re_ohm", "im_ohm"}.issubset(fields):
        ap.error("measurements need re_ohm and im_ohm columns")
    observations = [(float(r["re_ohm"]), float(r["im_ohm"])) for r in rows]
    if not observations or any(not all(map(math.isfinite, z)) for z in observations):
        ap.error("measurements must contain at least one finite complex impedance")

    rng = random.Random(args.seed)
    low, high = points[0][0], points[-1][0]
    particles = [rng.uniform(low, high) for _ in range(args.particles)]
    weights = [1.0 / args.particles] * args.particles
    # A broad first measurement avoids imposing a direction or a starting point.
    print("sample,estimate_cells,map_cells,std_cells,ess")
    sigma2 = args.noise * args.noise
    for k, z in enumerate(observations):
        if k:
            particles = [min(high, max(low, x + rng.gauss(0.0, args.motion)))
                         for x in particles]
        logw = []
        for x, prior in zip(particles, weights):
            predicted = interp(points, x)
            d2 = (z[0] - predicted[0]) ** 2 + (z[1] - predicted[1]) ** 2
            logw.append(math.log(max(prior, 1e-300)) - d2 / (2.0 * sigma2))
        peak = max(logw)
        unnorm = [math.exp(w - peak) for w in logw]
        total = sum(unnorm)
        weights = [w / total for w in unnorm]
        mean = sum(x * w for x, w in zip(particles, weights))
        variance = sum(w * (x - mean) ** 2 for x, w in zip(particles, weights))
        map_x = particles[max(range(len(weights)), key=weights.__getitem__)]
        ess = 1.0 / sum(w * w for w in weights)
        print(f"{k},{mean:.8g},{map_x:.8g},{math.sqrt(variance):.8g},{ess:.8g}")
        # Resample only when the weighted sample set is becoming degenerate.
        if ess < args.particles * 0.5:
            particles = systematic_resample(particles, weights, rng)
            weights = [1.0 / args.particles] * args.particles


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, csv.Error) as exc:
        print(f"receiver-position-tracker: {exc}", file=sys.stderr)
        sys.exit(2)
