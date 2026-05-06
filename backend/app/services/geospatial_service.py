from typing import Any

from affine import Affine
from pyproj import CRS, Geod, Transformer
from pyproj.exceptions import CRSError
from shapely.geometry import Point, Polygon, box, mapping
from shapely import make_valid
from shapely.ops import transform as shp_transform


def validate_crs(source_crs: str | None) -> bool:
    if not source_crs:
        return False
    try:
        CRS.from_user_input(source_crs)
        return True
    except CRSError:
        return False


def safe_transform_geometry(geom, source_crs: str | None, target_crs: str = "EPSG:4326"):
    if geom is None:
        return None
    if not source_crs:
        raise ValueError("CRS is missing")
    if not validate_crs(source_crs):
        raise ValueError(f"Invalid CRS: {source_crs}")
    src = CRS.from_user_input(source_crs)
    dst = CRS.from_user_input(target_crs)
    transformer = Transformer.from_crs(src, dst, always_xy=True)
    return shp_transform(transformer.transform, geom)


def transform_crs_to_wgs84(geom, source_crs: str):
    return safe_transform_geometry(geom, source_crs, "EPSG:4326")


def is_projected_meter_crs(crs: str | None) -> bool:
    if not crs or not validate_crs(crs):
        return False
    c = CRS.from_user_input(crs)
    unit_name = (c.axis_info[0].unit_name.lower() if c.axis_info else "")
    return c.is_projected and unit_name in {"metre", "meter"}


def pixel_bbox_to_wgs84_polygon(transform, x1: float, y1: float, x2: float, y2: float) -> Polygon:
    tl = transform * (x1, y1)
    tr = transform * (x2, y1)
    br = transform * (x2, y2)
    bl = transform * (x1, y2)
    return Polygon([tl, tr, br, bl, tl])


def pixel_bbox_to_image_crs_polygon(transform, x1: float, y1: float, x2: float, y2: float) -> Polygon:
    return pixel_bbox_to_wgs84_polygon(transform, x1, y1, x2, y2)


def pixel_bbox_to_geo_polygon(transform, x1: float, y1: float, x2: float, y2: float) -> Polygon:
    return pixel_bbox_to_image_crs_polygon(transform, x1, y1, x2, y2)


def pixel_bbox_to_wgs84_polygon_with_crs(
    transform,
    source_crs: str | None,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> Polygon:
    geom = pixel_bbox_to_image_crs_polygon(transform, x1, y1, x2, y2)
    if not source_crs:
        raise ValueError("CRS is missing")
    src = CRS.from_user_input(source_crs)
    if src.to_epsg() == 4326:
        return geom
    return safe_transform_geometry(geom, source_crs, "EPSG:4326")


def pixel_point_to_wgs84(transform, x: float, y: float) -> Point:
    gx, gy = transform * (x, y)
    return Point(gx, gy)


def calculate_centroid(geom) -> Point:
    return geom.centroid


def calculate_area_m2(geom_wgs84: Polygon) -> float:
    return calculate_geodesic_area_m2(geom_wgs84)


def calculate_geodesic_area_m2(geom_wgs84: Polygon) -> float:
    if geom_wgs84 is None or geom_wgs84.is_empty:
        return 0.0
    geod = Geod(ellps="WGS84")
    area_m2, _ = geod.geometry_area_perimeter(geom_wgs84)
    return abs(float(area_m2))


def validate_geometry(geom) -> bool:
    return geom is not None and geom.is_valid and not geom.is_empty


def repair_invalid_geometry(geom):
    if geom is None:
        return None
    if validate_geometry(geom):
        return geom
    fixed = make_valid(geom)
    return fixed if validate_geometry(fixed) else None


def create_geojson_feature(geom, properties: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"type": "Feature", "geometry": mapping(geom), "properties": properties or {}}


def create_geojson_feature_collection(features: list[dict[str, Any]]) -> dict[str, Any]:
    return {"type": "FeatureCollection", "features": features}


def image_bounds_to_wgs84(bounds, source_crs: str | None):
    geom = box(bounds.left, bounds.bottom, bounds.right, bounds.top)
    if not source_crs:
        raise ValueError("CRS is missing")
    src = CRS.from_user_input(source_crs)
    if src.to_epsg() == 4326:
        return geom
    return safe_transform_geometry(geom, source_crs, "EPSG:4326")


def estimate_gsd_meters(transform, crs: str | None, image_width: int, image_height: int) -> float | None:
    if transform is None or not crs or not validate_crs(crs):
        return None
    src = CRS.from_user_input(crs)
    x_res = abs(float(transform.a))
    y_res = abs(float(transform.e))
    if src.to_epsg() == 4326:
        # Approximate meters per degree around center latitude.
        center_lat = 0.0
        if image_height > 0:
            center_lat = (transform.f + (image_height / 2.0) * transform.e)
        m_per_deg_lat = 111132.0
        m_per_deg_lon = 111320.0 * abs(__import__("math").cos(__import__("math").radians(center_lat)))
        return float(((x_res * m_per_deg_lon) + (y_res * m_per_deg_lat)) / 2.0)
    if is_projected_meter_crs(crs):
        return float((x_res + y_res) / 2.0)
    return None


def is_georeferenced_raster(src) -> bool:
    return bool(src.crs and src.transform and src.transform != Affine.identity())
