from __future__ import annotations

import json
from dataclasses import dataclass

from app.core.config import Settings


@dataclass(frozen=True)
class ConfigIssue:
    code: str
    message: str


def _parse_json_setting(name: str, raw: str) -> ConfigIssue | None:
    try:
        json.loads(raw)
        return None
    except Exception as exc:  # pragma: no cover
        return ConfigIssue(code="INVALID_JSON", message=f"{name} is not valid JSON: {exc}")


def validate_settings(settings: Settings) -> list[ConfigIssue]:
    issues: list[ConfigIssue] = []

    # Validate JSON-encoded configuration values
    issues.extend(
        issue
        for issue in [
            _parse_json_setting("CORS_ALLOWED_ORIGINS_JSON", settings.cors_allowed_origins_json),
            _parse_json_setting("DETECTION_THRESHOLDS_JSON", settings.detection_thresholds_json),
        ]
        if issue is not None
    )

    env = (settings.env or "development").lower().strip()
    is_prod_like = env in {"production", "prod", "staging", "stage"}

    # Fail-closed production checks
    if is_prod_like:
        if not settings.secret_key or settings.secret_key.strip().lower() == "change-me":
            issues.append(
                ConfigIssue(
                    code="UNSAFE_JWT_SECRET",
                    message="JWT_SECRET must be set to a non-default value in production/staging.",
                )
            )

        # CORS constraints when using credentialed requests
        try:
            origins = json.loads(settings.cors_allowed_origins_json)
            origins = [str(o).strip() for o in origins if str(o).strip()]
        except Exception:
            origins = []
        if settings.cors_allow_credentials and any(o == "*" for o in origins):
            issues.append(
                ConfigIssue(
                    code="UNSAFE_CORS_WILDCARD",
                    message='CORS_ALLOWED_ORIGINS_JSON must not contain "*" when CORS_ALLOW_CREDENTIALS=true in production/staging.',
                )
            )

        # Cookie security
        if not settings.secure_cookies:
            issues.append(
                ConfigIssue(
                    code="UNSAFE_COOKIES",
                    message="SECURE_COOKIES should be true in production/staging (requires HTTPS).",
                )
            )

        samesite = (settings.cookie_samesite or "").lower().strip()
        if samesite not in {"lax", "strict", "none"}:
            issues.append(
                ConfigIssue(
                    code="INVALID_COOKIE_SAMESITE",
                    message='COOKIE_SAMESITE must be one of: "lax", "strict", "none".',
                )
            )
        if samesite == "none" and not settings.secure_cookies:
            issues.append(
                ConfigIssue(
                    code="COOKIE_SAMESITE_NONE_REQUIRES_SECURE",
                    message='COOKIE_SAMESITE="none" requires SECURE_COOKIES=true.',
                )
            )

        # Signed upload flow safety: if configured, enforce non-trivial secret.
        if settings.signed_upload_secret is not None and settings.signed_upload_secret.strip() != "":
            if len(settings.signed_upload_secret.strip()) < 16:
                issues.append(
                    ConfigIssue(
                        code="WEAK_SIGNED_UPLOAD_SECRET",
                        message="SIGNED_UPLOAD_SECRET should be at least 16 characters.",
                    )
                )

        # Default admin bootstrap should not be enabled without explicit credentials
        if settings.default_admin_enabled:
            missing = [
                k
                for k, v in [
                    ("DEFAULT_ADMIN_USERNAME", settings.default_admin_username),
                    ("DEFAULT_ADMIN_EMAIL", settings.default_admin_email),
                    ("DEFAULT_ADMIN_PASSWORD", settings.default_admin_password),
                ]
                if not (v or "").strip()
            ]
            if missing:
                issues.append(
                    ConfigIssue(
                        code="DEFAULT_ADMIN_INCOMPLETE",
                        message=f"DEFAULT_ADMIN_ENABLED=true but missing required values: {', '.join(missing)}",
                    )
                )

    return issues

