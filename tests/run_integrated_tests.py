"""
Integrated Server and Test Runner
Spawns ThreadedHTTPServer on an ephemeral port (3099), runs verify_endpoints,
and cleanly shuts down the server.
"""

import threading
import time
import os
import sys
import urllib.request

# Ensure root in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import server
from tests import verify_endpoints

def run_test_suite():
    port = 3099
    server.PORT = port
    server.seed_db_if_empty()
    httpd = server.ThreadedHTTPServer(('127.0.0.1', port), server.EventIQHandler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    print(f"[+] Ephemeral test server active on port {port}")
    time.sleep(0.5)

    # Configure verify_endpoints to target test port
    verify_endpoints.PORT = port
    verify_endpoints.BASE_URL = f"http://127.0.0.1:{port}"

    try:
        verify_endpoints.run_checks()
        print("[+] All API endpoints verified end-to-end!")
    finally:
        httpd.shutdown()
        server_thread.join(timeout=2)
        print("[+] Ephemeral test server cleanly shut down.")

if __name__ == "__main__":
    run_test_suite()
