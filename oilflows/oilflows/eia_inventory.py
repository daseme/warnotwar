from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import requests

from .arcgis import create_retrying_session


EIA_HIST_XLS_URL = "https://www.eia.gov/dnav/pet/hist_xls/{sourcekey}w.xls"

# Weekly EIA series behind the buffer dataset. Values are thousand barrels
# (stocks) and thousand barrels/day (refinery inputs), so their ratio is days.
BUFFER_SERIES = {
    "crude_stocks_incl_spr_mbbl": "WCRSTUS1",
    "commercial_crude_mbbl": "WCESTUS1",
    "spr_crude_mbbl": "WCSSTUS1",
    "refinery_crude_inputs_mbd": "WCRRIUS2",
}

# Refined products: stocks and demand ("product supplied" is EIA's proxy
# for consumption). Sourcekeys verified against the live dnav endpoints.
PRODUCT_SERIES = {
    "gasoline_stocks_mbbl": "WGTSTUS1",
    "distillate_stocks_mbbl": "WDISTUS1",
    "products_supplied_mbd": "WRPUPUS2",
    "gasoline_supplied_mbd": "WGFUPUS2",
    "distillate_supplied_mbd": "WDIUPUS2",
}

# Tolerated relative gap in the incl_spr ≈ commercial + spr identity;
# EIA series are independently rounded.
IDENTITY_TOLERANCE = 0.01


def fetch_eia_weekly_xls(
    sourcekey: str,
    *,
    timeout_seconds: int = 120,
    session: requests.Session | None = None,
) -> bytes:
    client = session or create_retrying_session()
    response = client.get(
        EIA_HIST_XLS_URL.format(sourcekey=sourcekey),
        timeout=(15, timeout_seconds),
        headers={"User-Agent": "ko-oilflows/1.0"},
    )
    response.raise_for_status()

    content = response.content
    # Legacy .xls files start with the OLE2 compound-document magic. Anything
    # else (an HTML error page, a redirect stub) is schema drift: fail loudly.
    if not content.startswith(b"\xd0\xcf\x11\xe0"):
        raise RuntimeError(
            f"EIA download for {sourcekey} is not a legacy .xls workbook."
        )
    return content


def parse_eia_weekly_xls(
    source,
    *,
    expected_sourcekey: str,
    value_column: str,
) -> pd.DataFrame:
    """Parse one EIA dnav 'Data 1' sheet into (week_end, value).

    Layout is validated rather than assumed: a 'Sourcekey' row naming the
    expected series and a 'Date' header row must both be present.
    """
    raw = pd.read_excel(source, sheet_name="Data 1", header=None)

    first_col = raw.iloc[:, 0].astype(str).str.strip()

    key_rows = raw.loc[first_col == "Sourcekey"]
    if key_rows.empty:
        raise RuntimeError(
            f"EIA sheet for {expected_sourcekey}: no Sourcekey row found."
        )
    found_key = str(key_rows.iloc[0, 1]).strip()
    if found_key != expected_sourcekey:
        raise RuntimeError(
            f"EIA sourcekey mismatch: expected {expected_sourcekey}, "
            f"found {found_key}."
        )

    date_rows = first_col.index[first_col == "Date"]
    if len(date_rows) == 0:
        raise RuntimeError(
            f"EIA sheet for {expected_sourcekey}: no Date header row found."
        )
    start = date_rows[0] + 1

    frame = raw.iloc[start:, :2].copy()
    frame.columns = ["week_end", value_column]
    frame["week_end"] = pd.to_datetime(frame["week_end"], errors="raise")
    frame[value_column] = pd.to_numeric(frame[value_column], errors="coerce")
    frame = frame.dropna(subset=["week_end"]).reset_index(drop=True)

    if frame["week_end"].duplicated().any():
        raise RuntimeError(
            f"EIA sheet for {expected_sourcekey}: duplicate week-ending dates."
        )
    if frame[value_column].notna().sum() == 0:
        raise RuntimeError(
            f"EIA sheet for {expected_sourcekey}: no numeric observations."
        )

    return frame.sort_values("week_end").reset_index(drop=True)


