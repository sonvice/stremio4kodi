"""
Direct HTTP / HLS Playback Provider
Handles direct web video streams.
"""

from typing import Optional
from resources.lib.mediacore.models import StreamRelease, PlaybackResult
from resources.lib.mediacore.playback.base import BasePlaybackProvider


class DirectHttpProvider(BasePlaybackProvider):
    name = "Direct"
    priority = 5

    def is_alive(self, timeout: Optional[float] = None) -> bool:
        return True

    def can_handle(self, release: StreamRelease) -> bool:
        url = release.url or ""
        return url.startswith("http://") or url.startswith("https://")

    def resolve(self, release: StreamRelease) -> PlaybackResult:
        return PlaybackResult(
            success=True,
            url=release.url,
            provider=self.name,
            title=release.title,
            is_live=release.is_live,
            headers={"User-Agent": "Kodi"},
            message="Reproduciendo stream directo",
        )
