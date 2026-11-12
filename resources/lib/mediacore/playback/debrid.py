"""
Multi-Debrid Playback Provider
Direct CDN streaming via Real-Debrid, AllDebrid, Premiumize, TorBox, and Debrid-Link.
"""

from typing import Optional
from resources.lib.mediacore.models import StreamRelease, PlaybackResult
from resources.lib.mediacore.playback.base import BasePlaybackProvider
from resources.lib.debrid import RealDebrid
from resources.lib.logger import log


class DebridPlaybackProvider(BasePlaybackProvider):
    name = "Debrid"
    priority = 2

    def __init__(self):
        self._client = RealDebrid()

    def is_configured(self) -> bool:
        return self._client.is_configured()

    def is_alive(self, timeout: Optional[float] = None) -> bool:
        return self.is_configured()

    def can_handle(self, release: StreamRelease) -> bool:
        if not self.is_configured():
            return False
        # Can handle if torrent hash or magnet link exists
        return release.is_torrent

    def resolve(self, release: StreamRelease) -> PlaybackResult:
        if not self.is_configured():
            return PlaybackResult(
                success=False,
                provider=self.name,
                title=release.title,
                error="Ningún proveedor Debrid está configurado",
            )

        provider_name = self._client.get_active_provider_name()
        query = release.info_hash or release.magnet_uri or release.url
        log(f"Resolving via {provider_name}: {release.title} ({query[:40]}...)", level="info")

        direct_url = self._client.resolve(query, release.file_idx)
        if direct_url:
            return PlaybackResult(
                success=True,
                url=direct_url,
                provider=provider_name,
                title=release.title,
                message=f"Reproduciendo con {provider_name}",
            )

        return PlaybackResult(
            success=False,
            provider=provider_name,
            title=release.title,
            error=f"{provider_name} no pudo resolver el stream (no en caché o error de API)",
        )
