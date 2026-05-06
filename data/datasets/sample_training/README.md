# Sample Training Dataset (Quickstart)

This folder is for a small **real** training subset built from your converted datasets.

No fake images are generated in this project.
You must first place real datasets under `data/raw/` and run converters.

## Build a quick sample set

```bash
python ai/prepare_dataset.py --include-xview --include-dota --include-dior --include-rareplanes --max-samples 600 --output data/datasets/sample_training
```

This creates:

- `data/datasets/sample_training/images/{train,val,test}`
- `data/datasets/sample_training/labels/{train,val,test}`
- `data/datasets/sample_training/data.yaml`
- `data/datasets/sample_training/dataset_stats.json`

## Train quickly

```bash
python ai/training.py --data-yaml data/datasets/sample_training/data.yaml --model yolov8m.pt --epochs 20 --imgsz 1024 --batch 8 --device 0
```

If GPU is unavailable, set `--device cpu`.
