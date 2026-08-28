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

# Buffer layer: EIA raw files are gitignored, so fetch them when absent.
if [ ! -f data/raw/eia/WCRSTUS1w.xls ]; then
  "$PY" -m oilflows.pull_eia_inventory
fi
"$PY" -m oilflows.build_buffer
"$PY" -m oilflows.build_products

# Verification layer: hand-curated claims/estimates ledgers -> published JSON.
"$PY" -m oilflows.build_verification

# Teaching layer: real-tape checkpoints for the module's labs 6 and 8.
"$PY" -m oilflows.build_teaching

mkdir -p "$ROOT/data"
cp data/published/oilflows_daily.json "$ROOT/data/"
cp data/published/oilflows_meta.json "$ROOT/data/"
cp data/published/us_crude_buffer_weekly.json "$ROOT/data/"
cp data/published/us_crude_buffer_meta.json "$ROOT/data/"
cp data/published/us_products_weekly.json "$ROOT/data/"
cp data/published/us_products_meta.json "$ROOT/data/"
cp data/published/hormuz_verification.json "$ROOT/data/"
cp data/published/us_oil_flow_claims.json "$ROOT/data/"
cp data/published/hormuz_checkpoints.json "$ROOT/data/"
# Optional download/debug artifacts for the "view the data" links.
cp data/published/oilflows_daily.csv "$ROOT/data/"
cp data/published/us_crude_buffer_weekly.csv "$ROOT/data/"

echo
echo "Copied oilflows + buffer JSON/CSV/meta -> $ROOT/data/"
