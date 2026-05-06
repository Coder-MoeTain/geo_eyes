import argparse
import json
import shutil
from pathlib import Path

from PIL import Image


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def coco_bbox_to_yolo(x: float, y: float, w: float, h: float, width: int, height: int) -> tuple[float, float, float, float]:
    x_center = (x + w / 2.0) / width
    y_center = (y + h / 2.0) / height
    bw = w / width
    bh = h / height
    return (
        clamp(x_center, 0.0, 1.0),
        clamp(y_center, 0.0, 1.0),
        clamp(bw, 0.0, 1.0),
        clamp(bh, 0.0, 1.0),
    )


def convert(images_dir: Path, coco_json: Path, output_dir: Path, class_map_path: Path):
    class_map = json.loads(class_map_path.read_text(encoding="utf-8"))
    coco = json.loads(coco_json.read_text(encoding="utf-8"))

    out_images = output_dir / "images"
    out_labels = output_dir / "labels"
    out_images.mkdir(parents=True, exist_ok=True)
    out_labels.mkdir(parents=True, exist_ok=True)

    cat_lookup = {int(c["id"]): str(c["name"]) for c in coco.get("categories", [])}
    image_lookup = {int(i["id"]): i for i in coco.get("images", [])}
    grouped: dict[int, list[str]] = {}

    for ann in coco.get("annotations", []):
        image_id = int(ann.get("image_id", -1))
        cat_id = int(ann.get("category_id", -1))
        if image_id not in image_lookup or cat_id not in cat_lookup:
            continue
        cat_name = cat_lookup[cat_id]
        if cat_name not in class_map:
            continue
        bbox = ann.get("bbox", [])
        if len(bbox) != 4:
            continue
        img = image_lookup[image_id]
        width = int(img.get("width", 0))
        height = int(img.get("height", 0))
        if width <= 0 or height <= 0:
            continue
        x, y, w, h = [float(v) for v in bbox]
        cx, cy, bw, bh = coco_bbox_to_yolo(x, y, w, h, width, height)
        cls = int(class_map[cat_name])
        grouped.setdefault(image_id, []).append(f"{cls} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")

    converted = 0
    for image_id, lines in grouped.items():
        img_info = image_lookup[image_id]
        file_name = img_info.get("file_name", "")
        if not file_name:
            continue
        src_img = images_dir / file_name
        if not src_img.exists():
            continue
        # Validate image readability
        with Image.open(src_img):
            pass
        dst_img = out_images / src_img.name
        shutil.copy2(src_img, dst_img)
        stem = Path(file_name).stem
        (out_labels / f"{stem}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        converted += 1

    print(json.dumps({"converted_images": converted, "output": output_dir.as_posix()}, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Convert RarePlanes COCO annotations to YOLO labels")
    parser.add_argument("--images-dir", required=True)
    parser.add_argument("--coco-json", required=True, help="COCO annotation JSON path")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--class-map", required=True, help="JSON mapping COCO category name -> YOLO class_id")
    args = parser.parse_args()

    convert(
        images_dir=Path(args.images_dir).resolve(),
        coco_json=Path(args.coco_json).resolve(),
        output_dir=Path(args.output_dir).resolve(),
        class_map_path=Path(args.class_map).resolve(),
    )


if __name__ == "__main__":
    main()
