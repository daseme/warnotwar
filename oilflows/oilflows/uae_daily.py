from __future__ import annotations

import numpy as np
import pandas as pd


RUWAYS_PORT_ID = "port512"
DAS_PORT_ID = "port2237"
FUJAIRAH_PORT_ID = "port362"

DEFAULT_BASELINE_START = pd.Timestamp("2025-07-01")
DEFAULT_BASELINE_END = pd.Timestamp("2025-12-31")


def build_uae_daily(
    portwatch_raw: pd.DataFrame,
    *,
    start_date: str = "2025-06-22",
    baseline_start: str = "2025-07-01",
    baseline_end: str = "2025-12-31",
) -> pd.DataFrame:
    """Build UAE Gulf and bypass activity proxies from PortWatch.

    Gulf proxy:
      Jabal Az Zannah-Ruways + Das Island export_tanker.

    Bypass proxy:
      Fujairah export_tanker.

    Important limitations:
      * PortWatch export_tanker is an estimated metric-ton loading proxy,
        not an official crude-export volume.
      * Fujairah is a mixed tanker/product port, so this is a route-activity
        proxy rather than a crude-only series.
      * JODI does not provide usable UAE crude-export observations for this
        period, so we do not scale these proxies to an official national level.
      * Proxy bypass share is only the share of the OBSERVED PortWatch proxy
        signals. It is not a UAE national route share.
    """
    prepared = prepare_uae_portwatch(portwatch_raw)

    start = pd.Timestamp(start_date)
    end = prepared["date"].max()

    calendar = pd.DataFrame(
        {"date": pd.date_range(start, end, freq="D")}
    )

    result = calendar.merge(
        prepared,
        on="date",
        how="left",
        validate="one_to_one",
    )

    result["uae_gulf_proxy_mt"] = (
        result["uae_ruways_proxy_mt"].fillna(0.0)
        + result["uae_das_proxy_mt"].fillna(0.0)
    )

    result["uae_bypass_fujairah_proxy_mt"] = (
        result["uae_fujairah_proxy_mt"]
    )

    result["uae_gulf_proxy_mt_7d"] = (
        result["uae_gulf_proxy_mt"]
        .rolling(window=7, min_periods=7)
        .mean()
    )
    result["uae_bypass_fujairah_proxy_mt_7d"] = (
        result["uae_bypass_fujairah_proxy_mt"]
        .rolling(window=7, min_periods=7)
        .mean()
    )

    observed_total7 = (
        result["uae_gulf_proxy_mt_7d"]
        + result["uae_bypass_fujairah_proxy_mt_7d"]
    )
    result["uae_observed_proxy_mt_7d"] = observed_total7

    result["uae_proxy_bypass_share_7d"] = np.where(
        observed_total7 > 0,
        result["uae_bypass_fujairah_proxy_mt_7d"] / observed_total7,
        np.nan,
    )

    bstart = pd.Timestamp(baseline_start)
    bend = pd.Timestamp(baseline_end)

    baseline_mask = result["date"].between(bstart, bend)
    gulf_baseline = result.loc[
        baseline_mask, "uae_gulf_proxy_mt_7d"
    ].mean()
    bypass_baseline = result.loc[
        baseline_mask, "uae_bypass_fujairah_proxy_mt_7d"
    ].mean()

    if not np.isfinite(gulf_baseline) or gulf_baseline <= 0:
        raise RuntimeError("UAE Gulf baseline is not positive.")
    if not np.isfinite(bypass_baseline) or bypass_baseline <= 0:
        raise RuntimeError("UAE Fujairah baseline is not positive.")

    result["uae_gulf_proxy_index_7d"] = (
        result["uae_gulf_proxy_mt_7d"] / gulf_baseline * 100.0
    )
    result["uae_bypass_proxy_index_7d"] = (
        result["uae_bypass_fujairah_proxy_mt_7d"]
        / bypass_baseline
        * 100.0
    )

    result["uae_proxy_baseline_start"] = bstart
    result["uae_proxy_baseline_end"] = bend
    result["uae_gulf_proxy_baseline_mt_7d"] = gulf_baseline
    result["uae_bypass_proxy_baseline_mt_7d"] = bypass_baseline
    result["uae_official_status"] = "proxy_only_no_jodi_export_volume"

    return result


def prepare_uae_portwatch(raw: pd.DataFrame) -> pd.DataFrame:
    required = {"date", "portid", "export_tanker"}
    missing = sorted(required - set(raw.columns))
    if missing:
        raise RuntimeError(
            f"PortWatch input is missing columns: {missing}"
        )

    wanted = [RUWAYS_PORT_ID, DAS_PORT_ID, FUJAIRAH_PORT_ID]

    frame = raw.loc[
        raw["portid"].astype(str).isin(wanted)
    ].copy()

    if frame.empty:
        raise RuntimeError("No UAE PortWatch route rows found.")

    frame["date"] = pd.to_datetime(frame["date"], errors="raise")
    frame["export_tanker"] = pd.to_numeric(
        frame["export_tanker"],
        errors="raise",
    )

    duplicate_rows = frame.loc[
        frame.duplicated(["date", "portid"], keep=False)
    ]

    for (_, _), group in duplicate_rows.groupby(["date", "portid"]):
        if group["export_tanker"].nunique(dropna=False) > 1:
            raise RuntimeError(
                "Conflicting UAE PortWatch observations found for "
                f"{group.iloc[0]['portid']} on "
                f"{group.iloc[0]['date']}."
            )

    sort_columns = ["date", "portid"]
    if "ObjectId" in frame.columns:
        sort_columns.append("ObjectId")

    frame = (
        frame.sort_values(sort_columns)
        .drop_duplicates(["date", "portid"], keep="first")
    )

    pivot = frame.pivot(
        index="date",
        columns="portid",
        values="export_tanker",
    ).reset_index()

    for portid in wanted:
        if portid not in pivot.columns:
            pivot[portid] = np.nan

    return (
        pivot[
            ["date", RUWAYS_PORT_ID, DAS_PORT_ID, FUJAIRAH_PORT_ID]
        ]
        .rename(
            columns={
                RUWAYS_PORT_ID: "uae_ruways_proxy_mt",
                DAS_PORT_ID: "uae_das_proxy_mt",
                FUJAIRAH_PORT_ID: "uae_fujairah_proxy_mt",
            }
        )
        .sort_values("date")
        .reset_index(drop=True)
    )
