import argparse
import json
from pathlib import Path

import rasterio
from shapely.geometry import Polygon, mapping
from ultralytics import YOLO


def _pixel_to_geo(transform, x: float, y: float) -> tuple[float, float]:
    return transform * (x, y)


def _to_geo_polygon(transform, x1: float, y1: float, x2: float, y2: float):
    tl = _pixel_to_geo(transform, x1, y1)
    tr = _pixel_to_geo(transform, x2, y1)
    br = _pixel_to_geo(transform, x2, y2)
    bl = _pixel_to_geo(transform, x1, y2)
    return Polygon([tl, tr, br, bl, tl])


def run_inference(
    source: str,
    model_path: str,
    imgsz: int,
    conf: float,
    iou: float,
    device: str,
):
    model = YOLO(model_path)
    return model.predict(source=source, imgsz=imgsz, conf=conf, iou=iou, device=device, save=False, verbose=False)


def detections_to_json(results) -> dict:
    items = []
    for r in results:
        image_path = Path(r.path)
        transform = None
        if image_path.suffix.lower() in {".tif", ".tiff"}:
            with rasterio.open(image_path) as src:
                transform = src.transform
        for box in r.boxes:
            cls = int(box.cls[0].item())
            score = float(box.conf[0].item())
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            payload = {
                "image": image_path.as_posix(),
                "class_id": cls,
                "class_name": r.names.get(cls, str(cls)),
                "confidence": score,
                "bbox_xyxy": [x1, y1, x2, y2],
            }
            if transform is not None:
                poly = _to_geo_polygon(transform, x1, y1, x2, y2)
                payload["geometry_geojson"] = mapping(poly)
                payload["centroid"] = [poly.centroid.x, poly.centroid.y]
            items.append(payload)
    return {"detections": items, "count": len(items)}


def main():
    parser = argparse.ArgumentParser(description="Run object detection on image/GeoTIFF")
    parser.add_argument("--source", required=True, help="Image path or directory")
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--imgsz", type=int, default=1024)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--iou", type=float, default=0.5)
    parser.add_argument("--device", default="0")
    parser.add_argument("--output-json", default="data/inference/output.json")
    args = parser.parse_args()

    source_path = Path(args.source).resolve()
    results = run_inference(
        source=source_path.as_posix(),
        model_path=args.model_path,
        imgsz=args.imgsz,
        conf=args.conf,
        iou=args.iou,
        device=args.device,
    )
    payload = detections_to_json(results)
    out = Path(args.output_json).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"output_json": out.as_posix(), "count": payload["count"]}, indent=2))


if __name__ == "__main__":
    main()
