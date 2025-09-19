# -*- coding: utf-8 -*-
import os


class Config:
    # Default to production-safe: DEBUG off unless explicitly enabled
    DEBUG = os.getenv("DEBUG", os.getenv("FLASK_DEBUG", "0")).lower() in ("1", "true", "yes", "on")
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "5000"))

    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "1234")
    DB_NAME = os.getenv("DB_NAME", "myapp")


