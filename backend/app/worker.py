import asyncio
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from celery import Celery
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.crud import create_ai_model, create_detection, create_satellite_image, get_active_model
from app.db.session import SessionLocal
from app.services.airport_service import import_ourairports_csv
from app.services.audit_service import write_audit_log
from app.services.change_detection_service import spatial_change_detection
from app.services.imagery_service import download_cog_asset
from app.services.ml_service import run_yolo_geotiff_inference
from app.services.stac_service import search_stac_scene

celery_app = Celery(
    "geoeye_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)


def _set_job_progress(db: Session, task_id: str, status: str, progress: float, message: str):
    db.execute(
        text(
            """
            UPDATE detection_jobs
            SET status=:status, progress=:progress, message=:message
            WHERE task_id=:task_id
            """
        ),
        {"task_id": task_id, "status": status, "progress": progress, "message": message},
    )
    db.commit()


@celery_app.task(name="tasks.acquire_and_detect")
def acquire_and_detect(
    latitude: float,
    longitude: float,
    provider: str,
    cloud_max: float,
    resolution_m: float,
    start_date: str | None = None,
    end_date: str | None = None,
    model_id: int | None = None,
):
    db: Session = SessionLocal()
    task_id = acquire_and_detect.request.id
    try:
        from datetime import datetime

        st_start = datetime.fromisoformat(start_date) if start_date else None
        st_end = datetime.fromisoformat(end_date) if end_date else None
        _set_job_progress(db, task_id, "running", 0.1, "searching imagery")
        scene = asyncio.run(
            search_stac_scene(
                latitude=latitude,
                longitude=longitude,
                cloud_max=cloud_max,
                provider=provider,
                start_date=st_start,
                end_date=st_end,
            )
        )
        if not scene:
            raise RuntimeError("No satellite scene found for requested coordinate/date/provider filters")
        if scene.get("asset_url"):
            local_name = f"stac_{scene.get('stac_item_id', 'scene')}.tif"
            scene["local_tif_path"] = download_cog_asset(scene["asset_url"], local_name)
        _set_job_progress(db, task_id, "running", 0.25, "loading model")
        if not scene.get("local_tif_path"):
            raise RuntimeError("No downloadable GeoTIFF asset available for selected query")
        active_model = None
        if model_id:
            from app.models import AIModel

            active_model = db.query(AIModel).filter(AIModel.id == model_id).one_or_none()
        if not active_model:
            active_model = get_active_model(db)
        if not active_model:
            raise RuntimeError("No active aircraft detection model found")
        chosen_model_path = active_model.weights_path
        detections = run_yolo_geotiff_inference(scene.get("local_tif_path"), model_path=chosen_model_path)
        _set_job_progress(db, task_id, "running", 0.7, "storing detections")
        image = create_satellite_image(
            db=db,
            provider=scene["provider"],
            acquisition_date=scene["acquisition_date"],
            cloud_cover=scene["cloud_cover"],
            resolution_m=resolution_m,
            bounds_wkt=scene.get("bounds_wkt"),
            asset_url=scene.get("asset_url"),
            metadata=scene,
        )
        persisted = []
        for d in detections:
            item = create_detection(
                db=db,
                image_id=image.id,
                model_id=active_model.id,
                class_name=d["class_name"],
                confidence=d["confidence"],
                pixel_bbox=d.get("pixel_bbox") or {"xyxy": d.get("pixel_bbox_xyxy")},
                polygon_wkt=d["polygon_wkt"],
                centroid_wkt=d["centroid_wkt"],
                georeferenced=bool(d["polygon_wkt"]),
                timestamp=d["timestamp"],
                attributes={
                    "source_asset_url": scene.get("asset_url"),
                    "pixel_bbox_xyxy": d.get("pixel_bbox_xyxy"),
                    "coordinate_space": "wgs84",
                },
            )
            persisted.append(item.id)
        db.commit()
        _set_job_progress(db, task_id, "completed", 1.0, "completed")
        return {"scene": scene, "detections": detections, "stored_detection_ids": persisted}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(name="tasks.train_model")
def train_model(
    dataset_yaml: str,
    epochs: int,
    img_size: int,
    batch_size: int,
    model: str,
    device: str = "0",
    training_method: str = "yolov8-supervised",
):
    db: Session = SessionLocal()
    task_id = train_model.request.id
    try:
        if training_method != "yolov8-supervised":
            raise RuntimeError(f"Unsupported training method: {training_method}")

        repo_root = Path(__file__).resolve().parents[2]
        training_script = repo_root / "ai" / "training.py"
        runs_root = repo_root / "data" / "runs" / "geoeye"
        runs_root.mkdir(parents=True, exist_ok=True)
        run_name = f"yolov8-aircraft-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        dataset_yaml_path = Path(dataset_yaml)
        if not dataset_yaml_path.is_absolute():
            dataset_yaml_path = repo_root / dataset_yaml_path
        dataset_yaml_path = dataset_yaml_path.resolve()

        _set_job_progress(db, task_id, "running", 0.05, "validating training inputs")
        if not dataset_yaml_path.exists():
            raise RuntimeError(f"Dataset yaml not found: {dataset_yaml_path}")

        _set_job_progress(db, task_id, "running", 0.1, "starting training process")
        cmd = [
            sys.executable,
            str(training_script),
            "--data-yaml",
            str(dataset_yaml_path),
            "--model",
            model,
            "--epochs",
            str(epochs),
            "--imgsz",
            str(img_size),
            "--batch",
            str(batch_size),
            "--device",
            device,
            "--project",
            str(runs_root),
            "--name",
            run_name,
        ]
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        epoch_re = re.compile(r"\b(\d+)\s*/\s*(\d+)\b")
        output_tail: list[str] = []
        max_tail = 120
        for raw_line in proc.stdout or []:
            line = raw_line.strip()
            if not line:
                continue
            output_tail.append(line)
            if len(output_tail) > max_tail:
                output_tail = output_tail[-max_tail:]
            match = epoch_re.search(line)
            if match:
                current_epoch = int(match.group(1))
                total_epochs = max(int(match.group(2)), 1)
                # Keep 10% buffer for artifact registration after training loop.
                progress = min(0.9, 0.1 + (current_epoch / total_epochs) * 0.8)
                _set_job_progress(db, task_id, "running", progress, f"epoch {current_epoch}/{total_epochs}")
        return_code = proc.wait()
        if return_code != 0:
            raise RuntimeError("\n".join(output_tail[-20:]) or "Training process failed.")

        _set_job_progress(db, task_id, "running", 0.93, "registering trained model")
        weights_path = str(runs_root / run_name / "weights" / "best.pt")
        if not os.path.exists(weights_path):
            raise RuntimeError(f"Training finished but best.pt not found: {weights_path}")
        row = create_ai_model(
            db,
            name=run_name,
            version="v1",
            weights_path=weights_path,
            metrics={
                "training_method": training_method,
                "dataset_yaml": str(dataset_yaml_path),
                "epochs": epochs,
                "img_size": img_size,
                "batch_size": batch_size,
                "base_model": model,
                "device": device,
                "train_stdout_tail": "\n".join(output_tail[-20:]),
            },
            active=True,
        )
        db.commit()
        _set_job_progress(db, task_id, "completed", 1.0, "training completed")
        write_audit_log(db, "train_model", "/tasks/train_model", "success", details={"model_id": row.id})
        return {
            "status": "completed",
            "training_method": training_method,
            "model_id": row.id,
            "model_name": run_name,
            "weights_path": weights_path,
            "base_model": model,
        }
    except Exception as exc:
        db.rollback()
        _set_job_progress(db, task_id, "failed", 1.0, str(exc))
        raise
    finally:
        db.close()


@celery_app.task(name="tasks.detect_uploaded")
def detect_uploaded(image_id: int, image_path: str | None = None):
    db: Session = SessionLocal()
    task_id = detect_uploaded.request.id
    try:
        _set_job_progress(db, task_id, "running", 0.1, "loading image metadata")
        if not image_path:
            row = db.execute(
                text("SELECT asset_url FROM satellite_images WHERE id = :id"),
                {"id": image_id},
            ).first()
            if not row or not row[0]:
                raise RuntimeError("Uploaded image path was not found for detection task")
            image_path = row[0]
        _set_job_progress(db, task_id, "running", 0.3, "loading model")
        active_model = get_active_model(db)
        if not active_model:
            raise RuntimeError("No active aircraft detection model found")
        chosen_model_path = active_model.weights_path
        _set_job_progress(db, task_id, "running", 0.6, "running inference")
        detections = run_yolo_geotiff_inference(image_path, model_path=chosen_model_path)
        persisted = []
        for d in detections:
            item = create_detection(
                db=db,
                image_id=image_id,
                model_id=active_model.id,
                class_name=d["class_name"],
                confidence=d["confidence"],
                pixel_bbox=d.get("pixel_bbox") or {"xyxy": d.get("pixel_bbox_xyxy")},
                polygon_wkt=d["polygon_wkt"],
                centroid_wkt=d["centroid_wkt"],
                georeferenced=bool(d["polygon_wkt"]),
                timestamp=d["timestamp"],
                attributes={
                    "source_asset_url": image_path,
                    "pixel_bbox_xyxy": d.get("pixel_bbox_xyxy"),
                    "coordinate_space": "wgs84" if image_path.lower().endswith((".tif", ".tiff")) else "normalized",
                },
            )
            persisted.append(item.id)
        db.commit()
        _set_job_progress(db, task_id, "completed", 1.0, "completed")
        return {"image_id": image_id, "stored_detection_ids": persisted, "count": len(persisted)}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(name="tasks.import_airports")
def import_airports_task(csv_path: str):
    db: Session = SessionLocal()
    try:
        inserted = import_ourairports_csv(db, csv_path)
        return {"inserted": inserted}
    finally:
        db.close()


@celery_app.task(name="tasks.change_detection")
def change_detection_task(before_image_id: int, after_image_id: int, match_distance_m: float = 40.0):
    db: Session = SessionLocal()
    try:
        return spatial_change_detection(db, before_image_id, after_image_id, match_distance_m)
    finally:
        db.close()
