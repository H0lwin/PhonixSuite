# -*- coding: utf-8 -*-
"""Centralized client configuration loader.
Priority order for server base URL:
1) Environment variable SERVER_BASE_URL
2) client/config.json -> {"server_base_url": "http://host:port"}
3) Default: http://127.0.0.1:5000
"""
from __future__ import annotations
import os
import json
from typing import Optional

_DEFAULT_BASE = "http://127.0.0.1:5000"
_CONFIG_JSON_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "config.json"))


def _read_json_base(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        base = (data or {}).get("server_base_url")
        if isinstance(base, str) and base.strip():
            return base.strip()
    except Exception:
        pass
    return None


def get_base_url() -> str:
    # 1) Environment variable takes highest priority
    env = os.getenv("SERVER_BASE_URL")
    if env and env.strip():
        return env.strip().rstrip("/")

    # 2) config.json next to packaged executable (PyInstaller onefile/onefolder)
    try:
        import sys
        exe = getattr(sys, "executable", None)
        if exe:
            exe_json = _read_json_base(os.path.join(os.path.dirname(exe), "config.json"))
            if exe_json:
                return exe_json.rstrip("/")
        # 2b) config.json embedded inside one-file bundle (sys._MEIPASS)
        bundle_dir = getattr(sys, "_MEIPASS", None)
        if bundle_dir:
            bundle_json = _read_json_base(os.path.join(bundle_dir, "config.json"))
            if bundle_json:
                return bundle_json.rstrip("/")
    except Exception:
        pass

    # 3) client/config.json (development/source tree)
    json_base = _read_json_base(_CONFIG_JSON_PATH)
    if json_base:
        return json_base.rstrip("/")

    # 4) Default
    return _DEFAULT_BASE