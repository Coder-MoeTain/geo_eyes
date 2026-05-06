from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import json


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    project_name: str = "GeoEye-AI Intelligence Portal"
    env: str = "development"
    secret_key: str = Field(default="change-me", alias="JWT_SECRET")
    access_token_expire_minutes: int = 1440
    default_admin_enabled: bool = False
    default_admin_username: str = ""
    default_admin_email: str = ""
    default_admin_password: str = ""
    rate_limit_redis_prefix: str = "geoeye:rl"
    cors_allowed_origins_json: str = '["http://localhost:5173","http://127.0.0.1:5173"]'
    cors_allow_credentials: bool = True
    secure_cookies: bool = False
    cookie_samesite: str = "lax"
    cookie_domain: str | None = None
    signed_upload_secret: str | None = None
    signed_upload_expire_minutes: int = 15
    public_titiler_url: str = "http://localhost/titiler"
    internal_titiler_url: str = "http://titiler:8000"
    max_model_size_mb: int = 2048

    postgres_user: str = "geoeye"
    postgres_password: str = "geoeye"
    postgres_db: str = "geoeye"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    stac_api_url: str = "https://earth-search.aws.element84.com/v1"
    yolo_model_path: str = "/models/yolov8-aircraft.pt"
    sam_model_path: str = "/models/sam_vit_h_4b8939.pth"
    upload_dir: str = "/data/uploads"
    max_upload_size_mb: int = Field(default=256, alias="MAX_UPLOAD_MB")
    titiler_base_url: str = "http://titiler:8000"
    detection_thresholds_json: str = '{"aircraft":0.25,"large_aircraft":0.3,"cargo_aircraft":0.35}'
    iou_merge_threshold: float = 0.45
    min_bbox_px: int = 6
    max_bbox_px: int = 5000
    # Ultralytics device: "0", "cuda:0", or "cpu"
    yolo_device: str = Field(default="0", alias="YOLO_DEVICE")

    @property
    def database_url(self) -> str:
        import os

        explicit = os.getenv("DATABASE_URL")
        if explicit:
            return explicit
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()


def detection_thresholds() -> dict[str, float]:
    try:
        return json.loads(settings.detection_thresholds_json)
    except Exception:
        return {"aircraft": 0.25, "large_aircraft": 0.3, "cargo_aircraft": 0.35}


def cors_allowed_origins() -> list[str]:
    try:
        val = json.loads(settings.cors_allowed_origins_json)
        return [str(v).strip() for v in val if str(v).strip()]
    except Exception:
        return ["http://localhost:5173", "http://127.0.0.1:5173"]
