#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if (($# != 2)); then
  echo "Usage: $0 CALIBRATION.csv MEASUREMENTS.csv" >&2
  exit 2
fi
cd "$ROOT"
exec python3 scripts/locate.py "$@"
