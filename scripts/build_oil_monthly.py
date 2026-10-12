#!/usr/bin/env python3
"""Write data/oil_monthly.json: Brent and WTI by month from FRED, as far back as they go.

Usage: scripts/build_oil_monthly.py

Series: MCOILBRENTEU (Brent, Europe, from May 1987) and MCOILWTICO (WTI, Cushing,
from January 1986), monthly averages of daily spot prices as FRED publishes them,
dollars per barrel, not adjusted for inflation. No key is needed for the CSV endpoint.
"""
import csv
import io
import json
import os
import urllib.request
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERIES = {'brent': 'MCOILBRENTEU', 'wti': 'MCOILWTICO'}


def pull(sid):
    url = f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}'
    txt = urllib.request.urlopen(url, timeout=30).read().decode('utf-8')
    rows = list(csv.reader(io.StringIO(txt)))
    assert rows[0][1] == sid, rows[0]
    return [[r[0][:7], round(float(r[1]), 2)] for r in rows[1:] if r[1] not in ('', '.')]


def main():
    out = {
        'rule': 'Monthly average spot prices as FRED publishes them, dollars per barrel, not adjusted for inflation: Brent (Europe) from May 1987, WTI (Cushing) from January 1986. Drawn beside the deaths because they share the years, nothing more.',
        'source': {k: f'FRED series {v}' for k, v in SERIES.items()},
        'pulled': date.today().isoformat(),
    }
    for k, sid in SERIES.items():
        out[k] = pull(sid)
    json.dump(out, open(os.path.join(ROOT, 'data', 'oil_monthly.json'), 'w'), separators=(',', ':'))
    print('wrote data/oil_monthly.json:', {k: (v[0][0], v[-1][0], len(v)) for k, v in out.items() if isinstance(v, list)})


if __name__ == '__main__':
    main()
