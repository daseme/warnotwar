#!/usr/bin/env python3
"""
Build data/quadrant.json: one row per week since the war began, placing the
week in Adam's quadrant. Two axes:

  think  — the Dean Street Heuristic as written on the front page: BNO's last
           close of the week. Under 49 peace, over 55 war, between them the
           perpetual war sweet spot.
  are    — the strait. Before the estimates ledger begins (24 Aug 2026) the
           PortWatch tanker-activity index from oilflows_daily.json (100 = a
           normal late-2025 week). From then on the newest independent tracker
           reading of oil leaving through Hormuz, from hormuz_verification.json,
           as a share of the pre-war rate. A week is "shut" when the strait is
           below three quarters of normal, the line the oilflows page already
           uses for the break in early March.

A second fact row carries Uppsala's deaths for the Gulf dyad by month, from
data/ucdp.json, so the two meanings of "are we at war" can be compared.

Usage: python3 scripts/build_quadrant.py [--prewar-mbd 17]
Reads only files already in data/. Writes data/quadrant.json.
"""
import argparse
import datetime as dt
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

WAR_START = dt.date(2026, 2, 28)
BNO_LOW, BNO_HIGH = 49.0, 55.0          # the heuristic, as on index.html
STRAIT_OPEN_SHARE = 0.75                # below this the strait counts as shut
DEATHS_WAR_MONTH = 84                   # 1,000 a year, UCDP's war line, by month
DEATHS_CONFLICT_MONTH = 25              # UCDP's conflict line, 25 a year, applied by month


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def d(s):
    return dt.date.fromisoformat(s[:10])


def monday(day):
    return day - dt.timedelta(days=day.weekday())


