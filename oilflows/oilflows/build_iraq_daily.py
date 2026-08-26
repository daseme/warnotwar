from pathlib import Path

import pandas as pd

from .iraq_daily import build_iraq_daily
from .settings import Settings


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    settings = Settings(project_root=project_root)

    portwatch_path = (
        settings.raw_dir / "portwatch_daily_selected_ports.csv"
    )
    somo_path = settings.processed_dir / "somo_iraq_exports.csv"
    hormuz_path = settings.processed_dir / "hormuz_daily.csv"
    output_path = settings.processed_dir / "iraq_basrah_daily.csv"

    portwatch = pd.read_csv(portwatch_path, dtype={"portid": "string"})
    somo = pd.read_csv(somo_path)
    hormuz = pd.read_csv(hormuz_path)

    result = build_iraq_daily(
        portwatch,
        somo,
        hormuz,
        start_date=settings.start_date,
    )

    result.to_csv(output_path, index=False)

    print(f"Rows: {len(result):,}")
    print(f"First date: {result['date'].min().date()}")
    print(f"Last date: {result['date'].max().date()}")
    print(f"Wrote {output_path}")

    print("\nCalibration periods:")
    report = (
        result[
            [
                "calibration_period_start",
                "calibration_period_end",
                "official_basrah_barrels",
                "allocation_method",
                "iraq_basrah_barrels",
            ]
        ]
        .dropna(subset=["calibration_period_start"])
        .groupby(
            [
                "calibration_period_start",
                "calibration_period_end",
                "official_basrah_barrels",
                "allocation_method",
            ],
            as_index=False,
            dropna=False,
        )
        .agg(
            allocated_barrels=("iraq_basrah_barrels", "sum"),
            allocated_days=("iraq_basrah_barrels", "count"),
        )
    )

    report["difference"] = (
        report["allocated_barrels"]
        - report["official_basrah_barrels"]
    )

    print(
        report.to_string(
            index=False,
            formatters={
                "official_basrah_barrels": "{:,.0f}".format,
                "allocated_barrels": "{:,.0f}".format,
                "difference": "{:,.6f}".format,
            },
        )
    )

    print("\nSelected disruption window:")
    sample = result.loc[
        result["date"].between("2026-02-20", "2026-04-10"),
        [
            "date",
            "iraq_basrah_barrels",
            "iraq_basrah_mbd",
            "iraq_basrah_7d_mbd",
            "allocation_method",
        ],
    ]
    print(sample.to_string(index=False))


if __name__ == "__main__":
    main()
