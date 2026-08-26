from pathlib import Path

import pandas as pd

from .jodi import GULF_COUNTRIES, pull_jodi_crude_exports
from .settings import Settings


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    settings = Settings(project_root=project_root)

    years = (2025, 2026)

    exports, annual_files = pull_jodi_crude_exports(
        years,
        timeout_seconds=settings.request_timeout_seconds,
    )

    settings.raw_dir.mkdir(parents=True, exist_ok=True)
    settings.processed_dir.mkdir(parents=True, exist_ok=True)

    for year, content in annual_files.items():
        path = settings.raw_dir / f"jodi_primary_{year}.csv"
        path.write_bytes(content)
        print(f"Wrote {path}")

    output_path = settings.processed_dir / "jodi_crude_exports_monthly.csv"
    exports.to_csv(output_path, index=False)
    print(f"Wrote {output_path}")

    print("\nCoverage by country:")
    coverage = (
        exports.groupby(["country_code", "country"], as_index=False)
        .agg(
            first_month=("month", "min"),
            last_month=("month", "max"),
            observations=("crude_exports_kbd", "count"),
            missing_values=("crude_exports_kbd", lambda s: int(s.isna().sum())),
        )
        .sort_values("country_code")
    )
    print(coverage.to_string(index=False))

    print("\nLatest available observations:")
    latest = (
        exports.dropna(subset=["crude_exports_kbd"])
        .sort_values("month")
        .groupby(["country_code", "country"], as_index=False)
        .tail(1)
        .sort_values("country_code")
    )
    print(
        latest[
            [
                "country_code",
                "country",
                "month",
                "crude_exports_kbd",
                "assessment_code",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
