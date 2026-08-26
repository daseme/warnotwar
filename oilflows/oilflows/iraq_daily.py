from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


BASRAH_PORT_ID = "port2479"


@dataclass(frozen=True)
class AllocationResult:
    frame: pd.DataFrame
    method: str


def build_iraq_daily(
    portwatch_raw: pd.DataFrame,
    somo_periods: pd.DataFrame,
    hormuz_daily: pd.DataFrame,
    *,
    start_date: str = "2025-06-22",
) -> pd.DataFrame:
    """Build a daily official-calibrated Iraq Persian Gulf crude series.

    SOMO Basrah crude barrels are the official calibration total because
    Basrah is the Persian Gulf export stream. SOMO total exports are retained
    as metadata but are not used to calibrate Gulf flows.

    Allocation hierarchy for a fully observed SOMO period:
      1. PortWatch Basrah export_tanker daily weights.
      2. Hormuz tanker-count daily weights if PortWatch has no positive signal.
      3. Uniform calendar-day weights if both signals are zero.

    A SOMO period with incomplete PortWatch calendar coverage is not allocated.
    This prevents assigning an entire monthly official total to a partial month
    (notably June 2025, because our PortWatch history begins June 22).
    """
    basrah = prepare_basrah_portwatch(portwatch_raw)
    somo = prepare_somo_periods(somo_periods)
    hormuz = prepare_hormuz_daily(hormuz_daily)

    start = pd.Timestamp(start_date)
    last_official = somo["period_end"].max()

    output_dates = pd.DataFrame(
        {"date": pd.date_range(start, last_official, freq="D")}
    )

    allocations: list[pd.DataFrame] = []

    for period in somo.itertuples(index=False):
        period_result = allocate_somo_period(
            period_start=period.period_start,
            period_end=period.period_end,
            basrah_barrels=float(period.basrah_barrels),
            total_barrels=float(period.total_barrels),
            portwatch_basrah=basrah,
            hormuz_daily=hormuz,
            source_file=period.source_file,
            granularity=period.granularity,
        )
        allocations.append(period_result.frame)

    allocated = pd.concat(allocations, ignore_index=True)

    result = output_dates.merge(
        allocated,
        on="date",
        how="left",
        validate="one_to_one",
    )

    result["iraq_basrah_mbd"] = result["iraq_basrah_barrels"] / 1_000_000.0
    result["iraq_basrah_7d_mbd"] = (
        result["iraq_basrah_mbd"]
        .rolling(window=7, min_periods=7)
        .mean()
    )

    return result


def allocate_somo_period(
    *,
    period_start: pd.Timestamp,
    period_end: pd.Timestamp,
    basrah_barrels: float,
    total_barrels: float,
    portwatch_basrah: pd.DataFrame,
    hormuz_daily: pd.DataFrame,
    source_file: str,
    granularity: str,
) -> AllocationResult:
    """Allocate one official SOMO Basrah total across calendar days."""
    calendar = pd.DataFrame(
        {"date": pd.date_range(period_start, period_end, freq="D")}
    )

    period_pw = calendar.merge(
        portwatch_basrah[["date", "export_tanker"]],
        on="date",
        how="left",
        validate="one_to_one",
    )

    has_full_portwatch_coverage = period_pw["export_tanker"].notna().all()

    if not has_full_portwatch_coverage:
        frame = calendar.assign(
            iraq_basrah_barrels=np.nan,
            allocation_method="unavailable_partial_portwatch_period",
        )
        return AllocationResult(
            frame=add_period_metadata(
                frame,
                period_start=period_start,
                period_end=period_end,
                basrah_barrels=basrah_barrels,
                total_barrels=total_barrels,
                source_file=source_file,
                granularity=granularity,
            ),
            method="unavailable_partial_portwatch_period",
        )

    portwatch_weights = period_pw["export_tanker"].fillna(0.0).clip(lower=0.0)

    if float(portwatch_weights.sum()) > 0:
        allocated = allocate_by_weights(
            calendar,
            portwatch_weights,
            basrah_barrels,
            method="official_portwatch_weighted",
        )
        return AllocationResult(
            frame=add_period_metadata(
                allocated,
                period_start=period_start,
                period_end=period_end,
                basrah_barrels=basrah_barrels,
                total_barrels=total_barrels,
                source_file=source_file,
                granularity=granularity,
            ),
            method="official_portwatch_weighted",
        )

    period_hormuz = calendar.merge(
        hormuz_daily[["date", "hormuz_tanker_count"]],
        on="date",
        how="left",
        validate="one_to_one",
    )
    hormuz_weights = (
        period_hormuz["hormuz_tanker_count"]
        .fillna(0.0)
        .clip(lower=0.0)
    )

    if float(hormuz_weights.sum()) > 0:
        allocated = allocate_by_weights(
            calendar,
            hormuz_weights,
            basrah_barrels,
            method="official_hormuz_weighted",
        )
        return AllocationResult(
            frame=add_period_metadata(
                allocated,
                period_start=period_start,
                period_end=period_end,
                basrah_barrels=basrah_barrels,
                total_barrels=total_barrels,
                source_file=source_file,
                granularity=granularity,
            ),
            method="official_hormuz_weighted",
        )

    uniform_weights = pd.Series(1.0, index=calendar.index)
    allocated = allocate_by_weights(
        calendar,
        uniform_weights,
        basrah_barrels,
        method="official_uniform_fallback",
    )

    return AllocationResult(
        frame=add_period_metadata(
            allocated,
            period_start=period_start,
            period_end=period_end,
            basrah_barrels=basrah_barrels,
            total_barrels=total_barrels,
            source_file=source_file,
            granularity=granularity,
        ),
        method="official_uniform_fallback",
    )


