"""
Base Metadata Provider Contract
"""

from typing import List, Optional
from resources.lib.mediacore.models import MediaItem


class BaseMetadataProvider:
    name: str = "BaseMetadata"

    def get_item(self, media_type: str, item_id: str) -> Optional[MediaItem]:
        raise NotImplementedError

    def search(self, query: str, media_type: str = "movie") -> List[MediaItem]:
        raise NotImplementedError

    def get_trending(self, media_type: str = "movie", page: int = 1) -> List[MediaItem]:
        raise NotImplementedError

    def get_popular(self, media_type: str = "movie", page: int = 1) -> List[MediaItem]:
        raise NotImplementedError
