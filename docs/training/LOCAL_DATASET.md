## Create an image dataset *now* (ready for training)

This repo trains YOLOv8 using a **YOLO-format dataset**:

```text
<source-root>/
  images/
    <image files...>
  labels/
    <matching .txt files...>
```

Each label line must be:

`<class_id> <x_center> <y_center> <width> <height>`

All coordinates are normalized to `[0,1]`.

### 1) Create a local source folder

Use one of:

- PowerShell:

```powershell
.\infra\scripts\init_local_dataset.ps1
```

- Bash:

```bash
./infra/scripts/init_local_dataset.sh
```

This creates:

`data/raw/local_yolo/images/` and `data/raw/local_yolo/labels/`

### 2) Put your images + labels in the source folder

- Copy images into `data/raw/local_yolo/images/`
- Copy matching `.txt` label files into `data/raw/local_yolo/labels/`
  - Example: `IMG_0001.jpg` → `IMG_0001.txt`

### 3) Build a train/val/test dataset (creates `data.yaml`)

```bash
python ai/dataset_creation.py ^
  --sources data/raw/local_yolo ^
  --output data/datasets/local_training ^
  --classes-file data/datasets/classes.txt ^
  --train-ratio 0.7 ^
  --val-ratio 0.2 ^
  --seed 42
```

Output:

```text
data/datasets/local_training/
  images/train|val|test
  labels/train|val|test
  data.yaml
  dataset_stats.json
```

### 4) Train (GPU)

```bash
python ai/training.py --data-yaml data/datasets/local_training/data.yaml --model yolov8m.pt --epochs 20 --imgsz 1024 --batch 8 --device 0
```

