# Dataset Integration Notes (Local Workflow)

Supported public datasets:

- xView
- DOTA
- Airbus Aircraft Detection
- RarePlanes
- DIOR

## 1) Prepare source folders

For each source, convert/export into YOLO layout first:

```text
<source-root>/
  images/
    ...image files...
  labels/
    ...matching .txt files...
```

Each label line must be:

`<class_id> <x_center> <y_center> <width> <height>`

All coordinate values are normalized to `[0,1]`.

### Raw dataset converters (implemented)

#### xView -> YOLO

```bash
python ai/converters/xview_to_yolo.py \
  --geojson data/raw/xview/xView_train.geojson \
  --images-dir data/raw/xview/images \
  --output-dir data/raw/xview_yolo \
  --class-map data/datasets/mappings/xview_typeid_to_yolo.json
```

#### DOTA -> YOLO

```bash
python ai/converters/dota_to_yolo.py \
  --images-dir data/raw/dota/images \
  --labels-dir data/raw/dota/labelTxt \
  --output-dir data/raw/dota_yolo \
  --class-map data/datasets/mappings/dota_to_yolo.json
```

Each converter outputs:

```text
<output-dir>/
  images/
  labels/
```

Use those output dirs as inputs to `ai/dataset_creation.py`.

#### DIOR -> YOLO

```bash
python ai/converters/dior_to_yolo.py \
  --images-dir data/raw/dior/images \
  --annotations-dir data/raw/dior/annotations \
  --output-dir data/raw/dior_yolo \
  --class-map data/datasets/mappings/dior_to_yolo.json
```

#### RarePlanes (COCO JSON) -> YOLO

```bash
python ai/converters/rareplanes_coco_to_yolo.py \
  --images-dir data/raw/rareplanes/images \
  --coco-json data/raw/rareplanes/annotations/instances_train.json \
  --output-dir data/raw/rareplanes_yolo \
  --class-map data/datasets/mappings/rareplanes_to_yolo.json
```

## 2) Create merged training dataset

Create class list file:

```text
data/datasets/classes.txt
```

Example:

```text
boeing-aircraft
airbus-aircraft
medium-aircraft
cargo-aircraft
military-aircraft
```

Run dataset builder:

```bash
python ai/dataset_creation.py \
  --sources data/raw/xview data/raw/dota data/raw/rareplanes \
  --output data/datasets/aircraft \
  --classes-file data/datasets/classes.txt \
  --train-ratio 0.7 \
  --val-ratio 0.2
```

Output:

```text
data/datasets/aircraft/
  images/train|val|test
  labels/train|val|test
  data.yaml
  dataset_stats.json
```

## 3) Train model locally

```bash
python ai/training.py \
  --data-yaml data/datasets/aircraft/data.yaml \
  --model yolov8m.pt \
  --epochs 80 \
  --imgsz 1024 \
  --batch 8 \
  --device 0
```

## 4) Run detection locally

```bash
python ai/inference.py \
  --source data/sample/geotiff_sample.tif \
  --model-path runs/geoeye/yolov8-aircraft/weights/best.pt \
  --output-json data/inference/output.json
```
