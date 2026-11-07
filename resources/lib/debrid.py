# -*- coding: utf-8 -*-
"""
Multi-Debrid Manager — Universal Debrid client for Stremio for Kodi.
Supports:
  1. Real-Debrid (RD)
  2. AllDebrid (AD)
  3. Premiumize (PM)
  4. TorBox (TB)
  5. Debrid-Link (DL)
Universal HTTP (requests + urllib + curl fallback) for Android TV compatibility.
"""
import json
import urllib.request
import urllib.parse
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed

from resources.lib.config import Config
from resources.lib.logger import log

try:
    import requests as _requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    _requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except ImportError:
    _requests = None


class BaseDebridClient:
    NAME = "BaseDebrid"
    BADGE = "DB"

    def is_configured(self):
        return False

    def _headers(self):
        return {
            "User-Agent": "Stremio4Kodi/3.3",
            "Accept": "application/json"
        }

    def _get(self, url, headers=None, timeout=8):
        h = headers if headers is not None else self._headers()
        # 1. requests
        if _requests:
            try:
                resp = _requests.get(url, headers=h, timeout=(timeout, timeout + 4), verify=False)
                resp.raise_for_status()
                text = resp.text.strip()
                return json.loads(text) if text else None
            except Exception as e:
                log(f"{self.NAME} requests GET error: {e}", level="debug")

        # 2. urllib
        try:
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                text = resp.read().decode("utf-8", errors="ignore").strip()
                return json.loads(text) if text else None
        except Exception as e:
            log(f"{self.NAME} urllib GET error: {e}", level="debug")

        # 3. curl fallback
        try:
            import subprocess
            cmd = ["curl", "-skL", "--connect-timeout", str(timeout), "--max-time", str(timeout + 5)]
            for k, v in h.items():
                cmd += ["-H", f"{k}: {v}"]
            cmd.append(url)
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 8)
            text = res.stdout.strip()
            return json.loads(text) if text else None
        except Exception as e:
            log(f"{self.NAME} curl GET error: {e}", level="debug")

        return None

    def _post(self, url, data=None, json_data=None, headers=None, timeout=8):
        h = headers if headers is not None else dict(self._headers())
        # 1. requests
        if _requests:
            try:
                if json_data is not None:
                    resp = _requests.post(url, headers=h, json=json_data, timeout=(timeout, timeout + 4), verify=False)
                else:
                    resp = _requests.post(url, headers=h, data=data, timeout=(timeout, timeout + 4), verify=False)
                resp.raise_for_status()
                text = resp.text.strip()
                return json.loads(text) if text else None
            except Exception as e:
                log(f"{self.NAME} requests POST error: {e}", level="debug")

        # 2. urllib
        try:
            if json_data is not None:
                encoded = json.dumps(json_data).encode("utf-8")
                h["Content-Type"] = "application/json"
            elif data is not None:
                encoded = urllib.parse.urlencode(data).encode("utf-8")
                h["Content-Type"] = "application/x-www-form-urlencoded"
            else:
                encoded = b""
            req = urllib.request.Request(url, data=encoded, headers=h)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                text = resp.read().decode("utf-8", errors="ignore").strip()
                return json.loads(text) if text else None
        except Exception as e:
            log(f"{self.NAME} urllib POST error: {e}", level="debug")

        # 3. curl fallback
        try:
            import subprocess
            cmd = ["curl", "-skL", "--connect-timeout", str(timeout), "--max-time", str(timeout + 5), "-X", "POST"]
            for k, v in h.items():
                cmd += ["-H", f"{k}: {v}"]
            if json_data is not None:
                cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(json_data)]
            elif data:
                for k, v in data.items():
                    cmd += ["--data-urlencode", f"{k}={v}"]
            cmd.append(url)
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 8)
            text = res.stdout.strip()
            return json.loads(text) if text else None
        except Exception as e:
            log(f"{self.NAME} curl POST error: {e}", level="debug")

        return None


