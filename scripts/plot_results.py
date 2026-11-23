#!/usr/bin/env python3
"""Create separate, high-resolution plots from the C solver output."""
import csv, pathlib, sys

def read(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    return ([float(r["x_cells"]) for r in rows],
            [float(r["re_ohm"]) for r in rows],
            [float(r["im_ohm"]) for r in rows],
            [float(r["magnitude_ohm"]) for r in rows])

def main(out):
    import matplotlib.pyplot as plt
    paths = sorted(pathlib.Path("results").glob("*.csv"))
    if not paths:
        raise SystemExit("no result CSV files found in results/")

    prefix = pathlib.Path(out)
    if prefix.suffix:
        prefix = prefix.with_suffix("")
    magnitude_path = prefix.with_name(prefix.name + "_magnitude.png")
    complex_path = prefix.with_name(prefix.name + "_complex_plane.png")
    magnitude_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(14, 8))
    for p in paths:
        x, re, im, mag = read(p)
        label = p.stem.replace("_", " ")
        ax.plot(x, mag, label=label, linewidth=2)
    ax.set(title="Input impedance magnitude by receiver position",
           xlabel="Receiver position (coil pitches)", ylabel="|Zeq| (ohm)")
    ax.grid(True, alpha=.3)
    ax.legend(fontsize=10)
    fig.tight_layout()
    fig.savefig(magnitude_path, dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 10))
    for p in paths:
        x, re, im, mag = read(p)
        label = p.stem.replace("_", " ")
        ax.plot(re, im, label=label, linewidth=2)
    ax.set(title="Input impedance trajectory",
           xlabel="Re[Zeq] (ohm)", ylabel="Im[Zeq] (ohm)")
    ax.grid(True, alpha=.3)
    ax.legend(fontsize=10)
    ax.set_aspect("equal", adjustable="datalim")
    fig.tight_layout()
    fig.savefig(complex_path, dpi=220)
    plt.close(fig)
    print(f"Wrote {magnitude_path} and {complex_path}")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/curves")
