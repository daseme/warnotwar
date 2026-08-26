from pathlib import Path

import pandas as pd


APPROVED_VALUES = {"1", "1.0", "true", "yes"}

MEASUREMENT_COLUMNS = (
    "year",
    "month",
    "day",
    "portname",
    "country",
    "ISO3",
    "portcalls_tanker",
    "import_tanker",
    "export_tanker",
)


def inspect_raw_portwatch(project_root: Path) -> tuple[Path, Path, Path]:
    processed_dir = project_root / "data" / "processed"
    raw_dir = project_root / "data" / "raw"
    processed_dir.mkdir(parents=True, exist_ok=True)

    approved = read_approved_candidates(
        processed_dir / "terminal_candidates.csv"
    )
    daily = read_daily_portwatch(
        raw_dir / "portwatch_daily_selected_ports.csv"
    )

    metadata = (
        approved[
            [
                "portid",
                "portname",
                "role",
                "include_group",
                "seed_country",
                "seed_search_name",
            ]
        ]
        .drop_duplicates(subset=["portid"])
        .copy()
    )

    merged = daily.merge(
        metadata,
        on="portid",
        how="inner",
        validate="many_to_one",
        suffixes=("", "_approved"),
    )

    if merged.empty:
        raise RuntimeError(
            "The daily PortWatch file contains rows, but none matched "
            "the approved terminal IDs."
        )

    deduped, duplicate_rows, conflicts = dedupe_port_dates(merged)

    duplicate_path = processed_dir / "duplicate_port_dates.csv"
    duplicate_rows.to_csv(duplicate_path, index=False)

    conflict_path = processed_dir / "conflicting_port_dates.csv"
    conflicts.to_csv(conflict_path, index=False)

    if not conflicts.empty:
        raise RuntimeError(
            "Conflicting duplicate port/date observations exist. "
            "Review data/processed/conflicting_port_dates.csv."
        )

    coverage_path = write_terminal_coverage(
        approved=metadata,
        daily=deduped,
        output_dir=processed_dir,
    )
    weekly_path = write_weekly_proxy(deduped, processed_dir)

    print(f"Approved terminals: {len(metadata)}")
    print(f"Raw daily rows matched: {len(merged):,}")
    print(f"Exact duplicate rows removed: {len(merged) - len(deduped):,}")
    print("Conflicting duplicate groups: 0")
    print(f"Unique port/date observations: {len(deduped):,}")
    print(f"Wrote {coverage_path}")
    print(f"Wrote {duplicate_path}")
    print(f"Wrote {conflict_path}")
    print(f"Wrote {weekly_path}")

    return coverage_path, duplicate_path, weekly_path


