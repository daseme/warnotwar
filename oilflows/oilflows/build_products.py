from pathlib import Path
import json

from .eia_inventory import (
    PRODUCT_SERIES,
    build_products_metadata,
    build_products_weekly,
    parse_eia_weekly_xls,
)
from .publish import dataframe_to_json_records
from .settings import Settings


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    settings = Settings(project_root=project_root)

    eia_dir = settings.raw_dir / "eia"
    parsed = {
        column: parse_eia_weekly_xls(
            eia_dir / f"{sourcekey}w.xls",
            expected_sourcekey=sourcekey,
            value_column=column,
        )
        for column, sourcekey in PRODUCT_SERIES.items()
    }

    weekly = build_products_weekly(parsed)
    publish = weekly.copy()
    for column in ("gasoline_days_cover", "distillate_days_cover"):
        publish[column] = publish[column].round(2)

    metadata = build_products_metadata(weekly)

    published = project_root / "data" / "published"
    published.mkdir(parents=True, exist_ok=True)
    csv_path = published / "us_products_weekly.csv"
    json_path = published / "us_products_weekly.json"
    meta_path = published / "us_products_meta.json"

    publish.to_csv(csv_path, index=False)
    json_path.write_text(
        dataframe_to_json_records(publish, date_column="week_end"),
        encoding="utf-8",
    )
    meta_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )

    print(f"Rows: {len(publish):,} ({metadata['first_week']} .. {metadata['last_week']})")
    g, d = metadata["gasoline_days_cover"], metadata["distillate_days_cover"]
    print(
        f"gasoline: {g['latest']} days cover, rank {g['rank_from_low']} from low of {g['weeks_observed']:,} weeks; "
        f"distillate: {d['latest']} days, rank {d['rank_from_low']} of {d['weeks_observed']:,}"
    )
    print(f"products supplied: {metadata['latest']['products_supplied_mbd']} mb/d")
    for p in (csv_path, json_path, meta_path):
        print("Wrote", p)


if __name__ == "__main__":
    main()
