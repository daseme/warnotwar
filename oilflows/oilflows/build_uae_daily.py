from pathlib import Path

import pandas as pd

from .settings import Settings
from .uae_daily import build_uae_daily


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    settings = Settings(project_root=project_root)

    portwatch_path = (
        settings.raw_dir / "portwatch_daily_selected_ports.csv"
    )
    output_path = (
        settings.processed_dir / "uae_crude_routes_daily.csv"
    )

    portwatch = pd.read_csv(
        portwatch_path,
        dtype={"portid": "string"},
    )

    result = build_uae_daily(
        portwatch,
        start_date=settings.start_date,
    )

    result.to_csv(output_path, index=False)

    print(f"Rows: {len(result):,}")
    print(f"First date: {result['date'].min().date()}")
    print(f"Last date: {result['date'].max().date()}")
    print(f"Wrote {output_path}")

    first = result.iloc[0]
    print("\nBaseline (2025-07-01 through 2025-12-31):")
    print(
        "Gulf proxy 7d mean: "
        f"{first['uae_gulf_proxy_baseline_mt_7d']:,.0f} mt/day"
    )
    print(
        "Fujairah proxy 7d mean: "
        f"{first['uae_bypass_proxy_baseline_mt_7d']:,.0f} mt/day"
    )

    print(
        "\nWeekly route-proxy snapshots "
        "(NOT official crude volumes or national route shares):"
    )

    sample = result.loc[
        result["date"].between("2026-02-23", result["date"].max())
        & (result["date"].dt.weekday == 0),
        [
            "date",
            "uae_gulf_proxy_mt_7d",
            "uae_bypass_fujairah_proxy_mt_7d",
            "uae_gulf_proxy_index_7d",
            "uae_bypass_proxy_index_7d",
            "uae_proxy_bypass_share_7d",
        ],
    ]

    print(
        sample.to_string(
            index=False,
            formatters={
                "uae_gulf_proxy_mt_7d":
                    lambda x: "" if pd.isna(x) else f"{x:,.0f}",
                "uae_bypass_fujairah_proxy_mt_7d":
                    lambda x: "" if pd.isna(x) else f"{x:,.0f}",
                "uae_gulf_proxy_index_7d":
                    lambda x: "" if pd.isna(x) else f"{x:.1f}",
                "uae_bypass_proxy_index_7d":
                    lambda x: "" if pd.isna(x) else f"{x:.1f}",
                "uae_proxy_bypass_share_7d":
                    lambda x: "" if pd.isna(x) else f"{x:.1%}",
            },
        )
    )


if __name__ == "__main__":
    main()
