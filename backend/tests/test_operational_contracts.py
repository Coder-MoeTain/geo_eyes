from pathlib import Path


def test_geospatial_upgrade_contracts():
    content = Path("app/services/geospatial_service.py").read_text(encoding="utf-8")
    assert "def calculate_geodesic_area_m2(" in content
    assert "def estimate_gsd_meters(" in content
    assert "def is_georeferenced_raster(" in content
    assert "def pixel_bbox_to_wgs84_polygon_with_crs(" in content


def test_upload_and_model_workflow_contracts():
    upload = Path("app/services/upload_service.py").read_text(encoding="utf-8")
    assert "footprint_wgs84_geojson" in upload
    assert "estimate_gsd_meters" in upload
    assert "band_count" in upload

    model = Path("app/services/model_service.py").read_text(encoding="utf-8")
    assert "def extract_model_metadata(" in model
    assert "max_model_size_mb" in model


def test_api_contracts_for_airport_change_and_review():
    api = Path("app/api.py").read_text(encoding="utf-8")
    assert '@router.get("/airports/{airport_id}/activity"' in api
    assert '@router.get("/airports/{airport_id}/detections"' in api
    assert '@router.patch("/detections/{detection_id}/review"' in api
    assert "require_any_role" in api


def test_create_satellite_image_maps_footprint_column():
    """Regression: ORM attribute is `footprint` (DB column `bounds`); `bounds=` was ignored."""
    crud = Path("app/db/crud.py").read_text(encoding="utf-8")
    assert "footprint=WKTElement(bounds_wkt" in crud
    assert "create_satellite_image" in crud
    assert "bounds=WKTElement" not in crud


def test_detection_static_routes_registered_before_id_route():
    """FastAPI matches in order; geojson/export must not be parsed as detection_id."""
    api = Path("app/api.py").read_text(encoding="utf-8")
    idx_list = api.find('@router.get("/detections"')
    idx_geojson = api.find('@router.get("/detections/geojson"')
    idx_export = api.find('@router.get("/detections/export.csv"')
    idx_detail = api.find('@router.get("/detections/{detection_id}"')
    assert idx_list != -1 and idx_geojson != -1 and idx_export != -1 and idx_detail != -1
    assert idx_list < idx_geojson < idx_detail
    assert idx_list < idx_export < idx_detail
