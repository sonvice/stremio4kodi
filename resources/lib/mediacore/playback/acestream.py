"""
AceStream Playback Provider
Live P2P IPTV streaming via AceWeb HTTP (port 6878) or Horus.
"""

from typing import Optional
from resources.lib.mediacore.models import StreamRelease, PlaybackResult
from resources.lib.mediacore.playback.base import BasePlaybackProvider
from resources.lib.config import Config
from resources.lib.logger import log


class AceStreamPlaybackProvider(BasePlaybackProvider):
    name = "AceStream"
    priority = 4

    def is_alive(self, timeout: Optional[float] = None) -> bool:
        host = (Config.acestream_host() or "127.0.0.1").strip()
        port = Config.acestream_port() or 6878
        t = timeout or 1.0
        try:
            import socket
            with socket.create_connection((host, int(port)), timeout=t):
                return True
        except Exception:
            return False

    def can_handle(self, release: StreamRelease) -> bool:
        return release.is_live or "acestream" in release.source_name.lower() or (release.url and "acestream://" in release.url)

    def resolve(self, release: StreamRelease) -> PlaybackResult:
        host = (Config.acestream_host() or "127.0.0.1").strip()
        port = Config.acestream_port() or 6878
        engine = Config.acestream_engine()  # "AceWeb" or "Horus"

        raw_id = release.url.replace("acestream://", "").strip() if release.url else release.info_hash
        if not raw_id:
            return PlaybackResult(
                success=False,
                provider=self.name,
                title=release.title,
                error="ID de canal AceStream no encontrado",
            )

        log(f"Resolving AceStream via {engine}: {release.title} ({raw_id[:16]}...)", level="info")

        if engine == "Horus":
            import urllib.parse
            url = f"plugin://script.module.horus?action=play&id={urllib.parse.quote_plus(raw_id)}&title={urllib.parse.quote_plus(release.title)}"
            return PlaybackResult(
                success=True,
                url=url,
                provider=self.name,
                title=release.title,
                is_live=True,
                message="Reproduciendo con Horus",
            )
        else:
            # AceWeb HTTP manifest URL
            url = f"http://{host}:{port}/ace/manifest.m3u8?id={raw_id}"
            headers = {
                "User-Agent": "Kodi",
                "Connection": "keep-alive",
            }
            return PlaybackResult(
                success=True,
                url=url,
                provider=self.name,
                title=release.title,
                is_live=True,
                headers=headers,
                message=f"Reproduciendo con AceStream ({host})",
            )
