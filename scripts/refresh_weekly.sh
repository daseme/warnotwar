#!/usr/bin/env bash
# CI-safe weekly refresh: EIA-based artifacts + the claims ledger only.
# (PortWatch/JODI/SOMO/market refreshes need local raw state and stay manual.)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/oilflows"

PY="${PYTHON:-python3}"
"$PY" -m oilflows.pull_eia_inventory
"$PY" -m oilflows.build_buffer
"$PY" -m oilflows.build_products
"$PY" -m oilflows.build_verification
"$PY" -m pytest tests/test_eia_inventory.py tests/test_verification.py -q

mkdir -p "$ROOT/data"
cp data/published/us_crude_buffer_weekly.json "$ROOT/data/"
cp data/published/us_crude_buffer_weekly.csv "$ROOT/data/"
cp data/published/us_crude_buffer_meta.json "$ROOT/data/"
cp data/published/us_products_weekly.json "$ROOT/data/"
cp data/published/us_products_meta.json "$ROOT/data/"
cp data/published/hormuz_verification.json "$ROOT/data/"
cp data/published/us_oil_flow_claims.json "$ROOT/data/"
echo "weekly refresh complete"
