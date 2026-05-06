from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.core.config import settings


def _serializer() -> URLSafeTimedSerializer:
    secret = settings.signed_upload_secret or settings.secret_key
    return URLSafeTimedSerializer(secret_key=secret, salt="geoeye-upload-signature")


def create_signed_upload_token(
    user_id: int,
    filename: str,
    mime_type: str | None = None,
    size_bytes: int | None = None,
) -> str:
    payload = {
        "user_id": user_id,
        "filename": filename,
        "mime_type": mime_type,
        "size_bytes": size_bytes,
    }
    return _serializer().dumps(payload)


def verify_signed_upload_token(token: str) -> dict:
    try:
        return _serializer().loads(token, max_age=settings.signed_upload_expire_minutes * 60)
    except SignatureExpired as exc:
        raise ValueError("Signed upload URL expired") from exc
    except BadSignature as exc:
        raise ValueError("Invalid signed upload URL") from exc