# ══════════════════════════════════════════════════════════
#  1. Real-Debrid Client
# ══════════════════════════════════════════════════════════
class RealDebridClient(BaseDebridClient):
    NAME = "Real-Debrid"
    BADGE = "RD"
    API = "https://api.real-debrid.com/rest/1.0"

    def is_configured(self):
        return Config.rd_enabled() and bool(Config.rd_apikey())

    def _headers(self):
        return {
            "Authorization": f"Bearer {Config.rd_apikey()}",
            "User-Agent": "Stremio4Kodi/3.3",
        }

    def check_cache(self, hashes):
        if not self.is_configured() or not hashes:
            return set()
        cached = set()
        try:
            for i in range(0, len(hashes), 10):
                batch = hashes[i:i+10]
                url = f"{self.API}/torrents/instantAvailability/" + "/".join(batch)
                data = self._get(url, timeout=6)
                if not data or not isinstance(data, dict):
                    continue
                for h, info in data.items():
                    if isinstance(info, dict) and info.get("rd"):
                        cached.add(h.lower())
                    elif isinstance(info, list) and len(info) > 0:
                        cached.add(h.lower())
        except Exception as e:
            log(f"RD check_cache error: {e}", level="debug")
        return cached

    def resolve(self, magnet_or_hash, file_idx=None):
        if not self.is_configured():
            return None
        try:
            if not magnet_or_hash.startswith("magnet:"):
                magnet_or_hash = f"magnet:?xt=urn:btih:{magnet_or_hash}"

            resp = self._post(f"{self.API}/torrents/addMagnet", {"magnet": magnet_or_hash})
            if not resp or "id" not in resp:
                return None
            torrent_id = resp["id"]

            info = self._get(f"{self.API}/torrents/info/{torrent_id}")
            if not info:
                return None

            files = info.get("files", [])
            if file_idx is not None and isinstance(file_idx, int) and file_idx < len(files):
                file_ids = str(files[file_idx]["id"])
            else:
                video_exts = (".mkv", ".mp4", ".avi", ".mov", ".wmv", ".ts")
                video_files = [f for f in files if any(f.get("path", "").lower().endswith(e) for e in video_exts)]
                if video_files:
                    biggest = max(video_files, key=lambda f: f.get("bytes", 0))
                    file_ids = str(biggest["id"])
                else:
                    file_ids = "all"

            self._post(f"{self.API}/torrents/selectFiles/{torrent_id}", {"files": file_ids})
            info = self._get(f"{self.API}/torrents/info/{torrent_id}")
            if not info or not info.get("links"):
                return None

            unrestrict = self._post(f"{self.API}/unrestrict/link", {"link": info["links"][0]})
            if unrestrict and unrestrict.get("download"):
                return unrestrict["download"]
        except Exception as e:
            log(f"RD resolve error: {e}", level="warning")
        return None


# ══════════════════════════════════════════════════════════
#  2. AllDebrid Client
# ══════════════════════════════════════════════════════════
class AllDebridClient(BaseDebridClient):
    NAME = "AllDebrid"
    BADGE = "AD"
    API = "https://api.alldebrid.com/v4"

    def is_configured(self):
        return Config.alldebrid_enabled() and bool(Config.alldebrid_apikey())

    def check_cache(self, hashes):
        if not self.is_configured() or not hashes:
            return set()
        cached = set()
        key = Config.alldebrid_apikey()
        try:
            for i in range(0, len(hashes), 20):
                batch = hashes[i:i+20]
                q_params = "&".join([f"magnets[]={h}" for h in batch])
                url = f"{self.API}/magnet/instant?agent=stremio4kodi&apikey={key}&{q_params}"
                data = self._get(url, timeout=6)
                if data and data.get("status") == "success":
                    m_list = data.get("data", {}).get("magnets", [])
                    for m in m_list:
                        if m.get("instant"):
                            cached.add(m.get("magnet", "").lower())
        except Exception as e:
            log(f"AllDebrid check_cache error: {e}", level="debug")
        return cached

    def resolve(self, magnet_or_hash, file_idx=None):
        if not self.is_configured():
            return None
        key = Config.alldebrid_apikey()
        try:
            if not magnet_or_hash.startswith("magnet:"):
                magnet_or_hash = f"magnet:?xt=urn:btih:{magnet_or_hash}"

            url = f"{self.API}/magnet/upload?agent=stremio4kodi&apikey={key}&magnet={quote(magnet_or_hash)}"
            resp = self._get(url)
            if not resp or resp.get("status") != "success":
                return None

            magnets = resp.get("data", {}).get("magnets", [])
            if not magnets or not magnets[0].get("ready"):
                return None

            links = magnets[0].get("links", [])
            if not links:
                return None

            # Pick target file
            chosen_link = links[0].get("link")
            if file_idx is not None and isinstance(file_idx, int) and file_idx < len(links):
                chosen_link = links[file_idx].get("link")
            else:
                video_exts = (".mkv", ".mp4", ".avi", ".ts")
                v_links = [l for l in links if any(l.get("filename", "").lower().endswith(e) for e in video_exts)]
                if v_links:
                    chosen_link = max(v_links, key=lambda x: x.get("size", 0)).get("link")

            if not chosen_link:
                return None

            unlock_url = f"{self.API}/link/unlock?agent=stremio4kodi&apikey={key}&link={quote(chosen_link)}"
            unlock_resp = self._get(unlock_url)
            if unlock_resp and unlock_resp.get("status") == "success":
                return unlock_resp.get("data", {}).get("link")
        except Exception as e:
            log(f"AllDebrid resolve error: {e}", level="warning")
        return None


