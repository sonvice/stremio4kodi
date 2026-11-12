"""
DHT & Public Scrapers Source Provider
Parallel queries to Bitsearch, Apibay, and SolidTorrents.
"""

from typing import List
from resources.lib.mediacore.models import MediaItem, StreamRelease
from resources.lib.mediacore.sources.base import BaseSource
from resources.lib.dht_search import BitsearchClient
from resources.lib.logger import log


class DhtSource(BaseSource):
    name = "DHT"

    def __init__(self):
        self._client = BitsearchClient()

    def is_enabled(self) -> bool:
        return True

    def search(self, item: MediaItem) -> List[StreamRelease]:
        if item.is_episode and item.season is not None and item.episode is not None:
            query = f"{item.title} S{item.season:02d}E{item.episode:02d}"
            category = "series"
        else:
            query = f"{item.title} {item.year or ''}".strip()
            category = "movies"

        log(f"DHT searching: '{query}' ({category})", level="info")
        raw_streams = self._client.search(query, category=category)
        if not raw_streams:
            return []

        releases: List[StreamRelease] = []
        for s in raw_streams:
            try:
                from resources.lib.rtn import RTN
                meta = RTN.parse(s)

                title = s.get("title") or s.get("name") or "DHT Stream"
                info_hash = s.get("infoHash") or s.get("info_hash") or ""
                size = s.get("size") or 0
                try:
                    size_bytes = int(size)
                except Exception:
                    size_bytes = 0

                raw_seeds = s.get("seeders") if s.get("seeders") is not None else s.get("seeds")
                try:
                    seeds = int(raw_seeds) if raw_seeds is not None else meta.get("seeds", 0)
                except Exception:
                    seeds = 0

                source_name = s.get("source") or meta.get("addon") or "DHT"

                rel = StreamRelease(
                    source_name=source_name,
                    title=title,
                    info_hash=info_hash,
                    size_bytes=size_bytes,
                    size_formatted=meta.get("size") or "",
                    seeds=seeds,
                    quality=meta.get("resolution") or "Unknown",
                    codec=meta.get("codec") or "",
                    hdr=meta.get("hdr") or "",
                    audio_channels=meta.get("audio") or "",
                    variant=meta.get("language") or "V.O.",
                    url=f"magnet:?xt=urn:btih:{info_hash}&dn={title}",
                    extra={"raw": s},
                )
                releases.append(rel)
            except Exception as e:
                log(f"Error converting DHT stream: {e}", level="debug")

        return releases
