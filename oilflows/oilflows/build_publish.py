from pathlib import Path
import json

import pandas as pd

from .publish import (
    build_publish_daily,
    build_publish_metadata,
    dataframe_to_json_records,
)
from .settings import Settings


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    settings = Settings(project_root=project_root)

    processed = settings.processed_dir
    published = project_root / "data" / "published"
    published.mkdir(parents=True, exist_ok=True)

    master = pd.read_csv(
        processed / "oilflows_daily_master.csv"
    )
    timeline = pd.read_csv(
        processed / "shock_timeline.csv"
    )
    response = pd.read_csv(
        processed / "market_shock_response.csv"
    )

    daily = build_publish_daily(
        master,
        timeline,
        response,
    )

    metadata = build_publish_metadata(daily)

    csv_path = published / "oilflows_daily.csv"
    json_path = published / "oilflows_daily.json"
    meta_path = published / "oilflows_meta.json"

    daily.to_csv(csv_path, index=False)
    json_path.write_text(
        dataframe_to_json_records(daily),
        encoding="utf-8",
    )
    meta_path.write_text(
        json.dumps(
            metadata,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(f"Rows: {len(daily):,}")
    print(f"First date: {pd.to_datetime(daily['date']).min().date()}")
    print(f"Last date: {pd.to_datetime(daily['date']).max().date()}")
    print(f"Wrote {csv_path}")
    print(f"Wrote {json_path}")
    print(f"Wrote {meta_path}")

    print("\nShock markers:")
    markers = daily.loc[
        daily["shock_marker"].notna(),
        ["date", "shock_marker"],
    ]
    print(markers.to_string(index=False))

    print("\nLatest observation dates:")
    for key, value in metadata["latest_observation_dates"].items():
        print(f"{key:24} {value}")


if __name__ == "__main__":
    main()
