#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
mkdir -p "${repo_root}/data/raw/local_yolo/images" "${repo_root}/data/raw/local_yolo/labels"

echo "Created:"
echo " - data/raw/local_yolo/images"
echo " - data/raw/local_yolo/labels"
echo ""
echo "Next:"
echo " - Copy images into data/raw/local_yolo/images"
echo " - Copy YOLO label .txt files into data/raw/local_yolo/labels"

