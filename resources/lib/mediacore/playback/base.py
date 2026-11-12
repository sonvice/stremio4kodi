"""
Base Playback Provider Contract
Every engine (TorrServer, Elementum, Debrid, AceStream) implements this contract.
"""

from typing import Optional
from resources.lib.mediacore.models import StreamRelease, PlaybackResult


class BasePlaybackProvider:
    """Abstract Base Class for Playback Providers."""

    name: str = "Base"
    priority: int = 100

    def is_alive(self, timeout: Optional[float] = None) -> bool:
        """Fast non-blocking check to determine if the playback engine is available."""
        return True

    def can_handle(self, release: StreamRelease) -> bool:
        """Determines if this provider can play the given release."""
        return False

    def resolve(self, release: StreamRelease) -> PlaybackResult:
        """
        Resolves the release into a direct playable URL.
        Returns PlaybackResult with success=True and url, or success=False with error.
        """
        raise NotImplementedError
