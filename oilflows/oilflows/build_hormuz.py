from pathlib import Path

import pandas as pd

from .hormuz import build_hormuz_daily, prepare_hormuz, validate_hormuz


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    source_path = project_root / "data" / "raw" / "portwatch_hormuz_daily.csv"
    output_path = project_root / "data" / "processed" / "hormuz_daily.csv"

    if not source_path.exists():
        raise FileNotFoundError(source_path)

    raw = pd.read_csv(source_path)
    prepared = prepare_hormuz(raw)
    validation = validate_hormuz(prepared)

    print(f"Rows: {validation.row_count:,}")
    print(f"First date: {validation.first_date.date()}")
    print(f"Last date: {validation.last_date.date()}")
    print(f"Missing dates: {len(validation.missing_dates)}")
    print(f"Duplicate dates: {len(validation.duplicate_dates)}")

    result = build_hormuz_daily(raw)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)

    print(f"Wrote {output_path}")

    print("\nRecent 14-day snapshot:")
    print(
        result.tail(14)[
            [
                "date",
                "hormuz_tanker_count",
                "hormuz_tanker_count_7d",
                "hormuz_tanker_capacity",
                "hormuz_tanker_capacity_7d",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
