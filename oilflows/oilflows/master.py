from __future__ import annotations

import numpy as np
import pandas as pd


def build_daily_master(
    hormuz: pd.DataFrame,
    iraq: pd.DataFrame,
    kuwait: pd.DataFrame,
    saudi: pd.DataFrame,
    uae: pd.DataFrame,
    market: pd.DataFrame | None = None,
    *,
    start_date: str = "2025-06-22",
    baseline_start: str = "2025-07-01",
    baseline_end: str = "2025-12-31",
) -> pd.DataFrame:
    """Merge validated oil-flow and optional market layers."""
    frames = {
        "hormuz": _prepare(
            hormuz,
            [
                "date",
                "hormuz_tanker_count",
                "hormuz_tanker_count_7d",
                "hormuz_tanker_capacity",
                "hormuz_tanker_capacity_7d",
            ],
        ),
        "iraq": _prepare(
            iraq,
            [
                "date",
                "iraq_basrah_mbd",
                "iraq_basrah_7d_mbd",
                "allocation_method",
                "calibration_source",
            ],
            rename={
                "allocation_method": "iraq_allocation_method",
                "calibration_source": "iraq_calibration_source",
            },
        ),
        "kuwait": _prepare(
            kuwait,
            [
                "date",
                "kuwait_crude_mbd",
                "kuwait_crude_7d_mbd",
                "allocation_method",
                "calibration_source",
            ],
            rename={
                "allocation_method": "kuwait_allocation_method",
                "calibration_source": "kuwait_calibration_source",
            },
        ),
        "saudi": _prepare(
            saudi,
            [
                "date",
                "saudi_official_crude_mbd",
                "saudi_gulf_juaymah_proxy_mt",
                "saudi_gulf_juaymah_proxy_mt_7d",
                "saudi_bypass_yanbu_proxy_mt",
                "saudi_bypass_yanbu_proxy_mt_7d",
                "saudi_proxy_bypass_share_7d",
                "saudi_official_status",
            ],
        ),
        "uae": _prepare(
            uae,
            [
                "date",
                "uae_gulf_proxy_mt_7d",
                "uae_bypass_fujairah_proxy_mt_7d",
                "uae_gulf_proxy_index_7d",
                "uae_bypass_proxy_index_7d",
                "uae_proxy_bypass_share_7d",
                "uae_official_status",
            ],
        ),
    }

    if market is not None:
        frames["market"] = _prepare(
            market,
            [
                "date",
                "brent_spot_usd",
                "brent_spot_last_usd",
                "bno_close_usd",
                "bno_last_close_usd",
                "bno_adj_close_usd",
                "bno_volume",
                "brent_observed",
                "bno_observed",
            ],
        )

    start = pd.Timestamp(start_date)
    end = max(frame["date"].max() for frame in frames.values())

    result = pd.DataFrame({"date": pd.date_range(start, end, freq="D")})

    for frame in frames.values():
        result = result.merge(
            frame,
            on="date",
            how="left",
            validate="one_to_one",
        )

    result["known_gulf_official_mbd"] = result[
        ["iraq_basrah_mbd", "kuwait_crude_mbd"]
    ].sum(axis=1, min_count=2)
    result["known_gulf_official_7d_mbd"] = (
        result["known_gulf_official_mbd"]
        .rolling(window=7, min_periods=7)
        .mean()
    )

    result["core_official_exports_mbd"] = result[
        [
            "iraq_basrah_mbd",
            "kuwait_crude_mbd",
            "saudi_official_crude_mbd",
        ]
    ].sum(axis=1, min_count=3)
    result["core_official_exports_7d_mbd"] = (
        result["core_official_exports_mbd"]
        .rolling(window=7, min_periods=7)
        .mean()
    )

    bstart = pd.Timestamp(baseline_start)
    bend = pd.Timestamp(baseline_end)
    baseline = result["date"].between(bstart, bend)

    for source, output in [
        ("hormuz_tanker_count_7d", "hormuz_tanker_count_index_7d"),
        ("known_gulf_official_7d_mbd", "known_gulf_official_index_7d"),
        ("core_official_exports_7d_mbd", "core_official_exports_index_7d"),
        ("saudi_gulf_juaymah_proxy_mt_7d", "saudi_gulf_proxy_index_7d"),
        ("saudi_bypass_yanbu_proxy_mt_7d", "saudi_bypass_proxy_index_7d"),
    ]:
        _add_index(result, source, output, baseline)

    result["master_baseline_start"] = bstart
    result["master_baseline_end"] = bend

    result["official_core_complete"] = (
        result[
            [
                "iraq_basrah_mbd",
                "kuwait_crude_mbd",
                "saudi_official_crude_mbd",
            ]
        ]
        .notna()
        .all(axis=1)
    )

    return result


def _prepare(
    frame: pd.DataFrame,
    columns: list[str],
    *,
    rename: dict[str, str] | None = None,
) -> pd.DataFrame:
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise RuntimeError(f"Input is missing expected columns: {missing}")

    out = frame[columns].copy()
    out["date"] = pd.to_datetime(out["date"], errors="raise")

    if out["date"].duplicated().any():
        raise RuntimeError("Duplicate dates found in master input.")

    if rename:
        out = out.rename(columns=rename)

    return out.sort_values("date").reset_index(drop=True)


def _add_index(
    frame: pd.DataFrame,
    source_column: str,
    output_column: str,
    baseline_mask: pd.Series,
) -> None:
    baseline_value = frame.loc[baseline_mask, source_column].mean()

    if not np.isfinite(baseline_value) or baseline_value <= 0:
        raise RuntimeError(
            f"Cannot construct baseline index for {source_column}."
        )

    frame[output_column] = (
        frame[source_column] / baseline_value * 100.0
    )
