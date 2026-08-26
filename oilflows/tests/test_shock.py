import pandas as pd

from oilflows.shock import (
    build_market_response_summary,
    build_shock_timeline,
)


def make_master():
    dates = pd.date_range("2026-02-01", periods=10, freq="D")
    idx = [100, 90, 80, 74, 49, 24, 9, 4, 0.9, 2]

    return pd.DataFrame(
        {
            "date": dates,
            "hormuz_tanker_count_index_7d": idx,
            "brent_spot_last_usd": [70, 70, 71, 72, 75, 80, 90, 100, 110, 105],
            "bno_last_close_usd": [30, 30, 31, 31, 32, 34, 38, 42, 45, 44],
            "known_gulf_official_index_7d": idx,
            "core_official_exports_index_7d": idx,
            "saudi_gulf_proxy_index_7d": idx,
            "saudi_bypass_proxy_index_7d": [100] * 10,
            "uae_gulf_proxy_index_7d": idx,
            "uae_bypass_proxy_index_7d": [100] * 10,
        }
    )


def test_threshold_crossings_use_first_date_at_or_below_threshold():
    result = build_shock_timeline(
        make_master(),
        search_start="2026-02-01",
    )

    row75 = result.loc[result["threshold_pct"] == 75.0].iloc[0]
    row10 = result.loc[result["threshold_pct"] == 10.0].iloc[0]
    row1 = result.loc[result["threshold_pct"] == 1.0].iloc[0]

    assert row75["first_date"] == pd.Timestamp("2026-02-04")
    assert row10["first_date"] == pd.Timestamp("2026-02-07")
    assert row1["first_date"] == pd.Timestamp("2026-02-09")


def test_market_response_summary_finds_peak():
    result = build_market_response_summary(
        make_master(),
        anchor_date="2026-02-07",
        pre_days=3,
    )

    brent = result.loc[result["market"] == "Brent spot"].iloc[0]

    assert brent["pre_anchor_date"] == pd.Timestamp("2026-02-04")
    assert brent["pre_anchor_value"] == 72.0
    assert brent["anchor_value"] == 90.0
    assert brent["peak_value"] == 110.0
    assert brent["peak_date"] == pd.Timestamp("2026-02-09")
