from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    project_root: Path
    start_date: str = "2025-06-22"
    request_timeout_seconds: int = 120
    page_size: int = 500

    @property
    def raw_dir(self) -> Path:
        return self.project_root / "data" / "raw"

    @property
    def processed_dir(self) -> Path:
        return self.project_root / "data" / "processed"


PORTS_REGISTRY_URL = (
    "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/ArcGIS/rest/services/"
    "PortWatch_ports_database/FeatureServer/0/query"
)

DAILY_PORTS_URL = (
    "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/ArcGIS/rest/services/"
    "Daily_Ports_Data/FeatureServer/0/query"
)

DAILY_CHOKEPOINTS_URL = (
    "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/ArcGIS/rest/services/"
    "Daily_Chokepoints_Data/FeatureServer/0/query"
)

HORMUZ_PORT_ID = "chokepoint6"
