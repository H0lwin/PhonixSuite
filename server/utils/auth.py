# -*- coding: utf-8 -*-
"""DB-backed token auth with TTL and sliding expiration.
- Expect header: X-Auth-Token
- Tokens persisted in MySQL with expires_at
"""
import functools
from typing import Optional, Dict
from flask import request, jsonify, g

from models.auth_token import (
    ensure_auth_token_schema,
    issue_db_token,
    get_user_by_token,
    revoke_db_token,
    DEFAULT_TTL_MINUTES,
)


def issue_token(user: dict, ttl_minutes: int = DEFAULT_TTL_MINUTES) -> str:
    ensure_auth_token_schema()
    return issue_db_token(user, ttl_minutes=ttl_minutes)


def revoke_token(token: str):
    revoke_db_token(token)


def get_current_user() -> Optional[dict]:
    token = request.headers.get("X-Auth-Token", "").strip()
    if not token:
        return None
    # Sliding expiration enabled by default
    return get_user_by_token(token, sliding_extend=True, ttl_minutes=DEFAULT_TTL_MINUTES)


def require_auth(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
        g.user = user
        return fn(*args, **kwargs)
    return wrapper


def require_roles(*roles):
    def dec(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({"status": "error", "message": "Unauthorized"}), 401
            if roles and user.get("role") not in roles:
                return jsonify({"status": "error", "message": "Forbidden"}), 403
            g.user = user
            return fn(*args, **kwargs)
        return wrapper
    return dec


def require_admin(fn):
    """Decorator to require admin role"""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
        if user.get("role") != "admin":
            return jsonify({"status": "error", "message": "Admin access required"}), 403
        g.user = user
        return fn(*args, **kwargs)
    return wrapper


def require_admin_or_owner(resource_type: str, id_param: str = "id"):
    """Decorator to require admin role or ownership of a resource
    
    Args:
        resource_type: Type of resource ('loan', 'loan_buyer', etc.)
        id_param: Name of the URL parameter containing the resource ID
    """
    def dec(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({"status": "error", "message": "Unauthorized"}), 401
            
            # Admin has access to everything
            if user.get("role") == "admin":
                g.user = user
                return fn(*args, **kwargs)
            
            # Check ownership based on resource type
            resource_id = kwargs.get(id_param)
            if not resource_id:
                return jsonify({"status": "error", "message": "Invalid resource ID"}), 400
            
            if not check_resource_ownership(user, resource_type, resource_id):
                return jsonify({"status": "error", "message": "Access denied: You can only access your own records"}), 403
            
            g.user = user
            return fn(*args, **kwargs)
        return wrapper
    return dec


def check_resource_ownership(user: dict, resource_type: str, resource_id: int) -> bool:
    """Check if user owns or has access to a specific resource"""
    from database import get_connection
    
    conn = get_connection(True)
    cur = conn.cursor()
    
    user_nid = user.get("national_id")
    user_role = user.get("role")
    
    try:
        if resource_type == "loan":
            cur.execute("SELECT created_by_nid FROM loans WHERE id=%s", (resource_id,))
            row = cur.fetchone()
            if row and row[0] == user_nid:
                return True
                
        elif resource_type == "loan_buyer":
            # Check if user is the broker or creator
            cur.execute("SELECT broker, created_by_nid FROM loan_buyers WHERE id=%s", (resource_id,))
            row = cur.fetchone()
            if row:
                broker_nid, creator_nid = row[0], row[1]
                if user_nid in (broker_nid, creator_nid):
                    return True
        
        return False
    except Exception:
        return False
    finally:
        cur.close()
        conn.close()
