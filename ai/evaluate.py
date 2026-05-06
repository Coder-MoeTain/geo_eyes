import argparse
import json
from pathlib import Path

from ultralytics import YOLO


def evaluate(model_path: str, data_yaml: str, imgsz: int, split: str):
    model = YOLO(model_path)
    return model.val(data=data_yaml, imgsz=imgsz, split=split)


def main():
    parser = argparse.ArgumentParser(description="Evaluate YOLOv8 model")
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--data-yaml", required=True)
    parser.add_argument("--imgsz", type=int, default=1024)
    parser.add_argument("--split", default="val", choices=["train", "val", "test"])
    parser.add_argument("--output-json", default="")
    args = parser.parse_args()

    metrics = evaluate(args.model_path, args.data_yaml, args.imgsz, args.split)
    summary = {
        "map50": float(getattr(metrics.box, "map50", 0.0)),
        "map": float(getattr(metrics.box, "map", 0.0)),
        "precision": float(getattr(metrics.box, "mp", 0.0)),
        "recall": float(getattr(metrics.box, "mr", 0.0)),
    }
    print(json.dumps(summary, indent=2))
    if args.output_json:
        Path(args.output_json).write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
