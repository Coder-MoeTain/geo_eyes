import argparse
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dataset-root", required=True)
    p.add_argument("--classes-file", required=True)
    p.add_argument("--output", default="")
    a = p.parse_args()
    root = Path(a.dataset_root).resolve()
    classes = [x.strip() for x in Path(a.classes_file).read_text(encoding="utf-8").splitlines() if x.strip()]
    out = Path(a.output).resolve() if a.output else root / "data.yaml"
    text = "\n".join(
        [
            f"path: {root.as_posix()}",
            "train: images/train",
            "val: images/val",
            "test: images/test",
            f"names: {classes}",
        ]
    )
    out.write_text(text + "\n", encoding="utf-8")
    print({"data_yaml": out.as_posix()})


if __name__ == "__main__":
    main()
