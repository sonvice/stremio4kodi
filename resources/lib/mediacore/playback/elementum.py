"""
Elementum Playback Provider
Local BitTorrent streaming via Elementum daemon on http://127.0.0.1:65220.
Used as fallback or primary if user explicitly selects Elementum.
"""

import urllib.request
import urllib.parse
from typing import Optional

from resources.lib.mediacore.models import StreamRelease, PlaybackResult
from resources.lib.mediacore.playback.base import BasePlaybackProvider
from resources.lib.config import Config
from resources.lib.logger import log


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Prevents following redirects so Kodi can receive the direct stream URL."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class ElementumProvider(BasePlaybackProvider):
    name = "Elementum"
    priority = 3  # Fallback engine

    def is_alive(self, timeout: Optional[float] = None) -> bool:
        t = timeout or 1.0
        try:
            req = urllib.request.Request("http://127.0.0.1:65220/", headers={"User-Agent": "Kodi"})
            with urllib.request.urlopen(req, timeout=t) as r:
                return True
        except Exception:
            return False

    def can_handle(self, release: StreamRelease) -> bool:
        return release.is_torrent

    def _try_recover(self) -> bool:
        """Attempts auto-healing Elementum if daemon is offline."""
        if not Config.elementum_auto_heal():
            return False
        try:
            from resources.lib import dependencies
            return dependencies.heal_elementum_if_needed()
        except Exception as e:
            log(f"Elementum auto-heal notice: {e}", level="warning")
            return False

    def resolve(self, release: StreamRelease) -> PlaybackResult:
        if not self.is_alive():
            if not self._try_recover():
                return PlaybackResult(
                    success=False,
                    provider=self.name,
                    title=release.title,
                    error="Elementum no está instalado o su daemon no responde",
                )

        uri = release.magnet_uri or release.url
        if not uri:
            return PlaybackResult(
                success=False,
                provider=self.name,
                title=release.title,
                error="Release no tiene magnet ni URL válida para Elementum",
            )

        encoded = urllib.parse.quote(uri, safe="")
        play_url = f"http://127.0.0.1:65220/play?uri={encoded}"
        if release.file_idx is not None:
            play_url += f"&oindex={release.file_idx}"

        opener = urllib.request.build_opener(NoRedirectHandler())
        opener.addheaders = [("User-Agent", "plugin.video.elementum")]

        log(f"Resolving stream via Elementum daemon: {play_url[:120]}...", level="info")

        try:
            # 300s timeout so Python doesn't prematurely interrupt Kodi's buffering dialog
            res = opener.open(play_url, timeout=300)
            if res and res.getcode() in (301, 302, 303, 307):
                loc = res.geturl()
                if loc and loc.startswith("http"):
                    log(f"Elementum resolved direct stream: {loc}", level="info")
                    return PlaybackResult(
                        success=True,
                        url=loc,
                        provider=self.name,
                        title=release.title,
                        message="Reproduciendo con Elementum",
                    )
        except Exception as e:
            log(f"Elementum daemon resolve ended: {e}", level="info")
            if release.info_hash:
                try:
                    pause_req = urllib.request.Request(f"http://127.0.0.1:65220/torrents/pause/{release.info_hash}")
                    urllib.request.urlopen(pause_req, timeout=1.5)
                except Exception:
                    pass
            return PlaybackResult(
                success=False,
                provider=self.name,
                title=release.title,
                error=f"Elementum cancelado o error en el búfer: {e}",
            )

        return PlaybackResult(
            success=False,
            provider=self.name,
            title=release.title,
            error="Elementum no retornó URL de reproducción",
        )
