"""
Base Source Contract
Every stream source (Stremio Addons, Torznab/Jackett, DHT) implements this interface.
"""

from typing import List
from resources.lib.mediacore.models import MediaItem, StreamRelease


class BaseSource:
    """Abstract Base Class for stream sources and indexers."""

    name: str = "BaseSource"

    def is_enabled(self) -> bool:
        """Checks if this source is enabled in settings."""
        return True

    def search(self, item: MediaItem) -> List[StreamRelease]:
        """
        Searches for available streams for the given MediaItem.
        Returns a list of StreamRelease objects.
        """
        raise NotImplementedError
