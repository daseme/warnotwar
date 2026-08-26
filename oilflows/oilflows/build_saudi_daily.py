from pathlib import Path

import pandas as pd

from .saudi_daily import build_saudi_daily
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
        settings.processed_dir / "saudi_crude_routes_daily.csv"
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

    result = build_saudi_daily(
        portwatch,
        jodi,
        start_date=settings.start_date,
    )

    result.to_csv(output_path, index=False)

    print(f"Rows: {len(result):,}")
    print(f"First date: {result['date'].min().date()}")
    print(f"Last date: {result['date'].max().date()}")
    print(f"Wrote {output_path}")

    official = (
        result.dropna(subset=["saudi_official_crude_mbd"])
        .groupby(
            [
                "saudi_calibration_period_start",
                "saudi_calibration_period_end",
                "saudi_official_crude_mbd",
            ],
            as_index=False,
        )
        .size()
    )

    print("\nOfficial Saudi crude-export level:")
    print(
        official[
            [
                "saudi_calibration_period_start",
                "saudi_calibration_period_end",
                "saudi_official_crude_mbd",
            ]
        ].to_string(
            index=False,
            formatters={
                "saudi_official_crude_mbd": "{:.3f}".format,
            },
        )
    )

    print(
        "\nWeekly route-proxy snapshots "
        "(Juaymah Gulf vs Yanbu bypass; NOT national route shares):"
    )

    sample = result.loc[
        result["date"].between("2026-02-23", result["date"].max())
        & (result["date"].dt.weekday == 0),
        [
            "date",
            "saudi_official_crude_mbd",
            "saudi_gulf_juaymah_proxy_mt_7d",
            "saudi_bypass_yanbu_proxy_mt_7d",
            "saudi_proxy_bypass_share_7d",
            "saudi_official_status",
        ],
    ]

    print(
        sample.to_string(
            index=False,
            formatters={
                "saudi_official_crude_mbd":
                    lambda x: "" if pd.isna(x) else f"{x:.3f}",
                "saudi_gulf_juaymah_proxy_mt_7d":
                    lambda x: "" if pd.isna(x) else f"{x:,.0f}",
                "saudi_bypass_yanbu_proxy_mt_7d":
                    lambda x: "" if pd.isna(x) else f"{x:,.0f}",
                "saudi_proxy_bypass_share_7d":
                    lambda x: "" if pd.isna(x) else f"{x:.1%}",
            },
        )
    )


if __name__ == "__main__":
    main()
