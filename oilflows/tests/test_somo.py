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
