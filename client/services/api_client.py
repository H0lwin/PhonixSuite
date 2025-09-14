# -*- coding: utf-8 -*-
"""Centralized HTTP client that injects X-Auth-Token into all requests.
Use this instead of calling requests directly in views.
"""
from typing import Any, Dict, Optional
import json
import requests
from ..state import session

DEFAULT_TIMEOUT = 15


def _headers(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    h = {"Content-Type": "application/json"}
    tok = session.get_token()
    if tok:
        h["X-Auth-Token"] = tok
    if extra:
        h.update(extra)
    return h


def get(url: str, timeout: int = DEFAULT_TIMEOUT) -> requests.Response:
    return requests.get(url, headers=_headers(), timeout=timeout)


def post_json(url: str, payload: Dict[str, Any], timeout: int = DEFAULT_TIMEOUT) -> requests.Response:
    return requests.post(url, headers=_headers(), data=json.dumps(payload).encode("utf-8"), timeout=timeout)

# Backwards-compat alias
post = post_json


def delete(url: str, timeout: int = DEFAULT_TIMEOUT) -> requests.Response:
    return requests.delete(url, headers=_headers(), timeout=timeout)


def patch_json(url: str, payload: Dict[str, Any], timeout: int = DEFAULT_TIMEOUT) -> requests.Response:
    return requests.patch(url, headers=_headers(), data=json.dumps(payload).encode("utf-8"), timeout=timeout)


def parse_json(resp: requests.Response) -> Dict[str, Any]:
    """Safely parse JSON from a response.
    - If body is not JSON or status != 200 without a JSON body, return a standard error dict.
    """
    try:
        data = resp.json()
    except Exception:
        return {"status": "error", "message": "Invalid JSON response"}
    # Normalize non-200 without explicit status
    if resp.status_code != 200 and not isinstance(data, dict):
        return {"status": "error", "message": f"HTTP {resp.status_code}"}
    if isinstance(data, dict) and "status" not in data and resp.status_code != 200:
        return {"status": "error", "message": f"HTTP {resp.status_code}"}
    return data
