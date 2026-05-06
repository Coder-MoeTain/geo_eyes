from pathlib import Path


def test_geospatial_contracts_present():
    content = Path("app/services/geospatial_service.py").read_text(encoding="utf-8")
    assert "def validate_crs(" in content
    assert "def safe_transform_geometry(" in content
    assert "def validate_geometry(" in content
    assert "def repair_invalid_geometry(" in content
    assert "def pixel_bbox_to_geo_polygon(" in content
    assert "def image_bounds_to_wgs84(" in content
    assert "make_valid" in content


def test_login_lockout_contracts_present():
    content = Path("app/services/rate_limiter.py").read_text(encoding="utf-8")
    assert "def check_login_allowed(" in content
    assert "def register_login_failure(" in content
    assert "def clear_login_failures(" in content
    assert "Too many failed logins" in content


def test_detect_coordinate_is_async_and_awaits_stac():
    content = Path("app/api.py").read_text(encoding="utf-8")
    assert "async def detect_coordinate(" in content
    assert "scene = await search_stac_scene(" in content
