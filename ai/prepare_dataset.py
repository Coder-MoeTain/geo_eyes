import argparse
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]):
    print(">", " ".join(cmd))
    proc = subprocess.run(cmd, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")


def main():
    parser = argparse.ArgumentParser(description="End-to-end dataset preparation pipeline")
    parser.add_argument("--classes-file", default="data/datasets/classes.txt")
    parser.add_argument("--output", default="data/datasets/aircraft")
    parser.add_argument("--include-xview", action="store_true")
    parser.add_argument("--include-dota", action="store_true")
    parser.add_argument("--include-dior", action="store_true")
    parser.add_argument("--include-rareplanes", action="store_true")
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--val-ratio", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    sources: list[str] = []

    if args.include_xview:
        run(
            [
                sys.executable,
                "ai/converters/xview_to_yolo.py",
                "--geojson",
                "data/raw/xview/xView_train.geojson",
                "--images-dir",
                "data/raw/xview/images",
                "--output-dir",
                "data/raw/xview_yolo",
                "--class-map",
                "data/datasets/mappings/xview_typeid_to_yolo.json",
            ]
        )
        sources.append("data/raw/xview_yolo")

    if args.include_dota:
        run(
            [
                sys.executable,
                "ai/converters/dota_to_yolo.py",
                "--images-dir",
                "data/raw/dota/images",
                "--labels-dir",
                "data/raw/dota/labelTxt",
                "--output-dir",
                "data/raw/dota_yolo",
                "--class-map",
                "data/datasets/mappings/dota_to_yolo.json",
            ]
        )
        sources.append("data/raw/dota_yolo")

    if args.include_dior:
        run(
            [
                sys.executable,
                "ai/converters/dior_to_yolo.py",
                "--images-dir",
                "data/raw/dior/images",
                "--annotations-dir",
                "data/raw/dior/annotations",
                "--output-dir",
                "data/raw/dior_yolo",
                "--class-map",
                "data/datasets/mappings/dior_to_yolo.json",
            ]
        )
        sources.append("data/raw/dior_yolo")

    if args.include_rareplanes:
        run(
            [
                sys.executable,
                "ai/converters/rareplanes_coco_to_yolo.py",
                "--images-dir",
                "data/raw/rareplanes/images",
                "--coco-json",
                "data/raw/rareplanes/annotations/instances_train.json",
                "--output-dir",
                "data/raw/rareplanes_yolo",
                "--class-map",
                "data/datasets/mappings/rareplanes_to_yolo.json",
            ]
        )
        sources.append("data/raw/rareplanes_yolo")

    if not sources:
        raise RuntimeError("No dataset source enabled. Use --include-* flags.")

    run(
        [
            sys.executable,
            "ai/dataset_creation.py",
            "--sources",
            *sources,
            "--output",
            args.output,
            "--classes-file",
            args.classes_file,
            "--train-ratio",
            str(args.train_ratio),
            "--val-ratio",
            str(args.val_ratio),
            "--seed",
            str(args.seed),
        ]
    )
    print({"prepared_dataset": Path(args.output).resolve().as_posix(), "sources": sources})


if __name__ == "__main__":
    main()
