import argparse
import json
import shutil
from pathlib import Path

from PIL import Image


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def poly_to_yolo(coords: list[float], width: int, height: int) -> tuple[float, float, float, float]:
    xs = coords[0::2]
    ys = coords[1::2]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    x_center = ((xmin + xmax) / 2.0) / width
    y_center = ((ymin + ymax) / 2.0) / height
    bw = (xmax - xmin) / width
    bh = (ymax - ymin) / height
    return (
        clamp(x_center, 0.0, 1.0),
        clamp(y_center, 0.0, 1.0),
        clamp(bw, 0.0, 1.0),
        clamp(bh, 0.0, 1.0),
    )


def convert(images_dir: Path, labels_dir: Path, output_dir: Path, class_map_path: Path):
    class_map = json.loads(class_map_path.read_text(encoding="utf-8"))
    out_images = output_dir / "images"
    out_labels = output_dir / "labels"
    out_images.mkdir(parents=True, exist_ok=True)
    out_labels.mkdir(parents=True, exist_ok=True)

    converted = 0
    for label_file in labels_dir.rglob("*.txt"):
        stem = label_file.stem
        image_candidates = []
        for ext in (".png", ".jpg", ".jpeg", ".tif", ".tiff"):
            candidate = images_dir / f"{stem}{ext}"
            if candidate.exists():
                image_candidates.append(candidate)
        if not image_candidates:
            continue
        image_file = image_candidates[0]
        with Image.open(image_file) as im:
            width, height = im.width, im.height

        yolo_lines: list[str] = []
        for raw in label_file.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("imagesource:") or line.startswith("gsd:"):
                continue
            parts = line.split()
            if len(parts) < 10:
                continue
            try:
                coords = [float(v) for v in parts[:8]]
                cls_name = parts[8]
            except ValueError:
                continue
            if cls_name not in class_map:
                continue
            x, y, w, h = poly_to_yolo(coords, width, height)
            cls = int(class_map[cls_name])
            yolo_lines.append(f"{cls} {x:.6f} {y:.6f} {w:.6f} {h:.6f}")

        if not yolo_lines:
            continue
        shutil.copy2(image_file, out_images / image_file.name)
        (out_labels / f"{stem}.txt").write_text("\n".join(yolo_lines) + "\n", encoding="utf-8")
        converted += 1

    print(json.dumps({"converted_images": converted, "output": output_dir.as_posix()}, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Convert DOTA polygon annotations to YOLO labels")
    parser.add_argument("--images-dir", required=True)
    parser.add_argument("--labels-dir", required=True, help="Directory containing DOTA labelTxt files")
    parser.add_argument("--output-dir", required=True, help="Output root (creates images/ and labels/)")
    parser.add_argument("--class-map", required=True, help="JSON file mapping DOTA class name -> YOLO class_id")
    args = parser.parse_args()
    convert(
        images_dir=Path(args.images_dir).resolve(),
        labels_dir=Path(args.labels_dir).resolve(),
        output_dir=Path(args.output_dir).resolve(),
        class_map_path=Path(args.class_map).resolve(),
    )


if __name__ == "__main__":
    main()
