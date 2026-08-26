from pathlib import Path
import json

import pandas as pd

from .eia_inventory import (
    BUFFER_SERIES,
    build_buffer_metadata,
    build_buffer_weekly,
    parse_eia_weekly_xls,
)
from .publish import dataframe_to_json_records
from .settings import Settings


PUBLISH_COLUMNS = [
    "week_end",
    "crude_stocks_incl_spr_mbbl",
    "commercial_crude_mbbl",
    "spr_crude_mbbl",
    "refinery_crude_inputs_mbd",
    "days_supply_incl_spr",
    "commercial_days_supply",
    "spr_days_equivalent",
    "days_supply_incl_spr_percentile",
]


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    settings = Settings(project_root=project_root)

    eia_dir = settings.raw_dir / "eia"
    parsed = {}
    for column, sourcekey in BUFFER_SERIES.items():
        parsed[column] = parse_eia_weekly_xls(
            eia_dir / f"{sourcekey}w.xls",
            expected_sourcekey=sourcekey,
            value_column=column,
        )

    weekly = build_buffer_weekly(
        parsed["crude_stocks_incl_spr_mbbl"],
        parsed["commercial_crude_mbbl"],
        parsed["spr_crude_mbbl"],
        parsed["refinery_crude_inputs_mbd"],
    )

    # Round the derived ratios for publication; source volumes stay verbatim.
    publish = weekly[PUBLISH_COLUMNS].copy()
    for column in [
        "days_supply_incl_spr",
        "commercial_days_supply",
        "spr_days_equivalent",
        "days_supply_incl_spr_percentile",
    ]:
        publish[column] = publish[column].round(2)

    metadata = build_buffer_metadata(weekly)

    published = project_root / "data" / "published"
    published.mkdir(parents=True, exist_ok=True)

    csv_path = published / "us_crude_buffer_weekly.csv"
    json_path = published / "us_crude_buffer_weekly.json"
    meta_path = published / "us_crude_buffer_meta.json"

    publish.to_csv(csv_path, index=False)
    json_path.write_text(
        dataframe_to_json_records(publish, date_column="week_end"),
        encoding="utf-8",
    )
    meta_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Rows: {len(publish):,}")
    print(f"Weeks: {metadata['first_week']} through {metadata['last_week']}")
    print(f"Wrote {csv_path}")
    print(f"Wrote {json_path}")
    print(f"Wrote {meta_path}")

    latest = publish.dropna(subset=["days_supply_incl_spr"]).iloc[-1]
    print(
        f"\nLatest week {pd.Timestamp(latest['week_end']).date()}: "
        f"{latest['days_supply_incl_spr']:.1f} days incl SPR "
        f"({latest['commercial_days_supply']:.1f} commercial + "
        f"{latest['spr_days_equivalent']:.1f} SPR-equivalent), "
        f"{latest['days_supply_incl_spr_percentile']:.1f}th percentile "
        "of weekly observations since "
        f"{metadata['first_week'][:4]}."
    )
    if metadata["prior_lower_date"]:
        print(
            f"Prior lower reading: {metadata['prior_lower_date']} "
            f"({metadata['years_since_prior_lower']} years ago)."
        )
    else:
        print("No prior lower reading in the EIA history (all-time low).")


if __name__ == "__main__":
    main()
