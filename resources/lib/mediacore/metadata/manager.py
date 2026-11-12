"""
Metadata Hub Manager
Coordinates metadata providers (TMDB, Trakt, Cinemeta) and ratings enrichment.
"""

from typing import List, Optional
from resources.lib.mediacore.models import MediaItem
from resources.lib.mediacore.metadata.tmdb import TmdbMetadataProvider
from resources.lib.mediacore.metadata.ratings import RatingsEnricher
from resources.lib.cache import CacheDB
from resources.lib.config import Config
from resources.lib.logger import log


class MetadataManager:
    def __init__(self):
        self.tmdb = TmdbMetadataProvider()
        self.ratings = RatingsEnricher()
        self.cache = CacheDB()

    def get_item(self, media_type: str, item_id: str) -> Optional[MediaItem]:
        cache_key = f"mediacore:meta:{media_type}:{item_id}"
        if Config.cache_enabled():
            cached = self.cache.get(cache_key)
            if cached and isinstance(cached, dict):
                return MediaItem(**cached)

        item = self.tmdb.get_item(media_type, item_id)
        if item:
            self.ratings.enrich(item)
            if Config.cache_enabled():
                self.cache.set(cache_key, item.to_dict(), ttl=86400)
        return item

    def search(self, query: str, media_type: str = "movie") -> List[MediaItem]:
        return self.tmdb.search(query, media_type=media_type)

    def get_trending(self, media_type: str = "movie", page: int = 1) -> List[MediaItem]:
        return self.tmdb.get_trending(media_type=media_type, page=page)

    def get_popular(self, media_type: str = "movie", page: int = 1) -> List[MediaItem]:
        return self.tmdb.get_popular(media_type=media_type, page=page)
