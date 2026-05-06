from fastapi import Depends, Header, HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models import User
from app.security import ALGORITHM

def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    auth = request.headers.get("authorization", "")
    token: str | None = None
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
    user = db.query(User).filter(User.username == username, User.is_active.is_(True)).one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_role(required_role: str):
    def _validator(user: User = Depends(get_current_user), x_api_token: str | None = Header(default=None)) -> User:
        if x_api_token and user.api_token and x_api_token == user.api_token:
            return user
        if user.role not in [required_role, "admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"{required_role} role required")
        return user

    return _validator


def require_any_role(roles: list[str]):
    allowed = set(roles + ["admin"])

    def _validator(user: User = Depends(get_current_user), x_api_token: str | None = Header(default=None)) -> User:
        if x_api_token and user.api_token and x_api_token == user.api_token:
            return user
        if user.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"One of roles required: {', '.join(sorted(allowed))}")
        return user

    return _validator
