#!/usr/bin/env bash
# Rebuild the oilflows published artifacts and copy the site-facing files
# into the public data/ directory the static site serves.
#
# This covers the build/publish half of the pipeline. A full data refresh
# (PortWatch, JODI, SOMO, market pulls) still runs upstream of this; see
# OILFLOWS_INTEGRATION_BRIEF.md §12 for the dependency order. SOMO workbook
# download remains a manual step.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/oilflows"

PY=".venv/bin/python"
if [ ! -x "$PY" ]; then
  PY="python3"
fi

"$PY" -m pytest -q
"$PY" -m oilflows.build_master >/dev/null
"$PY" -m oilflows.build_shock_timeline >/dev/null
"$PY" -m oilflows.build_publish

mkdir -p "$ROOT/data"
cp data/published/oilflows_daily.json "$ROOT/data/"
cp data/published/oilflows_meta.json "$ROOT/data/"
# Optional download/debug artifact for the "view the data" link.
cp data/published/oilflows_daily.csv "$ROOT/data/"

echo
echo "Copied oilflows_daily.{json,csv} + oilflows_meta.json -> $ROOT/data/"
