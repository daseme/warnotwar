from collections.abc import Iterable
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def create_retrying_session() -> requests.Session:
    """Create an HTTP session that retries transient ArcGIS failures."""
    retry_policy = Retry(
        total=5,
        connect=5,
        read=5,
        status=5,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        raise_on_status=False,
    )

    adapter = HTTPAdapter(max_retries=retry_policy)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fetch_all_features(
    url: str,
    where: str,
    out_fields: Iterable[str],
    *,
    page_size: int = 500,
    timeout_seconds: int = 120,
    session: requests.Session | None = None,
) -> list[dict[str, Any]]:
    """Fetch every ArcGIS FeatureServer row matching a WHERE clause."""
    client = session or create_retrying_session()
    rows: list[dict[str, Any]] = []
    offset = 0

    while True:
        params = {
            "where": where,
            "outFields": ",".join(out_fields),
            "returnGeometry": "false",
            "resultOffset": offset,
            "resultRecordCount": page_size,
            "orderByFields": "ObjectId ASC",
            "f": "json",
        }

        response = client.get(
            url,
            params=params,
            timeout=(15, timeout_seconds),
        )
        response.raise_for_status()
        payload = response.json()

        if "error" in payload:
            raise RuntimeError(f"ArcGIS error: {payload['error']}")

        features = payload.get("features", [])
        page = [feature["attributes"] for feature in features]
        rows.extend(page)

        if len(page) < page_size:
            return rows

        offset += page_size
