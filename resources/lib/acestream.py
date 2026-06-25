# -*- coding: utf-8 -*-
"""
AceStream — Fetch, parse and play AceStream channels.
Supports JSON (hashes.json) and M3U (hashes_acestream.m3u) sources.
Playback via: Plexus, Horus, AceStream app (Android), or direct acestream://.
"""
import re
import json as jsonlib
from collections import OrderedDict

from resources.lib.config import Config
from resources.lib.cache import CacheDB
from resources.lib.logger import log

# Suppress SSL warnings
try:
    import requests as _requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    _requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except ImportError:
    _requests = None


class AceStreamClient:
    def __init__(self):
        self.cache = CacheDB()

    # ══════════════════════════════════════════════════════
    #  HTTP — same dual-method as StremioClient
    # ══════════════════════════════════════════════════════
    def _get_raw(self, url, timeout=15):
        """HTTP GET returning raw text (not JSON)."""
        text = self._get_raw_requests(url, timeout)
        if text is not None:
            return text
        text = self._get_raw_curl(url, timeout)
        if text is not None:
            return text
        return None

    def _get_raw_requests(self, url, timeout):
        if not _requests:
            return None
        try:
            resp = _requests.get(
                url,
                headers={"User-Agent": "Stremio4Kodi/3.2"},
                timeout=(timeout, timeout + 10),
                verify=False,
            )
            resp.raise_for_status()
            return resp.text
        except ImportError:
            pass
        except Exception as e:
            log(f"AceStream requests error [{url[:80]}]: {e}", level="debug")
        return None

    def _get_raw_curl(self, url, timeout):
        try:
            import subprocess
            result = subprocess.run(
                ["curl", "-skL", "--connect-timeout", str(timeout),
                 "--max-time", str(timeout + 10),
                 "-H", "User-Agent: Stremio4Kodi/3.2",
                 url],
                capture_output=True, text=True, timeout=timeout + 15,
            )
            return result.stdout if result.stdout else None
        except FileNotFoundError:
            log("curl not found", level="debug")
        except Exception as e:
            log(f"AceStream curl error [{url[:80]}]: {e}", level="debug")
        return None

    # ══════════════════════════════════════════════════════
    #  FETCH & PARSE — JSON or M3U
    # ══════════════════════════════════════════════════════
    def fetch_channels(self, force_refresh=False):
        """Fetch channels from configured AceStream URLs.
        Returns list of dicts: {title, hash, group, logo, tvg_id}
        Uses JSON endpoint as primary, M3U as fallback.
        """
        cache_key = "acestream:channels"
        if not force_refresh:
            cached = self.cache.get(cache_key)
            if cached:
                return cached

        urls = Config.acestream_urls()
        if not urls:
            log("No AceStream URLs configured", level="warning")
            return []

        from concurrent.futures import ThreadPoolExecutor, as_completed

        def _fetch_one(url):
            try:
                raw = self._get_raw(url)
                if not raw:
                    log(f"AceStream: empty response from {url[:80]}", level="warning")
                    return []

                raw = raw.strip()
                if raw.startswith("{") or raw.startswith("["):
                    # JSON format
                    parsed = self._parse_json(raw)
                elif raw.startswith("#EXTM3U"):
                    # M3U format
                    parsed = self._parse_m3u(raw)
                else:
                    log(f"AceStream: unknown format from {url[:80]}", level="warning")
                    return []

                if parsed:
                    log(f"AceStream: loaded {len(parsed)} channels from {url[:60]}", level="info")
                    return parsed
            except Exception as e:
                log(f"AceStream fetch error [{url[:60]}]: {e}", level="error")
            return []

        channels = []
        with ThreadPoolExecutor(max_workers=min(5, len(urls))) as executor:
            futures = {executor.submit(_fetch_one, url): url for url in urls}
            for future in as_completed(futures):
                url = futures[future]
                try:
                    res = future.result()
                    channels.extend(res)
                except Exception as e:
                    log(f"Error executing fetch for {url}: {e}", level="error")

        # Dedup by hash
        seen = set()
        unique = []
        for ch in channels:
            h = ch.get("hash", "")
            if h and h not in seen:
                seen.add(h)
                unique.append(ch)

        # Cache for configured TTL (default 30 minutes for live content)
        if unique:
            self.cache.set(cache_key, unique, ttl=Config.acestream_cache_ttl())

        return unique

    def _parse_json(self, raw):
        """Parse hashes.json format."""
        try:
            data = jsonlib.loads(raw)
            hashes = data.get("hashes", []) if isinstance(data, dict) else data
            channels = []
            for item in hashes:
                if not isinstance(item, dict):
                    continue
                h = item.get("hash", "").strip()
                if not h:
                    continue
                channels.append({
                    "title": item.get("title", "Canal desconocido"),
                    "hash": h,
                    "group": item.get("group", "Otros"),
                    "logo": item.get("logo", ""),
                    "tvg_id": item.get("tvg_id", ""),
                })
            return channels
        except Exception as e:
            log(f"AceStream JSON parse error: {e}", level="error")
            return []

    def _parse_m3u(self, raw):
        """Parse M3U format with acestream:// URLs."""
        channels = []
        lines = raw.split("\n")
        current_info = {}

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith("#EXTINF:"):
                # Parse: #EXTINF:-1 tvg-id="..." tvg-logo="..." group-title="...",Title
                current_info = {}

                # Extract tvg-id
                tvg_match = re.search(r'tvg-id="([^"]*)"', line)
                if tvg_match:
                    current_info["tvg_id"] = tvg_match.group(1)

                # Extract logo
                logo_match = re.search(r'tvg-logo="([^"]*)"', line)
                if logo_match:
                    current_info["logo"] = logo_match.group(1)

                # Extract group
                group_match = re.search(r'group-title="([^"]*)"', line)
                if group_match:
                    current_info["group"] = group_match.group(1)

                # Extract title (after last comma)
                comma_pos = line.rfind(",")
                if comma_pos >= 0:
                    current_info["title"] = line[comma_pos + 1:].strip()

            elif line.startswith("acestream://"):
                # Extract hash
                ace_hash = line.replace("acestream://", "").strip()
                if ace_hash and current_info:
                    channels.append({
                        "title": current_info.get("title", "Canal"),
                        "hash": ace_hash,
                        "group": current_info.get("group", "Otros"),
                        "logo": current_info.get("logo", ""),
                        "tvg_id": current_info.get("tvg_id", ""),
                    })
                current_info = {}

        return channels

    # ══════════════════════════════════════════════════════
    #  GROUPS — Organize channels by category
    # ══════════════════════════════════════════════════════
    def get_groups(self, channels=None):
        """Get ordered list of unique groups from channels."""
        if channels is None:
            channels = self.fetch_channels()
        groups = OrderedDict()
        for ch in channels:
            g = ch.get("group", "Otros")
            if g not in groups:
                groups[g] = {
                    "name": g,
                    "count": 0,
                    "logo": "",
                }
            groups[g]["count"] += 1
            # Use first logo found for the group
            if not groups[g]["logo"] and ch.get("logo"):
                groups[g]["logo"] = ch["logo"]
        return list(groups.values())

    def get_channels_by_group(self, group_name, channels=None):
        """Get channels filtered by group name."""
        if channels is None:
            channels = self.fetch_channels()
        return [ch for ch in channels if ch.get("group", "Otros") == group_name]

    # ══════════════════════════════════════════════════════
    #  PLAYBACK — Build playable URL for AceStream hash
    # ══════════════════════════════════════════════════════
    @staticmethod
    def build_play_url(ace_hash, title=""):
        """Build a playable URL for the given AceStream hash.
        Uses the configured engine (Plexus, Horus, AceStream app, etc.)
        """
        engine = Config.acestream_engine()
        log(f"AceStream play: engine={engine}, hash={ace_hash[:20]}..., title={title}", level="info")

        from urllib.parse import quote

        if engine == "Plexus":
            # p2p-streams / Plexus
            return (f"plugin://program.plexus/"
                    f"?mode=1&name={quote(title, safe='')}&url={ace_hash}")

        elif engine == "Horus":
            # Horus acestream addon
            return (f"plugin://script.module.horus/"
                    f"?action=play&infohash={ace_hash}")

        elif engine == "AceStream":
            # AceStream Engine direct (requires acestream:// handler)
            return f"acestream://{ace_hash}"

        elif engine == "AceWeb":
            # AceStream HTTP API (local engine running on port)
            port = Config.acestream_engine_port()
            return (f"http://127.0.0.1:{port}/ace/getstream"
                    f"?id={ace_hash}")

        elif engine == "Elementum":
            # Some people run acestream through Elementum
            return (f"plugin://plugin.video.elementum/"
                    f"?action=play&infohash={ace_hash}")

        else:
            # Default: try acestream:// protocol
            return f"acestream://{ace_hash}"

    @staticmethod
    def get_acestream_info():
        """Return info string about the current AceStream timestamp from cache."""
        try:
            cache = CacheDB()
            channels = cache.get("acestream:channels")
            if channels:
                count = len(channels)
                return f"{count} canales cargados"
        except Exception:
            pass
        return "No cargado"
