# -*- coding: utf-8 -*-
"""
Real-Debrid — Resolve torrent hashes to direct HTTP download links.
v4: Universal HTTP (requests + curl fallback) for Android TV compatibility.
"""
import json
from resources.lib.config import Config
from resources.lib.logger import log

# Suppress SSL warnings
try:
    import requests as _requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    _requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except ImportError:
    _requests = None

RD_API = "https://api.real-debrid.com/rest/1.0"


class RealDebrid:
    def __init__(self):
        self.api_key = Config.rd_apikey()

    def is_configured(self):
        return Config.rd_enabled() and bool(self.api_key)

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "Stremio4Kodi/2.4",
        }

    # ── HTTP GET ──────────────────────────────────────────
    def _get(self, url, timeout=10):
        data = self._get_requests(url, timeout)
        if data is not None:
            return data
        return self._get_curl(url, timeout)

    def _get_requests(self, url, timeout):
        if not _requests:
            return None
        try:
            resp = _requests.get(url, headers=self._headers(),
                                 timeout=(timeout, timeout + 5), verify=False)
            resp.raise_for_status()
            text = resp.text.strip()
            return json.loads(text) if text else None
        except Exception as e:
            log(f"RD requests GET error: {e}", level="debug")
            return None

    def _get_curl(self, url, timeout=10):
        try:
            import subprocess
            result = subprocess.run(
                ["curl", "-skL", "--connect-timeout", str(timeout),
                 "--max-time", str(timeout + 5),
                 "-H", f"Authorization: Bearer {self.api_key}",
                 "-H", "User-Agent: Stremio4Kodi/2.4",
                 url],
                capture_output=True, text=True, timeout=timeout + 10,
            )
            text = result.stdout.strip()
            return json.loads(text) if text else None
        except FileNotFoundError:
            log("curl not found (Android TV?)", level="debug")
        except Exception as e:
            log(f"RD curl GET error: {e}", level="debug")
        return None

    # ── HTTP POST ─────────────────────────────────────────
    def _post(self, url, data, timeout=10):
        result = self._post_requests(url, data, timeout)
        if result is not None:
            return result
        return self._post_curl(url, data, timeout)

    def _post_requests(self, url, data, timeout):
        if not _requests:
            return None
        try:
            resp = _requests.post(url, headers=self._headers(), data=data,
                                  timeout=(timeout, timeout + 5), verify=False)
            resp.raise_for_status()
            text = resp.text.strip()
            return json.loads(text) if text else None
        except Exception as e:
            log(f"RD requests POST error: {e}", level="debug")
            return None

    def _post_curl(self, url, data, timeout=10):
        try:
            import subprocess
            cmd = ["curl", "-skL", "--connect-timeout", str(timeout),
                   "--max-time", str(timeout + 5),
                   "-X", "POST",
                   "-H", f"Authorization: Bearer {self.api_key}",
                   "-H", "User-Agent: Stremio4Kodi/2.4"]
            for key, val in data.items():
                cmd += ["--data-urlencode", f"{key}={val}"]
            cmd.append(url)
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout + 10,
            )
            text = result.stdout.strip()
            return json.loads(text) if text else None
        except FileNotFoundError:
            log("curl not found (Android TV?)", level="debug")
        except Exception as e:
            log(f"RD curl POST error: {e}", level="debug")
        return None

    def resolve(self, magnet_or_hash, file_idx=None):
        """Add torrent to RD and get direct download link."""
        if not self.is_configured():
            return None
        try:
            if not magnet_or_hash.startswith("magnet:"):
                magnet_or_hash = f"magnet:?xt=urn:btih:{magnet_or_hash}"

            log(f"RD addMagnet: {magnet_or_hash[:80]}", level="info")
            resp = self._post(
                f"{RD_API}/torrents/addMagnet",
                {"magnet": magnet_or_hash},
            )
            if not resp:
                log("RD addMagnet: empty response", level="error")
                return None
            if "error" in resp:
                log(f"RD addMagnet error: {resp}", level="error")
                return None

            torrent_id = resp.get("id")
            if not torrent_id:
                log(f"RD no torrent ID: {resp}", level="error")
                return None

            info = self._get(f"{RD_API}/torrents/info/{torrent_id}")
            if not info:
                return None

            # Select files
            files = info.get("files", [])
            if file_idx is not None and file_idx < len(files):
                file_ids = str(files[file_idx]["id"])
            else:
                video_exts = (".mkv", ".mp4", ".avi", ".mov", ".wmv")
                video_files = [
                    f for f in files
                    if any(f.get("path", "").lower().endswith(e) for e in video_exts)
                ]
                if video_files:
                    biggest = max(video_files, key=lambda f: f.get("bytes", 0))
                    file_ids = str(biggest["id"])
                else:
                    file_ids = "all"

            log(f"RD selectFiles: {file_ids}", level="info")
            self._post(
                f"{RD_API}/torrents/selectFiles/{torrent_id}",
                {"files": file_ids},
            )

            # Get links
            info = self._get(f"{RD_API}/torrents/info/{torrent_id}")
            if not info:
                return None

            status = info.get("status", "")
            log(f"RD torrent status: {status}", level="info")

            links = info.get("links", [])
            if not links:
                log("RD: No links (torrent may not be cached)", level="warning")
                return None

            # Unrestrict
            resp = self._post(
                f"{RD_API}/unrestrict/link",
                {"link": links[0]},
            )
            if not resp:
                return None

            download_url = resp.get("download")
            if download_url:
                log(f"RD OK: {download_url[:80]}...", level="info")
            return download_url

        except Exception as e:
            log(f"RD resolve error: {e}", level="error")
            return None

    def check_cache(self, hashes):
        if not self.is_configured() or not hashes:
            return set()
        try:
            cached = set()
            # Small batches of 10 to avoid URL length limits
            for i in range(0, len(hashes), 10):
                batch = hashes[i:i+10]
                url = f"{RD_API}/torrents/instantAvailability/" + "/".join(batch)
                data = self._get(url, timeout=8)
                if not data or not isinstance(data, dict):
                    continue
                for h, info in data.items():
                    if isinstance(info, dict) and info.get("rd"):
                        cached.add(h.lower())
                    elif isinstance(info, list) and len(info) > 0:
                        cached.add(h.lower())
            log(f"RD cache check: {len(cached)}/{len(hashes)} cached", level="info")
            return cached
        except Exception as e:
            log(f"RD cache check error: {e}", level="error")
            return set()

    def tag_cached_streams(self, streams):
        if not self.is_configured():
            return streams
        hashes = []
        for s in streams:
            h = s.get("infoHash", "").lower()
            if h:
                hashes.append(h)
        cached = self.check_cache(hashes)
        for s in streams:
            h = s.get("infoHash", "").lower()
            s["_rd_cached"] = h in cached
        return streams
