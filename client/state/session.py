# -*- coding: utf-8 -*-
"""Simple in-memory session store for the desktop client.
Holds the current auth token and role.
"""
from typing import Optional

_token: Optional[str] = None
_role: Optional[str] = None
_display_name: Optional[str] = None


def set_session(token: str, role: str, display_name: str) -> None:
    global _token, _role, _display_name
    _token = token or ""
    _role = role or "user"
    _display_name = display_name or ""


def clear_session() -> None:
    global _token, _role, _display_name
    _token = None
    _role = None
    _display_name = None


def get_token() -> Optional[str]:
    return _token


def get_role() -> Optional[str]:
    return _role


def get_display_name() -> Optional[str]:
    return _display_name