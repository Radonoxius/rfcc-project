#!/usr/bin/env bash
set -euo pipefail
mkdir -p results
make
./rfcc results/short.csv 6 0.0 40 10
./rfcc results/matched.csv 6 1.82 40 10
./rfcc results/open.csv 6 1000000000 40 10
./rfcc results/termination_0p8.csv 6 0.8 40 10
./rfcc results/termination_0p8_12cells.csv 12 0.8 40 10
if command -v python3 >/dev/null && python3 -c 'import matplotlib' 2>/dev/null; then
  python3 scripts/plot_results.py results/curves.png
fi
echo "Replication data written to results/"
