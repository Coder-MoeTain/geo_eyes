import argparse
import subprocess
import sys


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--images-dir", required=True)
    p.add_argument("--coco-json", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--class-map", default="data/datasets/mappings/rareplanes_to_yolo.json")
    a = p.parse_args()
    cmd = [
        sys.executable,
        "ai/converters/rareplanes_coco_to_yolo.py",
        "--images-dir",
        a.images_dir,
        "--coco-json",
        a.coco_json,
        "--output-dir",
        a.output_dir,
        "--class-map",
        a.class_map,
    ]
    raise SystemExit(subprocess.run(cmd).returncode)


if __name__ == "__main__":
    main()
