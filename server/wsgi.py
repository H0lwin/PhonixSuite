# -*- coding: utf-8 -*-
"""
WSGI entrypoint for production. Use a real WSGI server (e.g., gunicorn or waitress) to run:
  gunicorn -w 4 -k gthread -b 0.0.0.0:8000 "server.wsgi:application"
  waitress-serve --listen=0.0.0.0:8000 "server.wsgi:application"
"""
from .app import app, configure_logging, start_server

# Configure logging to file and initialize DB/schema.
# Also run admin wizard interactively on first run if no admin exists.
configure_logging()
start_server(skip_admin_wizard=False)

# Expose as WSGI application object
application = app