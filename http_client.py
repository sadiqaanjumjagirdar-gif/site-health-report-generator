 #http_client.py
import os
import requests


def get_session() -> requests.Session:
    """
    Create a requests Session with optional proxy behavior.

    - If DISABLE_PROXY=1, ignore proxy-related environment variables.
    - Otherwise, requests will honor HTTP_PROXY/HTTPS_PROXY (if set).

    This makes the app work both on corporate networks (proxy required)
    and on public hosts like Render (no corporate proxy DNS).
    """
    s = requests.Session()

    # Most reliable way to ignore env proxies in requests
    if os.getenv("DISABLE_PROXY", "0") == "1":
        s.trust_env = False

    return s