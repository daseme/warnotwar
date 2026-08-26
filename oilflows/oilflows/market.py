from __future__ import annotations

from io import StringIO
from datetime import date, timedelta, timezone, datetime

import pandas as pd
import requests

from .arcgis import create_retrying_session


FRED_BRENT_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/BNO"


def pull_market_daily(
    *,
    start_date: str = "2025-06-22",
    end_date: str | None = None,
    timeout_seconds: int = 120,
    session: requests.Session | None = None,
) -> tuple[pd.DataFrame, str, dict]:
    """Fetch Brent spot and BNO daily market data.

    Brent:
      FRED series DCOILBRENTEU, sourced from the U.S. EIA.
      This is a spot-price series in USD/barrel.

    BNO:
      Yahoo Finance v8 chart endpoint.
      `close` is retained as the unadjusted trading-session close.
      `adjclose` is retained separately when supplied.

    Returns:
      processed market frame,
      raw FRED CSV text,
      raw Yahoo JSON object.
    """
    client = session or create_retrying_session()

    start = pd.Timestamp(start_date).date()
    end = (
        pd.Timestamp(end_date).date()
        if end_date is not None
        else date.today()
    )

    fred_text = fetch_fred_brent(
        start,
        end,
        timeout_seconds=timeout_seconds,
        session=client,
    )
    yahoo_json = fetch_bno_yahoo(
        start,
        end,
        timeout_seconds=timeout_seconds,
        session=client,
    )

    brent = parse_fred_brent(fred_text)
    bno = parse_bno_yahoo(yahoo_json)

    market = brent.merge(
        bno,
        on="date",
        how="outer",
        validate="one_to_one",
    ).sort_values("date").reset_index(drop=True)

    market = market.loc[
        market["date"].between(pd.Timestamp(start), pd.Timestamp(end))
    ].reset_index(drop=True)

    return market, fred_text, yahoo_json


def fetch_fred_brent(
    start: date,
    end: date,
    *,
    timeout_seconds: int,
    session: requests.Session,
) -> str:
    response = session.get(
        FRED_BRENT_URL,
        params={
            "id": "DCOILBRENTEU",
            "cosd": start.isoformat(),
            "coed": end.isoformat(),
        },
        timeout=(15, timeout_seconds),
        headers={"User-Agent": "ko-oilflows/1.0"},
    )
    response.raise_for_status()

    if "DCOILBRENTEU" not in response.text:
        raise RuntimeError("Unexpected FRED Brent response.")

    return response.text


def fetch_bno_yahoo(
    start: date,
    end: date,
    *,
    timeout_seconds: int,
    session: requests.Session,
) -> dict:
    # Yahoo's period2 is exclusive, so move one day beyond requested end.
    period1 = int(
        datetime(
            start.year, start.month, start.day,
            tzinfo=timezone.utc,
        ).timestamp()
    )
    inclusive_end = end + timedelta(days=1)
    period2 = int(
        datetime(
            inclusive_end.year,
            inclusive_end.month,
            inclusive_end.day,
            tzinfo=timezone.utc,
        ).timestamp()
    )

    response = session.get(
        YAHOO_CHART_URL,
        params={
            "period1": period1,
            "period2": period2,
            "interval": "1d",
            "events": "div,splits",
        },
        timeout=(15, timeout_seconds),
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/120 Safari/537.36"
            )
        },
    )
    response.raise_for_status()
    payload = response.json()

    chart = payload.get("chart", {})
    if chart.get("error"):
        raise RuntimeError(f"Yahoo BNO error: {chart['error']}")
    if not chart.get("result"):
        raise RuntimeError("Yahoo BNO response contained no chart result.")

    return payload


def parse_fred_brent(text: str) -> pd.DataFrame:
    frame = pd.read_csv(
        StringIO(text),
        na_values=[".", ""],
    )

    if "DATE" in frame.columns:
        date_col = "DATE"
    elif "observation_date" in frame.columns:
        date_col = "observation_date"
    else:
        raise RuntimeError(
            f"Unexpected FRED date column: {list(frame.columns)}"
        )

    if "DCOILBRENTEU" not in frame.columns:
        raise RuntimeError("FRED Brent value column missing.")

    result = frame[[date_col, "DCOILBRENTEU"]].rename(
        columns={
            date_col: "date",
            "DCOILBRENTEU": "brent_spot_usd",
        }
    )
    result["date"] = pd.to_datetime(result["date"], errors="raise")
    result["brent_spot_usd"] = pd.to_numeric(
        result["brent_spot_usd"],
        errors="coerce",
    )

    return result.sort_values("date").reset_index(drop=True)


def parse_bno_yahoo(payload: dict) -> pd.DataFrame:
    result = payload["chart"]["result"][0]
    timestamps = result.get("timestamp") or []
    quote = (result.get("indicators", {}).get("quote") or [{}])[0]
    adjclose_blocks = (
        result.get("indicators", {}).get("adjclose") or [{}]
    )
    adjclose = adjclose_blocks[0].get("adjclose") or [None] * len(timestamps)

    closes = quote.get("close") or [None] * len(timestamps)
    volumes = quote.get("volume") or [None] * len(timestamps)

    if not (
        len(timestamps) == len(closes) == len(adjclose) == len(volumes)
    ):
        raise RuntimeError("Yahoo BNO arrays have inconsistent lengths.")

    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(
                timestamps,
                unit="s",
                utc=True,
            ).tz_convert("America/New_York").normalize().tz_localize(None),
            "bno_close_usd": closes,
            "bno_adj_close_usd": adjclose,
            "bno_volume": volumes,
        }
    )

    for column in [
        "bno_close_usd",
        "bno_adj_close_usd",
        "bno_volume",
    ]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    if frame["date"].duplicated().any():
        raise RuntimeError("Duplicate BNO trading dates returned by Yahoo.")

    return frame.sort_values("date").reset_index(drop=True)


def add_market_calendar_features(
    market: pd.DataFrame,
    *,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Expand market observations to a calendar with explicit last-close fields."""
    calendar = pd.DataFrame(
        {
            "date": pd.date_range(
                pd.Timestamp(start_date),
                pd.Timestamp(end_date),
                freq="D",
            )
        }
    )

    frame = calendar.merge(
        market,
        on="date",
        how="left",
        validate="one_to_one",
    )

    frame["brent_spot_last_usd"] = frame["brent_spot_usd"].ffill()
    frame["bno_last_close_usd"] = frame["bno_close_usd"].ffill()

    frame["brent_observed"] = frame["brent_spot_usd"].notna()
    frame["bno_observed"] = frame["bno_close_usd"].notna()

    return frame