# ══════════════════════════════════════════════════════════
#  3. Premiumize Client
# ══════════════════════════════════════════════════════════
class PremiumizeClient(BaseDebridClient):
    NAME = "Premiumize"
    BADGE = "PM"
    API = "https://www.premiumize.me/api"

    def is_configured(self):
        return Config.premiumize_enabled() and bool(Config.premiumize_apikey())

    def check_cache(self, hashes):
        if not self.is_configured() or not hashes:
            return set()
        cached = set()
        key = Config.premiumize_apikey()
        try:
            for i in range(0, len(hashes), 20):
                batch = hashes[i:i+20]
                q_params = "&".join([f"items[]={h}" for h in batch])
                url = f"{self.API}/cache/check?apikey={key}&{q_params}"
                data = self._get(url, timeout=6)
                if data and data.get("status") == "success":
                    responses = data.get("response", [])
                    for idx, is_c in enumerate(responses):
                        if is_c and idx < len(batch):
                            cached.add(batch[idx].lower())
        except Exception as e:
            log(f"Premiumize check_cache error: {e}", level="debug")
        return cached

    def resolve(self, magnet_or_hash, file_idx=None):
        if not self.is_configured():
            return None
        key = Config.premiumize_apikey()
        try:
            if not magnet_or_hash.startswith("magnet:"):
                magnet_or_hash = f"magnet:?xt=urn:btih:{magnet_or_hash}"

            url = f"{self.API}/transfer/directdl"
            resp = self._post(url, data={"src": magnet_or_hash, "apikey": key})
            if not resp or resp.get("status") != "success":
                return None

            content = resp.get("content", [])
            if content:
                if file_idx is not None and isinstance(file_idx, int) and file_idx < len(content):
                    return content[file_idx].get("link")
                video_files = [f for f in content if any(f.get("path", "").lower().endswith(e) for e in (".mkv", ".mp4", ".avi", ".ts"))]
                if video_files:
                    return max(video_files, key=lambda x: x.get("size", 0)).get("link")
                return content[0].get("link")

            if resp.get("location"):
                return resp["location"]
        except Exception as e:
            log(f"Premiumize resolve error: {e}", level="warning")
        return None


# ══════════════════════════════════════════════════════════
#  4. TorBox Client
# ══════════════════════════════════════════════════════════
class TorBoxClient(BaseDebridClient):
    NAME = "TorBox"
    BADGE = "TB"
    API = "https://api.torbox.app/v1/api"

    def is_configured(self):
        return Config.torbox_enabled() and bool(Config.torbox_apikey())

    def _headers(self):
        return {
            "Authorization": f"Bearer {Config.torbox_apikey()}",
            "User-Agent": "Stremio4Kodi/3.3",
        }

    def check_cache(self, hashes):
        if not self.is_configured() or not hashes:
            return set()
        cached = set()
        try:
            for i in range(0, len(hashes), 25):
                batch = hashes[i:i+25]
                url = f"{self.API}/torrents/checkcached?hash={','.join(batch)}&format=list"
                data = self._get(url, timeout=6)
                if data and data.get("success"):
                    for item in data.get("data", []):
                        if isinstance(item, dict) and "hash" in item:
                            cached.add(item["hash"].lower())
                        elif isinstance(item, str):
                            cached.add(item.lower())
        except Exception as e:
            log(f"TorBox check_cache error: {e}", level="debug")
        return cached

    def resolve(self, magnet_or_hash, file_idx=None):
        if not self.is_configured():
            return None
        key = Config.torbox_apikey()
        try:
            if not magnet_or_hash.startswith("magnet:"):
                magnet_or_hash = f"magnet:?xt=urn:btih:{magnet_or_hash}"

            add_resp = self._post(f"{self.API}/torrents/createtorrent", data={"magnet": magnet_or_hash, "seed": 1, "allow_zip": False})
            if not add_resp or not add_resp.get("success"):
                return None

            torrent_id = add_resp.get("data", {}).get("torrent_id")
            if not torrent_id:
                return None

            fid = str(file_idx) if file_idx is not None else "0"
            dl_url = f"{self.API}/torrents/requestdl?token={key}&torrent_id={torrent_id}&file_id={fid}"
            dl_resp = self._get(dl_url)
            if dl_resp and dl_resp.get("success") and dl_resp.get("data"):
                return dl_resp["data"]
        except Exception as e:
            log(f"TorBox resolve error: {e}", level="warning")
        return None


