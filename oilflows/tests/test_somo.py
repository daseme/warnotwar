from pathlib import Path

import pandas as pd
from openpyxl import Workbook

from oilflows.somo import (
    SomoPeriod,
    periods_to_frame,
    validate_december_against_annual,
)


def test_periods_to_frame_computes_kbd():
    period = SomoPeriod(
        period_start=pd.Timestamp("2026-04-01"),
        period_end=pd.Timestamp("2026-04-30"),
        granularity="month",
        basrah_barrels=4_500_000,
        total_barrels=9_000_000,
        krg_barrels=300_000,
        source_file="x.xlsx",
        source_sheet="English",
    )

    frame = periods_to_frame([period])

    assert frame.iloc[0]["days"] == 30
    assert frame.iloc[0]["basrah_kbd"] == 150.0
    assert frame.iloc[0]["total_kbd"] == 300.0


def test_multi_month_period_uses_full_period_days():
    period = SomoPeriod(
        period_start=pd.Timestamp("2026-05-01"),
        period_end=pd.Timestamp("2026-06-30"),
        granularity="multi_month",
        basrah_barrels=20_238_836,
        total_barrels=32_114_677,
        krg_barrels=1_564_625,
        source_file="x.xlsx",
        source_sheet="English",
    )

    assert period.days == 61
    assert round(period.total_kbd, 3) == round(32_114_677 / 61 / 1000, 3)


def test_december_crosscheck_accepts_matching_values():
    annual = [
        SomoPeriod(
            period_start=pd.Timestamp("2025-12-01"),
            period_end=pd.Timestamp("2025-12-31"),
            granularity="month",
            basrah_barrels=100_420_048,
            total_barrels=107_651_061,
            krg_barrels=5_997_527,
            source_file="annual.xlsx",
            source_sheet="annual",
        )
    ]
    december = SomoPeriod(
        period_start=pd.Timestamp("2025-12-01"),
        period_end=pd.Timestamp("2025-12-31"),
        granularity="month",
        basrah_barrels=100_420_048,
        total_barrels=107_651_061,
        krg_barrels=5_997_527,
        source_file="december.xlsx",
        source_sheet="english",
    )

    validate_december_against_annual(annual, december)


def test_curated_reports_add_periods_and_leave_missing_months_out(tmp_path):
    from oilflows.somo import periods_to_frame, read_curated_reports, validate_periods

    path = tmp_path / "somo_reports.csv"
    path.write_text(
        "period_start,period_end,granularity,basrah_barrels,krg_barrels,total_barrels,source_file,source_url,note\n"
        "2026-08-01,2026-08-31,month,69754934,2173016,73687617,August report,https://example.org/a.pdf,note\n"
    )
    frame = periods_to_frame(read_curated_reports(path))
    validate_periods(frame)
    row = frame.iloc[0]
    assert row["days"] == 31
    assert round(row["basrah_kbd"], 1) == 2250.2
    assert round(row["total_kbd"], 1) == 2377.0
    assert row["source_sheet"] == "export summary"
