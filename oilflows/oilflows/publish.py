from __future__ import annotations

from collections import defaultdict
import json

import pandas as pd


PUBLISH_COLUMNS = [
    "date",
    "hormuz_tanker_count_7d",
    "hormuz_tanker_count_index_7d",
    "known_gulf_official_7d_mbd",
    "known_gulf_official_index_7d",
    "core_official_exports_7d_mbd",
    "core_official_exports_index_7d",
    "saudi_gulf_proxy_index_7d",
    "saudi_bypass_proxy_index_7d",
    "uae_gulf_proxy_index_7d",
    "uae_bypass_proxy_index_7d",
    "brent_spot_last_usd",
    "brent_observed",
    "bno_last_close_usd",
    "bno_observed",
    "shock_marker",
]


def build_publish_daily(
    master: pd.DataFrame,
    shock_timeline: pd.DataFrame,
    market_response: pd.DataFrame,
) -> pd.DataFrame:
    """Build the compact site-facing daily oil-flow dataset.

    This intentionally excludes implementation details, raw PortWatch tonnage,
    source filenames, assessment codes, and other internal calibration fields.

    Important semantics:
      * Hormuz index: 100 = Jul-Dec 2025 tanker-count baseline.
      * known_gulf_official: Iraq Basrah + Kuwait only.
      * core_official_exports: Iraq Basrah + Kuwait + Saudi NATIONAL exports;
        it is not a Hormuz-only flow measure.
      * Saudi/UAE route indices are PortWatch activity proxies, not official
        national route shares.
      * Brent/BNO fields are last observed market values on the calendar date;
        brent_observed/bno_observed mark whether that calendar date carries an
        actual market observation or a carried-forward last value.
    """
    required = set(PUBLISH_COLUMNS) - {"shock_marker"}
    missing = sorted(required - set(master.columns))
    if missing:
        raise RuntimeError(
            f"Master dataset missing publish columns: {missing}"
        )

    frame = master[list(required)].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="raise")

    if frame["date"].duplicated().any():
        raise RuntimeError("Duplicate dates found in master dataset.")

    markers = build_shock_markers(
        shock_timeline,
        market_response,
    )

    frame["shock_marker"] = frame["date"].map(markers)

    return (
        frame[PUBLISH_COLUMNS]
        .sort_values("date")
        .reset_index(drop=True)
    )


def build_shock_markers(
    shock_timeline: pd.DataFrame,
    market_response: pd.DataFrame,
) -> dict[pd.Timestamp, str]:
    markers: defaultdict[pd.Timestamp, list[str]] = defaultdict(list)

    threshold_required = {"threshold_pct", "first_date"}
    if not threshold_required.issubset(shock_timeline.columns):
        missing = sorted(threshold_required - set(shock_timeline.columns))
        raise RuntimeError(
            f"Shock timeline missing columns: {missing}"
        )

    for row in shock_timeline.itertuples(index=False):
        date = pd.Timestamp(row.first_date)
        threshold = float(row.threshold_pct)

        if threshold.is_integer():
            label = str(int(threshold))
        else:
            label = str(threshold).rstrip("0").rstrip(".")

        markers[date].append(f"hormuz_below_{label}pct")

    response_required = {"market", "peak_date"}
    if not response_required.issubset(market_response.columns):
        missing = sorted(response_required - set(market_response.columns))
        raise RuntimeError(
            f"Market response missing columns: {missing}"
        )

    for row in market_response.itertuples(index=False):
        date = pd.Timestamp(row.peak_date)
        market = str(row.market).lower()

        if "brent" in market:
            markers[date].append("brent_peak")
        elif "bno" in market:
            markers[date].append("bno_peak")

    return {
        date: "|".join(labels)
        for date, labels in markers.items()
    }


