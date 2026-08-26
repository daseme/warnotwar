from __future__ import annotations

from io import BytesIO
from typing import Iterable

import pandas as pd
import requests

from .arcgis import create_retrying_session


JODI_PRIMARY_BASE = (
    "https://www.jodidata.org/_resources/files/downloads/"
    "oil-data/annual-csv/primary"
)

GULF_COUNTRIES = {
    "SA": "Saudi Arabia",
    "IQ": "Iraq",
    "KW": "Kuwait",
    "AE": "United Arab Emirates",
    "IR": "Iran",
    "QA": "Qatar",
    "BH": "Bahrain",
}

REQUIRED_COLUMNS = {
    "REF_AREA",
    "TIME_PERIOD",
    "ENERGY_PRODUCT",
    "FLOW_BREAKDOWN",
    "UNIT_MEASURE",
    "OBS_VALUE",
    "ASSESSMENT_CODE",
}


def pull_jodi_crude_exports(
    years: Iterable[int],
    *,
    timeout_seconds: int = 120,
    session: requests.Session | None = None,
) -> tuple[pd.DataFrame, dict[int, bytes]]:
    """Download JODI primary annual CSVs and return Gulf crude exports in kb/d."""
    client = session or create_retrying_session()

    annual_files: dict[int, bytes] = {}
    annual_frames: list[pd.DataFrame] = []

    for year in sorted(set(years)):
        content = download_primary_year(
            year,
            timeout_seconds=timeout_seconds,
            session=client,
        )
        annual_files[year] = content
        annual_frames.append(read_primary_csv(content, year))

    combined = pd.concat(annual_frames, ignore_index=True)
    exports = select_gulf_crude_exports(combined)
    validate_gulf_exports(exports)

    return exports, annual_files


def download_primary_year(
    year: int,
    *,
    timeout_seconds: int = 120,
    session: requests.Session,
) -> bytes:
    """Download one annual JODI primary CSV.

    JODI uses two filename conventions: the current year is commonly named
    primaryyearYYYY.csv while completed years are commonly YYYY.csv.
    Try both so the pipeline survives the annual rollover.
    """
    errors: list[str] = []

    for url in primary_year_urls(year):
        try:
            response = session.get(
                url,
                timeout=(15, timeout_seconds),
                headers={"User-Agent": "ko-oilflows/1.0"},
            )
            if response.status_code == 404:
                errors.append(f"{url}: 404")
                continue

            response.raise_for_status()

            if not response.content:
                errors.append(f"{url}: empty response")
                continue

            print(f"Downloaded JODI {year}: {url}")
            return response.content

        except requests.RequestException as exc:
            errors.append(f"{url}: {exc}")

    details = "\n".join(errors)
    raise RuntimeError(
        f"Could not download JODI primary CSV for {year}.\n{details}"
    )


def primary_year_urls(year: int) -> tuple[str, str]:
    return (
        f"{JODI_PRIMARY_BASE}/primaryyear{year}.csv",
        f"{JODI_PRIMARY_BASE}/{year}.csv",
    )


def read_primary_csv(content: bytes, year: int) -> pd.DataFrame:
    frame = pd.read_csv(
        BytesIO(content),
        dtype={
            "REF_AREA": "string",
            "TIME_PERIOD": "string",
            "ENERGY_PRODUCT": "string",
            "FLOW_BREAKDOWN": "string",
            "UNIT_MEASURE": "string",
            "ASSESSMENT_CODE": "string",
        },
    )

    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        raise RuntimeError(
            f"JODI {year} CSV is missing expected columns: {missing}"
        )

    frame["SOURCE_YEAR_FILE"] = year
    return frame


def select_gulf_crude_exports(frame: pd.DataFrame) -> pd.DataFrame:
    """Select monthly crude oil exports reported in thousand barrels/day."""
    selected = frame.loc[
        frame["REF_AREA"].isin(GULF_COUNTRIES)
        & frame["ENERGY_PRODUCT"].eq("CRUDEOIL")
        & frame["FLOW_BREAKDOWN"].eq("TOTEXPSB")
        & frame["UNIT_MEASURE"].eq("KBD")
    ].copy()

    selected["OBS_VALUE"] = pd.to_numeric(
        selected["OBS_VALUE"],
        errors="coerce",
    )
    selected["month"] = pd.to_datetime(
        selected["TIME_PERIOD"] + "-01",
        errors="raise",
    )

    selected["country"] = selected["REF_AREA"].map(GULF_COUNTRIES)

    result = selected[
        [
            "month",
            "REF_AREA",
            "country",
            "OBS_VALUE",
            "ASSESSMENT_CODE",
            "SOURCE_YEAR_FILE",
        ]
    ].rename(
        columns={
            "REF_AREA": "country_code",
            "OBS_VALUE": "crude_exports_kbd",
            "ASSESSMENT_CODE": "assessment_code",
            "SOURCE_YEAR_FILE": "source_year_file",
        }
    )

    return result.sort_values(
        ["month", "country_code"]
    ).reset_index(drop=True)


def validate_gulf_exports(frame: pd.DataFrame) -> None:
    if frame.empty:
        raise RuntimeError(
            "JODI download succeeded but no Gulf CRUDEOIL/TOTEXPSB/KBD rows were found."
        )

    duplicates = frame.duplicated(
        ["month", "country_code"],
        keep=False,
    )
    if duplicates.any():
        rows = frame.loc[
            duplicates,
            ["month", "country_code", "crude_exports_kbd"],
        ]
        raise RuntimeError(
            "Duplicate JODI country-month crude export rows found:\n"
            f"{rows.to_string(index=False)}"
        )

    negative = frame["crude_exports_kbd"].dropna() < 0
    if negative.any():
        raise RuntimeError("Negative JODI crude export observations found.")
