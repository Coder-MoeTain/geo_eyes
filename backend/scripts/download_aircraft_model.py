import argparse
from pathlib import Path

from huggingface_hub import hf_hub_download


def download_model(repo_id: str, filename: str, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    downloaded = hf_hub_download(repo_id=repo_id, filename=filename, local_dir=output_dir.as_posix())
    print({"downloaded_model": downloaded})


def main():
    parser = argparse.ArgumentParser(description="Download real aircraft YOLO model weights from HuggingFace")
    parser.add_argument("--repo-id", default="keremberke/yolov8m-aircraft-detection")
    parser.add_argument("--filename", default="best.pt")
    parser.add_argument("--output-dir", default="data/models")
    args = parser.parse_args()
    download_model(args.repo_id, args.filename, Path(args.output_dir).resolve())


if __name__ == "__main__":
    main()
