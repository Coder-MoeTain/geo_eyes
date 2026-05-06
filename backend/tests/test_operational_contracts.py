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
