# -*- coding: utf-8 -*-
"""DB-backed auth tokens with TTL and sliding expiration.
- Tokens are stored in MySQL with expires_at
- Each valid use extends expiry (sliding expiration)
"""
from __future__ import annotations
from typing import Optional, Dict
from datetime import datetime, timedelta
import uuid

from database import get_connection

# Default TTL in minutes
DEFAULT_TTL_MINUTES = 60


def ensure_auth_token_schema() -> None:
    """Create auth_tokens table if not exists."""
    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_tokens (
            token VARCHAR(64) PRIMARY KEY,
            user_id INT NOT NULL,
            national_id VARCHAR(10) NOT NULL,
            full_name VARCHAR(191) NULL,
            role VARCHAR(100) NOT NULL,
            issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            INDEX idx_expires (expires_at),
            CONSTRAINT fk_auth_token_user FOREIGN KEY (user_id) REFERENCES employees(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
        """
    )
    conn.commit(); cur.close(); conn.close()


def _now() -> datetime:
    # Use UTC to avoid timezone ambiguity
    return datetime.utcnow()


def _new_token() -> str:
    return uuid.uuid4().hex + uuid.uuid4().hex[:32]


def issue_db_token(user: dict, ttl_minutes: int = DEFAULT_TTL_MINUTES) -> str:
    """Create and persist a token for the given user, returning the token string."""
    ensure_auth_token_schema()  # defensive ensure
    token = _new_token()[:64]
    expires_at = _now() + timedelta(minutes=int(ttl_minutes or DEFAULT_TTL_MINUTES))
    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO auth_tokens (token, user_id, national_id, full_name, role, expires_at)
        VALUES (%s,%s,%s,%s,%s,%s)
        """,
        (
            token,
            user.get("id"),
            user.get("national_id"),
            user.get("full_name"),
            user.get("role") or "user",
            expires_at,
        ),
    )
    conn.commit(); cur.close(); conn.close()
    return token


def get_user_by_token(token: str, sliding_extend: bool = True, ttl_minutes: int = DEFAULT_TTL_MINUTES) -> Optional[Dict]:
    """Return user payload for a valid token, optionally extending expiry (sliding)."""
    if not token:
        return None
    now = _now()
    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT user_id, national_id, full_name, role, expires_at
        FROM auth_tokens
        WHERE token=%s AND expires_at > %s
        LIMIT 1
        """,
        (token, now),
    )
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        return None

    user = {
        "user_id": row[0],
        "national_id": row[1],
        "full_name": row[2],
        "role": row[3],
    }

    if sliding_extend:
        new_exp = now + timedelta(minutes=int(ttl_minutes or DEFAULT_TTL_MINUTES))
        try:
            cur2 = conn.cursor()
            cur2.execute("UPDATE auth_tokens SET expires_at=%s WHERE token=%s", (new_exp, token))
            conn.commit(); cur2.close()
        except Exception:
            # Non-fatal: if extend fails, still return current user
            pass

    cur.close(); conn.close()
    return user


def revoke_db_token(token: str) -> None:
    if not token:
        return
    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute("DELETE FROM auth_tokens WHERE token=%s", (token,))
    conn.commit(); cur.close(); conn.close()


def cleanup_expired_tokens() -> int:
    """Delete expired tokens; returns number of removed rows."""
    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute("DELETE FROM auth_tokens WHERE expires_at <= %s", (_now(),))
    affected = cur.rowcount or 0
    conn.commit(); cur.close(); conn.close()
    return affected