def build_buffer_weekly(
    incl_spr: pd.DataFrame,
    commercial: pd.DataFrame,
    spr: pd.DataFrame,
    refinery_inputs: pd.DataFrame,
) -> pd.DataFrame:
    """Join the weekly EIA inputs and compute days-of-supply ratios.

    Only matching week-ending dates are joined; no series is interpolated or
    forward-filled. Days of supply is stocks (thousand bbl) divided by
    refinery crude inputs (thousand bbl/day) — a cushion ratio, never a
    countdown.
    """
    frame = incl_spr
    for other in (commercial, spr, refinery_inputs):
        frame = frame.merge(
            other,
            on="week_end",
            how="inner",
            validate="one_to_one",
        )
    frame = frame.sort_values("week_end").reset_index(drop=True)
    if frame.empty:
        raise RuntimeError("No overlapping EIA weeks across buffer inputs.")

    validate_stock_identity(frame)

    inputs = frame["refinery_crude_inputs_mbd"]
    # Zero or missing refinery inputs make the ratio undefined, not infinite.
    safe_inputs = inputs.where(inputs > 0)

    frame["days_supply_incl_spr"] = (
        frame["crude_stocks_incl_spr_mbbl"] / safe_inputs
    )
    frame["commercial_days_supply"] = (
        frame["commercial_crude_mbbl"] / safe_inputs
    )
    frame["spr_days_equivalent"] = frame["spr_crude_mbbl"] / safe_inputs

    frame["days_supply_incl_spr_percentile"] = historical_percentile(
        frame["days_supply_incl_spr"]
    )

    return frame


