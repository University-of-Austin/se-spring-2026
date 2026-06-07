"""Authentication helpers for the BBS web frontend.

Cookie-based sessions using the sessions table in bbs.db.
"""

import sys
import os

# Add parent dir to path so we can import services/db
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import Request, HTTPException, Depends
from db import engine
import services


def get_db():
    """Yield a database connection for FastAPI dependency injection."""
    with engine.begin() as conn:
        yield conn


def get_current_user(request: Request, conn=Depends(get_db)):
    """Read session cookie and return user dict or None."""
    token = request.cookies.get("bbs_session")
    if not token:
        return None
    user_id = services.validate_session(conn, token)
    if not user_id:
        return None
    row = conn.execute(
        __import__("sqlalchemy").text(
            "SELECT id, username, role, is_banned FROM users WHERE id = :uid"
        ),
        {"uid": user_id},
    ).fetchone()
    if not row:
        return None
    return {"id": row[0], "username": row[1], "role": row[2], "is_banned": row[3]}


def require_user(request: Request, conn=Depends(get_db)):
    """Require authentication. Raises 401 if not logged in."""
    user = get_current_user(request, conn)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    if user.get("is_banned"):
        raise HTTPException(status_code=403, detail="Account banned")
    return user


def require_admin(request: Request, conn=Depends(get_db)):
    """Require admin/mod role. Raises 403 if not authorized."""
    user = require_user(request, conn)
    if user["role"] not in ("admin", "mod"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
