from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.session import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(32), default="user", nullable=False)
    api_token = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SatelliteImage(Base):
    __tablename__ = "satellite_images"
    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=True)
    original_filename = Column(String(255), nullable=True)
    file_path = Column(Text, nullable=True)
    original_file_path = Column(Text, nullable=True)
    cog_file_path = Column(Text, nullable=True)
    is_cog = Column(Boolean, default=False)
    image_type = Column(String(32), nullable=True)
    source = Column(String(64), nullable=True)
    provider = Column(String(64), nullable=False)
    acquisition_date = Column(DateTime, nullable=False)
    cloud_cover = Column(Float, default=0.0)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    band_count = Column(Integer, nullable=True)
    dtype = Column(String(64), nullable=True)
    gsd_m = Column(Float, nullable=True)
    crs = Column(String(128), nullable=True)
    resolution_m = Column(Float, default=10.0)
    footprint = Column("bounds", Geometry("POLYGON", srid=4326))
    bounds_json = Column(JSON, default=dict)
    georeferenced = Column(Boolean, default=False)
    warning = Column(Text, nullable=True)
    suitability_score = Column(Float, nullable=True)
    asset_url = Column(Text, nullable=True)
    extra_metadata = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class AircraftClass(Base):
    __tablename__ = "aircraft_classes"
    id = Column(Integer, primary_key=True)
    name = Column(String(128), unique=True, nullable=False)
    description = Column(Text, nullable=True)


class Detection(Base):
    __tablename__ = "detections"
    id = Column(Integer, primary_key=True)
    image_id = Column(Integer, ForeignKey("satellite_images.id"), nullable=True)
    model_id = Column(Integer, ForeignKey("ai_models.id"), nullable=True)
    class_id = Column(Integer, ForeignKey("aircraft_classes.id"), nullable=True)
    class_name = Column(String(128), nullable=True)
    confidence = Column(Float, nullable=False)
    pixel_bbox = Column(JSON, default=dict)
    bbox_polygon = Column("geo_polygon", Geometry("POLYGON", srid=4326), nullable=True)
    centroid = Column(Geometry("POINT", srid=4326), nullable=True)
    georeferenced = Column(Boolean, default=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    source = Column(String(64), default="yolov8")
    attributes = Column(JSON, default=dict)
    qa_status = Column(String(32), default="pending")
    false_positive = Column(Boolean, default=False)
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    image = relationship("SatelliteImage")
    aircraft_class = relationship("AircraftClass")


class AIModel(Base):
    __tablename__ = "ai_models"
    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)
    file_path = Column(Text, nullable=True)
    model_type = Column(String(64), default="yolov8")
    classes = Column(JSON, default=list)
    checksum_sha256 = Column(String(128), nullable=True, unique=True)
    uploader = Column(String(100), nullable=True)
    input_size = Column(Integer, nullable=True)
    stride = Column(Integer, nullable=True)
    framework_version = Column(String(64), nullable=True)
    version = Column(String(64), nullable=False)
    framework = Column(String(64), default="pytorch")
    weights_path = Column(Text, nullable=False)
    metrics = Column(JSON, default=dict)
    status = Column(String(32), default="uploaded")
    active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Airport(Base):
    __tablename__ = "airports"
    id = Column(Integer, primary_key=True)
    ident = Column(String(16), unique=True, nullable=True)
    icao_code = Column(String(8), unique=True, nullable=True)
    iata_code = Column(String(8), nullable=True)
    name = Column(String(255), nullable=False)
    municipality = Column(String(128), nullable=True)
    country = Column(String(64), nullable=True)
    type = Column(String(64), nullable=True)
    geom = Column(Geometry("POINT", srid=4326), nullable=False)


class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True)
    level = Column(String(32), default="info")
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String(32), default="open")
    related_detection_id = Column(Integer, ForeignKey("detections.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class GeoEvent(Base):
    __tablename__ = "geo_events"
    id = Column(Integer, primary_key=True)
    event_type = Column(String(64), nullable=False)
    geom = Column(Geometry("GEOMETRY", srid=4326), nullable=False)
    payload = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    username_snapshot = Column(String(100), nullable=True)
    action = Column(String(128), nullable=False)
    endpoint = Column(String(255), nullable=False)
    status = Column(String(32), nullable=False)
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class DetectionJob(Base):
    __tablename__ = "detection_jobs"
    id = Column(Integer, primary_key=True)
    task_id = Column(String(255), unique=True, nullable=False, index=True)
    image_id = Column(Integer, ForeignKey("satellite_images.id"), nullable=True)
    job_type = Column(String(64), default="detection")
    status = Column(String(32), default="pending")
    progress = Column(Float, default=0.0)
    current_step = Column(String(128), nullable=True)
    message = Column(Text, nullable=True)
    error_code = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    result = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class ChangeDetectionJob(Base):
    __tablename__ = "change_detection_jobs"
    id = Column(Integer, primary_key=True)
    task_id = Column(String(255), unique=True, nullable=False, index=True)
    before_image_id = Column(Integer, ForeignKey("satellite_images.id"), nullable=True)
    after_image_id = Column(Integer, ForeignKey("satellite_images.id"), nullable=True)
    job_type = Column(String(64), default="change_detection")
    status = Column(String(32), default="pending")
    progress = Column(Float, default=0.0)
    current_step = Column(String(128), nullable=True)
    message = Column(Text, nullable=True)
    error_code = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    result = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token = Column(String(512), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
