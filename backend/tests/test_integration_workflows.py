from pathlib import Path


def test_upload_detect_map_overlay_workflow_contract():
    api_content = Path("app/api.py").read_text(encoding="utf-8")
    assert '@router.post("/uploads"' in api_content
    assert '@router.post("/uploads/{image_id}/detect"' in api_content
    assert '@router.get("/uploaded-image/{image_id}/tiles")' in api_content
    assert "build_titiler_urls(path)" in api_content

    frontend_content = Path("../frontend/src/views/UploadDetectPage.vue").read_text(encoding="utf-8")
    assert "store.uploadAndDetect" in frontend_content
    assert "store.loadUploadedTileUrl" in frontend_content
    assert ':raster-tiles-url="store.uploadedTileUrl"' in frontend_content


def test_stac_warning_path_contract():
    stac_content = Path("app/services/stac_service.py").read_text(encoding="utf-8")
    assert "suitable_for_aircraft_detection" in stac_content
    assert "This imagery may be insufficient for reliable aircraft detection." in stac_content

    api_content = Path("app/api.py").read_text(encoding="utf-8")
    assert "if scene.get(\"suitable_for_aircraft_detection\") is False" in api_content
    assert "High-resolution imagery is required for aircraft detection." in api_content
