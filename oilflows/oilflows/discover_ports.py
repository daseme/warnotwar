from pathlib import Path

from .settings import Settings
from .portwatch import fetch_port_registry
from .terminal_registry import resolve_terminal_candidates


def discover_port_candidates(settings: Settings) -> Path:
    settings.raw_dir.mkdir(parents=True, exist_ok=True)
    settings.processed_dir.mkdir(parents=True, exist_ok=True)

    registry = fetch_port_registry(
        page_size=settings.page_size,
        timeout_seconds=settings.request_timeout_seconds,
    )
    candidates = resolve_terminal_candidates(registry)

    registry_path = settings.raw_dir / "portwatch_ports_registry.csv"
    candidates_path = settings.processed_dir / "terminal_candidates.csv"
    registry.to_csv(registry_path, index=False)
    candidates.to_csv(candidates_path, index=False)
    return candidates_path


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    output = discover_port_candidates(Settings(project_root=project_root))
    print(f"Wrote {output}")
    print("Review candidate rows and mark approved=1 for the exact terminals to include.")


if __name__ == "__main__":
    main()
