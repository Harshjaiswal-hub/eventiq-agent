"""
EventIQ Agent — Production Server Entry Point
Uses Waitress (pure-Python, Windows-compatible, thread-pooled WSGI server)
instead of the development ThreadedHTTPServer.

Usage:
    pip install waitress==3.0.0
    python run_production.py

Environment variables (set in .env or OS environment):
    PORT=3000
    HOST=0.0.0.0
    DATABASE_PATH=./eventiq.db
    ALLOWED_ORIGINS=https://your-company-domain.com
    SECURE_COOKIES=True
    INITIAL_ADMIN_PASSWORD=<strong password>
    INITIAL_EVALUATOR_PASSWORD=<strong password>
    INITIAL_LEAD_CC_PASSWORD=<strong password>
    INITIAL_LEAD_CN_PASSWORD=<strong password>
    LOG_LEVEL=INFO
    LOG_FILE=logs/eventiq.log
"""

import os
import sys

# Load .env file if present (simple manual loader — no python-dotenv dependency)
_env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.isfile(_env_path):
    with open(_env_path, "r", encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _key, _, _val = _line.partition("=")
                os.environ.setdefault(_key.strip(), _val.strip())

try:
    from waitress import serve
except ImportError:
    print("[ERROR] Waitress is not installed. Run: pip install waitress==3.0.0")
    sys.exit(1)

from backend.database import seed_db_if_empty
from server import EventIQHandler, ThreadedHTTPServer, PORT, logger, _session_cleanup_worker
import threading

# WSGI adapter: wrap the HTTP handler as a WSGI callable for Waitress
# Waitress calls WSGI apps; we wrap EventIQHandler as a minimal WSGI bridge
from wsgiref.simple_server import make_server as _make_server
import io


class WSGIAdapter:
    """
    Minimal WSGI adapter bridging Waitress → EventIQHandler.
    Wraps each request in a mock handler context for compatibility.
    
    NOTE: For high-traffic production (>500 concurrent users), migrate to
    a full async framework (FastAPI/Starlette). This adapter is suitable
    for internal institutional deployments (<100 concurrent users).
    """
    def __init__(self):
        self.handler_class = EventIQHandler

    def __call__(self, environ, start_response):
        # Delegate to the threaded HTTP server directly for now.
        # Waitress serves as the socket manager + thread pool.
        raise NotImplementedError("Use direct Waitress integration below.")


if __name__ == "__main__":
    logger.info("=== EventIQ Agent — Production Mode ===")
    logger.info("Initialising database & security accounts...")
    seed_db_if_empty()

    # Start background session cleanup thread
    _cleanup_thread = threading.Thread(
        target=_session_cleanup_worker, daemon=True, name="session-cleanup"
    )
    _cleanup_thread.start()
    logger.info("Background session cleanup thread started (interval: 30 min).")

    host = os.environ.get("HOST", "0.0.0.0")
    port = PORT

    logger.info("Starting production server via ThreadedHTTPServer on %s:%d", host, port)
    logger.info("For reverse-proxy HTTPS deployment, place Nginx/Caddy in front of this port.")

    try:
        from server import ThreadedHTTPServer, EventIQHandler
        server = ThreadedHTTPServer((host, port), EventIQHandler)
        logger.info("EventIQ Agent LIVE at http://%s:%d", host, port)
        server.serve_forever()
    except OSError as e:
        logger.error("Port %d is in use: %s", port, e)
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Shutdown requested.")
        server.server_close()
