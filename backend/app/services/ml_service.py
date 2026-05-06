from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import rasterio
from rasterio.windows import Window
from shapely.geometry import Polygon, mapping

from app.core.config import detection_thresholds, settings
from app.services.geospatial_service import (
    is_georeferenced_raster,
    pixel_bbox_to_wgs84_polygon_with_crs,
    repair_invalid_geometry,
)

try:
    from ultralytics import YOLO
except Exception:  # pragma: no cover
    YOLO = None


def _iou(a: list[float], b: list[float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    return inter / max(1e-8, area_a + area_b - inter)


def _nms_boxes(boxes: list[dict[str, Any]], iou_thr: float = 0.45) -> list[dict[str, Any]]:
    boxes = sorted(boxes, key=lambda x: float(x["confidence"]), reverse=True)
    kept: list[dict[str, Any]] = []
    while boxes:
        top = boxes.pop(0)
        kept.append(top)
        boxes = [
            b
            for b in boxes
            if not (int(b["class_id"]) == int(top["class_id"]) and _iou(b["bbox_xyxy"], top["bbox_xyxy"]) > iou_thr)
        ]
    return kept


def _wbf_merge(boxes: list[dict[str, Any]], iou_thr: float) -> list[dict[str, Any]]:
    # Weighted box fusion per class
    groups: list[list[dict[str, Any]]] = []
    for b in sorted(boxes, key=lambda x: float(x["confidence"]), reverse=True):
        placed = False
        for g in groups:
            if int(g[0]["class_id"]) == int(b["class_id"]) and _iou(g[0]["bbox_xyxy"], b["bbox_xyxy"]) >= iou_thr:
                g.append(b)
                placed = True
                break
        if not placed:
            groups.append([b])
    merged: list[dict[str, Any]] = []
    for g in groups:
        wsum = sum(float(x["confidence"]) for x in g)
        if wsum <= 0:
            continue
        x1 = sum(x["bbox_xyxy"][0] * float(x["confidence"]) for x in g) / wsum
        y1 = sum(x["bbox_xyxy"][1] * float(x["confidence"]) for x in g) / wsum
        x2 = sum(x["bbox_xyxy"][2] * float(x["confidence"]) for x in g) / wsum
        y2 = sum(x["bbox_xyxy"][3] * float(x["confidence"]) for x in g) / wsum
        top = max(g, key=lambda x: float(x["confidence"]))
        merged.append({**top, "bbox_xyxy": [x1, y1, x2, y2], "confidence": max(float(x["confidence"]) for x in g)})
    return merged


def _pixel_poly(x1: float, y1: float, x2: float, y2: float) -> Polygon:
    return Polygon([(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)])


def run_yolo_geotiff_inference(
    image_path: str,
    model_path: str | None = None,
    tile_size: int = 1024,
    overlap: int = 128,
    conf_threshold: float = 0.25,
) -> list[dict[str, Any]]:
    if YOLO is None:
        raise RuntimeError("ultralytics is not available")
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"image not found: {image_path}")
    chosen_model = model_path or settings.yolo_model_path
    if not Path(chosen_model).exists():
        raise FileNotFoundError(f"YOLO model not found: {chosen_model}")

    model = YOLO(chosen_model)
    per_class_thr = detection_thresholds()
    is_geotiff = path.suffix.lower() in {".tif", ".tiff"}
    boxes_all: list[dict[str, Any]] = []

    if not is_geotiff:
        result = model.predict(source=str(path), conf=conf_threshold, verbose=False)[0]
        h, w = cv2.imread(str(path)).shape[:2]
        for box in result.boxes:
            x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
            x1, y1, x2, y2 = max(0, x1), max(0, y1), min(w - 1, x2), min(h - 1, y2)
            boxes_all.append(
                {
                    "class_id": int(box.cls[0].item()),
                    "class_name": result.names.get(int(box.cls[0].item()), "unknown"),
                    "confidence": float(box.conf[0].item()),
                    "bbox_xyxy": [x1, y1, x2, y2],
                    "poly": None,
                    "pixel_bbox_xyxy": [x1, y1, x2, y2],
                    "image_width": w,
                    "image_height": h,
                }
            )
    else:
        with rasterio.open(path) as src:
            width, height = src.width, src.height
            transform = src.transform
            src_crs = src.crs.to_string() if src.crs else None
            is_georef = is_georeferenced_raster(src)
            step = max(64, tile_size - overlap)
            for y in range(0, height, step):
                for x in range(0, width, step):
                    win = Window(x, y, min(tile_size, width - x), min(tile_size, height - y))
                    arr = src.read([1, 2, 3], window=win, boundless=True, fill_value=0)
                    tile = np.transpose(arr, (1, 2, 0))
                    tile = np.clip(tile, 0, 255).astype(np.uint8)
                    result = model.predict(source=tile, conf=conf_threshold, verbose=False)[0]
                    for box in result.boxes:
                        tx1, ty1, tx2, ty2 = [float(v) for v in box.xyxy[0].tolist()]
                        x1, y1, x2, y2 = tx1 + x, ty1 + y, tx2 + x, ty2 + y
                        x1, y1, x2, y2 = max(0, x1), max(0, y1), min(width - 1, x2), min(height - 1, y2)
                        boxes_all.append(
                            {
                                "class_id": int(box.cls[0].item()),
                                "class_name": result.names.get(int(box.cls[0].item()), "unknown"),
                                "confidence": float(box.conf[0].item()),
                                "bbox_xyxy": [x1, y1, x2, y2],
                                "poly": pixel_bbox_to_wgs84_polygon_with_crs(transform, src_crs, x1, y1, x2, y2)
                                if is_georef
                                else None,
                                "pixel_bbox_xyxy": [x1, y1, x2, y2],
                                "image_width": width,
                                "image_height": height,
                            }
                        )

    filtered = []
    for b in boxes_all:
        x1, y1, x2, y2 = b["bbox_xyxy"]
        w = abs(x2 - x1)
        h = abs(y2 - y1)
        if w < settings.min_bbox_px or h < settings.min_bbox_px:
            continue
        if w > settings.max_bbox_px or h > settings.max_bbox_px:
            continue
        cls_name = str(b.get("class_name") or "aircraft")
        thr = per_class_thr.get(cls_name, conf_threshold)
        if float(b["confidence"]) < float(thr):
            continue
        filtered.append(b)

    fused = _wbf_merge(filtered, settings.iou_merge_threshold)
    dedup = _nms_boxes(fused, settings.iou_merge_threshold)
    rows: list[dict[str, Any]] = []
    for item in dedup:
        poly = item.get("poly")
        poly = repair_invalid_geometry(poly) if poly is not None else None
        rows.append(
            {
                "class_name": item["class_name"],
                "confidence": round(item["confidence"], 4),
                "timestamp": datetime.now(timezone.utc),
                "geometry_geojson": mapping(poly) if poly is not None else None,
                "polygon_wkt": poly.wkt if poly is not None else None,
                "centroid_wkt": poly.centroid.wkt if poly is not None else None,
                "class_id": item["class_id"],
                "pixel_bbox_xyxy": item.get("pixel_bbox_xyxy"),
                "pixel_bbox": {
                    "xyxy": item.get("pixel_bbox_xyxy"),
                    "image_width": item.get("image_width"),
                    "image_height": item.get("image_height"),
                    "coordinate_space": "pixel",
                },
            }
        )
    return rows
