#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CURVE="${1:-results/termination_0p8.csv}"
cd "$ROOT"
make resonator-array
if [[ ! -f "$CURVE" ]]; then
  if [[ "$CURVE" == "results/termination_0p8.csv" ]]; then
    ./resonator-array "$CURVE" 6 0.8 40 10
  else
    echo "Calibration curve not found: $CURVE" >&2
    exit 1
  fi
fi
exec python3 scripts/visualize_3d.py "$CURVE"
