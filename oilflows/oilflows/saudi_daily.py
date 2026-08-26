from __future__ import annotations

import numpy as np
import pandas as pd


SAUDI_COUNTRY_CODE = "SA"
JUAYMAH_PORT_ID = "port526"
YANBU_PORT_ID = "port570"


def build_saudi_daily(
    portwatch_raw: pd.DataFrame,
    jodi_monthly: pd.DataFrame,
    *,
    start_date: str = "2025-06-22",
) -> pd.DataFrame:
    """Build Saudi official crude exports plus Gulf/bypass route proxies.

    Critical limitation:
      Ras Tanura is absent from the current PortWatch daily service.

    Therefore:
      * JODI is used as the official NATIONAL crude-export level.
      * Juaymah export_tanker is retained as a Gulf-route activity proxy.
      * Yanbu export_tanker is retained as a Red Sea bypass-route proxy.
      * The JODI national total is NOT split or allocated between those routes.

    PortWatch export_tanker is an estimated metric-ton loading proxy, not an
    official crude-export volume. Route-proxy shares describe only the two
    observed PortWatch signals and must not be interpreted as Saudi national
    route shares.
    """
    routes = prepare_saudi_portwatch(portwatch_raw)
    jodi = prepare_saudi_jodi(jodi_monthly)

    start = pd.Timestamp(start_date)
    end = max(
        routes["date"].max(),
        jodi["period_end"].max(),
    )

    calendar = pd.DataFrame(
        {"date": pd.date_range(start, end, freq="D")}
    )

    official = expand_saudi_jodi_daily(jodi)

    result = (
        calendar
        .merge(official, on="date", how="left", validate="one_to_one")
        .merge(routes, on="date", how="left", validate="one_to_one")
    )

    result["saudi_official_status"] = np.where(
        result["saudi_official_crude_mbd"].notna(),
        "official_jodi_monthly_flat",
        "proxy_only_pending_jodi",
    )

    for column in [
        "saudi_gulf_juaymah_proxy_mt",
        "saudi_bypass_yanbu_proxy_mt",
    ]:
        result[f"{column}_7d"] = (
            result[column]
            .rolling(window=7, min_periods=7)
            .mean()
        )

    gulf7 = result["saudi_gulf_juaymah_proxy_mt_7d"]
    bypass7 = result["saudi_bypass_yanbu_proxy_mt_7d"]
    observed_total7 = gulf7 + bypass7

    result["saudi_observed_proxy_mt_7d"] = observed_total7
    result["saudi_proxy_bypass_share_7d"] = np.where(
        observed_total7 > 0,
        bypass7 / observed_total7,
        np.nan,
    )

    return result


def expand_saudi_jodi_daily(jodi: pd.DataFrame) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []

    for row in jodi.itertuples(index=False):
        dates = pd.date_range(
            row.period_start,
            row.period_end,
            freq="D",
        )
        frames.append(
            pd.DataFrame(
                {
                    "date": dates,
                    "saudi_official_crude_mbd":
                        float(row.crude_exports_kbd) / 1000.0,
                    "saudi_official_crude_kbd":
                        float(row.crude_exports_kbd),
                    "saudi_jodi_assessment_code":
                        row.assessment_code,
                    "saudi_jodi_source_year_file":
                        int(row.source_year_file),
                    "saudi_calibration_period_start":
                        row.period_start,
                    "saudi_calibration_period_end":
                        row.period_end,
                }
            )
        )

    if not frames:
        raise RuntimeError("No Saudi JODI periods available.")

    return pd.concat(frames, ignore_index=True)


def prepare_saudi_portwatch(raw: pd.DataFrame) -> pd.DataFrame:
    required = {"date", "portid", "export_tanker"}
    missing = sorted(required - set(raw.columns))
    if missing:
        raise RuntimeError(
            f"PortWatch input is missing columns: {missing}"
        )

    frame = raw.loc[
        raw["portid"].astype(str).isin(
            [JUAYMAH_PORT_ID, YANBU_PORT_ID]
        )
    ].copy()

    if frame.empty:
        raise RuntimeError(
            "No Saudi Juaymah/Yanbu PortWatch rows found."
        )

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
                "Conflicting Saudi PortWatch observations found for "
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

    for portid in [JUAYMAH_PORT_ID, YANBU_PORT_ID]:
        if portid not in pivot.columns:
            pivot[portid] = np.nan

    return (
        pivot[
            ["date", JUAYMAH_PORT_ID, YANBU_PORT_ID]
        ]
        .rename(
            columns={
                JUAYMAH_PORT_ID:
                    "saudi_gulf_juaymah_proxy_mt",
                YANBU_PORT_ID:
                    "saudi_bypass_yanbu_proxy_mt",
            }
        )
        .sort_values("date")
        .reset_index(drop=True)
    )


def prepare_saudi_jodi(raw: pd.DataFrame) -> pd.DataFrame:
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
        raw["country_code"].astype(str).eq(SAUDI_COUNTRY_CODE)
    ].copy()

    frame["crude_exports_kbd"] = pd.to_numeric(
        frame["crude_exports_kbd"],
        errors="coerce",
    )
    frame = frame.dropna(subset=["crude_exports_kbd"]).copy()

    if frame.empty:
        raise RuntimeError(
            "No usable Saudi JODI crude-export rows found."
        )

    frame["period_start"] = pd.to_datetime(
        frame["month"],
        errors="raise",
    ).dt.to_period("M").dt.start_time

    frame["period_end"] = (
        frame["period_start"] + pd.offsets.MonthEnd(0)
    )

    if frame["period_start"].duplicated().any():
        raise RuntimeError(
            "Duplicate Saudi JODI country-month observations found."
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
