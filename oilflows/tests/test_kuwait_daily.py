import pandas as pd

from oilflows.kuwait_daily import allocate_jodi_month


def test_allocate_jodi_month_reconciles_exactly():
    dates = pd.date_range("2026-01-01", periods=3, freq="D")
    portwatch = pd.DataFrame(
        {
            "date": dates,
            "export_tanker": [1.0, 2.0, 3.0],
        }
    )

    result = allocate_jodi_month(
        period_start=dates[0],
        period_end=dates[-1],
        official_kbd=200.0,
        assessment_code="3",
        source_year_file=2026,
        portwatch=portwatch,
    )

    official = 200_000.0 * 3
    assert result["kuwait_crude_barrels"].sum() == official
    assert result["allocation_method"].iloc[0] == "official_portwatch_weighted"


def test_allocate_jodi_month_uses_official_flat_when_signal_missing():
    dates = pd.date_range("2026-01-01", periods=3, freq="D")
    portwatch = pd.DataFrame(
        {
            "date": dates,
            "export_tanker": [0.0, 0.0, 0.0],
        }
    )

    result = allocate_jodi_month(
        period_start=dates[0],
        period_end=dates[-1],
        official_kbd=200.0,
        assessment_code="3",
        source_year_file=2026,
        portwatch=portwatch,
    )

    assert result["kuwait_crude_barrels"].tolist() == [200000.0] * 3
    assert result["kuwait_crude_barrels"].sum() == 600000.0
    assert (
        result["allocation_method"].iloc[0]
        == "official_monthly_flat_no_portwatch_signal"
    )


def test_allocate_jodi_month_refuses_partial_portwatch_period():
    dates = pd.date_range("2026-01-01", periods=3, freq="D")
    portwatch = pd.DataFrame(
        {
            "date": dates[1:],
            "export_tanker": [1.0, 1.0],
        }
    )

    result = allocate_jodi_month(
        period_start=dates[0],
        period_end=dates[-1],
        official_kbd=200.0,
        assessment_code="3",
        source_year_file=2026,
        portwatch=portwatch,
    )

    assert result["kuwait_crude_barrels"].isna().all()
    assert (
        result["allocation_method"].iloc[0]
        == "unavailable_partial_portwatch_period"
    )
