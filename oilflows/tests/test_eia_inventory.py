import json
import math

import pandas as pd
import pytest

from oilflows.eia_inventory import (
    build_buffer_metadata,
    build_buffer_weekly,
    historical_percentile,
    parse_eia_weekly_xls,
    prior_lower_date,
    validate_stock_identity,
)
from oilflows.publish import dataframe_to_json_records


def weekly(values, column, start="2026-01-02"):
    dates = pd.date_range(start, periods=len(values), freq="7D")
    return pd.DataFrame({"week_end": dates, column: values})


def make_inputs(n=5):
    return (
        weekly([800_000 - 10_000 * i for i in range(n)],
               "crude_stocks_incl_spr_mbbl"),
        weekly([420_000 - 8_000 * i for i in range(n)],
               "commercial_crude_mbbl"),
        weekly([380_000 - 2_000 * i for i in range(n)],
               "spr_crude_mbbl"),
        weekly([16_000] * n, "refinery_crude_inputs_mbd"),
    )


def test_days_supply_units_cancel_to_days():
    frame = build_buffer_weekly(*make_inputs())

    # 800,000 thousand bbl / 16,000 thousand bbl per day = 50 days
    assert frame.loc[0, "days_supply_incl_spr"] == pytest.approx(50.0)
    assert frame.loc[0, "commercial_days_supply"] == pytest.approx(26.25)
    assert frame.loc[0, "spr_days_equivalent"] == pytest.approx(23.75)
    # identity: incl_spr = commercial + spr components
    assert frame.loc[0, "days_supply_incl_spr"] == pytest.approx(
        frame.loc[0, "commercial_days_supply"]
        + frame.loc[0, "spr_days_equivalent"]
    )


def test_join_keeps_only_matching_weeks():
    incl, com, spr, inputs = make_inputs()
    inputs = inputs.iloc[1:]  # one series missing the first week

    frame = build_buffer_weekly(incl, com, spr, inputs)

    assert len(frame) == 4
    assert frame["week_end"].min() == pd.Timestamp("2026-01-09")


def test_missing_and_zero_inputs_do_not_divide():
    incl, com, spr, inputs = make_inputs()
    inputs.loc[0, "refinery_crude_inputs_mbd"] = 0.0
    inputs.loc[1, "refinery_crude_inputs_mbd"] = float("nan")

    frame = build_buffer_weekly(incl, com, spr, inputs)

    assert pd.isna(frame.loc[0, "days_supply_incl_spr"])
    assert pd.isna(frame.loc[1, "days_supply_incl_spr"])
    assert not any(
        math.isinf(v)
        for v in frame["days_supply_incl_spr"].dropna()
    )


def test_stock_identity_violation_fails_loudly():
    incl, com, spr, inputs = make_inputs()
    com.loc[2, "commercial_crude_mbbl"] = 100_000  # blow up the identity

    with pytest.raises(RuntimeError, match="identity"):
        build_buffer_weekly(incl, com, spr, inputs)

    assert validate_stock_identity(
        build_buffer_weekly(*make_inputs())
    ) <= 0.01


def test_historical_percentile_definition():
    series = pd.Series([50.0, 40.0, 45.0, float("nan"), 40.0])
    pct = historical_percentile(series)

    # 100 * count(history <= value) / count(history), over 4 observations
    assert pct[0] == pytest.approx(100.0)
    assert pct[1] == pytest.approx(50.0)   # two of four <= 40
    assert pct[2] == pytest.approx(75.0)
    assert pd.isna(pct[3])


def test_prior_lower_date_and_years():
    frame = pd.DataFrame(
        {
            "week_end": pd.to_datetime(
                ["2020-01-03", "2022-01-07", "2026-01-02"]
            ),
            "days_supply_incl_spr": [38.0, 60.0, 41.0],
        }
    )

    when, years = prior_lower_date(frame)
    assert when == "2020-01-03"
    assert years == pytest.approx(6.0, abs=0.1)


def test_prior_lower_returns_none_at_all_time_low():
    frame = pd.DataFrame(
        {
            "week_end": pd.to_datetime(["2020-01-03", "2026-01-02"]),
            "days_supply_incl_spr": [50.0, 41.0],
        }
    )

    assert prior_lower_date(frame) == (None, None)


def test_metadata_reports_latest_week_and_context():
    frame = build_buffer_weekly(*make_inputs())
    meta = build_buffer_metadata(
        frame,
        generated_at_utc="2026-08-26T00:00:00Z",
    )

    assert meta["first_week"] == "2026-01-02"
    assert meta["last_week"] == "2026-01-30"
    assert meta["latest_days_supply_incl_spr"] == pytest.approx(47.5)
    assert meta["historical_min_days_supply_incl_spr"] == pytest.approx(47.5)
    # stocks fall monotonically, so the latest week is the all-time low
    assert meta["prior_lower_date"] is None
    assert meta["current_percentile"] == pytest.approx(20.0)
    assert meta["generated_at_utc"] == "2026-08-26T00:00:00Z"
    # the countdown guardrail lives in the published definitions
    assert "not a countdown" in meta["definitions"]["days_supply_incl_spr"]


def test_buffer_json_emits_null_not_nan():
    incl, com, spr, inputs = make_inputs()
    inputs.loc[0, "refinery_crude_inputs_mbd"] = float("nan")
    frame = build_buffer_weekly(incl, com, spr, inputs)

    text = dataframe_to_json_records(frame, date_column="week_end")

    assert "NaN" not in text
    records = json.loads(text)
    assert records[0]["days_supply_incl_spr"] is None
    assert records[0]["week_end"] == "2026-01-02"


def test_parse_rejects_wrong_sourcekey(tmp_path):
    # Build a minimal fake dnav workbook in the legacy layout.
    frame = pd.DataFrame(
        [
            ["Back to Contents", "Data 1: Weekly Fake Series"],
            ["Sourcekey", "WRONGKEY1"],
            ["Date", "Weekly Fake Series (Thousand Barrels)"],
            [pd.Timestamp("2026-01-02"), 1000],
        ]
    )
    path = tmp_path / "fake.xlsx"
    with pd.ExcelWriter(path) as writer:
        frame.to_excel(
            writer, sheet_name="Data 1", header=False, index=False
        )

    with pytest.raises(RuntimeError, match="sourcekey mismatch"):
        parse_eia_weekly_xls(
            path,
            expected_sourcekey="WCRSTUS1",
            value_column="crude_stocks_incl_spr_mbbl",
        )


def test_parse_reads_valid_sheet(tmp_path):
    frame = pd.DataFrame(
        [
            ["Back to Contents", "Data 1: Weekly Fake Series"],
            ["Sourcekey", "WCRSTUS1"],
            ["Date", "Weekly Fake Series (Thousand Barrels)"],
            [pd.Timestamp("2026-01-02"), 1000],
            [pd.Timestamp("2026-01-09"), 1100],
        ]
    )
    path = tmp_path / "ok.xlsx"
    with pd.ExcelWriter(path) as writer:
        frame.to_excel(
            writer, sheet_name="Data 1", header=False, index=False
        )

    parsed = parse_eia_weekly_xls(
        path,
        expected_sourcekey="WCRSTUS1",
        value_column="crude_stocks_incl_spr_mbbl",
    )

    assert len(parsed) == 2
    assert parsed.loc[1, "crude_stocks_incl_spr_mbbl"] == 1100
