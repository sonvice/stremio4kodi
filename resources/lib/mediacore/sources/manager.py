"""
Sources Manager - Orchestrates multi-source scraping in parallel.
Queries Stremio addons, Torznab (Jackett/Prowlarr), and DHT simultaneously.
"""

from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed

from resources.lib.mediacore.models import MediaItem, StreamRelease
from resources.lib.mediacore.sources.base import BaseSource
from resources.lib.mediacore.sources.stremio import StremioSource
from resources.lib.mediacore.sources.torznab import TorznabSource
from resources.lib.mediacore.sources.dht import DhtSource
from resources.lib.mediacore.sources.live import LiveAceStreamSource
from resources.lib.logger import log


class SourcesManager:
    """Dispatches search queries across all enabled sources concurrently."""

    def __init__(self):
        self.stremio = StremioSource()
        self.torznab = TorznabSource()
        self.dht = DhtSource()
        self.live = LiveAceStreamSource()

        self._sources: List[BaseSource] = [
            self.stremio,
            self.torznab,
            self.dht,
            self.live,
        ]

    def search_all(self, item: MediaItem) -> List[StreamRelease]:
        """
        Executes parallel search across all enabled sources.
        Aggregates results into a single list of StreamRelease objects.
        """
        enabled = [s for s in self._sources if s.is_enabled()]
        if not enabled:
            return []

        all_releases: List[StreamRelease] = []

        def _run_source(src: BaseSource):
            try:
                return src.search(item)
            except Exception as e:
                log(f"Source {src.name} search error: {e}", level="warning")
                return []

        with ThreadPoolExecutor(max_workers=min(len(enabled), 6)) as pool:
            futures = {pool.submit(_run_source, s): s for s in enabled}
            for fut in as_completed(futures):
                s = futures[fut]
                try:
                    res = fut.result()
                    if res:
                        log(f"Source '{s.name}' returned {len(res)} streams", level="info")
                        all_releases.extend(res)
                except Exception as e:
                    log(f"Error processing result from {s.name}: {e}", level="error")

        return all_releases
