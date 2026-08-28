"""Real-tape checkpoints for the teaching module (labs 6 and 8).

Red-team constraints this build encodes:
- Checkpoint eligibility uses only events statable WITHOUT the future:
  pre-shock anchor, ledger threshold crossings, month-firsts, latest.
  Peaks are hindsight; they ship separately as reveal-time annotations
  and are never selectable prediction origins.
- Every displayed value is an as-of join: the latest figure that had
  been PUBLISHED by the checkpoint date, per field, with its own date.
- Month-firsts snap forward to the first date with genuinely observed
  market closes; zero-value bypass index readings are outage artifacts
  and treated as missing.
- Scoring thresholds are computed here from the real anchor row and
  emitted with the data — no literals shared with the simulation.
- No free-text news field exists in this schema, by design.
"""

from datetime import datetime, timezone
from pathlib import Path
import json

import pandas as pd

# EIA weekly data for a Friday week-end is normally released the
# following Wednesday (+5 days); holiday weeks slip to Thursday. The
# conservative +6 never shows a reader data that was not yet public.
EIA_PUBLICATION_LAG_DAYS = 6

# PortWatch indices trail the calendar by a few days (today's file runs
# three days behind); the freeze frame shows the reading that age.
FLOW_PUBLICATION_LAG_DAYS = 3

# A checkpoint needs a flow reading no staler than this to be on the tape.
FLOW_STALE_MAX_DAYS = 10

PRESHOCK_ANCHOR = "2026-02-23"


def _market_observed(row) -> bool:
    return bool(row["brent_observed"]) and bool(row["bno_observed"])


def _snap_forward(daily: pd.DataFrame, date: str) -> str | None:
    """First date >= `date` with genuinely observed market closes."""
    later = daily.loc[(daily["date"] >= date)
                      & daily["brent_observed"] & daily["bno_observed"]]
    return None if later.empty else later.iloc[0]["date"]


def _flow_asof(daily: pd.DataFrame, col: str, date: str):
    """Latest non-null reading published by `date` (value, asof_date).

    Zero readings in the bypass proxies are outage artifacts (a working
    export terminal never indexes at exactly 0.0) and count as missing.
    """
    cutoff = (pd.Timestamp(date)
              - pd.Timedelta(days=FLOW_PUBLICATION_LAG_DAYS)).strftime(
                  "%Y-%m-%d")
    series = daily.loc[daily["date"] <= cutoff, ["date", col]].dropna()
    if col != "hormuz_tanker_count_index_7d":
        series = series.loc[series[col] != 0.0]
    if series.empty:
        return None, None
    last = series.iloc[-1]
    return round(float(last[col]), 1), last["date"]


def checkpoint_dates(daily: pd.DataFrame) -> list[dict]:
    """Rule-derived, hindsight-free checkpoint list (rule shown on page)."""
    out = [{"date": PRESHOCK_ANCHOR, "why": "pre-shock anchor"}]

    marked = daily.dropna(subset=["shock_marker"])
    thresholds = marked.loc[
        marked["shock_marker"].str.contains("hormuz_below")
    ]
    if thresholds.empty:
        raise RuntimeError("no Hormuz threshold markers in daily series")
    out.append({"date": thresholds.iloc[0]["date"],
                "why": "first Hormuz threshold crossing"})
    out.append({"date": thresholds.iloc[-1]["date"],
                "why": "last Hormuz threshold crossing"})

    last_flow = daily.dropna(
        subset=["hormuz_tanker_count_index_7d"]).iloc[-1]["date"]
    latest_eligible = daily.loc[
        daily["brent_observed"] & daily["bno_observed"]
        & (daily["date"] <= (
            pd.Timestamp(last_flow)
            + pd.Timedelta(days=FLOW_STALE_MAX_DAYS)
        ).strftime("%Y-%m-%d"))
    ].iloc[-1]["date"]

    month = pd.Timestamp(out[-1]["date"]).to_period("M") + 1
    while str(month.start_time.date()) <= latest_eligible:
        snapped = _snap_forward(daily, str(month.start_time.date()))
        if snapped and snapped < latest_eligible:
            out.append({"date": snapped,
                        "why": f"first market day of "
                               f"{month.start_time.strftime('%B')}"})
        month += 1
    out.append({"date": latest_eligible, "why": "latest observation"})

    seen, dedup = set(), []
    for c in sorted(out, key=lambda c: c["date"]):
        if c["date"] not in seen:
            seen.add(c["date"])
            dedup.append(c)
    return dedup


def peak_annotations(daily: pd.DataFrame) -> list[dict]:
    """Hindsight markers, drawn only at reveal time — never origins."""
    out = []
    marked = daily.dropna(subset=["shock_marker"])
    for marker, field, label in [
        ("brent_peak", "brent_spot_last_usd", "Brent peak"),
        ("bno_peak", "bno_last_close_usd", "BNO peak"),
    ]:
        hit = marked.loc[marked["shock_marker"].str.contains(marker)]
        if not hit.empty:
            row = hit.iloc[0]
            out.append({
                "date": row["date"],
                "label": label,
                "value": round(float(row[field]), 2),
                "note": "identifiable only in hindsight",
            })
    return out


