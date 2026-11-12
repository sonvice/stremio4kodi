"""
Live AceStream Source Provider
Searches live sports and P2P IPTV channels via search-ace.stream and acestreamid.com.
"""

from typing import List
from resources.lib.mediacore.models import MediaItem, StreamRelease
from resources.lib.mediacore.sources.base import BaseSource
from resources.lib.acestream_search import AceStreamSearchClient
from resources.lib.logger import log


class LiveAceStreamSource(BaseSource):
    name = "LiveAceStream"

    def __init__(self):
        self._searcher = AceStreamSearchClient()

    def is_enabled(self) -> bool:
        from resources.lib.config import Config
        return Config.acestream_enabled()

    def search_query(self, query: str) -> List[StreamRelease]:
        """Searches live AceStream channels by text query."""
        if not self.is_enabled():
            return []

        log(f"LiveAceStream searching: '{query}'", level="info")
        results = self._searcher.search(query)
        releases: List[StreamRelease] = []

        for r in results:
            content_id = r.get("content_id") or ""
            name = r.get("name") or "Canal AceStream"
            source = r.get("source") or "AceStream"
            bitrate = r.get("bitrate") or ""

            rel = StreamRelease(
                source_name=f"AceStream ({source})",
                title=name,
                display_title=f"[COLOR red]● LIVE[/COLOR] {name} {bitrate}".strip(),
                info_hash=content_id,
                url=f"acestream://{content_id}",
                quality="Live",
                variant="Live",
                extra={"raw": r},
            )
            releases.append(rel)

        return releases

    def search(self, item: MediaItem) -> List[StreamRelease]:
        """Searches live channels matching the item title."""
        if not self.is_enabled():
            return []
        return self.search_query(item.title)
