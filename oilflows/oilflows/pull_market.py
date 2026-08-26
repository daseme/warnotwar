from pathlib import Path
import json

import pandas as pd

from .market import add_market_calendar_features, pull_market_daily
from .settings import Settings


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    settings = Settings(project_root=project_root)

    market, fred_text, yahoo_json = pull_market_daily(
        start_date=settings.start_date,
        timeout_seconds=settings.request_timeout_seconds,
    )

    settings.raw_dir.mkdir(parents=True, exist_ok=True)
    settings.processed_dir.mkdir(parents=True, exist_ok=True)

    fred_path = settings.raw_dir / "fred_brent_daily.csv"
    fred_path.write_text(fred_text, encoding="utf-8")

    yahoo_path = settings.raw_dir / "yahoo_bno_daily.json"
    yahoo_path.write_text(
        json.dumps(yahoo_json, indent=2),
        encoding="utf-8",
    )

    end_date = market["date"].max().date().isoformat()
    processed = add_market_calendar_features(
        market,
        start_date=settings.start_date,
        end_date=end_date,
    )

    output_path = settings.processed_dir / "market_daily.csv"
    processed.to_csv(output_path, index=False)

    print(f"Wrote {fred_path}")
    print(f"Wrote {yahoo_path}")
    print(f"Wrote {output_path}")

    brent = market.dropna(subset=["brent_spot_usd"])
    bno = market.dropna(subset=["bno_close_usd"])

    print("\nCoverage:")
    print(
        f"Brent: {len(brent):,} observations, "
        f"{brent['date'].min().date()} through "
        f"{brent['date'].max().date()}"
    )
    print(
        f"BNO:   {len(bno):,} observations, "
        f"{bno['date'].min().date()} through "
        f"{bno['date'].max().date()}"
    )

    print("\nRecent observed market sessions:")
    recent = market.loc[
        market[
            ["brent_spot_usd", "bno_close_usd"]
        ].notna().any(axis=1)
    ].tail(15)

    print(
        recent[
            [
                "date",
                "brent_spot_usd",
                "bno_close_usd",
                "bno_adj_close_usd",
                "bno_volume",
            ]
        ].to_string(
            index=False,
            formatters={
                "brent_spot_usd":
                    lambda x: "" if pd.isna(x) else f"{x:.2f}",
                "bno_close_usd":
                    lambda x: "" if pd.isna(x) else f"{x:.2f}",
                "bno_adj_close_usd":
                    lambda x: "" if pd.isna(x) else f"{x:.2f}",
                "bno_volume":
                    lambda x: "" if pd.isna(x) else f"{x:,.0f}",
            },
        )
    )


if __name__ == "__main__":
    main()
