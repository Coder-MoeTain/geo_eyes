import json
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import PlainTextResponse
from kombu.exceptions import OperationalError as KombuOperationalError
from sqlalchemy import text
from sqlalchemy.orm import Session
from shapely.geometry import box
from shapely.geometry import shape as shp_shape
from geoalchemy2.elements import WKTElement

from app.core.config import settings
from app.db.crud import compute_aircraft_statistics, create_satellite_image, list_detections, nearby_airports, set_active_model
from app.db.session import get_db
from app.deps import get_current_user, require_any_role, require_role
from app.models import AIModel, ChangeDetectionJob, DetectionJob, GeoEvent, RefreshToken, SatelliteImage, User
from app.schemas import (
    DetectRequest,
    GenericTaskResponse,
    LoginRequest,
    RefreshTokenRequest,
    SatelliteImageResponse,
    SignedUploadRequest,
    SignedUploadResponse,
    TokenResponse,
    TrainModelRequest,
    UploadImageResponse,
)
from app.security import create_access_token, create_refresh_token, verify_password
from app.services.airport_service import search_airports
from app.services.audit_service import write_audit_log
from app.services.heatmap_service import build_heatmap_feature_collection
from app.services.model_service import ensure_active_model_or_error, extract_model_metadata, file_sha256, save_model_file
from app.services.rate_limiter import check_login_allowed, clear_login_failures, enforce_rate_limit, register_login_failure
from app.services.stac_service import search_stac_scene
from app.services.signed_upload_service import create_signed_upload_token, verify_signed_upload_token
from app.services.tile_service import build_titiler_urls
from app.services.upload_service import save_upload
from app.services.geospatial_service import transform_crs_to_wgs84
from app.worker import celery_app

router = APIRouter(prefix="/api/v1")


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    cookie_kwargs = {
        "httponly": True,
        "secure": bool(settings.secure_cookies),
        "samesite": settings.cookie_samesite,
        "domain": settings.cookie_domain or None,
        "path": "/",
    }
    response.set_cookie("access_token", access_token, max_age=86400, **cookie_kwargs)
    response.set_cookie("refresh_token", refresh_token, max_age=86400 * 7, **cookie_kwargs)


def _uploaded_bounds_wkt(uploaded: dict) -> str | None:
    b = uploaded.get("bounds_json")
    crs = uploaded.get("crs")
    if not b or not crs:
        return None
    geom = box(b["left"], b["bottom"], b["right"], b["top"])
    if crs.upper() != "EPSG:4326":
        geom = transform_crs_to_wgs84(geom, crs)
    return geom.wkt


@router.post("/login", response_model=TokenResponse, tags=["auth"])
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    check_login_allowed(payload.username)
    user = db.query(User).filter(User.username == payload.username, User.is_active.is_(True)).one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        register_login_failure(payload.username)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    clear_login_failures(payload.username)
    token = create_access_token(payload.username)
    refresh = create_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token=refresh,
            expires_at=_utcnow_naive() + timedelta(days=7),
            revoked=False,
        )
    )
    db.commit()
    write_audit_log(db, "login", "/api/v1/login", "success", user=user)
    _set_auth_cookies(response, token, refresh)
    return TokenResponse(access_token=token, refresh_token=refresh)


@router.post("/auth/api-token", tags=["auth"])
def rotate_api_token(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    user.api_token = secrets.token_urlsafe(32)
    db.add(user)
    db.commit()
    write_audit_log(db, "rotate_api_token", "/api/v1/auth/api-token", "success", user=user)
    return {"api_token": user.api_token}


@router.get("/auth/me", tags=["auth"])
def auth_me(user: User = Depends(get_current_user)):
    return {"id": user.id, "username": user.username, "role": user.role}


@router.post("/auth/refresh", response_model=TokenResponse, tags=["auth"])
def auth_refresh(payload: RefreshTokenRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    refresh_token = payload.refresh_token or request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token is required")
    row = (
        db.query(RefreshToken)
        .filter(RefreshToken.token == refresh_token, RefreshToken.revoked.is_(False))
        .one_or_none()
    )
    if not row or row.expires_at < _utcnow_naive():
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    user = db.query(User).filter(User.id == row.user_id, User.is_active.is_(True)).one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Refresh token user not found")
    row.revoked = True
    db.add(row)
    next_refresh = create_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token=next_refresh,
            expires_at=_utcnow_naive() + timedelta(days=7),
            revoked=False,
        )
    )
    db.commit()
    access = create_access_token(user.username)
    _set_auth_cookies(response, access, next_refresh)
    return TokenResponse(access_token=access, refresh_token=next_refresh)


