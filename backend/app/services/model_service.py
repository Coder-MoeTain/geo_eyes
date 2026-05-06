from pathlib import Path
from uuid import uuid4
import hashlib

from fastapi import HTTPException, UploadFile

from app.core.config import settings


async def save_model_file(file: UploadFile) -> str:
    if not (file.filename or "").lower().endswith(".pt"):
        raise HTTPException(status_code=400, detail="Only .pt YOLO model files are supported")
    model_dir = Path("/models")
    model_dir.mkdir(parents=True, exist_ok=True)
    out = model_dir / f"{uuid4().hex}.pt"
    size = 0
    with out.open("wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > settings.max_model_size_mb * 1024 * 1024:
                out.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail=f"Model file exceeds {settings.max_model_size_mb}MB limit")
            f.write(chunk)
    await file.close()
    try:
        from ultralytics import YOLO

        YOLO(out.as_posix())
    except Exception as exc:
        out.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"Invalid YOLO model file: {exc}") from exc
    return out.as_posix()


def extract_model_metadata(path: str) -> dict:
    try:
        from ultralytics import YOLO
        import torch

        model = YOLO(path)
        names = getattr(model.model, "names", {}) or {}
        stride = getattr(model.model, "stride", None)
        stride_val = int(stride.max().item()) if stride is not None and hasattr(stride, "max") else None
        return {
            "classes": list(names.values()) if isinstance(names, dict) else [],
            "class_count": len(names) if isinstance(names, dict) else 0,
            "stride": stride_val,
            "task": getattr(model, "task", "detect"),
            "ultralytics_version": getattr(__import__("ultralytics"), "__version__", None),
            "torch_version": torch.__version__,
        }
    except Exception:
        return {}


def file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_active_model_or_error(active_model):
    if active_model:
        return active_model
    raise HTTPException(
        status_code=400,
        detail={
            "error": "No active aircraft detection model found",
            "message": "Upload or train a YOLO aircraft model before running detection.",
        },
    )
