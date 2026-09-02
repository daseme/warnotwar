"""Build data/market_daily.json + data/market_meta.json for market.html.

Question the page asks: the shock is big, but is anyone outside the oil
pit reacting? Sources:
  - FRED (DCOILBRENTEU, OVXCLS, VIXCLS, DGS10) when FRED_KEY is set
  - keyless fallbacks otherwise, or if a FRED call fails: Brent spot from
    the EIA RBRTE workbook; ^OVX, ^VIX, ^TNX from Yahoo Finance
  - BNO and SPY daily closes from Yahoo Finance always

Nothing is fabricated on failure: a source that cannot be fetched raises,
and the workflow leaves the previous files in place.
"""
import datetime as dt
import io
import json
import math
import os
import statistics
import sys
import urllib.request
from zoneinfo import ZoneInfo

import xlrd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DAILY = os.path.join(ROOT, "data", "market_daily.json")
OUT_META = os.path.join(ROOT, "data", "market_meta.json")

NY = ZoneInfo("America/New_York")
UA = {"User-Agent": "Mozilla/5.0 (warnotwar.com data refresh)"}

EIA_BRENT_XLS = "https://www.eia.gov/dnav/pet/hist_xls/RBRTEd.xls"
YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=2y&interval=1d"
FRED = ("https://api.stlouisfed.org/fred/series/observations"
        "?series_id={sid}&api_key={key}&file_type=json&observation_start={start}")
FRED_KEY = os.environ.get("FRED_KEY", "").strip()

START = "2025-06-23"          # first day of the site's BNO record
WAR_START = "2026-02-28"      # consensus start of the war
YOY_TROUBLE = (75, 100)       # Wilson's YoY "trouble zone", spot-price rule
BNO_LOW, BNO_HIGH = 49, 55    # the heuristic's level lines
JUMP_PCT = 4.0                # a one-day BNO move that counts as an event
CORR_WINDOW = 20


