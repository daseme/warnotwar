from pathlib import Path

import pandas as pd

from .settings import Settings
from .shock import build_market_response_summary, build_shock_timeline


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    settings = Settings(project_root=project_root)

    master_path = (
        settings.processed_dir / "oilflows_daily_master.csv"
    )
    master = pd.read_csv(master_path)

    timeline = build_shock_timeline(
        master,
        search_start="2026-02-23",
    )

    timeline_path = (
        settings.processed_dir / "shock_timeline.csv"
    )
    timeline.to_csv(timeline_path, index=False)

    print(f"Wrote {timeline_path}")

    print("\nFirst Hormuz 7-day threshold crossings:")
    print(
        timeline.to_string(
            index=False,
            formatters={
                "threshold_pct": "{:.0f}".format,
                "hormuz_index": "{:.1f}".format,
                "brent_usd":
                    lambda x: "" if pd.isna(x) else f"{x:.2f}",
                "bno_usd":
                    lambda x: "" if pd.isna(x) else f"{x:.2f}",
                "known_gulf_official_index":
                    lambda x: "" if pd.isna(x) else f"{x:.1f}",
                "core_official_exports_index":
                    lambda x: "" if pd.isna(x) else f"{x:.1f}",
                "saudi_gulf_proxy_index":
                    lambda x: "" if pd.isna(x) else f"{x:.1f}",
                "saudi_bypass_proxy_index":
                    lambda x: "" if pd.isna(x) else f"{x:.1f}",
                "uae_gulf_proxy_index":
                    lambda x: "" if pd.isna(x) else f"{x:.1f}",
                "uae_bypass_proxy_index":
                    lambda x: "" if pd.isna(x) else f"{x:.1f}",
            },
        )
    )

    if timeline.empty:
        return

    anchor = timeline.iloc[-1]["first_date"]
    response = build_market_response_summary(
        master,
        anchor_date=str(pd.Timestamp(anchor).date()),
    )

    response_path = (
        settings.processed_dir / "market_shock_response.csv"
    )
    response.to_csv(response_path, index=False)

    print(f"\nWrote {response_path}")
    print("\nMarket response around deepest threshold:")
    print(
        response.to_string(
            index=False,
            formatters={
                "pre_anchor_value": "{:.2f}".format,
                "anchor_value": "{:.2f}".format,
                "move_to_anchor_pct": "{:.1f}%".format,
                "peak_value": "{:.2f}".format,
                "move_pre_to_peak_pct": "{:.1f}%".format,
                "move_anchor_to_peak_pct": "{:.1f}%".format,
            },
        )
    )


if __name__ == "__main__":
    main()
