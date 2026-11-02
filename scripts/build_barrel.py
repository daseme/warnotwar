#!/usr/bin/env python3
"""
Build data/barrel.json for the barrel page: what a barrel costs, layer by layer,
for the parties to the war.

Pulls from the EIA (no key):
  - the monthly pump-price components for regular gasoline and diesel, the only
    machine-readable form being the two php tables
    (gaspump_hist.php, dieselpump_hist.php), back to 2000 and 2002;
  - weekly retail prices (pswrgvwall.xls, psw18vwall.xls), back to 1990 and 1994;
  - monthly WTI and Brent spot (RWTCm.xls, RBRTEm.xls) and monthly U.S. crude
    exports (MCREXUS2m.xls) from the dnav history files.
Reads data/barrel_quotes.csv, the hand-kept ledger of dated per-barrel quotes for
the Gulf exporter's barrel, Iran's barrel and the American producer.

Nothing is converted from one unit to another. Dollar layers are the source's
own per-barrel or per-gallon figures; shares are shares the source gave, or the
sum of sourced per-barrel layers against Brent for the same month, and the page
says which.

Usage: oilflows/.venv/bin/python scripts/build_barrel.py [--cache DIR] [--offline]
"""
import argparse
import csv
import datetime as dt
import io
import json
import os
import re
import sys
import urllib.request
from html.parser import HTMLParser

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
UA = {"User-Agent": "Mozilla/5.0 (warnotwar.com data build)"}
EIA = {
    "gas_components": "https://www.eia.gov/petroleum/gasdiesel/gaspump_hist.php",
    "diesel_components": "https://www.eia.gov/petroleum/gasdiesel/dieselpump_hist.php",
    "gas_weekly": "https://www.eia.gov/petroleum/gasdiesel/xls/pswrgvwall.xls",
    "diesel_weekly": "https://www.eia.gov/petroleum/gasdiesel/xls/psw18vwall.xls",
    "wti_monthly": "https://www.eia.gov/dnav/pet/hist_xls/RWTCm.xls",
    "brent_monthly": "https://www.eia.gov/dnav/pet/hist_xls/RBRTEm.xls",
    "exports_monthly": "https://www.eia.gov/dnav/pet/hist_xls/MCREXUS2m.xls",
}
WAR_START = "2026-02-28"
PREWAR_MONTH = "2026-02"
MON = {m: i + 1 for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}
MON["Sept"] = 9


def fetch(url, cache, offline):
    name = os.path.join(cache, re.sub(r"[^A-Za-z0-9.]+", "_", url.split("/")[-1]) or "index")
    if offline or (os.path.exists(name) and (dt.datetime.now().timestamp() - os.path.getmtime(name)) < 6 * 3600):
        if not os.path.exists(name):
            sys.exit(f"offline and no cache for {url}")
        return open(name, "rb").read()
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        b = r.read()
    os.makedirs(cache, exist_ok=True)
    open(name, "wb").write(b)
    return b


