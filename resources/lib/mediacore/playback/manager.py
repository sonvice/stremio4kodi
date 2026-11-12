"""
Playback Provider Manager
Orchestrates playback providers with smart priority, fast health checks, and sub-second fallbacks.
"""

from typing import Optional, List
from resources.lib.mediacore.models import StreamRelease, PlaybackResult
from resources.lib.mediacore.playback.base import BasePlaybackProvider
from resources.lib.mediacore.playback.torrserver import TorrServerProvider
from resources.lib.mediacore.playback.debrid import DebridPlaybackProvider
from resources.lib.mediacore.playback.elementum import ElementumProvider
from resources.lib.mediacore.playback.acestream import AceStreamPlaybackProvider
from resources.lib.mediacore.playback.direct import DirectHttpProvider
from resources.lib.config import Config
from resources.lib.logger import log


class PlaybackManager:
    """Central orchestrator for all playback providers."""

    def __init__(self):
        self.torrserver = TorrServerProvider()
        self.debrid = DebridPlaybackProvider()
        self.elementum = ElementumProvider()
        self.acestream = AceStreamPlaybackProvider()
        self.direct = DirectHttpProvider()

        self._providers: List[BasePlaybackProvider] = [
            self.debrid,
            self.torrserver,
            self.elementum,
            self.acestream,
            self.direct,
        ]

    def _check_p2p_privacy(self) -> bool:
        """Shows first-time P2P privacy warning if not accepted yet."""
        if Config.strict_debrid():
            log("P2P playback blocked by Strict Debrid mode", level="warning")
            try:
                import xbmcgui
                xbmcgui.Dialog().ok(
                    "Strict Debrid",
                    "Reproducción P2P local bloqueada por seguridad (Modo Estricto Debrid activo).",
                )
            except Exception:
                pass
            return False

        from resources.lib.cache import CacheDB
        cache = CacheDB()
        if not cache.get("_p2p_privacy_warned"):
            try:
                import xbmcgui
                confirm = xbmcgui.Dialog().yesno(
                    "Advertencia de Privacidad P2P",
                    "Vas a reproducir mediante un motor P2P local (TorrServer/Elementum).\n"
                    "Tu dirección IP será pública en la red Kademlia DHT.\n"
                    "¿Deseas continuar con la reproducción?",
                )
                if not confirm:
                    return False
                cache.set("_p2p_privacy_warned", True, ttl=31536000)
            except Exception:
                pass
        return True

    def get_preferred_engine(self) -> str:
        """Determines the active torrent engine based on settings and real-time probes."""
        setting = Config.torrent_engine() or "TorrServer"
        if setting == "TorrServer":
            return "TorrServer"
        if setting == "Elementum":
            return "Elementum"
        if setting == "Auto":
            if self.torrserver.is_alive(timeout=0.8):
                return "TorrServer"
            if self.elementum.is_alive(timeout=1.0):
                return "Elementum"
            return "TorrServer"
        return setting

    def resolve(self, release: StreamRelease) -> PlaybackResult:
        """
        Main entry point for resolving any stream release into a playable Kodi URL.
        Priority:
          1. Live AceStream streams -> AceStreamProvider
          2. Debrid cached streams -> DebridProvider
          3. P2P Torrents -> TorrServer (with instant <1s Elementum fallback)
          4. Direct HTTP -> DirectHttpProvider
        """
        # 1. Live AceStream
        if self.acestream.can_handle(release):
            return self.acestream.resolve(release)

        # 2. Debrid (if configured and stream is cached or user has RD enabled)
        if self.debrid.is_configured() and (release.is_debrid_cached or release.is_torrent):
            rd_res = self.debrid.resolve(release)
            if rd_res.success:
                return rd_res
            log("Debrid resolution failed or stream not cached, falling back to torrent engine...", level="info")
            if Config.strict_debrid():
                return PlaybackResult(
                    success=False,
                    provider="Debrid",
                    title=release.title,
                    error="Modo Estricto Debrid: el archivo no está en caché y P2P está desactivado",
                )

        # 3. P2P Torrents
        if release.is_torrent:
            if not self._check_p2p_privacy():
                return PlaybackResult(success=False, title=release.title, error="Cancelado por usuario (Privacidad P2P)")

            pref = self.get_preferred_engine()
            log(f"Resolving P2P torrent via preferred engine: {pref}", level="info")

            if pref == "TorrServer":
                ts_res = self.torrserver.resolve(release)
                if ts_res.success:
                    return ts_res
                # Instant fallback (< 1s) to Elementum
                log("TorrServer not available, initiating sub-second Elementum fallback...", level="info")
                try:
                    import xbmcgui
                    xbmcgui.Dialog().notification("Stremio4Kodi", "TorrServer no detectado. Usando Elementum...", xbmcgui.NOTIFICATION_INFO, 2500)
                except Exception:
                    pass
                return self.elementum.resolve(release)

            elif pref == "Elementum":
                el_res = self.elementum.resolve(release)
                if el_res.success:
                    return el_res
                # Fallback to TorrServer if Elementum fails
                if self.torrserver.is_alive(timeout=0.8):
                    log("Elementum failed, falling back to active TorrServer...", level="info")
                    try:
                        import xbmcgui
                        xbmcgui.Dialog().notification("Stremio4Kodi", "Elementum no respondió. Usando TorrServer...", xbmcgui.NOTIFICATION_INFO, 2500)
                    except Exception:
                        pass
                    return self.torrserver.resolve(release)
                return el_res

        # 4. Direct HTTP
        if self.direct.can_handle(release):
            return self.direct.resolve(release)

        return PlaybackResult(
            success=False,
            title=release.title,
            error="Ningún proveedor de reproducción disponible para este release",
        )
