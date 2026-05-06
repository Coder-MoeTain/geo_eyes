from time import time

import redis
from fastapi import HTTPException

from app.core.config import settings

_fallback_bucket: dict[str, list[int]] = {}
_fallback_login_fail: dict[str, list[int]] = {}
_redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)


def enforce_rate_limit(key: str, window: int = 60, max_calls: int = 120):
    now_s = int(time())
    namespaced = f"{settings.rate_limit_redis_prefix}:{key}:{now_s // window}"
    try:
        current = _redis_client.incr(namespaced)
        if current == 1:
            _redis_client.expire(namespaced, window + 2)
        if current > max_calls:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        return
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        calls = _fallback_bucket.get(key, [])
        calls = [t for t in calls if now_s - t < window]
        if len(calls) >= max_calls:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        calls.append(now_s)
        _fallback_bucket[key] = calls


def _login_key(username: str) -> str:
    return f"{settings.rate_limit_redis_prefix}:login-fail:{username.lower()}"


def check_login_allowed(username: str, lockout_seconds: int = 900, max_failures: int = 5):
    key = _login_key(username)
    now_s = int(time())
    try:
        val = _redis_client.get(key)
        if val and int(val) >= max_failures:
            ttl = _redis_client.ttl(key)
            raise HTTPException(status_code=429, detail=f"Too many failed logins. Try again in {max(1, ttl)}s")
        return
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        arr = [t for t in _fallback_login_fail.get(username, []) if now_s - t < lockout_seconds]
        if len(arr) >= max_failures:
            raise HTTPException(status_code=429, detail="Too many failed logins. Try again later.")
        _fallback_login_fail[username] = arr


def register_login_failure(username: str, lockout_seconds: int = 900):
    key = _login_key(username)
    now_s = int(time())
    try:
        val = _redis_client.incr(key)
        if val == 1:
            _redis_client.expire(key, lockout_seconds)
    except Exception:
        arr = _fallback_login_fail.get(username, [])
        arr.append(now_s)
        _fallback_login_fail[username] = arr


def clear_login_failures(username: str):
    key = _login_key(username)
    try:
        _redis_client.delete(key)
    except Exception:
        _fallback_login_fail.pop(username, None)
