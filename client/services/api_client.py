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


def delete(url: str, timeout: int = DEFAULT_TIMEOUT) -> requests.Response:
    return requests.delete(url, headers=_headers(), timeout=timeout)


def patch_json(url: str, payload: Dict[str, Any], timeout: int = DEFAULT_TIMEOUT) -> requests.Response:
    return requests.patch(url, headers=_headers(), data=json.dumps(payload).encode("utf-8"), timeout=timeout)
