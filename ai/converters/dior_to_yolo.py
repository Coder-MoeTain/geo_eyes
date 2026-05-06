import argparse
import json
import shutil
import xml.etree.ElementTree as ET
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


def find_image(images_dir: Path, stem: str) -> Path | None:
    for ext in (".jpg", ".jpeg", ".png", ".tif", ".tiff"):
        p = images_dir / f"{stem}{ext}"
        if p.exists():
            return p
    return None


def convert(images_dir: Path, annotations_dir: Path, output_dir: Path, class_map_path: Path):
    class_map = json.loads(class_map_path.read_text(encoding="utf-8"))
    out_images = output_dir / "images"
    out_labels = output_dir / "labels"
    out_images.mkdir(parents=True, exist_ok=True)
    out_labels.mkdir(parents=True, exist_ok=True)

    converted = 0
    for xml_file in annotations_dir.rglob("*.xml"):
        stem = xml_file.stem
        image_file = find_image(images_dir, stem)
        if not image_file:
            continue
        with Image.open(image_file) as im:
            width, height = im.width, im.height

        root = ET.parse(xml_file).getroot()
        lines: list[str] = []
        for obj in root.findall("object"):
            cls_name = (obj.findtext("name") or "").strip()
            if cls_name not in class_map:
                continue
            bnd = obj.find("bndbox")
            if bnd is None:
                continue
            try:
                xmin = float((bnd.findtext("xmin") or "0").strip())
                ymin = float((bnd.findtext("ymin") or "0").strip())
                xmax = float((bnd.findtext("xmax") or "0").strip())
                ymax = float((bnd.findtext("ymax") or "0").strip())
            except ValueError:
                continue
            x, y, w, h = bbox_to_yolo(xmin, ymin, xmax, ymax, width, height)
            cls = int(class_map[cls_name])
            lines.append(f"{cls} {x:.6f} {y:.6f} {w:.6f} {h:.6f}")

        if not lines:
            continue
        shutil.copy2(image_file, out_images / image_file.name)
        (out_labels / f"{stem}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        converted += 1

    print(json.dumps({"converted_images": converted, "output": output_dir.as_posix()}, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Convert DIOR XML annotations to YOLO labels")
    parser.add_argument("--images-dir", required=True)
    parser.add_argument("--annotations-dir", required=True, help="Directory containing DIOR XML files")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--class-map", required=True, help="JSON file mapping DIOR class name -> YOLO class_id")
    args = parser.parse_args()

    convert(
        images_dir=Path(args.images_dir).resolve(),
        annotations_dir=Path(args.annotations_dir).resolve(),
        output_dir=Path(args.output_dir).resolve(),
        class_map_path=Path(args.class_map).resolve(),
    )


if __name__ == "__main__":
    main()
