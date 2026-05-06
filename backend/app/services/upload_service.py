import imghdr
import struct
from pathlib import Path
from uuid import uuid4

import rasterio
from PIL import Image
from fastapi import HTTPException, UploadFile

from app.core.config import settings
from app.services.geospatial_service import estimate_gsd_meters, image_bounds_to_wgs84, is_georeferenced_raster, validate_crs

ALLOWED_EXTS = {".tif", ".tiff", ".png", ".jpg", ".jpeg"}
ALLOWED_MIME = {
    "image/tiff",
    "image/geotiff",
    "image/x-tiff",
    "image/png",
    "image/jpeg",
}


def _png_size(path: Path) -> tuple[int | None, int | None]:
    with path.open("rb") as f:
        sig = f.read(24)
    if len(sig) >= 24 and sig[:8] == b"\x89PNG\r\n\x1a\n":
        width, height = struct.unpack(">II", sig[16:24])
        return int(width), int(height)
    return None, None


async def save_upload(file: UploadFile) -> dict:
    filename = file.filename or "upload.bin"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(status_code=400, detail="Unsupported file extension")
    if file.content_type and file.content_type.lower() not in ALLOWED_MIME:
        raise HTTPException(status_code=400, detail="Unsupported MIME type")

    out_dir = Path(settings.upload_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{uuid4().hex}{ext}"

    size = 0
    with out_path.open("wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > settings.max_upload_size_mb * 1024 * 1024:
                out_path.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="File exceeds max size")
            f.write(chunk)
    await file.close()

    # Extra quick content validation for png/jpeg
    if ext in {".png", ".jpg", ".jpeg"}:
        kind = imghdr.what(out_path)
        if kind not in {"png", "jpeg"}:
            out_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail="Invalid image payload")
        if kind == "png":
            width, height = _png_size(out_path)
        else:
            with Image.open(out_path) as img:
                width, height = img.size
        return {
            "filename": filename,
            "local_path": out_path.as_posix(),
            "size_bytes": size,
            "mime_type": file.content_type or "application/octet-stream",
            "width": width,
            "height": height,
            "crs": None,
            "bounds_json": None,
            "resolution_m": None,
            "georeferenced": False,
            "suitability_score": 0.95,
            "coordinate_space": "pixel",
        }

    # GeoTIFF metadata extraction
    with rasterio.open(out_path) as src:
        if src.crs and not validate_crs(src.crs.to_string()):
            out_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail=f"Invalid raster CRS: {src.crs}")
        b = src.bounds
        crs = src.crs.to_string() if src.crs else None
        bounds_json = {"left": b.left, "bottom": b.bottom, "right": b.right, "top": b.top}
        resolution_m = estimate_gsd_meters(src.transform, crs, src.width, src.height)
        georef = is_georeferenced_raster(src)
        footprint = None
        if georef and crs:
            try:
                footprint = image_bounds_to_wgs84(src.bounds, crs)
            except Exception as exc:
                raise HTTPException(status_code=400, detail=f"GeoTIFF geospatial conversion failed: {exc}") from exc
        warning = None
        if resolution_m and resolution_m > 3:
            warning = "This imagery resolution may be insufficient for reliable aircraft detection."
        return {
            "filename": filename,
            "local_path": out_path.as_posix(),
            "size_bytes": size,
            "mime_type": file.content_type or "application/octet-stream",
            "width": src.width,
            "height": src.height,
            "crs": crs,
            "bounds_json": bounds_json,
            "resolution_m": resolution_m,
            "georeferenced": georef,
            "band_count": src.count,
            "dtype": str(src.dtypes[0]) if src.dtypes else None,
            "footprint_wgs84_geojson": __import__("shapely.geometry").geometry.mapping(footprint) if footprint else None,
            "is_cog": False,
            "overviews": src.overviews(1) if src.count > 0 else [],
            "compression": (src.profile or {}).get("compress"),
            "suitability_score": 0.2 if (resolution_m and resolution_m > 3) else 0.9,
            "warning": warning,
        }
