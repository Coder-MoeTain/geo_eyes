import argparse
import json
import random
import shutil
from pathlib import Path
from typing import Iterable

IMG_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}


def read_classes(path: Path) -> list[str]:
    lines = [x.strip() for x in path.read_text(encoding="utf-8").splitlines()]
    classes = [x for x in lines if x]
    if not classes:
        raise ValueError("classes file is empty")
    return classes


def valid_yolo_label_line(line: str) -> bool:
    parts = line.strip().split()
    if len(parts) != 5:
        return False
    try:
        int(parts[0])
        coords = [float(v) for v in parts[1:]]
    except ValueError:
        return False
    return all(0.0 <= v <= 1.0 for v in coords)


def validate_label_file(label_file: Path) -> bool:
    if not label_file.exists():
        return False
    lines = [x.strip() for x in label_file.read_text(encoding="utf-8").splitlines() if x.strip()]
    return all(valid_yolo_label_line(line) for line in lines)


def collect_pairs(sources: Iterable[Path]) -> list[tuple[Path, Path]]:
    pairs: list[tuple[Path, Path]] = []
    for src in sources:
        img_dir = src / "images"
        lbl_dir = src / "labels"
        if not img_dir.exists() or not lbl_dir.exists():
            continue
        for img in img_dir.rglob("*"):
            if img.suffix.lower() not in IMG_EXTS:
                continue
            rel = img.relative_to(img_dir).with_suffix(".txt")
            label = lbl_dir / rel
            if validate_label_file(label):
                pairs.append((img, label))
    return pairs


def split_pairs(pairs: list[tuple[Path, Path]], train_ratio: float, val_ratio: float, seed: int):
    rng = random.Random(seed)
    rng.shuffle(pairs)
    n = len(pairs)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)
    train = pairs[:n_train]
    val = pairs[n_train : n_train + n_val]
    test = pairs[n_train + n_val :]
    return train, val, test


def copy_pair(pair: tuple[Path, Path], image_dst: Path, label_dst: Path, prefix: str):
    img, lbl = pair
    name = f"{prefix}_{img.stem}"
    img_out = image_dst / f"{name}{img.suffix.lower()}"
    lbl_out = label_dst / f"{name}.txt"
    shutil.copy2(img, img_out)
    shutil.copy2(lbl, lbl_out)


def write_data_yaml(out_root: Path, classes: list[str]):
    content = "\n".join(
        [
            f"path: {out_root.as_posix()}",
            "train: images/train",
            "val: images/val",
            "test: images/test",
            f"names: {classes}",
        ]
    )
    (out_root / "data.yaml").write_text(content + "\n", encoding="utf-8")


def make_structure(out_root: Path):
    for split in ("train", "val", "test"):
        (out_root / "images" / split).mkdir(parents=True, exist_ok=True)
        (out_root / "labels" / split).mkdir(parents=True, exist_ok=True)


def build_dataset(
    source_roots: list[Path],
    out_root: Path,
    classes_file: Path,
    train_ratio: float,
    val_ratio: float,
    seed: int,
):
    if train_ratio <= 0 or val_ratio <= 0 or train_ratio + val_ratio >= 1:
        raise ValueError("train_ratio and val_ratio must be > 0 and train+val < 1")

    classes = read_classes(classes_file)
    pairs = collect_pairs(source_roots)
    if not pairs:
        raise ValueError("no valid image/label pairs found")

    make_structure(out_root)
    train, val, test = split_pairs(pairs, train_ratio, val_ratio, seed)
    split_map = {"train": train, "val": val, "test": test}

    for split, items in split_map.items():
        for idx, pair in enumerate(items):
            prefix = f"{split}{idx:06d}"
            copy_pair(
                pair,
                out_root / "images" / split,
                out_root / "labels" / split,
                prefix,
            )

    write_data_yaml(out_root, classes)
    stats = {
        "total_pairs": len(pairs),
        "train": len(train),
        "val": len(val),
        "test": len(test),
        "classes": classes,
        "sources": [p.as_posix() for p in source_roots],
    }
    (out_root / "dataset_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return stats


def main():
    parser = argparse.ArgumentParser(description="Create normalized YOLO dataset for aircraft training")
    parser.add_argument(
        "--sources",
        nargs="+",
        required=True,
        help="List of dataset roots. Each root must contain images/ and labels/ directories.",
    )
    parser.add_argument("--output", required=True, help="Output dataset root")
    parser.add_argument("--classes-file", required=True, help="Path to classes.txt")
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--val-ratio", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    stats = build_dataset(
        source_roots=[Path(x).resolve() for x in args.sources],
        out_root=Path(args.output).resolve(),
        classes_file=Path(args.classes_file).resolve(),
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        seed=args.seed,
    )
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
