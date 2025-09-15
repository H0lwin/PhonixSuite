# -*- coding: utf-8 -*-
"""Auth service helpers for login/logout that set/clear session.
"""
import json
from typing import Dict
from client.services import api_client
from client.state import session

API_LOGIN = "/api/auth/login"
API_LOGOUT = "/api/auth/logout"


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