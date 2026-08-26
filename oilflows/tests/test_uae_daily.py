import pandas as pd

from oilflows.uae_daily import build_uae_daily


def make_portwatch(start="2025-07-01", days=14):
    dates = pd.date_range(start, periods=days, freq="D")

    return pd.concat(
        [
            pd.DataFrame(
                {
                    "date": dates,
                    "portid": "port512",
                    "export_tanker": 100.0,
                }
            ),
            pd.DataFrame(
                {
                    "date": dates,
                    "portid": "port2237",
                    "export_tanker": 50.0,
                }
            ),
            pd.DataFrame(
                {
                    "date": dates,
                    "portid": "port362",
                    "export_tanker": 150.0,
                }
            ),
        ],
        ignore_index=True,
    )


def test_uae_gulf_proxy_sums_ruways_and_das():
    portwatch = make_portwatch()

    result = build_uae_daily(
        portwatch,
        start_date="2025-07-01",
        baseline_start="2025-07-01",
        baseline_end="2025-07-14",
    )

    row = result.loc[
        result["date"].eq(pd.Timestamp("2025-07-07"))
    ].iloc[0]

    assert row["uae_gulf_proxy_mt"] == 150.0
    assert row["uae_gulf_proxy_mt_7d"] == 150.0
    assert row["uae_bypass_fujairah_proxy_mt_7d"] == 150.0


def test_uae_baseline_indices_equal_100_for_constant_series():
    portwatch = make_portwatch()

    result = build_uae_daily(
        portwatch,
        start_date="2025-07-01",
        baseline_start="2025-07-01",
        baseline_end="2025-07-14",
    )

    row = result.iloc[-1]

    assert row["uae_gulf_proxy_index_7d"] == 100.0
    assert row["uae_bypass_proxy_index_7d"] == 100.0
    assert row["uae_proxy_bypass_share_7d"] == 0.5


def test_uae_status_is_proxy_only():
    portwatch = make_portwatch()

    result = build_uae_daily(
        portwatch,
        start_date="2025-07-01",
        baseline_start="2025-07-01",
        baseline_end="2025-07-14",
    )

    assert set(result["uae_official_status"]) == {
        "proxy_only_no_jodi_export_volume"
    }
