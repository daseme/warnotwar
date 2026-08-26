import pandas as pd
import pytest

from oilflows.hormuz import build_hormuz_daily, validate_hormuz


def sample_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=8, freq="D"),
            "portid": ["chokepoint6"] * 8,
            "portname": ["Strait of Hormuz"] * 8,
            "n_tanker": [10, 11, 12, 13, 14, 15, 16, 17],
            "n_total": [20, 21, 22, 23, 24, 25, 26, 27],
            "capacity_tanker": [
                100, 110, 120, 130, 140, 150, 160, 170
            ],
            "capacity": [
                200, 210, 220, 230, 240, 250, 260, 270
            ],
        }
    )


def test_build_hormuz_daily_adds_rolling_measures():
    result = build_hormuz_daily(sample_frame())

    assert result.loc[6, "hormuz_tanker_count_7d"] == 13
    assert result.loc[6, "hormuz_tanker_capacity_7d"] == 130
    assert pd.isna(result.loc[5, "hormuz_tanker_count_7d"])


def test_validate_hormuz_detects_missing_date():
    frame = sample_frame().drop(index=3).reset_index(drop=True)
    validation = validate_hormuz(frame)

    assert len(validation.missing_dates) == 1
    assert validation.missing_dates[0] == pd.Timestamp("2026-01-04")


def test_build_hormuz_daily_rejects_duplicate_date():
    frame = pd.concat(
        [sample_frame(), sample_frame().iloc[[0]]],
        ignore_index=True,
    )

    with pytest.raises(RuntimeError, match="Duplicate Hormuz dates"):
        build_hormuz_daily(frame)
