from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_tile_service_uses_titiler_proxy_prefix():
    content = (ROOT / "backend" / "app" / "services" / "tile_service.py").read_text(encoding="utf-8")
    assert '"/titiler/cog/tiles/' in content


def test_stac_marks_low_res_unsuitable():
    content = (ROOT / "backend" / "app" / "services" / "stac_service.py").read_text(encoding="utf-8")
    assert "suitable_for_aircraft_detection" in content
    assert 'provider in {"sentinel-2", "landsat", "all"}' in content


def test_upload_service_extracts_metadata_flags():
    content = (ROOT / "backend" / "app" / "services" / "upload_service.py").read_text(encoding="utf-8")
    assert '"georeferenced": False' in content
    assert '"bounds_json": bounds_json' in content


def test_change_detection_uses_spatial_distance():
    content = (ROOT / "backend" / "app" / "services" / "change_detection_service.py").read_text(encoding="utf-8")
    assert "movement_vector" in content
    assert "iou(" in content