def scoring_reads(daily: pd.DataFrame) -> list[dict]:
    """Freeze-frame factual reads, thresholds derived from the anchor."""
    anchor = daily.set_index("date").loc[PRESHOCK_ANCHOR]
    brent_up = round(float(anchor["brent_spot_last_usd"]) * 1.25, 2)
    hormuz0 = round(float(anchor["hormuz_tanker_count_index_7d"]), 1)
    return [
        {"key": "flow", "field": "hormuz", "op": "lt", "threshold": 15,
         "label": f"Hormuz activity index is below 15 "
                  f"(it read {hormuz0} on the pre-shock anchor day)"},
        {"key": "bypass", "field": "yanbu", "op": "gt", "threshold": 200,
         "label": "Yanbu activity index is above 200 — "
                  "at least twice its baseline"},
        {"key": "buffer", "field": "buffer", "op": "lt", "threshold": 45,
         "label": "The crude cushion is below 45 days of supply"},
        {"key": "brent", "field": "brent", "op": "gt",
         "threshold": brent_up,
         "label": f"Brent is up more than 25% from the pre-shock anchor "
                  f"(above ${brent_up:.2f})"},
        {"key": "calm", "field": "hormuz", "op": "gt", "threshold": 50,
         "label": "Hormuz activity index is above 50 — "
                  "more than half of baseline"},
    ]


def build_checkpoints(daily: pd.DataFrame, buffer: pd.DataFrame,
                      generated_at_utc: str | None = None) -> dict:
    rows = daily.set_index("date")
    buffer = buffer.copy()
    buffer["week_end"] = pd.to_datetime(buffer["week_end"])
    buffer["published"] = buffer["week_end"] + pd.Timedelta(
        days=EIA_PUBLICATION_LAG_DAYS
    )

    checkpoints = []
    cps = checkpoint_dates(daily)
    for i, c in enumerate(cps):
        d = c["date"]
        market = rows.loc[rows.index <= d]
        brent_row = market.loc[market["brent_observed"]].iloc[-1]
        bno_row = market.loc[market["bno_observed"]].iloc[-1]
        hormuz, hormuz_asof = _flow_asof(
            daily, "hormuz_tanker_count_index_7d", d)
        yanbu, yanbu_asof = _flow_asof(
            daily, "saudi_bypass_proxy_index_7d", d)
        fujairah, fujairah_asof = _flow_asof(
            daily, "uae_bypass_proxy_index_7d", d)
        avail = buffer.loc[buffer["published"] <= pd.Timestamp(d)]
        b = avail.iloc[-1] if not avail.empty else None
        nxt = cps[i + 1]["date"] if i + 1 < len(cps) else None
        checkpoints.append({
            "id": d,
            "date": d,
            "why": c["why"],
            "days_to_next": (
                (pd.Timestamp(nxt) - pd.Timestamp(d)).days
                if nxt else None),
            "brent": round(float(brent_row["brent_spot_last_usd"]), 2),
            "brent_asof": brent_row.name,
            "bno": round(float(bno_row["bno_last_close_usd"]), 2),
            "bno_asof": bno_row.name,
            "hormuz": hormuz, "hormuz_asof": hormuz_asof,
            "yanbu": yanbu, "yanbu_asof": yanbu_asof,
            "fujairah": fujairah, "fujairah_asof": fujairah_asof,
            "buffer": (round(float(b["days_supply_incl_spr"]), 1)
                       if b is not None else None),
            "buffer_week_end": (b["week_end"].date().isoformat()
                                if b is not None else None),
        })

    return {
        "schema_version": 2,
        "generated_at_utc": generated_at_utc or (
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")),
        "note": (
            "Real dated checkpoints from the record, for the teaching "
            "module's real-tape mode. Selection is rule-derived from "
            "events statable without knowing the future: pre-shock "
            "anchor, first and last Hormuz threshold crossings, "
            "month-firsts snapped to observed market days, latest "
            "observation. Every value is the latest figure PUBLISHED by "
            "the checkpoint date, per field, with its own as-of date. "
            "Peak markers are hindsight and ship as reveal-time "
            "annotations only."
        ),
        "revision_note": (
            "Archive values: activity indices are revised after first "
            "publication, so the reading a checkpoint shows is today's "
            "archive of that date, not a screenshot of what a reader "
            "saw then."
        ),
        "sources": {
            "flow_and_bypass": (
                "IMF PortWatch activity indices, 7-day "
                "(July–December 2025 average = 100); readings trail the "
                "calendar by a few days"),
            "brent": ("EIA Brent spot via FRED — latest close observed "
                      "by each date"),
            "bno": "BNO unadjusted close — latest observed by each date",
            "buffer": (
                "EIA weekly U.S. crude stocks incl. SPR divided by "
                "refinery inputs, in days; each week is released about "
                "five to six days after it ends, and the tape only "
                "shows weeks already released"),
        },
        "reads": scoring_reads(daily),
        "annotations": peak_annotations(daily),
        "checkpoints": checkpoints,
    }


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    published = project_root / "data" / "published"

    daily = pd.read_json(published / "oilflows_daily.json")
    daily["date"] = pd.to_datetime(daily["date"]).dt.strftime("%Y-%m-%d")
    buffer = pd.read_csv(published / "us_crude_buffer_weekly.csv")

    payload = build_checkpoints(daily, buffer)
    out = published / "hormuz_checkpoints.json"
    out.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False,
                   default=float),
        encoding="utf-8",
    )
    print(f"{len(payload['checkpoints'])} checkpoints "
          f"({payload['checkpoints'][0]['date']} .. "
          f"{payload['checkpoints'][-1]['date']}); "
          f"{len(payload['annotations'])} reveal annotations")
    for c in payload["checkpoints"]:
        print(f"  {c['date']}  brent {c['brent']:.2f} ({c['brent_asof']})  "
              f"bno {c['bno']:.2f} ({c['bno_asof']})  "
              f"hormuz {c['hormuz']} ({c['hormuz_asof']})  "
              f"yanbu {c['yanbu']}  "
              f"buffer {c['buffer']} (wk {c['buffer_week_end']})  "
              f"[{c['why']}]")
    print("Wrote", out)


if __name__ == "__main__":
    main()
