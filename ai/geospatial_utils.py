from typing import Any

import rasterio
from shapely.geometry import Polygon, mapping


def pixel_bbox_to_geojson(
    tif_path: str,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> dict[str, Any]:
    with rasterio.open(tif_path) as src:
        tl = src.transform * (x1, y1)
        tr = src.transform * (x2, y1)
        br = src.transform * (x2, y2)
        bl = src.transform * (x1, y2)
    poly = Polygon([tl, tr, br, bl, tl])
    return mapping(poly)
