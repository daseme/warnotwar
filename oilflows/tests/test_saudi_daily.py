import pandas as pd

from oilflows.saudi_daily import (
    build_saudi_daily,
    expand_saudi_jodi_daily,
)


def test_expand_saudi_jodi_daily_keeps_official_monthly_level_flat():
    jodi = pd.DataFrame(
        {
            "period_start": [pd.Timestamp("2026-01-01")],
            "period_end": [pd.Timestamp("2026-01-03")],
            "crude_exports_kbd": [7000.0],
            "assessment_code": ["3"],
            "source_year_file": [2026],
        }
    )

    result = expand_saudi_jodi_daily(jodi)

    assert result["saudi_official_crude_mbd"].tolist() == [7.0, 7.0, 7.0]
    assert result["saudi_official_crude_kbd"].tolist() == [7000.0] * 3


def test_saudi_route_proxy_share_uses_only_juaymah_and_yanbu():
    dates = pd.date_range("2026-01-01", periods=7, freq="D")

    portwatch = pd.concat(
        [
            pd.DataFrame(
                {
                    "date": dates,
                    "portid": "port526",
                    "export_tanker": 100.0,
                }
            ),
            pd.DataFrame(
                {
                    "date": dates,
                    "portid": "port570",
                    "export_tanker": 300.0,
                }
            ),
        ],
        ignore_index=True,
    )

    jodi = pd.DataFrame(
        {
            "month": ["2026-01-01"],
            "country_code": ["SA"],
            "crude_exports_kbd": [7000.0],
            "assessment_code": ["3"],
            "source_year_file": [2026],
        }
    )

    result = build_saudi_daily(
        portwatch,
        jodi,
        start_date="2026-01-01",
    )

    row = result.loc[result["date"].eq(pd.Timestamp("2026-01-07"))].iloc[0]

    assert row["saudi_gulf_juaymah_proxy_mt_7d"] == 100.0
    assert row["saudi_bypass_yanbu_proxy_mt_7d"] == 300.0
    assert row["saudi_proxy_bypass_share_7d"] == 0.75


def test_saudi_proxy_can_continue_after_last_jodi_month():
    dates = pd.date_range("2026-01-01", "2026-02-07", freq="D")

    portwatch = pd.concat(
        [
            pd.DataFrame(
                {
                    "date": dates,
                    "portid": "port526",
                    "export_tanker": 100.0,
                }
            ),
            pd.DataFrame(
                {
                    "date": dates,
                    "portid": "port570",
                    "export_tanker": 200.0,
                }
            ),
        ],
        ignore_index=True,
    )

    jodi = pd.DataFrame(
        {
            "month": ["2026-01-01"],
            "country_code": ["SA"],
            "crude_exports_kbd": [7000.0],
            "assessment_code": ["3"],
            "source_year_file": [2026],
        }
    )

    result = build_saudi_daily(
        portwatch,
        jodi,
        start_date="2026-01-01",
    )

    feb = result.loc[result["date"].eq(pd.Timestamp("2026-02-07"))].iloc[0]

    assert pd.isna(feb["saudi_official_crude_mbd"])
    assert feb["saudi_bypass_yanbu_proxy_mt"] == 200.0
    assert feb["saudi_official_status"] == "proxy_only_pending_jodi"
