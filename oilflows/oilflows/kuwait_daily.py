from __future__ import annotations

import numpy as np
import pandas as pd


KUWAIT_PORT_ID = "port743"
KUWAIT_COUNTRY_CODE = "KW"


def build_kuwait_daily(
    portwatch_raw: pd.DataFrame,
    jodi_monthly: pd.DataFrame,
    *,
    start_date: str = "2025-06-22",
) -> pd.DataFrame:
    """Build a daily Kuwait crude-export series calibrated to JODI.

    JODI supplies the official monthly crude-export average in kb/d.
    Mina Al Ahmadi PortWatch export_tanker observations supply the daily shape
    when that shape is available.

    For a complete calendar month with positive official exports but no
    positive PortWatch loading signal, preserve the official JODI monthly
    average as a flat daily series. This is explicitly labeled so it is not
    mistaken for observed daily timing.

    A partially observed PortWatch month is still left unavailable, because
    weighting a full monthly total into only part of the month would be wrong.
    """
    portwatch = prepare_kuwait_portwatch(portwatch_raw)
    jodi = prepare_kuwait_jodi(jodi_monthly)

    start = pd.Timestamp(start_date)
    last_official = jodi["period_end"].max()

    output = pd.DataFrame(
        {"date": pd.date_range(start, last_official, freq="D")}
    )

    allocations = [
        allocate_jodi_month(
            period_start=row.period_start,
            period_end=row.period_end,
            official_kbd=float(row.crude_exports_kbd),
            assessment_code=row.assessment_code,
            source_year_file=int(row.source_year_file),
            portwatch=portwatch,
        )
        for row in jodi.itertuples(index=False)
    ]

    allocated = pd.concat(allocations, ignore_index=True)

    result = output.merge(
        allocated,
        on="date",
        how="left",
        validate="one_to_one",
    )

    result["kuwait_crude_mbd"] = (
        result["kuwait_crude_barrels"] / 1_000_000.0
    )
    result["kuwait_crude_7d_mbd"] = (
        result["kuwait_crude_mbd"]
        .rolling(window=7, min_periods=7)
        .mean()
    )

    return result


def allocate_jodi_month(
    *,
    period_start: pd.Timestamp,
    period_end: pd.Timestamp,
    official_kbd: float,
    assessment_code: str,
    source_year_file: int,
    portwatch: pd.DataFrame,
) -> pd.DataFrame:
    calendar = pd.DataFrame(
        {"date": pd.date_range(period_start, period_end, freq="D")}
    )

    official_daily_barrels = float(official_kbd) * 1_000.0
    official_barrels = official_daily_barrels * len(calendar)

    period_pw = calendar.merge(
        portwatch[["date", "export_tanker"]],
        on="date",
        how="left",
        validate="one_to_one",
    )

    full_coverage = period_pw["export_tanker"].notna().all()

    metadata = {
        "calibration_period_start": period_start,
        "calibration_period_end": period_end,
        "official_kuwait_kbd": official_kbd,
        "official_kuwait_barrels": official_barrels,
        "assessment_code": assessment_code,
        "calibration_source": "JODI",
        "calibration_source_year_file": source_year_file,
    }

    if not full_coverage:
        return calendar.assign(
            kuwait_crude_barrels=np.nan,
            allocation_method="unavailable_partial_portwatch_period",
            **metadata,
        )

    if official_barrels == 0:
        return calendar.assign(
            kuwait_crude_barrels=0.0,
            allocation_method="official_zero",
            **metadata,
        )

    weights = (
        period_pw["export_tanker"]
        .fillna(0.0)
        .clip(lower=0.0)
        .astype(float)
    )

    if float(weights.sum()) <= 0:
        return calendar.assign(
            kuwait_crude_barrels=official_daily_barrels,
            allocation_method="official_monthly_flat_no_portwatch_signal",
            **metadata,
        )

    shares = weights / float(weights.sum())
    barrels = shares * official_barrels

    residual = official_barrels - float(barrels.sum())
    barrels.iloc[-1] += residual

    return calendar.assign(
        kuwait_crude_barrels=barrels.to_numpy(),
        allocation_method="official_portwatch_weighted",
        **metadata,
    )


def prepare_kuwait_portwatch(raw: pd.DataFrame) -> pd.DataFrame:
    required = {"date", "portid", "export_tanker"}
    missing = sorted(required - set(raw.columns))
    if missing:
        raise RuntimeError(
            f"PortWatch input is missing columns: {missing}"
        )

    frame = raw.loc[
        raw["portid"].astype(str).eq(KUWAIT_PORT_ID)
    ].copy()

    if frame.empty:
        raise RuntimeError(
            f"No PortWatch rows found for Mina Al Ahmadi ({KUWAIT_PORT_ID})."
        )

    frame["date"] = pd.to_datetime(frame["date"], errors="raise")
    frame["export_tanker"] = pd.to_numeric(
        frame["export_tanker"],
        errors="raise",
    )

    duplicate_rows = frame.loc[
        frame.duplicated("date", keep=False)
    ]

    for _, group in duplicate_rows.groupby("date"):
        if group["export_tanker"].nunique(dropna=False) > 1:
            raise RuntimeError(
                "Conflicting Mina Al Ahmadi PortWatch observations found "
                f"for {group.iloc[0]['date']}."
            )

    sort_columns = ["date"]
    if "ObjectId" in frame.columns:
        sort_columns.append("ObjectId")

    return (
        frame.sort_values(sort_columns)
        .drop_duplicates("date", keep="first")
        [["date", "export_tanker"]]
        .sort_values("date")
        .reset_index(drop=True)
    )


def prepare_kuwait_jodi(raw: pd.DataFrame) -> pd.DataFrame:
    required = {
        "month",
        "country_code",
        "crude_exports_kbd",
        "assessment_code",
        "source_year_file",
    }
    missing = sorted(required - set(raw.columns))
    if missing:
        raise RuntimeError(
            f"JODI input is missing columns: {missing}"
        )

    frame = raw.loc[
        raw["country_code"].astype(str).eq(KUWAIT_COUNTRY_CODE)
    ].copy()

    frame["crude_exports_kbd"] = pd.to_numeric(
        frame["crude_exports_kbd"],
        errors="coerce",
    )

    frame = frame.dropna(subset=["crude_exports_kbd"]).copy()

    if frame.empty:
        raise RuntimeError("No usable Kuwait JODI crude-export rows found.")

    frame["period_start"] = pd.to_datetime(
        frame["month"],
        errors="raise",
    ).dt.to_period("M").dt.start_time

    frame["period_end"] = (
        frame["period_start"]
        + pd.offsets.MonthEnd(0)
    )

    if frame["period_start"].duplicated().any():
        raise RuntimeError(
            "Duplicate Kuwait JODI country-month observations found."
        )

    return frame[
        [
            "period_start",
            "period_end",
            "crude_exports_kbd",
            "assessment_code",
            "source_year_file",
        ]
    ].sort_values("period_start").reset_index(drop=True)
