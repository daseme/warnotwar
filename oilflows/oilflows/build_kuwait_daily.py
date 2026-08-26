from pathlib import Path

import pandas as pd

from .kuwait_daily import build_kuwait_daily
from .settings import Settings


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    settings = Settings(project_root=project_root)

    portwatch_path = (
        settings.raw_dir / "portwatch_daily_selected_ports.csv"
    )
    jodi_path = (
        settings.processed_dir / "jodi_crude_exports_monthly.csv"
    )
    output_path = (
        settings.processed_dir / "kuwait_crude_daily.csv"
    )

    portwatch = pd.read_csv(
        portwatch_path,
        dtype={"portid": "string"},
    )
    jodi = pd.read_csv(
        jodi_path,
        dtype={
            "country_code": "string",
            "assessment_code": "string",
        },
    )

    result = build_kuwait_daily(
        portwatch,
        jodi,
        start_date=settings.start_date,
    )

    result.to_csv(output_path, index=False)

    print(f"Rows: {len(result):,}")
    print(f"First date: {result['date'].min().date()}")
    print(f"Last date: {result['date'].max().date()}")
    print(f"Wrote {output_path}")

    report = (
        result[
            [
                "calibration_period_start",
                "calibration_period_end",
                "official_kuwait_kbd",
                "official_kuwait_barrels",
                "allocation_method",
                "kuwait_crude_barrels",
            ]
        ]
        .dropna(subset=["calibration_period_start"])
        .groupby(
            [
                "calibration_period_start",
                "calibration_period_end",
                "official_kuwait_kbd",
                "official_kuwait_barrels",
                "allocation_method",
            ],
            as_index=False,
            dropna=False,
        )
        .agg(
            allocated_barrels=("kuwait_crude_barrels", "sum"),
            allocated_days=("kuwait_crude_barrels", "count"),
        )
    )

    report["difference"] = (
        report["allocated_barrels"]
        - report["official_kuwait_barrels"]
    )

    print("\nCalibration periods:")
    print(
        report.to_string(
            index=False,
            formatters={
                "official_kuwait_kbd": "{:,.1f}".format,
                "official_kuwait_barrels": "{:,.0f}".format,
                "allocated_barrels": "{:,.0f}".format,
                "difference": "{:,.6f}".format,
            },
        )
    )

    print("\nSelected disruption window:")
    sample = result.loc[
        result["date"].between("2026-02-20", "2026-06-30"),
        [
            "date",
            "kuwait_crude_barrels",
            "kuwait_crude_mbd",
            "kuwait_crude_7d_mbd",
            "allocation_method",
        ],
    ]
    print(sample.to_string(index=False))


if __name__ == "__main__":
    main()
