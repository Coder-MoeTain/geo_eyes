from pathlib import Path
from urllib.parse import quote_plus

from app.core.config import settings


def build_titiler_urls(local_geotiff_path: str) -> dict:
    path = Path(local_geotiff_path)
    if not path.exists():
        raise FileNotFoundError(f"Raster file not found for tiling: {local_geotiff_path}")
    if path.suffix.lower() not in {".tif", ".tiff"}:
        raise ValueError("TiTiler overlay is only available for GeoTIFF/COG files")
    encoded = quote_plus(path.as_posix())
    return {
        "tiles_url": f"{settings.public_titiler_url}/cog/tiles/{{z}}/{{x}}/{{y}}.png?url={encoded}",
        "proxy_tiles_url": f"/titiler/cog/tiles/{{z}}/{{x}}/{{y}}.png?url={encoded}",
        "tilejson_url": f"{settings.public_titiler_url}/cog/tilejson.json?url={encoded}",
        "metadata_url": f"{settings.public_titiler_url}/cog/info?url={encoded}",
        "service_url": settings.internal_titiler_url,
    }
