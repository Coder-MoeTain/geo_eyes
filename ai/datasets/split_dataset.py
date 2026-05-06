import argparse
import random
import shutil
from pathlib import Path

IMG_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--images-dir", required=True)
    p.add_argument("--labels-dir", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--train-ratio", type=float, default=0.7)
    p.add_argument("--val-ratio", type=float, default=0.2)
    p.add_argument("--seed", type=int, default=42)
    a = p.parse_args()
    imgs = [x for x in Path(a.images_dir).iterdir() if x.suffix.lower() in IMG_EXTS]
    random.Random(a.seed).shuffle(imgs)
    n = len(imgs)
    n_train = int(n * a.train_ratio)
    n_val = int(n * a.val_ratio)
    splits = {"train": imgs[:n_train], "val": imgs[n_train : n_train + n_val], "test": imgs[n_train + n_val :]}
    out = Path(a.output_dir)
    for split, arr in splits.items():
        (out / "images" / split).mkdir(parents=True, exist_ok=True)
        (out / "labels" / split).mkdir(parents=True, exist_ok=True)
        for img in arr:
            lbl = Path(a.labels_dir) / f"{img.stem}.txt"
            if not lbl.exists():
                continue
            shutil.copy2(img, out / "images" / split / img.name)
            shutil.copy2(lbl, out / "labels" / split / lbl.name)
    print({"output": out.as_posix(), "total_images": n})


if __name__ == "__main__":
    main()
