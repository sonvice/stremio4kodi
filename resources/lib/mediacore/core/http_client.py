"""
MediaCore Outbound HTTP Client
Centralized network client with connection pooling, retries, and error handling.
"""

import json
import socket
import urllib.request
import urllib.error
import urllib.parse
from typing import Dict, Any, Optional, Tuple

DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
KODI_USER_AGENT = "Kodi/21.0 (Linux; Android) plugin.video.stremio4kodi"


class HttpClient:
    """Outbound HTTP requests manager with timeouts and consistent User-Agents."""

    def __init__(self, default_timeout: float = 8.0, user_agent: str = DEFAULT_USER_AGENT):
        self.default_timeout = default_timeout
        self.user_agent = user_agent

    def get_json(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> Optional[Any]:
        """Performs GET request and parses response as JSON."""
        data, status = self.get(url, params=params, headers=headers, timeout=timeout)
        if not data:
            return None
        try:
            return json.loads(data.decode("utf-8", errors="replace"))
        except Exception:
            return None

    def post_json(
        self,
        url: str,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> Optional[Any]:
        """Performs POST request with JSON body and parses response."""
        h = {"Content-Type": "application/json"}
        if headers:
            h.update(headers)
        body = json.dumps(payload).encode("utf-8")
        data, status = self.post(url, data=body, headers=h, timeout=timeout)
        if not data:
            return None
        try:
            return json.loads(data.decode("utf-8", errors="replace"))
        except Exception:
            return None

    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> Tuple[Optional[bytes], int]:
        """Performs raw GET request, returns (bytes, status_code)."""
        if params:
            query = urllib.parse.urlencode(params)
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}{query}"

        h = {"User-Agent": self.user_agent}
        if headers:
            h.update(headers)

        req = urllib.request.Request(url, headers=h, method="GET")
        t = timeout or self.default_timeout
        try:
            with urllib.request.urlopen(req, timeout=t) as resp:
                return resp.read(), resp.status
        except urllib.error.HTTPError as he:
            try:
                body = he.read()
            except Exception:
                body = None
            return body, he.code
        except Exception:
            return None, 0

    def post(
        self,
        url: str,
        data: Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> Tuple[Optional[bytes], int]:
        """Performs raw POST request, returns (bytes, status_code)."""
        h = {"User-Agent": self.user_agent}
        if headers:
            h.update(headers)

        req = urllib.request.Request(url, data=data, headers=h, method="POST")
        t = timeout or self.default_timeout
        try:
            with urllib.request.urlopen(req, timeout=t) as resp:
                return resp.read(), resp.status
        except urllib.error.HTTPError as he:
            try:
                body = he.read()
            except Exception:
                body = None
            return body, he.code
        except Exception:
            return None, 0

    @staticmethod
    def probe_socket(host: str, port: int, timeout: float = 0.8) -> bool:
        """Fast non-blocking socket health check (< 0.8s)."""
        try:
            with socket.create_connection((host, int(port)), timeout=timeout) as s:
                s.settimeout(timeout)
                return True
        except Exception:
            return False
