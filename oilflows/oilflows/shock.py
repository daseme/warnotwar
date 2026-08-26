from __future__ import annotations

import pandas as pd


THRESHOLDS = (75.0, 50.0, 25.0, 10.0, 5.0, 1.0)


def build_shock_timeline(
    master: pd.DataFrame,
    *,
    search_start: str = "2026-02-01",
) -> pd.DataFrame:
    """Summarize when Hormuz activity crossed key disruption thresholds.

    Uses the already-normalized 7-day tanker-count index where 100 is the
    Jul-Dec 2025 baseline. Market values are taken from the calendar-aligned
    last-observed Brent spot and BNO close fields.

    A threshold row means: first date on/after search_start where the Hormuz
    index is less than or equal to that threshold.
    """
    required = {
        "date",
        "hormuz_tanker_count_index_7d",
        "brent_spot_last_usd",
        "bno_last_close_usd",
        "known_gulf_official_index_7d",
        "core_official_exports_index_7d",
        "saudi_gulf_proxy_index_7d",
        "saudi_bypass_proxy_index_7d",
        "uae_gulf_proxy_index_7d",
        "uae_bypass_proxy_index_7d",
    }
    missing = sorted(required - set(master.columns))
    if missing:
        raise RuntimeError(f"Master input missing columns: {missing}")

    frame = master.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="raise")
    frame = frame.sort_values("date").reset_index(drop=True)

    search = frame.loc[
        frame["date"] >= pd.Timestamp(search_start)
    ].copy()

    rows: list[dict] = []

    for threshold in THRESHOLDS:
        hit = search.loc[
            search["hormuz_tanker_count_index_7d"] <= threshold
        ].head(1)

        if hit.empty:
            continue

        row = hit.iloc[0]

        rows.append(
            {
                "threshold_pct": threshold,
                "first_date": row["date"],
                "hormuz_index": row["hormuz_tanker_count_index_7d"],
                "brent_usd": row["brent_spot_last_usd"],
                "bno_usd": row["bno_last_close_usd"],
                "known_gulf_official_index":
                    row["known_gulf_official_index_7d"],
                "core_official_exports_index":
                    row["core_official_exports_index_7d"],
                "saudi_gulf_proxy_index":
                    row["saudi_gulf_proxy_index_7d"],
                "saudi_bypass_proxy_index":
                    row["saudi_bypass_proxy_index_7d"],
                "uae_gulf_proxy_index":
                    row["uae_gulf_proxy_index_7d"],
                "uae_bypass_proxy_index":
                    row["uae_bypass_proxy_index_7d"],
            }
        )

    return pd.DataFrame(rows)


def build_market_response_summary(
    master: pd.DataFrame,
    *,
    anchor_date: str,
    pre_days: int = 7,
    horizon_end: str | None = None,
) -> pd.DataFrame:
    """Measure market move from a pre-shock anchor and subsequent peaks."""
    frame = master.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="raise")
    frame = frame.sort_values("date").reset_index(drop=True)

    anchor = pd.Timestamp(anchor_date)
    pre_anchor = anchor - pd.Timedelta(days=pre_days)

    pre_row = frame.loc[frame["date"] <= pre_anchor].tail(1)
    anchor_row = frame.loc[frame["date"] <= anchor].tail(1)

    if pre_row.empty or anchor_row.empty:
        raise RuntimeError("Could not resolve market anchor dates.")

    end = (
        pd.Timestamp(horizon_end)
        if horizon_end is not None
        else frame["date"].max()
    )

    window = frame.loc[
        frame["date"].between(anchor, end)
    ].copy()

    out = []

    for label, col in [
        ("Brent spot", "brent_spot_last_usd"),
        ("BNO close", "bno_last_close_usd"),
    ]:
        pre_value = float(pre_row.iloc[0][col])
        anchor_value = float(anchor_row.iloc[0][col])

        valid = window.dropna(subset=[col])
        peak_idx = valid[col].idxmax()
        peak_row = valid.loc[peak_idx]
        peak_value = float(peak_row[col])

        out.append(
            {
                "market": label,
                "pre_anchor_date": pre_row.iloc[0]["date"],
                "pre_anchor_value": pre_value,
                "anchor_date": anchor_row.iloc[0]["date"],
                "anchor_value": anchor_value,
                "move_to_anchor_pct":
                    (anchor_value / pre_value - 1.0) * 100.0,
                "peak_date": peak_row["date"],
                "peak_value": peak_value,
                "move_pre_to_peak_pct":
                    (peak_value / pre_value - 1.0) * 100.0,
                "move_anchor_to_peak_pct":
                    (peak_value / anchor_value - 1.0) * 100.0,
            }
        )

    return pd.DataFrame(out)