@router.post("/auth/logout", tags=["auth"])
def auth_logout(response: Response, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db.query(RefreshToken).filter(RefreshToken.user_id == user.id, RefreshToken.revoked.is_(False)).update({"revoked": True})
    db.commit()
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    write_audit_log(db, "logout", "/api/v1/auth/logout", "success", user=user)
    return {"status": "ok"}


@router.post("/uploads/sign", response_model=SignedUploadResponse, tags=["uploads"])
def sign_upload(payload: SignedUploadRequest, user: User = Depends(get_current_user)):
    token = create_signed_upload_token(
        user_id=user.id,
        filename=payload.filename,
        mime_type=payload.mime_type,
        size_bytes=payload.size_bytes,
    )
    return SignedUploadResponse(
        upload_url=f"/api/v1/uploads/signed/{token}",
        upload_token=token,
        expires_in_seconds=settings.signed_upload_expire_minutes * 60,
    )


@router.post("/uploads/signed/{token}", response_model=UploadImageResponse, tags=["uploads"])
async def upload_image_signed(
    token: str,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        payload = verify_signed_upload_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    if int(payload.get("user_id", -1)) != int(user.id):
        raise HTTPException(status_code=403, detail="Signed upload URL does not belong to current user")
    signed_filename = str(payload.get("filename") or "").strip()
    if not signed_filename or (file.filename and file.filename != signed_filename):
        raise HTTPException(status_code=400, detail="Uploaded filename does not match signed upload URL")
    if payload.get("mime_type") and file.content_type and payload.get("mime_type") != file.content_type:
        raise HTTPException(status_code=400, detail="Uploaded MIME type does not match signed upload URL")
    return await upload_image(file=file, user=user, db=db)


@router.post("/uploads", response_model=UploadImageResponse, tags=["uploads"])
async def upload_image(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    uploaded = await save_upload(file)
    image = create_satellite_image(
        db=db,
        provider="uploaded",
        acquisition_date=datetime.now(timezone.utc),
        cloud_cover=0.0,
        resolution_m=0.0,
        bounds_wkt=_uploaded_bounds_wkt(uploaded),
        asset_url=uploaded["local_path"],
        metadata=uploaded,
    )
    image.filename = uploaded["filename"]
    image.original_filename = uploaded["filename"]
    image.file_path = uploaded["local_path"]
    image.original_file_path = uploaded["local_path"]
    image.cog_file_path = uploaded.get("cog_path") or uploaded["local_path"]
    image.is_cog = bool(uploaded.get("is_cog"))
    image.image_type = "uploaded"
    image.source = "upload"
    image.width = uploaded.get("width")
    image.height = uploaded.get("height")
    image.band_count = uploaded.get("band_count")
    image.dtype = uploaded.get("dtype")
    image.crs = uploaded.get("crs")
    image.resolution_m = uploaded.get("resolution_m") or image.resolution_m
    image.gsd_m = uploaded.get("resolution_m")
    image.bounds_json = uploaded.get("bounds_json") or {}
    image.georeferenced = bool(uploaded.get("georeferenced"))
    image.warning = uploaded.get("warning")
    image.suitability_score = uploaded.get("suitability_score")
    db.commit()
    write_audit_log(db, "upload_image", "/api/v1/uploads", "success", user=user, details={"image_id": image.id})
    return UploadImageResponse(image_id=image.id, **uploaded)


@router.get("/uploads", tags=["uploads"])
def list_uploads(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = db.query(SatelliteImage).order_by(SatelliteImage.created_at.desc()).all()
    return {
        "items": [
            {
                "id": r.id,
                "filename": r.filename,
                "file_path": r.file_path,
                "georeferenced": r.georeferenced,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }


@router.get("/uploads/{image_id}", tags=["uploads"])
def get_upload(image_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    row = db.query(SatelliteImage).filter(SatelliteImage.id == image_id).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Upload not found")
    return {
        "id": row.id,
        "filename": row.filename,
        "file_path": row.file_path,
        "width": row.width,
        "height": row.height,
        "crs": row.crs,
        "georeferenced": row.georeferenced,
        "bounds_json": row.bounds_json,
        "metadata": row.extra_metadata,
    }


@router.post("/aoi", tags=["aoi"])
def save_aoi(payload: dict, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    name = payload.get("name")
    geojson = payload.get("geojson")
    if not name or not geojson:
        raise HTTPException(status_code=400, detail="name and geojson are required")
    try:
        geom = shp_shape(geojson)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid AOI geometry: {exc}") from exc
    row = GeoEvent(
        event_type="aoi",
        geom=WKTElement(geom.wkt, srid=4326),
        payload={"name": name, "geojson": geojson, "user_id": user.id},
    )
    db.add(row)
    db.commit()
    return {"id": row.id, "name": name}


@router.get("/aoi", tags=["aoi"])
def list_aoi(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = (
        db.query(GeoEvent)
        .filter(GeoEvent.event_type == "aoi")
        .order_by(GeoEvent.created_at.desc())
        .limit(200)
        .all()
    )
    return {"items": [{"id": r.id, "name": (r.payload or {}).get("name"), "geojson": (r.payload or {}).get("geojson")} for r in rows]}


@router.post("/uploads/{image_id}/detect", response_model=GenericTaskResponse, tags=["uploads", "detection"])
def detect_uploaded(image_id: int, user: User = Depends(require_any_role(["analyst"])), db: Session = Depends(get_db)):
    active = db.query(AIModel).filter(AIModel.active.is_(True)).first()
    ensure_active_model_or_error(active)
    row = db.query(SatelliteImage).filter(SatelliteImage.id == image_id).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Uploaded image not found")
    task = celery_app.send_task("tasks.detect_uploaded", kwargs={"image_id": image_id, "image_path": row.file_path})
    db.add(DetectionJob(task_id=task.id, image_id=image_id, status="pending", message="Queued"))
    db.commit()
    write_audit_log(db, "detect_uploaded", f"/api/v1/uploads/{image_id}/detect", "queued", user=user, details={"task_id": task.id})
    return GenericTaskResponse(task_id=task.id)


@router.post("/detect/uploaded/{image_id}", response_model=GenericTaskResponse, tags=["detection"])
def detect_uploaded_alias(image_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return detect_uploaded(image_id=image_id, user=user, db=db)


@router.post("/detect/coordinate", response_model=GenericTaskResponse, tags=["detection"])
async def detect_coordinate(
    payload: DetectRequest,
    user: User = Depends(require_any_role(["analyst"])),
    db: Session = Depends(get_db),
):
    active = db.query(AIModel).filter(AIModel.active.is_(True)).first()
    ensure_active_model_or_error(active)
    enforce_rate_limit("detect", window=60, max_calls=120)
    try:
        scene = await search_stac_scene(
            payload.latitude,
            payload.longitude,
            payload.cloud_max,
            payload.provider,
            payload.start_date,
            payload.end_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not scene:
        raise HTTPException(status_code=404, detail="No satellite scenes found for the requested coordinates/time range.")
    if scene.get("suitable_for_aircraft_detection") is False:
        raise HTTPException(
            status_code=400,
            detail="High-resolution imagery is required for aircraft detection. Upload a GeoTIFF or connect a high-resolution imagery provider.",
        )
    task = celery_app.send_task(
        "tasks.acquire_and_detect",
        kwargs={
            "latitude": payload.latitude,
            "longitude": payload.longitude,
            "provider": payload.provider,
            "cloud_max": payload.cloud_max,
            "resolution_m": payload.resolution_m,
            "start_date": payload.start_date.isoformat() if payload.start_date else None,
            "end_date": payload.end_date.isoformat() if payload.end_date else None,
            "model_id": active.id,
        },
    )
    db.add(DetectionJob(task_id=task.id, status="pending", message="Queued coordinate detection"))
    db.commit()
    write_audit_log(db, "detect", "/api/v1/detect", "queued", user=user, details={"task_id": task.id})
    return GenericTaskResponse(task_id=task.id)


@router.post("/detect", response_model=GenericTaskResponse, tags=["detection"])
async def detect_legacy(payload: DetectRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await detect_coordinate(payload=payload, user=user, db=db)


@router.get("/jobs/{task_id}", tags=["jobs"])
def task_status(
    task_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = celery_app.AsyncResult(task_id)
    job = db.query(DetectionJob).filter(DetectionJob.task_id == task_id).one_or_none()
    cjob = db.query(ChangeDetectionJob).filter(ChangeDetectionJob.task_id == task_id).one_or_none()
    if job:
        if result.ready():
            job.status = "completed" if result.successful() else "failed"
            job.progress = 1.0
            job.result = result.result if isinstance(result.result, dict) else {"result": str(result.result)}
            job.message = "completed" if result.successful() else "failed"
        elif not job.status or job.status in {"pending", "queued"}:
            job.status = result.status.lower()
        db.add(job)
        db.commit()
    if cjob:
        if result.ready():
            cjob.status = "completed" if result.successful() else "failed"
            cjob.progress = 1.0
            cjob.result = result.result if isinstance(result.result, dict) else {"result": str(result.result)}
            cjob.message = "completed" if result.successful() else "failed"
        elif not cjob.status or cjob.status in {"pending", "queued"}:
            cjob.status = result.status.lower()
        db.add(cjob)
        db.commit()
    return {
        "task_id": task_id,
        "status": (job.status if job else (cjob.status if cjob else result.status.lower())),
        "progress": (job.progress if job else (cjob.progress if cjob else 0.0)),
        "message": (job.message if job else (cjob.message if cjob else None)),
        "result": result.result if result.ready() else None,
    }


@router.post("/jobs/{task_id}/cancel", tags=["jobs"])
def cancel_job(
    task_id: str,
    force_terminate: bool = Query(default=False, description="If true, force-terminate the worker process (unsafe)."),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    # Production default: request cancellation without killing the worker process.
    # Force termination can leave partial files/DB state if tasks are not strictly idempotent.
    celery_app.control.revoke(task_id, terminate=bool(force_terminate))
    job = db.query(DetectionJob).filter(DetectionJob.task_id == task_id).one_or_none()
    cjob = db.query(ChangeDetectionJob).filter(ChangeDetectionJob.task_id == task_id).one_or_none()
    if job:
        job.status = "cancelled"
        job.message = "Cancelled by user"
        db.add(job)
    if cjob:
        cjob.status = "cancelled"
        cjob.message = "Cancelled by user"
        db.add(cjob)
    db.commit()
    return {"task_id": task_id, "status": "cancelled"}


@router.get("/tasks/{task_id}", tags=["jobs"])
def task_status_alias(task_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return task_status(task_id=task_id, db=db, _=user)


@router.get("/satellite-image", response_model=SatelliteImageResponse, tags=["satellite"])
async def get_satellite_image(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    provider: str = "sentinel-2",
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    cloud_max: float = Query(default=20, ge=0, le=100),
    resolution_m: float = Query(default=10, gt=0),
    _: User = Depends(get_current_user),
):
    enforce_rate_limit("satellite-image", window=60, max_calls=120)
    try:
        scene = await search_stac_scene(latitude, longitude, cloud_max, provider, start_date, end_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not scene:
        raise HTTPException(status_code=404, detail="No scene found for requested STAC filters.")
    return SatelliteImageResponse(
        provider=scene["provider"],
        acquisition_date=scene["acquisition_date"],
        cloud_cover=scene["cloud_cover"],
        preview_url=scene["preview_url"],
        bounds_geojson=scene["bounds_geojson"],
        resolution_m=scene.get("resolution_m"),
        suitable_for_aircraft_detection=scene.get("suitable_for_aircraft_detection"),
        warning=scene.get("warning"),
    )


@router.get("/detections", tags=["detection"])
def get_detections(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    limit: int = Query(default=100, ge=1, le=500),
    image_id: int | None = None,
    class_name: str | None = None,
    confidence_min: float | None = None,
):
    rows = list_detections(db, limit) if not image_id else db.execute(
        text(
            """
            SELECT d.id, d.confidence, d.timestamp, COALESCE(d.class_name, c.name) AS class_name,
                   ST_AsGeoJSON(d.geo_polygon) AS bbox_geojson
            FROM detections d
            LEFT JOIN aircraft_classes c ON c.id=d.class_id
            WHERE d.image_id = :image_id
              AND (:class_name IS NULL OR COALESCE(d.class_name, c.name)=:class_name)
              AND (:confidence_min IS NULL OR d.confidence>=:confidence_min)
            ORDER BY d.timestamp DESC
            LIMIT :limit
            """
        ),
        {"image_id": image_id, "class_name": class_name, "confidence_min": confidence_min, "limit": limit},
    ).mappings().all()
    items = [
        {
            "id": row.id,
            "class_name": row.class_name or "unknown-aircraft",
            "confidence": row.confidence,
            "geometry_geojson": json.loads(row.bbox_geojson) if row.bbox_geojson else None,
            "timestamp": row.timestamp,
        }
        for row in rows
    ]
    return {"total": len(items), "items": items}


@router.get("/detections/geojson", tags=["detection"])
def detections_geojson(db: Session = Depends(get_db), _: User = Depends(get_current_user), limit: int = 1000):
    rows = db.execute(
        text("SELECT id, class_name, confidence, ST_AsGeoJSON(geo_polygon) AS g FROM detections ORDER BY timestamp DESC LIMIT :limit"),
        {"limit": limit},
    ).mappings().all()
    return {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "geometry": json.loads(r["g"]), "properties": {"id": r["id"], "class_name": r["class_name"], "confidence": r["confidence"]}}
            for r in rows
            if r["g"]
        ],
    }


@router.get("/detections/export.csv", tags=["detection"])
def detections_export_csv(db: Session = Depends(get_db), _: User = Depends(require_any_role(["viewer", "analyst"]))):
    rows = db.execute(
        text("SELECT id, class_name, confidence, timestamp FROM detections ORDER BY timestamp DESC LIMIT 10000")
    ).mappings().all()
    lines = ["id,class_name,confidence,timestamp"]
    for r in rows:
        lines.append(f'{r["id"]},{r["class_name"]},{r["confidence"]},{r["timestamp"]}')
    return PlainTextResponse("\n".join(lines), media_type="text/csv")


@router.get("/detections/{detection_id}", tags=["detection"])
def get_detection_detail(detection_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    row = db.execute(
        text(
            """
            SELECT d.id, d.image_id, d.model_id, d.class_name, d.confidence, d.pixel_bbox, d.georeferenced,
                   ST_AsGeoJSON(d.geo_polygon) AS geo_polygon, ST_AsGeoJSON(d.centroid) AS centroid,
                   d.source, d.timestamp
            FROM detections d WHERE d.id=:id
            """
        ),
        {"id": detection_id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Detection not found")
    out = dict(row)
    out["geo_polygon"] = json.loads(out["geo_polygon"]) if out["geo_polygon"] else None
    out["centroid"] = json.loads(out["centroid"]) if out["centroid"] else None
    return out


@router.patch("/detections/{detection_id}/review", tags=["detection"])
def review_detection(
    detection_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_role(["analyst"])),
):
    status = str(payload.get("qa_status") or "").strip().lower()
    if status not in {"pending", "accepted", "rejected", "uncertain"}:
        raise HTTPException(status_code=400, detail="qa_status must be one of pending/accepted/rejected/uncertain")
    false_positive = bool(payload.get("false_positive", False))
    db.execute(
        text(
            """
            UPDATE detections
            SET qa_status=:qa_status,
                false_positive=:false_positive,
                reviewed_by_user_id=:reviewed_by_user_id,
                reviewed_at=NOW(),
                attributes = COALESCE(attributes, '{}'::jsonb) || :attrs::jsonb
            WHERE id=:id
            """
        ),
        {
            "id": detection_id,
            "qa_status": status,
            "false_positive": false_positive,
            "reviewed_by_user_id": user.id,
            "attrs": json.dumps({"review_comment": payload.get("comment")}),
        },
    )
    db.commit()
    write_audit_log(db, "review_detection", f"/api/v1/detections/{detection_id}/review", "success", user=user, details={"qa_status": status})
    return {"id": detection_id, "qa_status": status, "false_positive": false_positive}


@router.get("/aircraft-statistics")
def aircraft_statistics(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return compute_aircraft_statistics(db)


@router.get("/heatmap", tags=["heatmap"])
def heatmap(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    start_date: datetime | None = None,
    end_date: datetime | None = None,
):
    return build_heatmap_feature_collection(db, start_date, end_date)


@router.post("/train-model", response_model=GenericTaskResponse, tags=["models"])
def train_model(
    payload: TrainModelRequest,
    user: User = Depends(require_any_role(["model_manager"])),
    db: Session = Depends(get_db),
):
    enforce_rate_limit("train-model", window=300, max_calls=5)
    try:
        task = celery_app.send_task(
            "tasks.train_model",
            kwargs=payload.model_dump(),
        )
    except KombuOperationalError as exc:
        raise HTTPException(
            status_code=503,
            detail="Training queue unavailable. Start Redis and Celery worker, then retry.",
        ) from exc
    db.add(
        DetectionJob(
            task_id=task.id,
            job_type="training",
            status="pending",
            progress=0.0,
            current_step="queued",
            message=f"Queued {payload.training_method} training ({payload.model})",
            created_by_user_id=user.id,
        )
    )
    db.commit()
    write_audit_log(db, "train_model", "/api/v1/train-model", "queued", user=user, details={"task_id": task.id})
    return GenericTaskResponse(task_id=task.id)


@router.get("/training/options", tags=["models"])
def training_options(_: User = Depends(require_any_role(["model_manager"]))):
    return {
        "datasets": [
            {
                "id": "coco128.yaml",
                "name": "COCO128 (auto-download)",
                "description": "Ultralytics demo dataset. Automatically downloaded by YOLO training. Not aircraft-specific, but good to verify GPU training end-to-end.",
            },
            {
                "id": "data/datasets/sample_training/data.yaml",
                "name": "Sample training (local)",
                "description": "Built from your converted datasets. Requires you to populate data/raw/ first.",
            },
            {
                "id": "data/datasets/local_training/data.yaml",
                "name": "Local training dataset",
                "description": "Your own YOLO dataset built from data/raw/local_yolo via ai/dataset_creation.py.",
            },
        ],
        "methods": [
            {
                "id": "yolov8-supervised",
                "name": "YOLOv8 Supervised",
                "description": "Standard supervised object-detection training using Ultralytics YOLOv8.",
            }
        ],
        "base_models": [
            {"id": "yolov8n.pt", "family": "YOLOv8", "size": "nano"},
            {"id": "yolov8s.pt", "family": "YOLOv8", "size": "small"},
            {"id": "yolov8m.pt", "family": "YOLOv8", "size": "medium"},
            {"id": "yolov8l.pt", "family": "YOLOv8", "size": "large"},
            {"id": "yolov8x.pt", "family": "YOLOv8", "size": "xlarge"},
        ],
        "devices": [
            {"id": "0", "label": "GPU 0"},
            {"id": "cpu", "label": "CPU"},
        ],
    }


@router.get("/models")
def list_models(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = db.execute(
        text(
            """
            SELECT id, name, file_path, model_type, classes, version, framework, weights_path, metrics, active, created_at
            FROM ai_models
            ORDER BY created_at DESC
            """
        )
    ).mappings().all()
    return {"items": rows}


@router.post("/models/upload", tags=["models"])
async def upload_model(file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(require_any_role(["model_manager"]))):
    path = await save_model_file(file)
    checksum = file_sha256(path)
    dup = db.query(AIModel).filter(AIModel.checksum_sha256 == checksum).one_or_none()
    if dup:
        raise HTTPException(status_code=409, detail="Duplicate model upload detected (same checksum)")
    meta = extract_model_metadata(path)
    row = AIModel(
        name=(file.filename or "uploaded-model").replace(".pt", ""),
        version="v1",
        file_path=path,
        model_type="yolov8",
        classes=meta.get("classes")
        or ["aircraft", "medium_aircraft", "large_aircraft", "boeing_aircraft", "airbus_aircraft", "cargo_aircraft", "unknown_aircraft"],
        framework="pytorch",
        checksum_sha256=checksum,
        uploader=user.username,
        stride=meta.get("stride"),
        framework_version=meta.get("ultralytics_version") or "ultralytics",
        weights_path=path,
        metrics={"task": meta.get("task"), "class_count": meta.get("class_count"), "torch_version": meta.get("torch_version")},
        active=False,
    )
    db.add(row)
    db.commit()
    return {"id": row.id, "file_path": row.file_path}


@router.post("/models/{model_id}/activate")
def activate_model(model_id: int, db: Session = Depends(get_db), _: User = Depends(require_any_role(["model_manager"]))):
    row = set_active_model(db, model_id)
    if not row:
        raise HTTPException(status_code=404, detail="Model not found")
    db.commit()
    return {"status": "ok", "model_id": row.id}


@router.delete("/models/{model_id}", tags=["models"])
def delete_model(model_id: int, db: Session = Depends(get_db), _: User = Depends(require_any_role(["model_manager"]))):
    row = db.query(AIModel).filter(AIModel.id == model_id).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Model not found")
    if row.active:
        raise HTTPException(status_code=400, detail="Cannot delete active model. Disable or activate another model first.")
    db.delete(row)
    db.commit()
    return {"status": "deleted"}


@router.post("/models/{model_id}/disable", tags=["models"])
def disable_model(model_id: int, db: Session = Depends(get_db), _: User = Depends(require_any_role(["model_manager"]))):
    row = db.query(AIModel).filter(AIModel.id == model_id).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Model not found")
    row.active = False
    db.add(row)
    db.commit()
    return {"status": "disabled", "model_id": model_id}


@router.get("/airports/nearby", tags=["airports"])
def airports_nearby(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius_m: float = Query(default=50000, gt=0, le=1000000),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    rows = nearby_airports(db, lat, lon, radius_km=radius_m / 1000.0)
    return {
        "items": [
            {
                "id": r.id,
                "name": r.name,
                "icao_code": r.icao_code,
                "iata_code": r.iata_code,
                "country": r.country,
                "distance_m": float(r.distance_m),
                "geometry": json.loads(r.geometry),
            }
            for r in rows
        ]
    }


@router.get("/airports/search", tags=["airports"])
def airports_search(q: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = search_airports(db, q)
    return {"items": [{**dict(r), "geometry": json.loads(r["geometry"])} for r in rows]}


@router.get("/airports/{airport_id}", tags=["airports"])
def airport_detail(airport_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    row = db.execute(
        text(
            """
            SELECT id, ident, icao_code, iata_code, name, municipality, country, type, ST_AsGeoJSON(geom) AS geometry
            FROM airports
            WHERE id=:id
            """
        ),
        {"id": airport_id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Airport not found")
    out = dict(row)
    out["geometry"] = json.loads(out["geometry"])
    return out


@router.get("/airports/{airport_id}/activity", tags=["airports"])
def airport_activity(airport_id: int, radius_m: float = 5000, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    row = db.execute(
        text(
            """
            SELECT a.id, a.name,
                   COUNT(d.id) AS detection_count,
                   MAX(d.timestamp) AS last_detection
            FROM airports a
            LEFT JOIN detections d
              ON d.centroid IS NOT NULL
             AND ST_DWithin(a.geom::geography, d.centroid::geography, :radius_m)
            WHERE a.id=:id
            GROUP BY a.id, a.name
            """
        ),
        {"id": airport_id, "radius_m": radius_m},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Airport not found")
    return dict(row)


@router.get("/airports/{airport_id}/detections", tags=["airports"])
def airport_detections(airport_id: int, radius_m: float = 5000, limit: int = 200, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = db.execute(
        text(
            """
            SELECT d.id, d.class_name, d.confidence, d.timestamp, ST_AsGeoJSON(d.geo_polygon) AS geometry
            FROM airports a
            JOIN detections d
              ON d.geo_polygon IS NOT NULL
             AND ST_DWithin(a.geom::geography, d.centroid::geography, :radius_m)
            WHERE a.id=:id
            ORDER BY d.timestamp DESC
            LIMIT :limit
            """
        ),
        {"id": airport_id, "radius_m": radius_m, "limit": limit},
    ).mappings().all()
    return {"items": [{**dict(r), "geometry": json.loads(r["geometry"]) if r["geometry"] else None} for r in rows]}


@router.post("/change-detection", tags=["change-detection"])
def change_detection(
    before_image_id: int,
    after_image_id: int,
    match_distance_m: float = 40.0,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    task = celery_app.send_task(
        "tasks.change_detection",
        kwargs={
            "before_image_id": before_image_id,
            "after_image_id": after_image_id,
            "match_distance_m": match_distance_m,
        },
    )
    db.add(
        ChangeDetectionJob(
            task_id=task.id,
            before_image_id=before_image_id,
            after_image_id=after_image_id,
            status="pending",
            message="Queued",
        )
    )
    db.commit()
    return {"job_id": task.id}


@router.post("/airports/import", tags=["airports"])
def airports_import(csv_path: str, _: User = Depends(require_role("admin"))):
    task = celery_app.send_task("tasks.import_airports", kwargs={"csv_path": csv_path})
    return {"job_id": task.id}


@router.get("/uploaded-image/{image_id}/tiles")
def uploaded_image_tiles(image_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    row = db.execute(
        text("SELECT id, asset_url FROM satellite_images WHERE id=:id"),
        {"id": image_id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Uploaded image not found")
    path = str(row["asset_url"])
    if not path.lower().endswith((".tif", ".tiff")):
        raise HTTPException(status_code=400, detail="Tile overlay is only available for GeoTIFF uploads")
    return build_titiler_urls(path)


@router.get("/tiles/{image_id}/metadata", tags=["tiles"])
def tile_metadata(image_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    row = db.query(SatelliteImage).filter(SatelliteImage.id == image_id).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Image not found")
    return {
        "image_id": row.id,
        "filename": row.filename,
        "georeferenced": row.georeferenced,
        "crs": row.crs,
        "bounds_json": row.bounds_json,
        "resolution_m": row.resolution_m,
    }


@router.get("/tiles/{image_id}/tilejson.json", tags=["tiles"])
def tile_tilejson(image_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    row = db.query(SatelliteImage).filter(SatelliteImage.id == image_id).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Image not found")
    if not row.file_path or not str(row.file_path).lower().endswith((".tif", ".tiff")):
        raise HTTPException(status_code=400, detail="Tile service available only for uploaded GeoTIFF")
    urls = build_titiler_urls(str(row.file_path))
    return {"tilejson": "2.2.0", "tiles": [urls["tiles_url"]], "name": row.filename or f"image-{row.id}"}


@router.get("/admin/audit")
def admin_audit(
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=1000),
):
    write_audit_log(db, "read_audit", "/api/v1/admin/audit", "success", user=user, details={"limit": limit})
    rows = (
        db.query(
            User.username.label("username"),
            User.role.label("role"),
        )
        .filter(User.id == user.id)
        .first()
    )
    logs = db.execute(
        text(
            """
        SELECT id, username_snapshot, action, endpoint, status, details, created_at
        FROM audit_logs
        ORDER BY created_at DESC
        LIMIT :limit
        """
        ),
        {"limit": limit},
    ).mappings().all()
    return {"viewer": {"username": rows.username if rows else user.username, "role": rows.role if rows else user.role}, "items": logs}
