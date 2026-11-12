"""
TorrServer Playback Provider
Direct HTTP RAM streaming via TorrServer MatriX endpoint.
Priority engine for low-resource devices (Android TV, TV Boxes, FireStick).
"""

import json
import re
import socket
import urllib.request
import urllib.parse
from typing import Optional

from resources.lib.mediacore.models import StreamRelease, PlaybackResult
from resources.lib.mediacore.playback.base import BasePlaybackProvider
from resources.lib.config import Config
from resources.lib.logger import log


class TorrServerProvider(BasePlaybackProvider):
    name = "TorrServer"
    priority = 1  # Primary engine

    def __init__(self):
        pass

    @property
    def host(self) -> str:
        return (Config.torrserver_host() or "127.0.0.1").strip()

    @property
    def port(self) -> int:
        try:
            return int(Config.torrserver_port())
        except (ValueError, TypeError):
            return 8090

    @property
    def auth_required(self) -> bool:
        return Config.torrserver_auth()

    @property
    def user(self) -> str:
        return Config.torrserver_user().strip()

    @property
    def password(self) -> str:
        return Config.torrserver_pass()

    def _ensure_lan_bypass(self, host: str):
        """On CoreELEC/Linux, ensures LAN traffic to TorrServer bypasses VPN tunnels."""
        if not host or host in ("127.0.0.1", "localhost", "::1"):
            return
        try:
            import subprocess, shutil
            if shutil.which("ip") is not None:
                parts = host.split(".")
                if len(parts) == 4 and all(p.isdigit() for p in parts):
                    if host.startswith("192.168.") or host.startswith("10.") or host.startswith("172."):
                        subprocess.run(
                            ["ip", "route", "replace", f"{host}/32", "via", "192.168.1.1"],
                            timeout=1,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
        except Exception:
            pass

    def is_alive(self, timeout: Optional[float] = None) -> bool:
        """
        Ultra-fast health probe (< 0.8s).
        Localhost resolves in < 1ms, LAN in max 1.0s.
        """
        h = self.host
        p = self.port
        t = timeout if timeout is not None else (0.5 if h in ("127.0.0.1", "localhost") else 1.0)
        self._ensure_lan_bypass(h)
        try:
            with socket.create_connection((h, p), timeout=t) as s:
                s.settimeout(t)
                s.sendall(b"GET /echo HTTP/1.1\r\nHost: " + h.encode() + b"\r\nConnection: close\r\n\r\n")
                resp = s.recv(512)
                return b"200" in resp or b"MatriX" in resp or b"401" in resp
        except Exception as se:
            log(f"TorrServer probe notice ({h}:{p}): {se}", level="debug")
            return False

    def can_handle(self, release: StreamRelease) -> bool:
        """TorrServer handles any torrent (magnet, infoHash, or .torrent link)."""
        return release.is_torrent

    def resolve(self, release: StreamRelease) -> PlaybackResult:
        """
        Resolves torrent stream via TorrServer MatriX HTTP streaming endpoint.
        Returns PlaybackResult with playable HTTP URL.
        """
        h = self.host
        p = self.port

        # Fast pre-flight check (< 0.8s)
        if not self.is_alive(timeout=0.8):
            log(f"TorrServer at {h}:{p} is unreachable or offline", level="info")
            return PlaybackResult(
                success=False,
                provider=self.name,
                title=release.title,
                error=f"TorrServer ({h}:{p}) no está activo o no responde",
            )

        base_api_url = f"http://{h}:{p}"
        headers = {"User-Agent": "Kodi", "Content-Type": "application/json"}
        if self.auth_required and self.user:
            import base64
            cred = base64.b64encode(f"{self.user}:{self.password}".encode()).decode()
            headers["Authorization"] = f"Basic {cred}"

        uri = release.magnet_uri or release.url
        info_hash = release.info_hash
        file_idx = release.file_idx
        stream_title = release.title

        # Add torrent to TorrServer memory session (save_to_db=False)
        try:
            add_payload = json.dumps({
                "action": "add",
                "link": uri or (f"magnet:?xt=urn:btih:{info_hash}" if info_hash else ""),
                "title": stream_title or "Stream",
                "save_to_db": False,
            }).encode("utf-8")
            req = urllib.request.Request(f"{base_api_url}/torrents", data=add_payload, headers=headers)
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                pass
        except Exception as e:
            log(f"TorrServer add session notice: {e}", level="warning")
            return PlaybackResult(
                success=False,
                provider=self.name,
                title=release.title,
                error=f"Error al enviar torrent a TorrServer: {e}",
            )

        best_id = None
        chosen_filename = None

        # Quick file check (up to 4 attempts x 150ms)
        if info_hash:
            get_payload = json.dumps({"action": "get", "hash": info_hash}).encode("utf-8")
            import time
            for _ in range(4):
                try:
                    req = urllib.request.Request(f"{base_api_url}/torrents", data=get_payload, headers=headers)
                    with urllib.request.urlopen(req, timeout=1.0) as resp:
                        data = json.loads(resp.read().decode())
                        file_stats = data.get("file_stats") or []
                        if file_stats:
                            if file_idx is not None and isinstance(file_idx, int) and 0 <= file_idx < len(file_stats):
                                best_id = file_stats[file_idx].get("id")
                                chosen_filename = file_stats[file_idx].get("path", "").replace("\\", "/").split("/")[-1]
                            elif file_idx is None:
                                video_exts = (".mkv", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm", ".ts", ".m2ts")
                                v_files = [f for f in file_stats if any(f.get("path", "").lower().endswith(ext) for ext in video_exts)]
                                pool = v_files if v_files else file_stats
                                largest = max(pool, key=lambda x: x.get("length", 0))
                                best_id = largest.get("id")
                                chosen_filename = largest.get("path", "").replace("\\", "/").split("/")[-1]
                            break
                except Exception:
                    pass
                try:
                    import xbmc
                    xbmc.sleep(150)
                except ImportError:
                    time.sleep(0.15)

        if best_id is None:
            if file_idx is not None and isinstance(file_idx, int):
                best_id = file_idx + 1
            else:
                best_id = 1

        if not chosen_filename:
            safe_name = re.sub(r'[/\\?%*:|"<>]', ".", stream_title or "video").strip()
            if not any(safe_name.lower().endswith(ext) for ext in (".mkv", ".mp4", ".avi", ".ts")):
                safe_name += ".mkv"
            chosen_filename = safe_name

        auth_str = f"{urllib.parse.quote(self.user)}:{urllib.parse.quote(self.password)}@" if self.auth_required and self.user else ""
        encoded_filename = urllib.parse.quote(chosen_filename)
        encoded_link = urllib.parse.quote(uri or f"magnet:?xt=urn:btih:{info_hash}", safe="")
        stream_url = f"http://{auth_str}{h}:{p}/stream/{encoded_filename}?link={encoded_link}&index={best_id}&play"

        log(f"TorrServer resolved stream: {stream_url[:120]}...", level="info")
        return PlaybackResult(
            success=True,
            url=stream_url,
            provider=self.name,
            title=chosen_filename,
            message=f"Reproduciendo con TorrServer ({h})",
        )
