#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if (($# < 1)); then
  echo "Usage: $0 OUTPUT.csv [ARRAY_CELLS] [TERMINATION_OHMS] [RECEIVER_R_OHMS] [RECEIVER_X_OHMS]" >&2
  exit 2
fi
cd "$ROOT"
make resonator-array
exec ./resonator-array "$@"