def build_publish_metadata(
    publish: pd.DataFrame,
    *,
    generated_from: str = "oilflows_daily_master.csv",
    generated_at_utc: str | None = None,
) -> dict:
    frame = publish.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="raise")

    def latest_nonnull(column: str) -> str | None:
        rows = frame.loc[frame[column].notna(), "date"]
        if rows.empty:
            return None
        return rows.max().date().isoformat()

    def latest_observed(flag_column: str) -> str | None:
        # Freshness must reflect an actual market observation, never the
        # carried-forward *_last_* value.
        observed = frame[flag_column].fillna(False).astype(bool)
        rows = frame.loc[observed, "date"]
        if rows.empty:
            return None
        return rows.max().date().isoformat()

    if generated_at_utc is None:
        generated_at_utc = (
            pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ")
        )

    return {
        "schema_version": 2,
        "generated_at_utc": generated_at_utc,
        "generated_from": generated_from,
        "first_date": frame["date"].min().date().isoformat(),
        "last_date": frame["date"].max().date().isoformat(),
        "baseline": {
            "start": "2025-07-01",
            "end": "2025-12-31",
            "index_value": 100,
        },
        "latest_observation_dates": {
            "hormuz": latest_nonnull("hormuz_tanker_count_index_7d"),
            "known_gulf_official":
                latest_nonnull("known_gulf_official_index_7d"),
            "core_official_exports":
                latest_nonnull("core_official_exports_index_7d"),
            "saudi_gulf_proxy":
                latest_nonnull("saudi_gulf_proxy_index_7d"),
            "saudi_bypass_proxy":
                latest_nonnull("saudi_bypass_proxy_index_7d"),
            "uae_gulf_proxy":
                latest_nonnull("uae_gulf_proxy_index_7d"),
            "uae_bypass_proxy":
                latest_nonnull("uae_bypass_proxy_index_7d"),
            "brent": latest_observed("brent_observed"),
            "bno": latest_observed("bno_observed"),
        },
        "definitions": {
            "hormuz_tanker_count_index_7d":
                "7-day Hormuz tanker-count activity; 100 = Jul-Dec 2025 baseline.",
            "known_gulf_official_7d_mbd":
                "Official/calibrated Iraq Basrah + Kuwait crude exports, 7-day average mb/d.",
            "core_official_exports_7d_mbd":
                "Iraq Basrah + Kuwait + Saudi national crude exports, 7-day average mb/d; not Hormuz-only.",
            "saudi_gulf_proxy_index_7d":
                "Juaymah PortWatch Gulf-route activity proxy; 100 = Jul-Dec 2025 baseline.",
            "saudi_bypass_proxy_index_7d":
                "Yanbu PortWatch Red Sea bypass activity proxy; 100 = Jul-Dec 2025 baseline.",
            "uae_gulf_proxy_index_7d":
                "Ruways + Das Island PortWatch Gulf activity proxy; 100 = Jul-Dec 2025 baseline.",
            "uae_bypass_proxy_index_7d":
                "Fujairah PortWatch bypass/mixed activity proxy; 100 = Jul-Dec 2025 baseline.",
            "brent_spot_last_usd":
                "Most recently observed Brent spot price on or before the calendar date.",
            "bno_last_close_usd":
                "Most recently observed BNO unadjusted close on or before the calendar date.",
            "brent_observed":
                "True when the calendar date carries an actual Brent spot observation; false when brent_spot_last_usd is carried forward.",
            "bno_observed":
                "True when the calendar date carries an actual BNO trading close; false when bno_last_close_usd is carried forward.",
            "shock_marker":
                "Pipe-delimited event marker for threshold crossings or market peaks.",
        },
        "intentional_exclusions": [
            "Iran daily export estimate: public PortWatch coverage too sparse.",
            "Qatar daily export estimate: key terminal coverage incomplete.",
            "Saudi national Gulf-vs-bypass allocation: Ras Tanura absent from PortWatch.",
        ],
    }


def dataframe_to_json_records(
    frame: pd.DataFrame,
    *,
    date_column: str = "date",
) -> str:
    out = frame.copy()
    out[date_column] = (
        pd.to_datetime(out[date_column]).dt.strftime("%Y-%m-%d")
    )
    # Float columns silently coerce None back to NaN, and json.dumps would
    # then emit a literal NaN token that browsers reject; go through object
    # dtype so missing values become real JSON nulls.
    out = out.astype(object).where(pd.notna(out), None)
    records = out.to_dict(orient="records")
    return json.dumps(
        records,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
