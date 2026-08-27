from pathlib import Path

from .eia_inventory import BUFFER_SERIES, PRODUCT_SERIES, fetch_eia_weekly_xls
from .settings import Settings


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    settings = Settings(project_root=project_root)

    eia_dir = settings.raw_dir / "eia"
    eia_dir.mkdir(parents=True, exist_ok=True)

    for column, sourcekey in {**BUFFER_SERIES, **PRODUCT_SERIES}.items():
        content = fetch_eia_weekly_xls(
            sourcekey,
            timeout_seconds=settings.request_timeout_seconds,
        )
        path = eia_dir / f"{sourcekey}w.xls"
        path.write_bytes(content)
        print(f"Wrote {path} ({len(content):,} bytes) [{column}]")


if __name__ == "__main__":
    main()
