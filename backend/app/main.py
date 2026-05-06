import json

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse, StreamingResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.orm import Session

from app.api import router
from app.core.config import cors_allowed_origins, settings
from app.db.session import SessionLocal
from app.models import User
from app.security import hash_password

app = FastAPI(title=settings.project_name, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allowed_origins(),
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Token"],
)

app.include_router(router)


@app.middleware("http")
async def response_envelope_middleware(request, call_next):
    response = await call_next(request)
    if isinstance(response, (StreamingResponse, FileResponse)):
        return response
    ctype = response.headers.get("content-type", "")
    if "application/json" not in ctype:
        return response
    if not hasattr(response, "body") or response.body is None:
        return response
    try:
        raw = response.body.decode("utf-8")
        payload = json.loads(raw) if raw else None
    except Exception:
        return response
    if isinstance(payload, dict) and "success" in payload:
        return response
    if response.status_code >= 400:
        return response
    return JSONResponse(
        status_code=response.status_code,
        content={"success": True, "data": payload},
        headers={k: v for k, v in response.headers.items() if k.lower() != "content-length"},
    )


@app.middleware("http")
async def security_headers_middleware(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    if settings.env.lower() != "development":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_, exc: StarletteHTTPException):
    details = exc.detail
    if isinstance(details, dict) and "error" in details:
        code = details.get("error", "HTTP_ERROR")
        msg = details.get("message", str(details))
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "error": {"code": code, "message": msg, "details": details}},
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": {"code": "HTTP_ERROR", "message": str(details), "details": details}},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"success": False, "error": {"code": "VALIDATION_ERROR", "message": "Request validation failed", "details": exc.errors()}},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": {"code": "INTERNAL_ERROR", "message": str(exc), "details": {}}},
    )


@app.on_event("startup")
def ensure_default_admin():
    db: Session = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == settings.default_admin_username).one_or_none()
        if not existing:
            db.add(
                User(
                    username=settings.default_admin_username,
                    email=settings.default_admin_email,
                    password_hash=hash_password(settings.default_admin_password),
                    role="admin",
                    is_active=True,
                )
            )
            db.commit()
    except Exception:
        # Schema might be unavailable until Alembic migrations are applied.
        return
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok", "service": "geoeye-backend"}
