from datetime import datetime, timezone
from typing import Any

import httpx
from shapely.geometry import shape

from app.core.config import settings


def _bbox_from_center(latitude: float, longitude: float, delta: float = 0.02) -> list[float]:
    return [longitude - delta, latitude - delta, longitude + delta, latitude + delta]


async def search_stac_scene(
    latitude: float,
    longitude: float,
    cloud_max: float,
    provider: str = "sentinel-2",
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict[str, Any]:
    bbox = _bbox_from_center(latitude, longitude)
    start = start_date or datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = end_date or datetime.now(timezone.utc)
    provider_map = {
        "sentinel-2": ["sentinel-2-l2a"],
        "landsat": ["landsat-c2-l2"],
        "all": ["sentinel-2-l2a", "landsat-c2-l2"],
    }
    if provider not in provider_map:
        raise ValueError(f"Unsupported STAC provider '{provider}'. Use one of: {', '.join(provider_map.keys())}.")
    collections = provider_map[provider]
    payload = {
        "collections": collections,
        "bbox": bbox,
        "datetime": f"{start.isoformat()}/{end.isoformat()}",
        "limit": 1,
        "query": {"eo:cloud_cover": {"lte": cloud_max}},
        "sortby": [{"field": "properties.datetime", "direction": "desc"}],
    }
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(f"{settings.stac_api_url}/search", json=payload)
        response.raise_for_status()
        data = response.json()
    features = data.get("features", [])
    if not features:
        return {}
    feature = features[0]
    assets = feature.get("assets", {})
    visual = assets.get("visual") or assets.get("rendered_preview") or assets.get("thumbnail") or assets.get("preview")
    analytic = assets.get("analytic") or assets.get("data")
    geom = feature.get("geometry")
    bounds_wkt = shape(geom).wkt if geom else None
    return {
        "provider": provider,
        "acquisition_date": datetime.fromisoformat(
            feature["properties"]["datetime"].replace("Z", "+00:00")
        ),
        "cloud_cover": float(feature["properties"].get("eo:cloud_cover", 0)),
        "preview_url": (visual or {}).get("href"),
        "asset_url": (analytic or visual or {}).get("href"),
        "bounds_geojson": geom,
        "bounds_wkt": bounds_wkt,
        "local_tif_path": None,
        "stac_item_id": feature.get("id"),
        "collection": feature.get("collection"),
        "resolution_m": 10.0 if provider in {"sentinel-2", "all"} else 30.0 if provider == "landsat" else None,
        "suitable_for_aircraft_detection": False if provider in {"sentinel-2", "landsat", "all"} else True,
        "warning": "This imagery may be insufficient for reliable aircraft detection."
        if provider in {"sentinel-2", "landsat", "all"}
        else None,
    }