class Table(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.row, self.cell = [], None, None

    def handle_starttag(self, t, a):
        if t == "tr":
            self.row = []
        if t in ("td", "th") and self.row is not None:
            self.cell = ""

    def handle_endtag(self, t):
        if t in ("td", "th") and self.cell is not None:
            self.row.append(" ".join(self.cell.split()))
            self.cell = None
        if t == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None

    def handle_data(self, d):
        if self.cell is not None:
            self.cell += d


def components(html):
    """Rows of the EIA pump components table: month, retail $/gal, and the four shares in percent."""
    p = Table()
    p.feed(html.decode("utf-8", "replace"))
    hdr = next(r for r in p.rows if r and r[0].lower().startswith("mon"))
    idx = {}
    for i, h in enumerate(hdr):
        h = h.lower()
        if "retail" in h: idx["price"] = i
        elif "refining" in h: idx["refining"] = i
        elif "distribution" in h: idx["distribution"] = i
        elif "tax" in h: idx["taxes"] = i
        elif "crude" in h: idx["crude"] = i
    assert set(idx) == {"price", "refining", "distribution", "taxes", "crude"}, hdr
    out = []
    for r in p.rows:
        if len(r) != len(hdr) or not re.match(r"[A-Z][a-z]{2,8}-\d\d$", r[0]):
            continue
        mon, yy = r[0].split("-")
        month = f"{2000 + int(yy)}-{MON[mon[:3]]:02d}"
        price = float(r[idx["price"]])
        shares = {k: float(r[idx[k]]) for k in ("crude", "refining", "distribution", "taxes")}
        # dollars per gallon by component: the share times the price; EIA computes the shares from cents, so this is a rounding of its own figures
        dollars = {k: round(price * v / 100.0, 3) for k, v in shares.items()}
        out.append({"month": month, "price": price, "share": shares, "usd": dollars})
    out.sort(key=lambda x: x["month"])
    return out


def weekly(xls):
    d = pd.read_excel(io.BytesIO(xls), sheet_name="Data 1", header=2)
    s = d.iloc[:, [0, 1]].dropna()
    s.columns = ["date", "v"]
    return [{"date": str(a)[:10], "v": round(float(b), 3)} for a, b in zip(s.date, s.v)]


def monthly(xls):
    d = pd.read_excel(io.BytesIO(xls), sheet_name="Data 1", header=2)
    s = d.iloc[:, [0, 1]].dropna()
    s.columns = ["date", "v"]
    return {str(a)[:7]: round(float(b), 2) for a, b in zip(s.date, s.v)}


def records(series, key, latest_month):
    """Where the latest value sits against the whole series: rank from the top and the previous higher month."""
    vals = [(x["month"], x[key]) for x in series]
    cur = next(v for m, v in vals if m == latest_month)
    higher = [m for m, v in vals if v > cur and m != latest_month]
    rank = len(higher) + 1
    prev_higher = max(higher) if higher else None
    return {"value": cur, "rank_from_top": rank, "of": len(vals), "previous_higher_month": prev_higher}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=os.environ.get("BARREL_CACHE", os.path.join(os.path.expanduser("~"), ".cache", "warnotwar-eia")))
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()

    gas = components(fetch(EIA["gas_components"], a.cache, a.offline))
    dsl = components(fetch(EIA["diesel_components"], a.cache, a.offline))
    gas_w = weekly(fetch(EIA["gas_weekly"], a.cache, a.offline))
    dsl_w = weekly(fetch(EIA["diesel_weekly"], a.cache, a.offline))
    wti = monthly(fetch(EIA["wti_monthly"], a.cache, a.offline))
    brent = monthly(fetch(EIA["brent_monthly"], a.cache, a.offline))
    exports = monthly(fetch(EIA["exports_monthly"], a.cache, a.offline))

    with open(os.path.join(DATA, "barrel_quotes.csv"), encoding="utf-8", newline="") as f:
        quotes = list(csv.DictReader(f))
    for q in quotes:
        for k in ("value", "value_low", "value_high"):
            q[k] = float(q[k]) if q[k] not in ("", None) else None

    # ---- the driver's barrel: components since January 2025 for the strip, the whole series for records
    latest_c = gas[-1]["month"]
    assert dsl[-1]["month"] == latest_c, (latest_c, dsl[-1]["month"])
    def facts(series, w):
        lm = series[-1]["month"]
        pre = next(x for x in series if x["month"] == PREWAR_MONTH)
        cur = series[-1]
        wmax = max(w, key=lambda x: x["v"])
        wlatest = w[-1]
        higher_weeks = [x for x in w if x["v"] > wlatest["v"]]
        return {
            "latest_month": lm,
            "prewar": pre, "latest": cur,
            "change_usd": {k: round(cur["usd"][k] - pre["usd"][k], 3) for k in cur["usd"]},
            "price_change": round(cur["price"] - pre["price"], 3),
            "refining_share": records(series, "price", lm) and {**records([{"month": x["month"], "v": x["share"]["refining"]} for x in series], "v", lm)},
            "crude_share": records([{"month": x["month"], "v": x["share"]["crude"]} for x in series], "v", lm),
            "distribution_share": records([{"month": x["month"], "v": x["share"]["distribution"]} for x in series], "v", lm),
            "price_month": records([{"month": x["month"], "v": x["price"]} for x in series], "v", lm),
            "weekly": {"latest": wlatest, "max": wmax, "first": w[0]["date"], "latest_rank_from_top": len(higher_weeks) + 1, "weeks": len(w),
                        "war_max": max((x for x in w if x["date"] >= WAR_START), key=lambda x: x["v"])},
        }
    driver = {
        "gasoline": {"series_from": gas[0]["month"], "months": [x for x in gas if x["month"] >= "2025-01"], "facts": facts(gas, gas_w),
                      "weekly_since_2025": [x for x in gas_w if x["date"] >= "2025-01-01"]},
        "diesel": {"series_from": dsl[0]["month"], "months": [x for x in dsl if x["month"] >= "2025-01"], "facts": facts(dsl, dsl_w),
                    "weekly_since_2025": [x for x in dsl_w if x["date"] >= "2025-01-01"]},
    }

    # ---- the exporter's barrel at checkpoints: Brent for the month plus the sourced per-barrel layers
    # Brent for a month the EIA has not posted yet: the average of FRED's daily Brent spot in data/market_daily.json, so far
    brent_src = {}
    try:
        md = json.load(open(os.path.join(DATA, "market_daily.json")))
        bym = {}
        for r in md:
            if r.get("brent_spot") is not None:
                bym.setdefault(r["date"][:7], []).append((r["date"], r["brent_spot"]))
        for m, rows in bym.items():
            if m not in brent and m >= "2026-01":
                brent[m] = round(sum(v for _, v in rows) / len(rows), 2)
                brent_src[m] = f"average of FRED daily Brent spot, {len(rows)} days to {max(d for d, _ in rows)}"
    except FileNotFoundError:
        pass

    gulf = [q for q in quotes if q["barrel"] == "gulf"]
    checkpoints = ["2026-01", "2026-03", "2026-06", "2026-09", "2026-10"]
    LAYERS = ["freight", "war_risk", "sts", "fuel"]
    exporter = []
    for cp in checkpoints:
        layers = {}
        for L in LAYERS:
            qs = [q for q in gulf if q["layer"] == L and q["checkpoint"] == cp and q["value"] is not None and q["unit"] == "usd_per_barrel"]
            if qs:
                # when two sources price the same layer in the same month, the higher is the range top, the lower the bottom; the midpoint is drawn
                vals = [q["value"] for q in qs]
                layers[L] = {"usd": round(sum(vals) / len(vals), 2), "low": min(q["value_low"] or q["value"] for q in qs), "high": max(q["value_high"] or q["value"] for q in qs),
                             "quotes": [q["quote_id"] for q in qs]}
        notes = [q for q in gulf if q["checkpoint"] == cp and q["unit"] != "usd_per_barrel"]
        b = brent.get(cp)
        priced = sum(v["usd"] for v in layers.values())
        exporter.append({
            "checkpoint": cp, "brent": b, "brent_source": brent_src.get(cp, "EIA monthly average"), "layers": layers, "logistics_usd": round(priced, 2),
            "logistics_share_of_delivered": round(100 * priced / (b + priced), 1) if b and priced else None,
            "logistics_share_of_fob": round(100 * priced / b, 1) if b and priced else None,
            "complete": all(L in layers for L in LAYERS),
            "unpriced_layers": [L for L in LAYERS if L not in layers],
            "other_quotes": [q["quote_id"] for q in notes],
        })

    iran = [q for q in quotes if q["barrel"] == "iran"]
    iran_cp = []
    for cp in ["2026-02", "2026-03", "2026-06", "2026-08", "2026-09", "2026-10"]:
        disc = [q for q in iran if q["layer"] == "discount" and q["checkpoint"] == cp]
        vol = [q for q in iran if q["layer"] == "volume" and q["checkpoint"] == cp]
        if not disc and not vol:
            continue
        iran_cp.append({"checkpoint": cp, "brent": brent.get(cp),
                        "discount": disc[0]["value"] if disc else None, "discount_quote": disc[0]["quote_id"] if disc else None,
                        "volume_mbd": vol[0]["value"] if vol else None, "volume_quote": vol[0]["quote_id"] if vol else None,
                        "volume_known": bool(vol) and vol[0]["value"] is not None})
    prewar_vol = next((c["volume_mbd"] for c in iran_cp if c["checkpoint"] == PREWAR_MONTH), None)

    us = [q for q in quotes if q["barrel"] == "us"]
    months_2026 = sorted(m for m in wti if m >= "2025-01")
    producer = {
        "wti": [{"month": m, "usd": wti[m]} for m in months_2026],
        "brent": [{"month": m, "usd": brent[m], "source": brent_src.get(m, "EIA")} for m in sorted(brent) if m >= "2025-01"],
        "exports_kbd": [{"month": m, "kbd": exports[m]} for m in sorted(exports) if m >= "2025-01"],
        "prewar_wti": wti.get(PREWAR_MONTH), "latest_wti": {"month": months_2026[-1], "usd": wti[months_2026[-1]]},
        "exports_prewar": exports.get(PREWAR_MONTH), "exports_peak": max(((m, v) for m, v in exports.items() if m >= "2026-01"), key=lambda t: t[1]),
        "quotes": [q["quote_id"] for q in us],
    }

    out = {
        "schema_version": 1,
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "war_start": WAR_START, "prewar_month": PREWAR_MONTH,
        "driver": driver,
        "exporter": {"checkpoints": exporter, "layers": LAYERS, "claim": next((q["quote_id"] for q in gulf if q["layer"] == "claim"), None),
                      "share_series": [q["quote_id"] for q in gulf if q["layer"] == "freight_share"]},
        "iran": {"checkpoints": iran_cp, "prewar_volume_mbd": prewar_vol},
        "producer": producer,
        "quotes": {q["quote_id"]: q for q in quotes},
        "sources": {
            "components": "EIA Gasoline and Diesel Fuel Update, pump components history (gaspump_hist.php, dieselpump_hist.php), latest month " + latest_c,
            "weekly": "EIA weekly retail prices, pswrgvwall.xls and psw18vwall.xls, latest week " + gas_w[-1]["date"],
            "spot": "EIA spot prices, RWTC and RBRTE monthly, latest " + months_2026[-1],
            "exports": "EIA U.S. exports of crude oil, MCREXUS2 monthly, latest " + max(exports),
            "quotes": "data/barrel_quotes.csv, " + str(len(quotes)) + " dated quotes",
        },
        "method": {
            "components": "EIA's four components: crude is the refiner acquisition cost; refining is the spot price of the fuel less crude; distribution and marketing is the retail price less the other three; taxes are the national average of federal and state taxes. Refining and distribution are residuals, costs and profits together, and swing against each other when the retail price lags the spot price. Dollars per gallon here are EIA's shares times its retail price.",
            "exporter": "Each layer is a source's own per-barrel figure for that month, never a conversion from a day rate or a percentage of hull value; where two sources priced the same layer the midpoint is drawn and both are cited. The oil is Brent's monthly average from the EIA. The logistics share is the sum of the priced layers against Brent plus those layers. A checkpoint with an unpriced layer is marked, and its share is a floor.",
            "iran": "The discount is the price of Iranian Light against ICE Brent quoted by traders for that month; the fill is the export volume against the pre-war 1.7 million barrels a day. October has a volume statement and no price, because no cargo was being sold.",
        },
    }
    with open(os.path.join(DATA, "barrel.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(f"components to {latest_c}; weekly to {gas_w[-1]['date']}; spot to {months_2026[-1]}; exports to {max(exports)}")
    for e in exporter:
        print(f"  {e['checkpoint']} brent {e['brent']} logistics {e['logistics_usd']} share of delivered {e['logistics_share_of_delivered']} complete={e['complete']} unpriced={e['unpriced_layers']}")
    d = driver["diesel"]["facts"]
    print(f"  diesel {d['latest_month']}: refining share rank {d['refining_share']['rank_from_top']} of {d['refining_share']['of']}; weekly max {d['weekly']['max']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
