from collections.abc import Iterable
from datetime import date
from typing import Any

import pandas as pd

from .arcgis import create_retrying_session, fetch_all_features
from .settings import DAILY_CHOKEPOINTS_URL, DAILY_PORTS_URL, HORMUZ_PORT_ID, PORTS_REGISTRY_URL


PORT_REGISTRY_FIELDS = (
    "portid",
    "portname",
    "country",
    "ISO3",
    "fullname",
    "lat",
    "lon",
    "vessel_count_tanker",
    "industry_top1",
    "industry_top2",
    "industry_top3",
    "share_country_maritime_export",
    "LOCODE",
    "pageid",
    "ObjectId",
)

DAILY_PORT_FIELDS = (
    "date",
    "year",
    "month",
    "day",
    "portid",
    "portname",
    "country",
    "ISO3",
    "portcalls_tanker",
    "import_tanker",
    "export_tanker",
    "ObjectId",
)

HORMUZ_FIELDS = (
    "date",
    "year",
    "month",
    "day",
    "portid",
    "portname",
    "n_tanker",
    "n_total",
    "capacity_tanker",
    "capacity",
    "ObjectId",
)


def fetch_port_registry(*, page_size: int = 500, timeout_seconds: int = 120) -> pd.DataFrame:
    rows = fetch_all_features(
        PORTS_REGISTRY_URL,
        "1=1",
        PORT_REGISTRY_FIELDS,
        page_size=page_size,
        timeout_seconds=timeout_seconds,
    )
    return pd.DataFrame(rows)


def fetch_daily_ports(
    port_ids: Iterable[str],
    start_date: str,
    *,
    page_size: int = 500,
    timeout_seconds: int = 120,
) -> pd.DataFrame:
    """Fetch selected ports from start_date forward.

    Uses PortWatch's integer year/month/day fields rather than ArcGIS DateOnly
    SQL syntax. One port is queried at a time to keep requests small.
    """
    ids = tuple(sorted(set(port_ids)))
    if not ids:
        return pd.DataFrame(columns=DAILY_PORT_FIELDS)

    session = create_retrying_session()
    all_rows: list[dict[str, Any]] = []
    date_clause = build_start_date_clause(start_date)

    for index, port_id in enumerate(ids, start=1):
        escaped_port_id = escape_sql_string(port_id)
        where = f"portid='{escaped_port_id}' AND ({date_clause})"

        print(f"[{index}/{len(ids)}] Fetching {port_id}...")

        rows = fetch_all_features(
            DAILY_PORTS_URL,
            where,
            DAILY_PORT_FIELDS,
            page_size=page_size,
            timeout_seconds=timeout_seconds,
            session=session,
        )

        print(f"    {len(rows):,} rows")
        all_rows.extend(rows)

    frame = pd.DataFrame(all_rows)
    return normalize_daily_rows(frame, start_date)


def fetch_hormuz(
    start_date: str,
    *,
    page_size: int = 500,
    timeout_seconds: int = 120,
) -> pd.DataFrame:
    escaped_port_id = escape_sql_string(HORMUZ_PORT_ID)
    date_clause = build_start_date_clause(start_date)
    where = f"portid='{escaped_port_id}' AND ({date_clause})"

    print("Fetching Strait of Hormuz...")

    rows = fetch_all_features(
        DAILY_CHOKEPOINTS_URL,
        where,
        HORMUZ_FIELDS,
        page_size=page_size,
        timeout_seconds=timeout_seconds,
    )

    print(f"    {len(rows):,} Hormuz rows")
    return normalize_daily_rows(pd.DataFrame(rows), start_date)


def build_start_date_clause(start_date: str) -> str:
    """Return standardized SQL using numeric year/month/day fields."""
    cutoff = date.fromisoformat(start_date)
    y, m, d = cutoff.year, cutoff.month, cutoff.day

    return (
        f"year > {y} "
        f"OR (year = {y} AND month > {m}) "
        f"OR (year = {y} AND month = {m} AND day >= {d})"
    )


def normalize_daily_rows(frame: pd.DataFrame, start_date: str) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()

    normalized = frame.copy()
    normalized["date"] = pd.to_datetime(normalized["date"], errors="raise").dt.date
    cutoff = date.fromisoformat(start_date)
    normalized = normalized.loc[normalized["date"] >= cutoff]
    return normalized.sort_values(["date", "portid"]).reset_index(drop=True)


def escape_sql_string(value: str) -> str:
    return value.replace("'", "''")