def build_products_weekly(parsed: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Join the refined-product series and compute days-of-cover ratios.

    Same discipline as the crude buffer: matching weeks only, no
    interpolation, undefined ratios stay null, and days-of-cover is a
    cushion ratio, never a countdown — refineries keep producing.
    """
    frame = None
    for column in PRODUCT_SERIES:
        part = parsed[column]
        frame = part if frame is None else frame.merge(
            part, on="week_end", how="inner", validate="one_to_one"
        )
    frame = frame.sort_values("week_end").reset_index(drop=True)
    if frame.empty:
        raise RuntimeError("No overlapping EIA weeks across product inputs.")

    for stocks, supplied, out in [
        ("gasoline_stocks_mbbl", "gasoline_supplied_mbd", "gasoline_days_cover"),
        ("distillate_stocks_mbbl", "distillate_supplied_mbd", "distillate_days_cover"),
    ]:
        denom = frame[supplied].where(frame[supplied] > 0)
        frame[out] = frame[stocks] / denom

    return frame


def build_products_metadata(
    frame: pd.DataFrame,
    *,
    generated_at_utc: str | None = None,
) -> dict:
    if generated_at_utc is None:
        generated_at_utc = (
            pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ")
        )

    latest = frame.iloc[-1]

    def rank_low(column: str) -> dict:
        observed = frame.dropna(subset=[column])
        current = observed.iloc[-1][column]
        rank = 1 + int((observed[column] < current).sum())
        return {
            "latest": round(float(current), 1),
            "rank_from_low": rank,
            "weeks_observed": int(len(observed)),
        }

    return {
        "schema_version": 1,
        "frequency": "weekly",
        "source": "U.S. Energy Information Administration",
        "generated_at_utc": generated_at_utc,
        "first_week": frame["week_end"].min().date().isoformat(),
        "last_week": frame["week_end"].max().date().isoformat(),
        "latest": {
            "gasoline_stocks_mbbl": round(float(latest["gasoline_stocks_mbbl"]) / 1000, 1),
            "distillate_stocks_mbbl": round(float(latest["distillate_stocks_mbbl"]) / 1000, 1),
            "products_supplied_mbd": round(float(latest["products_supplied_mbd"]) / 1000, 2),
            "gasoline_supplied_mbd": round(float(latest["gasoline_supplied_mbd"]) / 1000, 2),
            "distillate_supplied_mbd": round(float(latest["distillate_supplied_mbd"]) / 1000, 2),
        },
        "gasoline_days_cover": rank_low("gasoline_days_cover"),
        "distillate_days_cover": rank_low("distillate_days_cover"),
        "definitions": {
            "days_cover": (
                "Product stocks divided by that week's product supplied "
                "(EIA's consumption proxy). A cushion ratio, not a "
                "countdown — refineries keep producing."
            ),
            "products_supplied_mbd": (
                "EIA's weekly proxy for U.S. consumption of petroleum "
                "products, million barrels per day."
            ),
        },
    }


def validate_stock_identity(frame: pd.DataFrame) -> float:
    """incl_spr ≈ commercial + spr must approximately hold; return worst gap."""
    total = frame["crude_stocks_incl_spr_mbbl"]
    parts = frame["commercial_crude_mbbl"] + frame["spr_crude_mbbl"]
    both = total.notna() & parts.notna()
    if not both.any():
        return 0.0

    rel_gap = ((total[both] - parts[both]).abs() / total[both]).max()
    if rel_gap > IDENTITY_TOLERANCE:
        raise RuntimeError(
            "EIA stock identity violated: incl_spr vs commercial+spr "
            f"differ by {rel_gap:.1%} (tolerance {IDENTITY_TOLERANCE:.0%})."
        )
    return float(rel_gap)


def historical_percentile(series: pd.Series) -> pd.Series:
    """Percentile of each value within the whole observed history.

    100 * count(history <= value) / count(history), over non-null values.
    A low percentile means inventories are unusually thin relative to
    refinery use.
    """
    values = series.to_numpy(dtype=float)
    observed = np.sort(values[~np.isnan(values)])
    if observed.size == 0:
        return pd.Series([np.nan] * len(series), index=series.index)

    ranks = np.searchsorted(observed, values, side="right")
    pct = 100.0 * ranks / observed.size
    pct[np.isnan(values)] = np.nan
    return pd.Series(pct, index=series.index)


def prior_lower_date(
    frame: pd.DataFrame,
    *,
    column: str = "days_supply_incl_spr",
) -> tuple[str | None, float | None]:
    """Most recent PRIOR week strictly lower than the latest observation.

    Returns (date_iso, years_since) or (None, None) when the latest reading
    is an all-time low or there is no prior history.
    """
    observed = frame.dropna(subset=[column])
    if observed.empty:
        return None, None

    latest = observed.iloc[-1]
    prior = observed.iloc[:-1]
    lower = prior.loc[prior[column] < latest[column]]
    if lower.empty:
        return None, None

    when = lower.iloc[-1]["week_end"]
    years = (latest["week_end"] - when).days / 365.25
    return when.date().isoformat(), round(float(years), 1)


def spr_decomposition(
    frame: pd.DataFrame,
    *,
    preshock_date: str = "2026-02-23",
    draw_window_weeks: int = 8,
) -> dict:
    """Neutral facts about where the crude cushion's change is coming from.

    No countdown arithmetic is computed here by design: a drawdown rate is
    a policy choice, and 'weeks remaining' framing is banned house-wide.
    """
    observed = frame.dropna(subset=["spr_crude_mbbl"]).reset_index(drop=True)
    latest = observed.iloc[-1]

    prior = observed.iloc[:-1]
    at_or_below = prior.loc[
        (prior["spr_crude_mbbl"] <= latest["spr_crude_mbbl"])
        & (prior["week_end"] < pd.Timestamp(preshock_date))
    ]
    lowest_since = (
        at_or_below["week_end"].max().date().isoformat()
        if not at_or_below.empty else None
    )

    recent = observed.tail(draw_window_weeks + 1)["spr_crude_mbbl"].diff()
    deltas = recent.dropna()
    draw_avg = deltas.mean()

    anchor = observed.loc[
        observed["week_end"] <= pd.Timestamp(preshock_date)
    ].iloc[-1]

    # 2022 reference peak: the multi-decade low is NOT solely a war effect;
    # the page must be able to say how much decline predates the shock.
    y2022 = observed.loc[
        observed["week_end"].dt.year.isin([2021, 2022])
    ]
    peak_2022 = (
        y2022.loc[y2022["spr_crude_mbbl"].idxmax()]
        if not y2022.empty else None
    )

    return {
        "spr_latest_mbbl": round(float(latest["spr_crude_mbbl"]) / 1000, 1),
        "spr_last_at_or_below_date": lowest_since,
        "spr_weekly_change_avg_mbbl": round(float(draw_avg) / 1000, 1),
        "spr_weekly_change_min_mbbl": round(float(deltas.min()) / 1000, 1),
        "spr_weekly_change_max_mbbl": round(float(deltas.max()) / 1000, 1),
        "spr_change_window_weeks": draw_window_weeks,
        "preshock_anchor_week": anchor["week_end"].date().isoformat(),
        "spr_delta_since_preshock_mbbl": round(
            (float(latest["spr_crude_mbbl"])
             - float(anchor["spr_crude_mbbl"])) / 1000, 1),
        "commercial_delta_since_preshock_mbbl": round(
            (float(latest["commercial_crude_mbbl"])
             - float(anchor["commercial_crude_mbbl"])) / 1000, 1),
        "spr_2022_peak_mbbl": (
            round(float(peak_2022["spr_crude_mbbl"]) / 1000, 1)
            if peak_2022 is not None else None),
        "spr_prewar_decline_mbbl": (
            round((float(peak_2022["spr_crude_mbbl"])
                   - float(anchor["spr_crude_mbbl"])) / 1000, 1)
            if peak_2022 is not None else None),
    }


def build_buffer_metadata(
    frame: pd.DataFrame,
    *,
    generated_at_utc: str | None = None,
    latest_release_date: str | None = None,
) -> dict:
    if generated_at_utc is None:
        generated_at_utc = (
            pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ")
        )

    days = frame["days_supply_incl_spr"].dropna()
    if days.empty:
        raise RuntimeError("Buffer dataset has no days-of-supply values.")

    latest = frame.dropna(subset=["days_supply_incl_spr"]).iloc[-1]
    min_idx = days.idxmin()
    lower_date, lower_years = prior_lower_date(frame)

    return {
        "schema_version": 1,
        "frequency": "weekly",
        "source": "U.S. Energy Information Administration",
        "generated_at_utc": generated_at_utc,
        "first_week": frame["week_end"].min().date().isoformat(),
        "last_week": frame["week_end"].max().date().isoformat(),
        "latest_release_date": latest_release_date,
        "latest_days_supply_incl_spr":
            round(float(latest["days_supply_incl_spr"]), 1),
        "latest_commercial_days_supply":
            round(float(latest["commercial_days_supply"]), 1)
            if pd.notna(latest["commercial_days_supply"]) else None,
        "latest_spr_days_equivalent":
            round(float(latest["spr_days_equivalent"]), 1)
            if pd.notna(latest["spr_days_equivalent"]) else None,
        "historical_mean_days_supply_incl_spr": round(float(days.mean()), 1),
        "historical_median_days_supply_incl_spr":
            round(float(days.median()), 1),
        "historical_min_days_supply_incl_spr": round(float(days.min()), 1),
        "historical_min_date":
            frame.loc[min_idx, "week_end"].date().isoformat(),
        "current_percentile":
            round(float(latest["days_supply_incl_spr_percentile"]), 1),
        "prior_lower_date": lower_date,
        "years_since_prior_lower": lower_years,
        "spr": spr_decomposition(frame),
        "definitions": {
            "days_supply_incl_spr": (
                "Total U.S. crude stocks, including the Strategic Petroleum "
                "Reserve, divided by that week's U.S. refinery crude inputs. "
                "A measure of the inventory cushion, not a countdown until "
                "the country runs out of oil."
            ),
            "commercial_days_supply": (
                "Commercial U.S. crude stocks divided by refinery crude "
                "inputs. Excludes the Strategic Petroleum Reserve."
            ),
            "spr_days_equivalent": (
                "SPR crude volume divided by that week's refinery crude "
                "inputs. Not the number of days until the SPR runs out; "
                "releases depend on policy decisions and physical "
                "distribution capacity."
            ),
            "days_supply_incl_spr_percentile": (
                "Share of all weekly observations since 1982 at or below "
                "this week's value. A low percentile means inventories are "
                "unusually thin relative to refinery use."
            ),
        },
        "caveats": [
            "Refinery inputs are seasonal: days of supply can move because "
            "the denominator moves, not only because stocks change.",
            "Long-run EIA stock definitions have changed over time; treat "
            "multi-decade rankings as approximate context.",
            "Weekly values represent the week ending on week_end and are "
            "released later; no daily inventory observations exist.",
        ],
    }
