import argparse
import subprocess
import sys


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--geojson", required=True)
    p.add_argument("--images-dir", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--class-map", default="data/datasets/mappings/xview_typeid_to_yolo.json")
    a = p.parse_args()
    cmd = [
        sys.executable,
        "ai/converters/xview_to_yolo.py",
        "--geojson",
        a.geojson,
        "--images-dir",
        a.images_dir,
        "--output-dir",
        a.output_dir,
        "--class-map",
        a.class_map,
    ]
    raise SystemExit(subprocess.run(cmd).returncode)


if __name__ == "__main__":
    main()
