# -*- coding: utf-8 -*-
"""Lightweight token-based auth and RBAC for the API.
- Issue a random token on login
- Expect header: X-Auth-Token
- Decorators to require auth and roles
Note: This is in-memory (resets on server restart). Suitable for prototype.
"""
import functools
import uuid
from typing import Optional, Dict
from flask import request, jsonify, g

# token -> payload
_tokens: Dict[str, dict] = {}


def issue_token(user: dict) -> str:
    token = uuid.uuid4().hex
    _tokens[token] = {
        "user_id": user.get("id"),
        "national_id": user.get("national_id"),
        "full_name": user.get("full_name"),
        "role": user.get("role"),
    }
    return token


def revoke_token(token: str):
    _tokens.pop(token, None)


def get_current_user() -> Optional[dict]:
    token = request.headers.get("X-Auth-Token", "").strip()
    if not token:
        return None
    return _tokens.get(token)


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