def allocate_by_weights(
    calendar: pd.DataFrame,
    weights: pd.Series,
    official_barrels: float,
    *,
    method: str,
) -> pd.DataFrame:
    """Allocate an official total exactly according to non-negative weights."""
    total_weight = float(weights.sum())
    if total_weight <= 0:
        raise ValueError("Allocation weights must have a positive sum.")

    shares = weights.astype(float) / total_weight
    barrels = shares * float(official_barrels)

    # Force exact reconciliation despite floating-point accumulation.
    residual = float(official_barrels) - float(barrels.sum())
    barrels.iloc[-1] += residual

    return calendar.assign(
        iraq_basrah_barrels=barrels.to_numpy(),
        allocation_method=method,
    )


def add_period_metadata(
    frame: pd.DataFrame,
    *,
    period_start: pd.Timestamp,
    period_end: pd.Timestamp,
    basrah_barrels: float,
    total_barrels: float,
    source_file: str,
    granularity: str,
) -> pd.DataFrame:
    return frame.assign(
        calibration_period_start=period_start,
        calibration_period_end=period_end,
        official_basrah_barrels=basrah_barrels,
        official_iraq_total_barrels=total_barrels,
        calibration_granularity=granularity,
        calibration_source="SOMO",
        calibration_source_file=source_file,
    )


def prepare_basrah_portwatch(raw: pd.DataFrame) -> pd.DataFrame:
    required = {"date", "portid", "export_tanker"}
    missing = sorted(required - set(raw.columns))
    if missing:
        raise RuntimeError(f"PortWatch input is missing columns: {missing}")

    frame = raw.loc[raw["portid"].astype(str).eq(BASRAH_PORT_ID)].copy()
    if frame.empty:
        raise RuntimeError(
            f"No PortWatch rows found for Basrah Oil Terminal ({BASRAH_PORT_ID})."
        )

    frame["date"] = pd.to_datetime(frame["date"], errors="raise")
    frame["export_tanker"] = pd.to_numeric(
        frame["export_tanker"],
        errors="raise",
    )

    duplicate_mask = frame.duplicated("date", keep=False)
    duplicate_rows = frame.loc[duplicate_mask]

    for _, group in duplicate_rows.groupby("date"):
        if group["export_tanker"].nunique(dropna=False) > 1:
            raise RuntimeError(
                "Conflicting Basrah PortWatch observations found for "
                f"{group.iloc[0]['date']}."
            )

    return (
        frame.sort_values(["date", "ObjectId"] if "ObjectId" in frame else ["date"])
        .drop_duplicates("date", keep="first")
        [["date", "export_tanker"]]
        .sort_values("date")
        .reset_index(drop=True)
    )


def prepare_somo_periods(raw: pd.DataFrame) -> pd.DataFrame:
    required = {
        "period_start",
        "period_end",
        "granularity",
        "basrah_barrels",
        "total_barrels",
        "source_file",
    }
    missing = sorted(required - set(raw.columns))
    if missing:
        raise RuntimeError(f"SOMO input is missing columns: {missing}")

    frame = raw.copy()
    frame["period_start"] = pd.to_datetime(frame["period_start"], errors="raise")
    frame["period_end"] = pd.to_datetime(frame["period_end"], errors="raise")
    frame["basrah_barrels"] = pd.to_numeric(
        frame["basrah_barrels"],
        errors="raise",
    )
    frame["total_barrels"] = pd.to_numeric(
        frame["total_barrels"],
        errors="raise",
    )

    return frame.sort_values("period_start").reset_index(drop=True)


def prepare_hormuz_daily(raw: pd.DataFrame) -> pd.DataFrame:
    required = {"date", "hormuz_tanker_count"}
    missing = sorted(required - set(raw.columns))
    if missing:
        raise RuntimeError(f"Hormuz input is missing columns: {missing}")

    frame = raw[["date", "hormuz_tanker_count"]].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="raise")
    frame["hormuz_tanker_count"] = pd.to_numeric(
        frame["hormuz_tanker_count"],
        errors="raise",
    )

    if frame["date"].duplicated().any():
        raise RuntimeError("Duplicate dates found in processed Hormuz series.")

    return frame.sort_values("date").reset_index(drop=True)
