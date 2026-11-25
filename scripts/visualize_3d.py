#!/usr/bin/env python3
"""Interactively visualize the coil layout and modeled impedance response."""

import argparse
import csv
import math
import sys


def load_curve(path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"x_cells", "re_ohm", "im_ohm", "magnitude_ohm", "phase_deg"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("curve CSV must contain x_cells,re_ohm,im_ohm,magnitude_ohm,phase_deg")
        rows = list(reader)
    if len(rows) < 2:
        raise ValueError("curve CSV must contain at least two data rows")
    values = [[float(row[key]) for key in ("x_cells", "re_ohm", "im_ohm", "magnitude_ohm", "phase_deg")]
              for row in rows]
    if any(not math.isfinite(value) for row in values for value in row):
        raise ValueError("curve values must all be finite")
    if any(b[0] <= a[0] for a, b in zip(values, values[1:])):
        raise ValueError("x_cells values must be strictly increasing")
    return tuple([row[i] for row in values] for i in range(5))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("curve", help="calibration curve CSV from resonator-array")
    args = parser.parse_args()
    try:
        x, re, im, magnitude, phase = load_curve(args.curve)
    except (OSError, ValueError, csv.Error) as exc:
        parser.error(str(exc))

    try:
        import matplotlib.pyplot as plt
        from matplotlib.widgets import Slider
    except ImportError:
        parser.error("matplotlib is required; install it with: python3 -m pip install matplotlib")

    x_min, x_max = x[0], x[-1]
    coil_x = [float(k) for k in range(math.ceil(x_min), math.floor(x_max) + 1)]
    if not coil_x:
        coil_x = [x_min, x_max]

    fig = plt.figure(figsize=(14, 9))
    ax3d = fig.add_subplot(2, 2, (1, 3), projection="3d")
    ax_mag = fig.add_subplot(2, 2, 2)
    ax_phase = fig.add_subplot(2, 2, 4)
    # Reserve a dedicated footer for the chart labels, slider, and live readout.
    fig.subplots_adjust(bottom=0.27, top=0.90, wspace=0.30, hspace=0.40)
    fig.suptitle("Receiver position and modeled circuit response", fontsize=16)

    theta = [2.0 * math.pi * k / 160 for k in range(161)]
    radius = 0.36
    for number, cx in enumerate(coil_x):
        ax3d.plot([cx + radius * math.cos(t) for t in theta],
                  [radius * math.sin(t) for t in theta], [0.0] * len(theta),
                  color="#2563eb", linewidth=2.2)
        ax3d.text(cx, 0, -0.12, f"{number + 1}", ha="center", fontsize=9)
    rx, ry, rz = 0.27, 0.0, 0.9
    receiver_ring, = ax3d.plot([], [], [], color="#dc2626", linewidth=3.0, label="moving receiver")
    receiver_center, = ax3d.plot([], [], [], marker="o", color="#991b1b", markersize=5)
    links = [ax3d.plot([], [], [], color="#f59e0b", linewidth=2.5, alpha=0.7)[0]
             for _ in range(2)]
    ax3d.set(xlim=(x_min - 0.7, x_max + 0.7), ylim=(-0.8, 0.8), zlim=(-0.25, 1.4),
             xlabel="Along the coil row (coil pitches)", ylabel="Across row", zlabel="Height (schematic)")
    ax3d.set_title("3D layout (schematic)")
    ax3d.view_init(elev=23, azim=-58)
    mag_line, = ax_mag.plot(x, magnitude, color="#2563eb", linewidth=1.8)
    mag_dot, = ax_mag.plot([], [], "o", color="#dc2626", markersize=8)
    ax_mag.set(title="Input impedance size", xlabel="Receiver position (coil pitches)",
               ylabel="Magnitude (ohms)")
    ax_mag.grid(True, alpha=0.3)
    phase_line, = ax_phase.plot(x, phase, color="#7c3aed", linewidth=1.8)
    phase_dot, = ax_phase.plot([], [], "o", color="#dc2626", markersize=8)
    ax_phase.set(title="Input impedance angle", xlabel="Receiver position (coil pitches)",
                 ylabel="Angle (degrees)")
    ax_phase.grid(True, alpha=0.3)
    for ax in (ax_mag, ax_phase):
        ax.set_xlim(x_min, x_max)

    slider_ax = fig.add_axes([0.23, 0.12, 0.62, 0.035])
    slider = Slider(slider_ax, "Receiver position", x_min, x_max,
                    valinit=x_min, valstep=(x_max - x_min) / max(len(x) - 1, 1))
    status = fig.text(0.5, 0.045, "", ha="center", va="center", fontsize=10)

    def update(position):
        position = float(position)
        receiver_ring.set_data_3d([position + rx * math.cos(t) for t in theta],
                                  [ry + rx * math.sin(t) for t in theta], [rz] * len(theta))
        receiver_center.set_data_3d([position], [ry], [rz])
        # The circuit model couples the receiver to the two closest array cells.
        left = min(max(math.floor(position), 0), len(coil_x) - 1)
        neighbors = [left, min(left + 1, len(coil_x) - 1)]
        for line, idx in zip(links, neighbors):
            distance = abs(position - coil_x[idx])
            coupling = math.exp(-(distance * distance) / (0.61 * 0.61))
            line.set_data_3d([position, coil_x[idx]], [ry, 0], [rz, 0])
            line.set_linewidth(0.8 + 3.2 * coupling)
            line.set_alpha(0.18 + 0.72 * coupling)

        nearest = min(range(len(x)), key=lambda i: abs(x[i] - position))
        mag_dot.set_data([x[nearest]], [magnitude[nearest]])
        phase_dot.set_data([x[nearest]], [phase[nearest]])
        status.set_text(f"x = {x[nearest]:.3f} pitches   |   Z = {re[nearest]:.4g} + j{im[nearest]:.4g} ohms")
        fig.canvas.draw_idle()

    slider.on_changed(update)
    update(x_min)
    plt.show()


if __name__ == "__main__":
    main()