def think_state(bno):
    if bno is None:
        return None
    if bno < BNO_LOW:
        return "peace"
    if bno > BNO_HIGH:
        return "war"
    return "sweet"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prewar-mbd", type=float, default=17.0,
                    help="pre-war Hormuz outbound rate the tracker readings are set against")
    ap.add_argument("--today", default=None, help="override today's date, YYYY-MM-DD")
    args = ap.parse_args()
    prewar = args.prewar_mbd
    today = d(args.today) if args.today else dt.date.today()

    market = load("market_daily.json")
    flows = load("oilflows_daily.json")
    verif = load("hormuz_verification.json")
    ucdp = load("ucdp.json")

    bno = [(d(r["date"]), r["bno"]) for r in market if r.get("bno") is not None]
    bno.sort()
    pw = [(d(r["date"]), r["hormuz_tanker_count_index_7d"]) for r in flows
          if r.get("hormuz_tanker_count_index_7d") is not None]
    pw.sort()
    # independent readings: hormuz outbound, a central value, not a single-day print
    # the same family the verification panel uses: all-liquids figures never enter the crude series
    FAMILY = {"crude", "crude_condensate", "unspecified"}
    est_all = [e for e in verif["estimates"]
               if e.get("scope") == "hormuz_outbound" and e.get("value_central") is not None
               and e.get("period") != "single_day" and (e.get("commodity") or "unspecified") in FAMILY]
    est = [(d(e["estimate_date"]), e) for e in est_all if e.get("date_precision") != "month"]
    est.sort(key=lambda t: (t[0], t[1].get("entered_date") or ""))
    # a month-precision reading is the month's average: it covers every week of that month
    monthly = {}
    for e in est_all:
        if e.get("date_precision") == "month":
            monthly.setdefault(e["estimate_date"][:7], []).append(e)
    for m in monthly:
        monthly[m].sort(key=lambda e: (e.get("entered_date") or "", e["estimate_id"]))

    gulf = ucdp["entries"]["gulf"]
    month_keys = ucdp["months"]["keys"]
    gulf_months = dict(zip(month_keys, gulf["months"]["best"]))
    candidate_from = ucdp["months"].get("candidate_from")
    reach = ucdp["reach"]

    def latest(series, upto):
        v = None
        for day, val in series:
            if day <= upto:
                v = (day, val)
            else:
                break
        return v

    weeks = []
    wk = monday(WAR_START)
    if wk < WAR_START:                      # start with the first full week of the war
        wk += dt.timedelta(days=7)
    last_bno_day = bno[-1][0]
    while wk <= today:
        end = wk + dt.timedelta(days=6)
        cut = min(end, today)
        row = {"week": wk.isoformat(), "to": end.isoformat(), "partial": end > today}

        # think: last BNO close in the week
        in_week = [(day, v) for day, v in bno if wk <= day <= end]
        if in_week:
            row["bno"] = in_week[-1][1]
            row["bno_date"] = in_week[-1][0].isoformat()
            row["think"] = think_state(row["bno"])
            row["days"] = {s: sum(1 for _, v in in_week if think_state(v) == s) for s in ("peace", "sweet", "war")}
        else:
            lb = latest(bno, cut)
            row["bno"] = lb[1] if lb else None
            row["bno_date"] = lb[0].isoformat() if lb else None
            row["think"] = think_state(row["bno"])
            row["days"] = None
            row["bno_carried"] = True

        # are: the strait. The ledger first: a dated weekly reading as of the week's end if one exists
        # from the last 21 days, else the month's average if a tracker published one, else the newest
        # dated reading; ship signals only where the ledger has nothing at all.
        lp = latest(pw, cut)
        if lp:
            row["signals"] = {"index": round(lp[1], 1), "date": lp[0].isoformat(), "share": round(lp[1] / 100.0, 3)}
        le = latest(est, cut)
        mk_week = wk.strftime("%Y-%m")
        if le and (cut - le[0]).days <= 21:
            day, e = le
            row["strait"] = {"source": "ledger", "basis": "weekly", "tracker": e["tracker"], "mbd": e["value_central"],
                             "date": day.isoformat(), "share": round(e["value_central"] / prewar, 3), "estimate_id": e["estimate_id"]}
        elif mk_week in monthly:
            e = monthly[mk_week][-1]
            row["strait"] = {"source": "ledger", "basis": "monthly", "tracker": e["tracker"], "mbd": e["value_central"],
                             "date": e["estimate_date"], "share": round(e["value_central"] / prewar, 3), "estimate_id": e["estimate_id"]}
        elif le:
            day, e = le
            row["strait"] = {"source": "ledger", "basis": "weekly", "tracker": e["tracker"], "mbd": e["value_central"],
                             "date": day.isoformat(), "share": round(e["value_central"] / prewar, 3), "estimate_id": e["estimate_id"]}
        elif lp:
            row["strait"] = {"source": "portwatch", "basis": "signals", "index": round(lp[1], 1), "date": lp[0].isoformat(),
                             "share": round(lp[1] / 100.0, 3)}
        if "strait" in row:
            row["are"] = "shut" if row["strait"]["share"] < STRAIT_OPEN_SHARE else "open"
        else:
            row["are"] = None

        # deaths: the week's month
        mk = wk.strftime("%Y-%m")
        if mk in gulf_months:
            n = gulf_months[mk]
            row["deaths"] = {"month": mk, "best": n,
                             "state": "war" if n >= DEATHS_WAR_MONTH else ("fighting" if n >= DEATHS_CONFLICT_MONTH else "quiet"),
                             "provisional": bool(candidate_from and mk >= candidate_from)}
        else:
            row["deaths"] = {"month": mk, "best": None, "state": "unknown", "provisional": True}

        # the cell
        t, a = row["think"], row["are"]
        if t is None or a is None:
            cell = None
        elif a == "shut":
            cell = "are-think" if t == "war" else ("are-sweet" if t == "sweet" else "are-not-think")
        else:
            cell = "think-not-are" if t == "war" else ("open-sweet" if t == "sweet" else "neither")
        row["cell"] = cell
        weeks.append(row)
        wk += dt.timedelta(days=7)

    full = [w for w in weeks if not w["partial"] and w["cell"]]
    counts = {}
    for w in full:
        counts[w["cell"]] = counts.get(w["cell"], 0) + 1
    # the same weeks with the sweet spot read as the market thinking we are at war
    counts_sweet_as_think = {
        "are-think": counts.get("are-think", 0) + counts.get("are-sweet", 0),
        "are-not-think": counts.get("are-not-think", 0),
        "think-not-are": counts.get("think-not-are", 0) + counts.get("open-sweet", 0),
        "neither": counts.get("neither", 0),
    }
    # what Uppsala moved between its last two pulls, for the Gulf months
    deaths_moves = None
    hpath = os.path.join(DATA, "ucdp_history.json")
    if os.path.exists(hpath):
        pulls = json.load(open(hpath, encoding="utf-8"))["pulls"]
        pulls = [p for p in pulls if p.get("month_keys") and p["entries"].get("gulf", {}).get("months")]
        if len(pulls) >= 2:
            a, b = pulls[-2], pulls[-1]
            ma = dict(zip(a["month_keys"], a["entries"]["gulf"]["months"]["best"]))
            mb = dict(zip(b["month_keys"], b["entries"]["gulf"]["months"]["best"]))
            moved = [{"month": m, "from": ma[m], "to": mb[m]} for m in mb if m in ma and ma[m] != mb[m]]
            added = [m for m in mb if m not in ma]
            deaths_moves = {"from_pull": a["pulled"], "to_pull": b["pulled"], "moved": moved, "months_added": added}

    # lags: runs of weeks where the strait is shut and the market says peace
    lags, run = [], None
    for w in weeks:
        if w["are"] == "shut" and w["think"] == "peace":
            if run is None:
                run = {"from": w["week"], "to": w["to"], "weeks": 1}
            else:
                run["to"] = w["to"]; run["weeks"] += 1
        else:
            if run:
                run["ended_by"] = w["think"]; lags.append(run); run = None
    if run:
        run["ended_by"] = None; lags.append(run)

    current = weeks[-1]
    out = {
        "schema_version": 1,
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "war_start": WAR_START.isoformat(),
        "rules": {
            "think": f"The Dean Street Heuristic, as on the front page: BNO's last close of the week. Under ${BNO_LOW:.0f} peace, over ${BNO_HIGH:.0f} war, between them the perpetual war sweet spot.",
            "are": f"The strait. A week counts as shut when oil leaving through Hormuz is below three quarters of normal. The reading is the estimates ledger's: a dated weekly tracker figure as of the week's end when one is less than three weeks old, otherwise the tracker's published average for that month, against a pre-war rate of about {prewar:g} million barrels a day, the figure Kpler's own percentages imply. Single-day prints and all-liquids figures never count, the same rule as the verification panel. Where the ledger has nothing for a week, PortWatch's tanker-signal index against a normal late-2025 week stands in, and the week says so.",
            "deaths": f"Uppsala's deaths in the Gulf dyad by the month the event began, UCDP best estimate. {DEATHS_WAR_MONTH} or more in a month is the war line (1,000 a year); {DEATHS_CONFLICT_MONTH} or more is the conflict line. Months from the candidate files are provisional; months Uppsala has not reached are unknown.",
            "cells": {
                "are-think": "we are at war and we think we are",
                "are-not-think": "we are at war and we think we are not",
                "are-sweet": "we are at war and we think it is perpetual war",
                "think-not-are": "we are not at war but we think we are",
                "open-sweet": "we are not at war and we think it is perpetual war",
                "neither": "we are not at war and we think we are not",
            },
        },
        "thresholds": {"bno_low": BNO_LOW, "bno_high": BNO_HIGH, "strait_open_share": STRAIT_OPEN_SHARE,
                       "prewar_mbd": prewar, "deaths_war_month": DEATHS_WAR_MONTH, "deaths_conflict_month": DEATHS_CONFLICT_MONTH},
        "sources": {
            "bno": "data/market_daily.json (Yahoo Finance daily closes), last " + last_bno_day.isoformat(),
            "portwatch": "data/oilflows_daily.json, hormuz_tanker_count_index_7d, last " + pw[-1][0].isoformat(),
            "ledger": "data/hormuz_verification.json estimates, newest independent reading " + est[-1][0].isoformat(),
            "ucdp": f"data/ucdp.json, {ucdp['versions']}, reach {reach}, pulled {ucdp['pulled']}",
        },
        "deaths_months": [
            {"month": m, "best": gulf_months[m],
             "state": "war" if gulf_months[m] >= DEATHS_WAR_MONTH else ("fighting" if gulf_months[m] >= DEATHS_CONFLICT_MONTH else "quiet"),
             "provisional": bool(candidate_from and m >= candidate_from)}
            for m in month_keys if m >= WAR_START.strftime("%Y-%m")],
        "counts": counts,
        "counts_sweet_as_think": counts_sweet_as_think,
        "deaths_moves": deaths_moves,
        "weeks_full": len(full),
        "lags": lags,
        "current": current,
        "weeks": weeks,
    }
    with open(os.path.join(DATA, "quadrant.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
        f.write("\n")

    print(f"{len(weeks)} weeks from {weeks[0]['week']}; {len(full)} full weeks placed")
    for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {v:3d}  {k:16s} {out['rules']['cells'][k]}")
    for l in lags:
        print(f"  lag: {l['from']} to {l['to']}, {l['weeks']} weeks, ended by {l['ended_by']}")
    c = current
    print(f"now: week of {c['week']}: think={c['think']} (BNO {c['bno']}), are={c['are']} "
          f"({c.get('strait', {}).get('share')}), deaths={c['deaths']['state']} → {c['cell']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
