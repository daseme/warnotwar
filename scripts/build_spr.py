#!/usr/bin/env python3
"""Build spr/data/spr_stocks.json from EIA's weekly and monthly SPR stock workbooks.

Weekly:  WCSSTUS1 (thousand barrels, week ending Friday, 1982-)
Monthly: MCSSTUS1 (thousand barrels, 1977-)
Output values are in million barrels, rounded to 0.01.
"""
import json, sys, urllib.request, io, datetime, pathlib

try:
    import xlrd
except ImportError:
    sys.exit("needs xlrd:  pip install xlrd")

URL = "https://www.eia.gov/dnav/pet/hist_xls/{key}.xls"
OUT = pathlib.Path(__file__).resolve().parent.parent / "spr" / "data" / "spr_stocks.json"


def fetch(key):
    req = urllib.request.Request(URL.format(key=key), headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
    if raw[:4] != b"\xd0\xcf\x11\xe0":
        raise RuntimeError(f"{key}: not a legacy .xls workbook")
    wb = xlrd.open_workbook(file_contents=raw)
    sh = wb.sheet_by_index(1)
    rows = []
    for r in range(sh.nrows):
        d, v = sh.cell(r, 0), sh.cell(r, 1)
        if d.ctype == 3 and v.ctype == 2:
            dt = xlrd.xldate_as_datetime(d.value, wb.datemode).date()
            rows.append([dt.isoformat(), round(v.value / 1000.0, 2)])
    if len(rows) < 100:
        raise RuntimeError(f"{key}: only {len(rows)} observations")
    return rows


def main():
    weekly = fetch("WCSSTUS1w")
    monthly = fetch("MCSSTUS1m")
    last_d, last_v = weekly[-1]
    prev_d, prev_v = weekly[-2]
    peak = max(weekly, key=lambda r: r[1])
    # last week before now at or below the current level (how far back to find a lower reserve)
    lower = [r for r in weekly[:-1] if r[1] <= last_v]
    out = {
        "generated": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
        "units": "million barrels",
        "source": "EIA weekly WCSSTUS1 and monthly MCSSTUS1",
        "latest": {"date": last_d, "mb": last_v, "week_change_mb": round(last_v - prev_v, 2)},
        "peak": {"date": peak[0], "mb": peak[1]},
        "last_lower": lower[-1][0] if lower else None,
        "weekly": weekly,
        "monthly": monthly,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, separators=(",", ":")))
    print(f"wrote {OUT} latest {last_d} {last_v} mb ({len(weekly)} weekly, {len(monthly)} monthly)")


if __name__ == "__main__":
    main()