# ══════════════════════════════════════════════════════════
#  5. Debrid-Link Client
# ══════════════════════════════════════════════════════════
class DebridLinkClient(BaseDebridClient):
    NAME = "Debrid-Link"
    BADGE = "DL"
    API = "https://debrid-link.com/api/v2"

    def is_configured(self):
        return Config.debridlink_enabled() and bool(Config.debridlink_apikey())

    def _headers(self):
        return {
            "Authorization": f"Bearer {Config.debridlink_apikey()}",
            "User-Agent": "Stremio4Kodi/3.3",
        }

    def check_cache(self, hashes):
        if not self.is_configured() or not hashes:
            return set()
        cached = set()
        try:
            for i in range(0, len(hashes), 20):
                batch = hashes[i:i+20]
                url = f"{self.API}/seedbox/cached?url={','.join(batch)}"
                data = self._get(url, timeout=6)
                if data and data.get("success"):
                    val = data.get("value", {})
                    for h in val.keys():
                        cached.add(h.lower())
        except Exception as e:
            log(f"Debrid-Link check_cache error: {e}", level="debug")
        return cached

    def resolve(self, magnet_or_hash, file_idx=None):
        if not self.is_configured():
            return None
        try:
            if not magnet_or_hash.startswith("magnet:"):
                magnet_or_hash = f"magnet:?xt=urn:btih:{magnet_or_hash}"

            resp = self._post(f"{self.API}/seedbox/add", data={"url": magnet_or_hash, "async": True})
            if not resp or not resp.get("success"):
                return None

            val = resp.get("value", {})
            if val.get("downloadUrl"):
                return val["downloadUrl"]
            files = val.get("files", [])
            if files:
                v_files = [f for f in files if any(f.get("name", "").lower().endswith(e) for e in (".mkv", ".mp4", ".avi", ".ts"))]
                if v_files and v_files[0].get("downloadUrl"):
                    return v_files[0]["downloadUrl"]
        except Exception as e:
            log(f"Debrid-Link resolve error: {e}", level="warning")
        return None


# ══════════════════════════════════════════════════════════
#  Unified Debrid Manager (Backwards-Compatible with RealDebrid)
# ══════════════════════════════════════════════════════════
class DebridManager:
    """
    Unified manager coordinating all configured Debrid providers.
    Directly compatible with calls to RealDebrid across the plugin.
    """
    def __init__(self):
        self.clients = [
            RealDebridClient(),
            AllDebridClient(),
            PremiumizeClient(),
            TorBoxClient(),
            DebridLinkClient(),
        ]

    def get_active_clients(self):
        return [c for c in self.clients if c.is_configured()]

    def is_configured(self):
        return any(c.is_configured() for c in self.clients)

    def get_active_provider_name(self):
        active = self.get_active_clients()
        return active[0].NAME if active else "Debrid"

    def get_active_badge(self):
        active = self.get_active_clients()
        return active[0].BADGE if active else "RD"

    def check_cache(self, hashes):
        active = self.get_active_clients()
        if not active or not hashes:
            return set()
        cached = set()
        for client in active:
            try:
                res = client.check_cache(hashes)
                if res:
                    cached.update(res)
            except Exception as e:
                log(f"{client.NAME} check_cache error: {e}", level="warning")
        return cached

    def tag_cached_streams(self, streams):
        active = self.get_active_clients()
        if not active or not streams:
            return streams

        hashes = [s.get("infoHash", "").lower() for s in streams if s.get("infoHash")]
        if not hashes:
            return streams

        for client in active:
            try:
                cached = client.check_cache(hashes)
                for s in streams:
                    h = s.get("infoHash", "").lower()
                    if h in cached:
                        s["_rd_cached"] = True
                        s["_debrid_provider"] = client.BADGE
            except Exception as e:
                log(f"{client.NAME} tag cache error: {e}", level="warning")

        return streams

    def resolve(self, magnet_or_hash, file_idx=None):
        active = self.get_active_clients()
        if not active:
            return None

        for client in active:
            try:
                url = client.resolve(magnet_or_hash, file_idx)
                if url:
                    log(f"Debrid resolved successfully via {client.NAME}", level="info")
                    return url
            except Exception as e:
                log(f"{client.NAME} resolution attempt failed: {e}", level="warning")

        return None


# Backwards compatibility alias
RealDebrid = DebridManager