def dedupe_port_dates(
    daily: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    duplicate_mask = daily.duplicated(
        subset=["portid", "date"],
        keep=False,
    )
    duplicate_rows = daily.loc[duplicate_mask].copy()

    conflicting_keys = []

    for key, group in duplicate_rows.groupby(["portid", "date"]):
        varying_columns = [
            column
            for column in MEASUREMENT_COLUMNS
            if column in group.columns
            and group[column].nunique(dropna=False) > 1
        ]
        if varying_columns:
            conflicting_keys.append(key)

    conflict_mask = pd.Series(False, index=daily.index)

    for portid, observation_date in conflicting_keys:
        conflict_mask |= (
            daily["portid"].eq(portid)
            & daily["date"].eq(observation_date)
        )

    conflicts = daily.loc[conflict_mask].copy()

    if not conflicts.empty:
        return daily.copy(), duplicate_rows, conflicts

    sort_columns = ["portid", "date"]
    if "ObjectId" in daily.columns:
        sort_columns.append("ObjectId")

    deduped = (
        daily.sort_values(sort_columns)
        .drop_duplicates(["portid", "date"], keep="first")
        .reset_index(drop=True)
    )

    return deduped, duplicate_rows, conflicts


def read_approved_candidates(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)

    candidates = pd.read_csv(
        path,
        dtype={
            "approved": "string",
            "portid": "string",
        },
    )

    approved_flag = (
        candidates["approved"]
        .fillna("")
        .str.strip()
        .str.lower()
        .isin(APPROVED_VALUES)
    )
    approved = candidates.loc[approved_flag].copy()

    if approved.empty:
        raise RuntimeError(
            "No approved terminals were recognized in terminal_candidates.csv."
        )

    approved["portid"] = approved["portid"].str.strip()
    return approved


def read_daily_portwatch(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)

    daily = pd.read_csv(
        path,
        dtype={"portid": "string"},
        parse_dates=["date"],
    )

    if daily.empty:
        raise RuntimeError(f"{path} contains no rows.")

    daily["portid"] = daily["portid"].str.strip()

    required = {
        "date",
        "portid",
        "portname",
        "export_tanker",
        "portcalls_tanker",
    }
    missing = sorted(required - set(daily.columns))
    if missing:
        raise RuntimeError(f"Raw PortWatch file is missing columns: {missing}")

    return daily


def write_terminal_coverage(
    approved: pd.DataFrame,
    daily: pd.DataFrame,
    output_dir: Path,
) -> Path:
    stats = (
        daily.groupby("portid", as_index=False)
        .agg(
            observed_days=("date", "nunique"),
            first_date=("date", "min"),
            last_date=("date", "max"),
            export_tanker_total=("export_tanker", "sum"),
            tanker_calls_total=("portcalls_tanker", "sum"),
            active_export_days=("export_tanker", lambda s: int((s > 0).sum())),
            active_tanker_call_days=("portcalls_tanker", lambda s: int((s > 0).sum())),
        )
    )

    coverage = approved.merge(stats, on="portid", how="left")

    for column in (
        "observed_days",
        "export_tanker_total",
        "tanker_calls_total",
        "active_export_days",
        "active_tanker_call_days",
    ):
        coverage[column] = coverage[column].fillna(0)

    coverage["has_daily_data"] = coverage["observed_days"] > 0
    coverage["has_export_signal"] = coverage["export_tanker_total"] > 0
    coverage["has_tanker_activity"] = coverage["tanker_calls_total"] > 0

    max_last_date = daily["date"].max()
    coverage["coverage_current"] = (
        pd.to_datetime(coverage["last_date"], errors="coerce")
        >= max_last_date - pd.Timedelta(days=7)
    )

    coverage["quality_flag"] = coverage.apply(classify_quality, axis=1)

    coverage = coverage.sort_values(
        ["quality_flag", "seed_country", "seed_search_name"]
    )

    path = output_dir / "terminal_coverage.csv"
    coverage.to_csv(path, index=False)
    return path


def classify_quality(row: pd.Series) -> str:
    if not row["has_daily_data"]:
        return "NO_DATA"
    if not row["has_export_signal"] and not row["has_tanker_activity"]:
        return "DEAD_SERIES"
    if not row["has_export_signal"]:
        return "NO_EXPORT_SIGNAL"
    if not row["coverage_current"]:
        return "STALE_SERIES"
    return "USABLE_PROXY"


def write_weekly_proxy(daily: pd.DataFrame, output_dir: Path) -> Path:
    weekly = (
        daily.assign(
            week=lambda frame: frame["date"]
            .dt.to_period("W-SUN")
            .dt.start_time
        )
        .groupby(["week", "include_group"], as_index=False)
        .agg(
            export_tanker_mt=("export_tanker", "sum"),
            tanker_calls=("portcalls_tanker", "sum"),
            observed_port_days=("date", "size"),
            active_export_observations=(
                "export_tanker",
                lambda s: int((s > 0).sum()),
            ),
        )
        .sort_values(["week", "include_group"])
    )

    path = output_dir / "weekly_terminal_proxy.csv"
    weekly.to_csv(path, index=False)
    return path


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    inspect_raw_portwatch(project_root)


if __name__ == "__main__":
    main()
