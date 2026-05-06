from pathlib import Path
from typing import Any

import httpx
from fastapi import HTTPException

from app.core.config import settings


def fetch_satellite_image_metadata(
    latitude: float,
    longitude: float,
    provider: str,
    cloud_max: float,
    resolution_m: float,
) -> dict[str, Any]:
    raise HTTPException(
        status_code=400,
        detail=f"No real imagery provider adapter configured for provider='{provider}'. Use STAC search or upload GeoTIFF.",
    )


def download_cog_asset(asset_url: str, target_name: str) -> str | None:
    if not asset_url:
        return None
    out_dir = Path(settings.upload_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / target_name
    # Local-first safety: only stream http/https public assets.
    if not asset_url.startswith(("http://", "https://")):
        return None
    with httpx.stream("GET", asset_url, timeout=90.0) as response:
        response.raise_for_status()
        with out_path.open("wb") as f:
            for chunk in response.iter_bytes():
                f.write(chunk)
    return out_path.as_posix()