def get(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def yahoo_closes(sym):
    """{date: close} keyed by New York calendar date. Drops today's bar if
    the session has not closed, so a half-day never lands in the record."""
    raw = json.loads(get(YAHOO.format(sym=sym)))
    res = raw["chart"]["result"][0]
    ts = res["timestamp"]
    closes = res["indicators"]["quote"][0]["close"]
    now_ny = dt.datetime.now(NY)
    today = now_ny.strftime("%Y-%m-%d")
    closed = now_ny.hour > 16 or (now_ny.hour == 16 and now_ny.minute >= 10)
    out = {}
    for t, c in zip(ts, closes):
        if c is None:
            continue
        d = dt.datetime.fromtimestamp(t, NY).strftime("%Y-%m-%d")
        if d == today and not closed:
            continue
        out[d] = round(float(c), 4)
    if not out:
        raise RuntimeError(f"yahoo {sym}: no closes")
    return out


def eia_brent_spot():
    """{date: usd/bbl} from the EIA dnav daily Brent workbook. Layout is
    checked (Sourcekey RBRTE, a Date header) rather than assumed."""
    book = xlrd.open_workbook(file_contents=get(EIA_BRENT_XLS))
    sh = book.sheet_by_name("Data 1")
    key = None
    start = None
    for i in range(min(sh.nrows, 10)):
        row = sh.row_values(i)
        if row and str(row[0]).strip() == "Sourcekey":
            key = str(row[1]).strip()
        if row and str(row[0]).strip() == "Date":
            start = i + 1
    if key != "RBRTE" or start is None:
        raise RuntimeError(f"EIA Brent sheet: unexpected layout (key={key})")
    out = {}
    for i in range(start, sh.nrows):
        d, v = sh.row_values(i)[:2]
        if d == "" or v == "":
            continue
        date = dt.datetime(*xlrd.xldate_as_tuple(d, book.datemode)[:3]).strftime("%Y-%m-%d")
        out[date] = round(float(v), 2)
    if not out:
        raise RuntimeError("EIA Brent sheet: no observations")
    return out


def fred_series(sid, start):
    """{date: value} from FRED; '.' marks a missing observation there."""
    raw = json.loads(get(FRED.format(sid=sid, key=FRED_KEY, start=start)))
    out = {}
    for o in raw.get("observations", []):
        if o["value"] not in (".", ""):
            out[o["date"]] = round(float(o["value"]), 4)
    if not out:
        raise RuntimeError(f"FRED {sid}: no observations")
    return out


def with_fallback(name, primary, fallback):
    """Try FRED first when a key is present; otherwise, or on any failure,
    use the keyless source. Returns (series, source_label)."""
    if FRED_KEY:
        try:
            return primary(), f"FRED {name}"
        except Exception as e:  # noqa: BLE001 - any failure falls back
            print(f"FRED {name} failed ({e}); using fallback", file=sys.stderr)
    return fallback()


def prior_obs(series_dates, series, target, tolerance_days=7):
    """Value at the latest observation on or before `target`, if it is
    within `tolerance_days`; else None."""
    import bisect
    i = bisect.bisect_right(series_dates, target) - 1
    if i < 0:
        return None
    d = series_dates[i]
    gap = (dt.date.fromisoformat(target) - dt.date.fromisoformat(d)).days
    return series[d] if gap <= tolerance_days else None


def pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return None
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return sxy / math.sqrt(sxx * syy)


def r(v, nd=2):
    return None if v is None else round(v, nd)


def main():
    # Brent needs a year of history before START for the YoY base
    fred_start = (dt.date.fromisoformat(START) - dt.timedelta(days=380)).isoformat()
    brent, src_brent = with_fallback("DCOILBRENTEU",
        lambda: fred_series("DCOILBRENTEU", fred_start),
        lambda: (eia_brent_spot(), "EIA RBRTE workbook"))
    ovx, src_ovx = with_fallback("OVXCLS",
        lambda: fred_series("OVXCLS", fred_start),
        lambda: (yahoo_closes("^OVX"), "Yahoo ^OVX"))
    vix, src_vix = with_fallback("VIXCLS",
        lambda: fred_series("VIXCLS", fred_start),
        lambda: (yahoo_closes("^VIX"), "Yahoo ^VIX"))
    tnx, src_10y = with_fallback("DGS10",
        lambda: fred_series("DGS10", fred_start),
        lambda: (yahoo_closes("^TNX"), "Yahoo ^TNX"))
    bno = yahoo_closes("BNO")
    spy = yahoo_closes("SPY")

    brent_dates = sorted(brent)
    # the equity calendar is the row calendar; oil-only days are not rows
    calendar = sorted(d for d in spy if d >= START)
    if not calendar:
        raise RuntimeError("no trading days on or after START")

    # daily returns need the day before START too
    all_spy = sorted(spy)
    all_bno = sorted(bno)

    def ret(series, ordered, d):
        i = ordered.index(d)
        if i == 0:
            return None
        p0 = series[ordered[i - 1]]
        return (series[d] / p0 - 1) * 100

    spy_ret_hist, bno_ret_hist = [], []   # aligned (date, spy_ret, bno_ret)
    peak = max(spy[d] for d in all_spy if d <= calendar[0])

    rows = []
    for d in calendar:
        row = {"date": d}
        b = brent.get(d)
        row["brent_spot"] = b
        yoy = None
        if b is not None:
            base_day = (dt.date.fromisoformat(d) - dt.timedelta(days=365)).isoformat()
            base = prior_obs(brent_dates, brent, base_day)
            if base:
                yoy = (b / base - 1) * 100
        row["brent_yoy_pct"] = r(yoy, 1)

        p = bno.get(d)
        row["bno"] = p
        bret = ret(bno, all_bno, d) if d in bno else None
        row["bno_ret_pct"] = r(bret, 2)
        row["bno_jump"] = bool(bret is not None and bret >= JUMP_PCT)
        row["bno_brent_ratio"] = r(p / b, 4) if (p is not None and b is not None) else None

        row["ovx"] = ovx.get(d)
        row["vix"] = vix.get(d)
        row["ovx_vix"] = r(ovx[d] / vix[d], 2) if (d in ovx and d in vix and vix[d]) else None

        s = spy[d]
        sret = ret(spy, all_spy, d)
        row["spy"] = s
        row["spy_ret_pct"] = r(sret, 2)
        peak = max(peak, s)
        row["spy_drawdown_pct"] = r((s / peak - 1) * 100, 2)

        corr = None
        if sret is not None and bret is not None:
            spy_ret_hist.append(sret)
            bno_ret_hist.append(bret)
            if len(spy_ret_hist) >= CORR_WINDOW:
                corr = pearson(spy_ret_hist[-CORR_WINDOW:], bno_ret_hist[-CORR_WINDOW:])
        row["corr20"] = r(corr, 3)

        row["us10y"] = tnx.get(d)
        rows.append(row)

    # what does BNO 55 mean in Brent terms right now? trailing-60-obs
    # median of the BNO/Brent ratio, so one odd day cannot move it
    ratios = [x["bno_brent_ratio"] for x in rows if x["bno_brent_ratio"] is not None][-60:]
    ratio_med = statistics.median(ratios) if ratios else None

    def last(field):
        for x in reversed(rows):
            if x[field] is not None:
                return x["date"], x[field]
        return None, None

    meta = {
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "schema_version": 1,
        "window_start": START,
        "war_start": WAR_START,
        "thresholds": {
            "brent_yoy_trouble_pct": list(YOY_TROUBLE),
            "bno_low": BNO_LOW, "bno_high": BNO_HIGH,
            "bno_jump_pct": JUMP_PCT, "corr_window_days": CORR_WINDOW,
        },
        "latest": {k: {"date": last(k)[0], "value": last(k)[1]} for k in
                   ["brent_spot", "brent_yoy_pct", "bno", "ovx", "vix", "ovx_vix",
                    "corr20", "spy_drawdown_pct", "us10y"]},
        "bno_brent_ratio_60obs_median": r(ratio_med, 4),
        "brent_equiv_of_bno_high": r(BNO_HIGH / ratio_med, 1) if ratio_med else None,
        "brent_equiv_of_bno_low": r(BNO_LOW / ratio_med, 1) if ratio_med else None,
        "jump_days": [x["date"] for x in rows if x["bno_jump"]],
        "sources": {
            "brent_spot": src_brent + " (EIA Europe Brent Spot FOB, daily, published weekly)",
            "ovx": src_ovx, "vix": src_vix, "us10y": src_10y,
            "bno_spy": "Yahoo Finance daily closes: BNO, SPY",
        },
    }

    with open(OUT_DAILY, "w") as f:
        json.dump(rows, f, separators=(",", ":"))
    with open(OUT_META, "w") as f:
        json.dump(meta, f, indent=1)
    print(f"{len(rows)} rows {rows[0]['date']}..{rows[-1]['date']}; "
          f"brent through {meta['latest']['brent_spot']['date']}; "
          f"{len(meta['jump_days'])} jump days")


if __name__ == "__main__":
    main()
