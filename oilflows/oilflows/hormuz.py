from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class HormuzValidation:
    row_count: int
    first_date: pd.Timestamp
    last_date: pd.Timestamp
    missing_dates: tuple[pd.Timestamp, ...]
    duplicate_dates: tuple[pd.Timestamp, ...]


def build_hormuz_daily(raw: pd.DataFrame) -> pd.DataFrame:
    """Validate and transform raw PortWatch Hormuz observations.

    PortWatch's n_tanker and capacity_tanker are retained as tanker-activity
    measures. They are not labeled as crude barrels or outbound flows because
    the source does not establish cargo/direction at that level.
    """
    prepared = prepare_hormuz(raw)
    validation = validate_hormuz(prepared)

    if validation.duplicate_dates:
        dates = ", ".join(d.date().isoformat() for d in validation.duplicate_dates[:10])
        raise RuntimeError(f"Duplicate Hormuz dates found: {dates}")

    if validation.missing_dates:
        dates = ", ".join(d.date().isoformat() for d in validation.missing_dates[:10])
        raise RuntimeError(f"Missing Hormuz dates found: {dates}")

    return add_rolling_measures(prepared)


def prepare_hormuz(raw: pd.DataFrame) -> pd.DataFrame:
    required = {
        "date",
        "portid",
        "portname",
        "n_tanker",
        "n_total",
        "capacity_tanker",
        "capacity",
    }
    missing = sorted(required - set(raw.columns))
    if missing:
        raise RuntimeError(f"Hormuz input is missing columns: {missing}")

    frame = raw.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="raise")

    numeric_columns = (
        "n_tanker",
        "n_total",
        "capacity_tanker",
        "capacity",
    )
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="raise")

    if (frame[list(numeric_columns)] < 0).any().any():
        raise RuntimeError("Negative Hormuz activity values found.")

    return frame.sort_values("date").reset_index(drop=True)


def validate_hormuz(frame: pd.DataFrame) -> HormuzValidation:
    duplicate_dates = tuple(
        pd.Timestamp(value)
        for value in frame.loc[
            frame.duplicated("date", keep=False),
            "date",
        ].drop_duplicates()
    )

    first_date = frame["date"].min()
    last_date = frame["date"].max()

    expected = pd.date_range(first_date, last_date, freq="D")
    observed = pd.DatetimeIndex(frame["date"].drop_duplicates())
    missing_dates = tuple(expected.difference(observed))

    return HormuzValidation(
        row_count=len(frame),
        first_date=first_date,
        last_date=last_date,
        missing_dates=missing_dates,
        duplicate_dates=duplicate_dates,
    )


def add_rolling_measures(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame[
        [
            "date",
            "n_tanker",
            "capacity_tanker",
            "n_total",
            "capacity",
        ]
    ].rename(
        columns={
            "n_tanker": "hormuz_tanker_count",
            "capacity_tanker": "hormuz_tanker_capacity",
            "n_total": "hormuz_total_vessel_count",
            "capacity": "hormuz_total_vessel_capacity",
        }
    )

    result["hormuz_tanker_count_7d"] = (
        result["hormuz_tanker_count"]
        .rolling(window=7, min_periods=7)
        .mean()
    )
    result["hormuz_tanker_capacity_7d"] = (
        result["hormuz_tanker_capacity"]
        .rolling(window=7, min_periods=7)
        .mean()
    )
    result["hormuz_total_vessel_count_7d"] = (
        result["hormuz_total_vessel_count"]
        .rolling(window=7, min_periods=7)
        .mean()
    )
    result["hormuz_total_vessel_capacity_7d"] = (
        result["hormuz_total_vessel_capacity"]
        .rolling(window=7, min_periods=7)
        .mean()
    )

    return result
