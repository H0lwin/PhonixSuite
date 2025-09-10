# -*- coding: utf-8 -*-
"""Auth service helpers for login/logout that set/clear session.
"""
import json
from typing import Dict
from . import api_client
from ..state import session

API_LOGIN = "http://127.0.0.1:5000/api/auth/login"
API_LOGOUT = "http://127.0.0.1:5000/api/auth/logout"


def login(national_id: str, password: str) -> Dict:
    resp = api_client.post_json(API_LOGIN, {"national_id": national_id, "password": password})
    data = resp.json()
    if data.get("status") == "success":
        session.set_session(data.get("token"), data.get("role"), data.get("display_name"))
    return data


def logout() -> None:
    try:
        api_client.post_json(API_LOGOUT, {})
    finally:
        session.clear_session()