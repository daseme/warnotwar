from pathlib import Path

import pandas as pd

from .master import build_daily_master
from .settings import Settings


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    settings = Settings(project_root=project_root)
    processed = settings.processed_dir

    market_path = processed / "market_daily.csv"
    market = pd.read_csv(market_path) if market_path.exists() else None

    master = build_daily_master(
        pd.read_csv(processed / "hormuz_daily.csv"),
        pd.read_csv(processed / "iraq_basrah_daily.csv"),
        pd.read_csv(processed / "kuwait_crude_daily.csv"),
        pd.read_csv(processed / "saudi_crude_routes_daily.csv"),
        pd.read_csv(processed / "uae_crude_routes_daily.csv"),
        market,
        start_date=settings.start_date,
    )

    output_path = processed / "oilflows_daily_master.csv"
    master.to_csv(output_path, index=False)

    print(f"Rows: {len(master):,}")
    print(f"First date: {master['date'].min().date()}")
    print(f"Last date: {master['date'].max().date()}")
    print(f"Wrote {output_path}")

    print("\nBaseline = 100 (2025-07-01 through 2025-12-31)")
    print(
        "Known Gulf official = Iraq Basrah + Kuwait.\n"
        "Core official exports = Iraq Basrah + Kuwait + Saudi national.\n"
        "Saudi national is NOT a Hormuz-only measure."
    )

    columns = [
        "date",
        "hormuz_tanker_count_index_7d",
        "known_gulf_official_index_7d",
        "core_official_exports_index_7d",
        "saudi_gulf_proxy_index_7d",
        "saudi_bypass_proxy_index_7d",
        "uae_gulf_proxy_index_7d",
        "uae_bypass_proxy_index_7d",
    ]

    if market is not None:
        columns += [
            "brent_spot_last_usd",
            "bno_last_close_usd",
        ]

    sample = master.loc[
        master["date"].between("2026-02-23", master["date"].max())
        & (master["date"].dt.weekday == 0),
        columns,
    ]

    print("\nWeekly disruption snapshot:")
    print(sample.tail(30).to_string(index=False))


if __name__ == "__main__":
    main()
