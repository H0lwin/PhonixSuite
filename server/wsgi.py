# -*- coding: utf-8 -*-
"""
WSGI entrypoint for production. Use a real WSGI server (e.g., gunicorn or waitress) to run:
  gunicorn -w 4 -k gthread -b 0.0.0.0:8000 "server.wsgi:application"
  waitress-serve --listen=0.0.0.0:8000 "server.wsgi:application"
"""
import os
import sys

# Ensure local module imports like `database` work even when imported as a package
sys.path.insert(0, os.path.dirname(__file__))

# Force non-interactive admin provisioning under WSGI
os.environ.setdefault("ADMIN_WIZARD_MODE", "noninteractive")

try:
    # Prefer package-relative import if available
    from .app import app, configure_logging, start_server
except Exception:
    # Fallback to top-level import if run without package context
    from app import app, configure_logging, start_server

# Configure logging to file and initialize DB/schema.
configure_logging()
# Run admin bootstrap in non-interactive mode on first start
start_server(skip_admin_wizard=False)

# Expose as WSGI application object
application = app