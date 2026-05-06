"""
Seed a local admin account (default: username admin, password admin).

Run from the backend directory (loads .env from cwd via app settings):

  py -3.10 scripts/seed_admin.py

Custom credentials:

  py -3.10 scripts/seed_admin.py --username admin --password admin --email admin@localhost

If the user already exists, use --force to reset password and ensure role admin.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.db.session import SessionLocal
from app.models import User
from app.security import hash_password


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed admin user (development).")
    parser.add_argument("--username", default="admin", help="Login username")
    parser.add_argument("--password", default="admin", help="Plain password (dev only)")
    parser.add_argument("--email", default="admin@localhost", help="Unique email for the user")
    parser.add_argument(
        "--force",
        action="store_true",
        help="If username exists, overwrite password_hash and set role=admin",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == args.username).one_or_none()
        if user:
            if not args.force:
                print(f"User {args.username!r} already exists. Use --force to reset password.")
                return 0
            user.password_hash = hash_password(args.password)
            user.role = "admin"
            user.is_active = True
            db.commit()
            print(f"Updated {args.username!r}: password reset, role=admin.")
            return 0

        taken = db.query(User).filter(User.email == args.email).one_or_none()
        if taken:
            print(f"Email {args.email!r} is already used by {taken.username!r}.")
            return 1

        db.add(
            User(
                username=args.username,
                email=args.email,
                password_hash=hash_password(args.password),
                role="admin",
                is_active=True,
            )
        )
        db.commit()
        print(f"Created user {args.username!r} ({args.email!r}) with role=admin.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
