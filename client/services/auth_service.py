# -*- coding: utf-8 -*-
"""Auth service helpers for login/logout that set/clear session.
"""
import json
from typing import Dict
import requests
from client.services import api_client
from client.state import session

API_LOGIN = "/api/auth/login"
API_LOGOUT = "/api/auth/logout"


def login(national_id: str, password: str) -> Dict:
    try:
        resp = api_client.post_json(API_LOGIN, {"national_id": national_id, "password": password})
    except requests.Timeout:
        return {"status": "error", "message": "Timeout connecting to server. Please try again."}
    except requests.ConnectionError:
        return {"status": "error", "message": "Cannot connect to server. Check your network or server address."}
    except requests.RequestException as e:
        return {"status": "error", "message": f"Network error: {str(e)}"}

    data = api_client.parse_json(resp)

    # Normalize common HTTP errors to user-friendly messages
    if resp.status_code == 401 and data.get("status") != "success":
        return {"status": "error", "message": "Invalid national ID or password."}
    if resp.status_code == 403 and data.get("status") != "success":
        return {"status": "error", "message": "Access denied. Contact administrator."}
    if resp.status_code >= 500 and data.get("status") != "success":
        return {"status": "error", "message": "Server error. Please try again later."}

    if data.get("status") == "success":
        session.set_session(data.get("token"), data.get("role"), data.get("display_name"))
        return data

    # Fallback generic error message
    return {"status": "error", "message": data.get("message") or f"HTTP {resp.status_code}"}


def logout() -> None:
    try:
        api_client.post_json(API_LOGOUT, {})
    finally:
        session.clear_session()