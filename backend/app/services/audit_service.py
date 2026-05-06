from datetime import datetime

from sqlalchemy.orm import Session

from app.models import AuditLog, User


def write_audit_log(
    db: Session,
    action: str,
    endpoint: str,
    status: str,
    user: User | None = None,
    details: dict | None = None,
):
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            username_snapshot=user.username if user else None,
            action=action,
            endpoint=endpoint,
            status=status,
            details=details or {},
            created_at=datetime.utcnow(),
        )
    )
    db.commit()
