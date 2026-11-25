#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if (($# < 2)); then
  echo "Usage: $0 CALIBRATION.csv MEASUREMENTS.csv [tracker options]" >&2
  echo "Example: $0 results/termination_0p8.csv measurements_complex.csv --noise 0.03 --motion 0.08" >&2
  exit 2
fi
cd "$ROOT"
make receiver-position-tracker
exec ./receiver-position-tracker "$@"
