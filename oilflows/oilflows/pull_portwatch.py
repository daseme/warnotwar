from pathlib import Path

import pandas as pd

from .portwatch import fetch_daily_ports, fetch_hormuz
from .settings import Settings


def pull_portwatch_history(settings: Settings) -> tuple[Path, Path]:
    approved = read_approved_terminals(settings.processed_dir / "terminal_candidates.csv")
    port_ids = approved["portid"].dropna().astype(str).unique().tolist()

    print(f"Approved ports: {len(port_ids)}")

    daily_ports = fetch_daily_ports(
        port_ids,
        settings.start_date,
        page_size=settings.page_size,
        timeout_seconds=settings.request_timeout_seconds,
    )

    if daily_ports.empty:
        raise RuntimeError(
            "PortWatch returned zero daily port rows. "
            "No files were written; check the ArcGIS query/filter."
        )

    returned_ports = set(daily_ports["portid"].dropna().astype(str))
    missing_ports = sorted(set(port_ids) - returned_ports)

    print(f"Daily port rows: {len(daily_ports):,}")
    print(f"Ports with data: {len(returned_ports)}/{len(port_ids)}")

    if missing_ports:
        print("WARNING: approved ports with no daily rows:")
        for port_id in missing_ports:
            print(f"  - {port_id}")

    hormuz = fetch_hormuz(
        settings.start_date,
        page_size=settings.page_size,
        timeout_seconds=settings.request_timeout_seconds,
    )

    if hormuz.empty:
        raise RuntimeError(
            "PortWatch returned zero Strait of Hormuz rows. "
            "No files were written."
        )

    settings.raw_dir.mkdir(parents=True, exist_ok=True)
    daily_path = settings.raw_dir / "portwatch_daily_selected_ports.csv"
    hormuz_path = settings.raw_dir / "portwatch_hormuz_daily.csv"

    daily_ports.to_csv(daily_path, index=False)
    hormuz.to_csv(hormuz_path, index=False)

    return daily_path, hormuz_path


def read_approved_terminals(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} does not exist. Run `python -m oilflows.discover_ports` first."
        )

    candidates = pd.read_csv(path, dtype={"approved": "string"})
    approved = candidates.loc[
        candidates["approved"]
        .fillna("")
        .str.strip()
        .isin({"1", "true", "TRUE", "yes", "YES"})
    ]

    if approved.empty:
        raise RuntimeError(
            "No terminals are approved. Review "
            "data/processed/terminal_candidates.csv and set approved=1."
        )

    duplicate_seeds = approved.duplicated(
        ["seed_country", "seed_search_name"],
        keep=False,
    )

    if duplicate_seeds.any():
        duplicates = approved.loc[
            duplicate_seeds,
            ["seed_country", "seed_search_name", "portid", "portname"],
        ]
        raise RuntimeError(
            "More than one approved match for a seed:\n"
            f"{duplicates.to_string(index=False)}"
        )

    return approved


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    daily_path, hormuz_path = pull_portwatch_history(
        Settings(project_root=project_root)
    )
    print(f"Wrote {daily_path}")
    print(f"Wrote {hormuz_path}")


if __name__ == "__main__":
    main()
