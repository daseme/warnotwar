import pandas as pd

from oilflows.iraq_daily import allocate_somo_period


def base_inputs(portwatch_values, hormuz_values):
    dates = pd.date_range("2026-01-01", periods=3, freq="D")

    portwatch = pd.DataFrame(
        {"date": dates, "export_tanker": portwatch_values}
    )
    hormuz = pd.DataFrame(
        {"date": dates, "hormuz_tanker_count": hormuz_values}
    )

    return dates, portwatch, hormuz


def test_allocate_somo_period_prefers_portwatch_weights():
    dates, portwatch, hormuz = base_inputs(
        [1.0, 2.0, 3.0],
        [9.0, 9.0, 9.0],
    )

    result = allocate_somo_period(
        period_start=dates[0],
        period_end=dates[-1],
        basrah_barrels=600.0,
        total_barrels=700.0,
        portwatch_basrah=portwatch,
        hormuz_daily=hormuz,
        source_file="test.xlsx",
        granularity="month",
    )

    assert result.method == "official_portwatch_weighted"
    assert result.frame["iraq_basrah_barrels"].tolist() == [100.0, 200.0, 300.0]
    assert result.frame["iraq_basrah_barrels"].sum() == 600.0


def test_allocate_somo_period_falls_back_to_hormuz_when_portwatch_zero():
    dates, portwatch, hormuz = base_inputs(
        [0.0, 0.0, 0.0],
        [1.0, 1.0, 2.0],
    )

    result = allocate_somo_period(
        period_start=dates[0],
        period_end=dates[-1],
        basrah_barrels=400.0,
        total_barrels=500.0,
        portwatch_basrah=portwatch,
        hormuz_daily=hormuz,
        source_file="test.xlsx",
        granularity="month",
    )

    assert result.method == "official_hormuz_weighted"
    assert result.frame["iraq_basrah_barrels"].tolist() == [100.0, 100.0, 200.0]
    assert result.frame["iraq_basrah_barrels"].sum() == 400.0


def test_allocate_somo_period_does_not_allocate_partial_portwatch_period():
    dates = pd.date_range("2026-01-01", periods=3, freq="D")
    portwatch = pd.DataFrame(
        {
            "date": dates[1:],
            "export_tanker": [1.0, 1.0],
        }
    )
    hormuz = pd.DataFrame(
        {
            "date": dates,
            "hormuz_tanker_count": [1.0, 1.0, 1.0],
        }
    )

    result = allocate_somo_period(
        period_start=dates[0],
        period_end=dates[-1],
        basrah_barrels=300.0,
        total_barrels=400.0,
        portwatch_basrah=portwatch,
        hormuz_daily=hormuz,
        source_file="test.xlsx",
        granularity="month",
    )

    assert result.method == "unavailable_partial_portwatch_period"
    assert result.frame["iraq_basrah_barrels"].isna().all()
