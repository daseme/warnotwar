import json
import math

import pandas as pd

from oilflows.publish import (
    build_publish_daily,
    build_publish_metadata,
    build_shock_markers,
    dataframe_to_json_records,
)


def make_master():
    dates = pd.date_range("2026-03-01", periods=8, freq="D")

    return pd.DataFrame(
        {
            "date": dates,
            "hormuz_tanker_count_7d": [10] * 8,
            "hormuz_tanker_count_index_7d": [100, 70, 60, 40, 30, 20, 5, 4],
            "known_gulf_official_7d_mbd": [4.0] * 8,
            "known_gulf_official_index_7d": [100] * 8,
            "core_official_exports_7d_mbd": [10.0] * 8,
            "core_official_exports_index_7d": [100] * 8,
            "saudi_gulf_proxy_index_7d": [100] * 8,
            "saudi_bypass_proxy_index_7d": [100] * 8,
            "uae_gulf_proxy_index_7d": [100] * 8,
            "uae_bypass_proxy_index_7d": [100] * 8,
            "brent_spot_last_usd": [70, 72, 74, 80, 85, 90, 100, 95],
            # Weekend Mar 7-8: last close carried forward, not observed.
            "brent_observed": [True] * 6 + [False, False],
            "bno_last_close_usd": [30, 31, 32, 34, 36, 38, 42, 41],
            "bno_observed": [True] * 6 + [False, False],
        }
    )


def make_timeline():
    return pd.DataFrame(
        {
            "threshold_pct": [75.0, 50.0, 10.0, 5.0],
            "first_date": [
                "2026-03-02",
                "2026-03-04",
                "2026-03-07",
                "2026-03-07",
            ],
        }
    )


def make_response():
    return pd.DataFrame(
        {
            "market": ["Brent spot", "BNO close"],
            "peak_date": ["2026-03-07", "2026-03-08"],
        }
    )


def test_shock_markers_combine_multiple_events_same_day():
    markers = build_shock_markers(
        make_timeline(),
        make_response(),
    )

    assert markers[pd.Timestamp("2026-03-07")] == (
        "hormuz_below_10pct|hormuz_below_5pct|brent_peak"
    )


def test_publish_daily_keeps_compact_schema():
    result = build_publish_daily(
        make_master(),
        make_timeline(),
        make_response(),
    )

    assert "allocation_method" not in result.columns
    assert "shock_marker" in result.columns
    assert "brent_observed" in result.columns
    assert "bno_observed" in result.columns
    assert len(result.columns) == 16


def test_publish_metadata_tracks_latest_nonnull_date():
    master = make_master()
    master.loc[
        master["date"] > pd.Timestamp("2026-03-06"),
        "known_gulf_official_index_7d",
    ] = float("nan")

    daily = build_publish_daily(
        master,
        make_timeline(),
        make_response(),
    )
    metadata = build_publish_metadata(daily)

    assert (
        metadata["latest_observation_dates"]["known_gulf_official"]
        == "2026-03-06"
    )


def test_publish_metadata_market_freshness_uses_observations():
    # The last two calendar days only carry forward-filled market values,
    # so freshness must report the last actually observed trading day.
    daily = build_publish_daily(
        make_master(),
        make_timeline(),
        make_response(),
    )
    metadata = build_publish_metadata(daily)

    assert metadata["latest_observation_dates"]["brent"] == "2026-03-06"
    assert metadata["latest_observation_dates"]["bno"] == "2026-03-06"
    # The carried-forward last values still extend to the end of the frame.
    assert daily["brent_spot_last_usd"].notna().all()


def test_publish_metadata_includes_generated_at_utc():
    daily = build_publish_daily(
        make_master(),
        make_timeline(),
        make_response(),
    )

    metadata = build_publish_metadata(
        daily,
        generated_at_utc="2026-08-26T00:00:00Z",
    )
    assert metadata["generated_at_utc"] == "2026-08-26T00:00:00Z"

    stamped = build_publish_metadata(daily)
    assert stamped["generated_at_utc"].endswith("Z")


def test_json_records_emit_null_not_nan():
    master = make_master()
    master.loc[
        master["date"] > pd.Timestamp("2026-03-05"),
        "hormuz_tanker_count_index_7d",
    ] = float("nan")

    daily = build_publish_daily(
        master,
        make_timeline(),
        make_response(),
    )
    text = dataframe_to_json_records(daily)

    assert "NaN" not in text

    records = json.loads(text)
    tail = records[-1]
    assert tail["hormuz_tanker_count_index_7d"] is None
    assert tail["bno_observed"] is False
    assert not any(
        isinstance(value, float) and math.isnan(value)
        for record in records
        for value in record.values()
    )
