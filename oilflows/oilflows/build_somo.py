from pathlib import Path

from .somo import build_somo_exports


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    raw_dir = project_root / "data" / "raw" / "somo"
    output_path = project_root / "data" / "processed" / "somo_iraq_exports.csv"

    result = build_somo_exports(raw_dir)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)

    print(f"Rows: {len(result)}")
    print(f"First period: {result['period_start'].min().date()}")
    print(f"Last period: {result['period_end'].max().date()}")
    print(f"Wrote {output_path}")

    print("\nOfficial Iraq crude export periods:")
    print(
        result[
            [
                "period_start",
                "period_end",
                "granularity",
                "basrah_barrels",
                "total_barrels",
                "basrah_kbd",
                "total_kbd",
                "source_file",
            ]
        ].to_string(
            index=False,
            formatters={
                "basrah_barrels": "{:,.0f}".format,
                "total_barrels": "{:,.0f}".format,
                "basrah_kbd": "{:,.1f}".format,
                "total_kbd": "{:,.1f}".format,
            },
        )
    )


if __name__ == "__main__":
    main()
