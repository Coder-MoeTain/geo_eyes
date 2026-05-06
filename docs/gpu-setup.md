# GPU Setup Guide

## NVIDIA Runtime

1. Install current NVIDIA driver.
2. Install NVIDIA Container Toolkit.
3. Restart Docker.

## Validate GPU in container

```bash
docker run --rm --gpus all nvidia/cuda:12.3.2-cudnn9-runtime-ubuntu22.04 nvidia-smi
```

## Run GeoEye worker with GPU

```bash
docker compose --profile gpu up --build worker-gpu
```

## Model optimization recommendations

- Use half precision (`fp16`) during inference where possible.
- Tune tile size and overlap to fit VRAM.
- Keep model weights on mounted volume (`data/models`).
