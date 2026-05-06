from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str | None = None


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = "user"


class DetectRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    start_date: datetime | None = None
    end_date: datetime | None = None
    cloud_max: float = Field(default=30.0, ge=0, le=100)
    resolution_m: float = Field(default=10.0, gt=0)
    provider: str = "sentinel-2"
    aoi_geojson: dict[str, Any] | None = None
    model_id: int | None = None
    uploaded_image_id: int | None = None


class DetectionFeature(BaseModel):
    id: int
    class_name: str
    confidence: float
    geometry_geojson: dict[str, Any]
    timestamp: datetime


class DetectionListResponse(BaseModel):
    total: int
    items: list[DetectionFeature]


class SatelliteImageResponse(BaseModel):
    provider: str
    acquisition_date: datetime
    cloud_cover: float
    preview_url: str | None = None
    bounds_geojson: dict[str, Any] | None = None
    resolution_m: float | None = None
    suitable_for_aircraft_detection: bool | None = None
    warning: str | None = None


class TrainModelRequest(BaseModel):
    dataset_yaml: str = "data/datasets/aircraft/data.yaml"
    epochs: int = 20
    img_size: int = 1024
    batch_size: int = 8
    model: str = "yolov8m.pt"
    device: str = "cpu"


class UploadImageResponse(BaseModel):
    image_id: int
    filename: str
    size_bytes: int
    mime_type: str
    local_path: str


class SignedUploadRequest(BaseModel):
    filename: str
    mime_type: str | None = None
    size_bytes: int | None = None


class SignedUploadResponse(BaseModel):
    upload_url: str
    upload_token: str
    expires_in_seconds: int


class GenericTaskResponse(BaseModel):
    task_id: str
    status: str = "queued"
