"""
Ratings & Rotten Tomatoes Metadata Enricher
Enriches MediaItem with Tomatometer, Audience Score, and Critics Consensus.
Inspired by HolyArrs rating ladders.
"""

from resources.lib.mediacore.models import MediaItem
from resources.lib.rottentomatoes import RottenTomatoesClient
from resources.lib.config import Config
from resources.lib.logger import log


class RatingsEnricher:
    def __init__(self):
        self._rt = RottenTomatoesClient()

    def enrich(self, item: MediaItem) -> MediaItem:
        if not Config.rt_enabled():
            return item

        try:
            m_type = "movie" if item.is_movie else "series"
            data = self._rt.get_info(item.title, year=str(item.year or ""), imdb_id=item.imdb_id, media_type=m_type)
            if data:
                item.rt_score = data.get("rotten_tomatoes") or ""
                item.rt_audience = data.get("audience_score") or ""
                item.rt_consensus = data.get("consensus") or ""
        except Exception as e:
            log(f"RatingsEnricher error for '{item.title}': {e}", level="debug")

        return item
