#!/usr/bin/env bash
# Weekly refresh, run by .github/workflows/update-oilflows.yml and by hand.
# Pulls every source the oilflows page uses, then rebuilds and publishes:
#   PortWatch ship signals (strait and terminals), JODI monthly exports,
#   Brent and BNO, EIA weekly stocks.
# SOMO's Iraq figures are not pulled: the workbooks in oilflows/data/raw/somo
# and the PDF-era rows in oilflows/data/curated/somo_reports.csv are kept by hand.
# Any failed pull stops the run before anything is copied into data/.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/oilflows"

PY="${PYTHON:-.venv/bin/python}"
if [ ! -x "$PY" ] && ! command -v "$PY" >/dev/null 2>&1; then
  PY="python3"
fi

for step in pull_portwatch build_hormuz pull_jodi build_somo build_iraq_daily \
            build_kuwait_daily build_saudi_daily build_uae_daily pull_market \
            pull_eia_inventory; do
  echo "== $step"
  "$PY" -m "oilflows.$step" >/dev/null
done

# tests, master, shock timeline, publish, buffer, products, verification,
# teaching checkpoints, then the copy into data/
PYTHON="$PY" bash "$ROOT/scripts/publish_oilflows.sh"

# the quadrant reads the files just published
cd "$ROOT"
python3 scripts/build_quadrant.py >/dev/null
echo "weekly refresh complete"
