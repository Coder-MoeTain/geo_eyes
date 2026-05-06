import argparse
import json
import shutil
from pathlib import Path

from PIL import Image


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def bbox_to_yolo(xmin: float, ymin: float, xmax: float, ymax: float, width: int, height: int) -> tuple[float, float, float, float]:
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


def load_image_sizes(images_dir: Path) -> dict[str, tuple[int, int, str]]:
    sizes: dict[str, tuple[int, int, str]] = {}
    for p in images_dir.rglob("*"):
        if p.suffix.lower() not in {".jpg", ".jpeg", ".png", ".tif", ".tiff"}:
            continue
        with Image.open(p) as im:
            sizes[p.stem] = (im.width, im.height, p.suffix.lower())
    return sizes


def convert(geojson_path: Path, images_dir: Path, output_dir: Path, class_map_path: Path):
    class_map = json.loads(class_map_path.read_text(encoding="utf-8"))
    image_sizes = load_image_sizes(images_dir)

    out_images = output_dir / "images"
    out_labels = output_dir / "labels"
    out_images.mkdir(parents=True, exist_ok=True)
    out_labels.mkdir(parents=True, exist_ok=True)

    data = json.loads(geojson_path.read_text(encoding="utf-8"))
    features = data.get("features", [])
    grouped: dict[str, list[str]] = {}

    for ft in features:
        props = ft.get("properties", {})
        image_id = str(props.get("image_id", ""))
        type_id = str(props.get("type_id", ""))
        bounds = props.get("bounds_imcoords", "")
        if not image_id or not bounds or type_id not in class_map:
            continue
        if image_id not in image_sizes:
            continue
        width, height, _ = image_sizes[image_id]
        try:
            vals = [float(x.strip()) for x in bounds.split(",")]
            if len(vals) != 4:
                continue
            xmin, ymin, xmax, ymax = vals
        except ValueError:
            continue
        x, y, w, h = bbox_to_yolo(xmin, ymin, xmax, ymax, width, height)
        cls = int(class_map[type_id])
        grouped.setdefault(image_id, []).append(f"{cls} {x:.6f} {y:.6f} {w:.6f} {h:.6f}")

    written = 0
    for image_stem, lines in grouped.items():
        _, _, ext = image_sizes[image_stem]
        src_img = next(images_dir.rglob(f"{image_stem}{ext}"))
        dst_img = out_images / src_img.name
        shutil.copy2(src_img, dst_img)
        (out_labels / f"{image_stem}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        written += 1

    print(json.dumps({"converted_images": written, "output": output_dir.as_posix()}, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Convert xView geojson annotations to YOLO labels")
    parser.add_argument("--geojson", required=True, help="xView annotation geojson path")
    parser.add_argument("--images-dir", required=True, help="Directory with xView images")
    parser.add_argument("--output-dir", required=True, help="Output root (creates images/ and labels/)")
    parser.add_argument("--class-map", required=True, help="JSON file mapping xView type_id -> YOLO class_id")
    args = parser.parse_args()

    convert(
        geojson_path=Path(args.geojson).resolve(),
        images_dir=Path(args.images_dir).resolve(),
        output_dir=Path(args.output_dir).resolve(),
        class_map_path=Path(args.class_map).resolve(),
    )


if __name__ == "__main__":
    main()
