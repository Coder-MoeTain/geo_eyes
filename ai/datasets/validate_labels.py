import argparse
from pathlib import Path


def valid_line(line: str) -> bool:
    p = line.split()
    if len(p) != 5:
        return False
    try:
        int(p[0])
        vals = [float(x) for x in p[1:]]
    except ValueError:
        return False
    return all(0 <= v <= 1 for v in vals)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--labels-dir", required=True)
    a = p.parse_args()
    bad = []
    for f in Path(a.labels_dir).rglob("*.txt"):
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), start=1):
            if line.strip() and not valid_line(line.strip()):
                bad.append({"file": f.as_posix(), "line": i, "text": line})
    if bad:
        print({"invalid_count": len(bad), "examples": bad[:20]})
        raise SystemExit(1)
    print({"status": "ok"})


if __name__ == "__main__":
    main()
