"""
Stremio Addons Source Provider
Queries Torrentio, Comet, MediaFusion, Peerflix, and other Stremio HTTP addons concurrently.
Normalizes results into standard StreamRelease objects.
"""

from typing import List
from resources.lib.mediacore.models import MediaItem, StreamRelease
from resources.lib.mediacore.sources.base import BaseSource
from resources.lib.stremio import StremioClient
from resources.lib.logger import log


class StremioSource(BaseSource):
    name = "StremioHub"

    def __init__(self):
        self._client = StremioClient()

    def is_enabled(self) -> bool:
        return True

    def search(self, item: MediaItem) -> List[StreamRelease]:
        """Queries Stremio addons using IMDb ID or formatted ID."""
        imdb_id = item.imdb_id
        if not imdb_id:
            # Fallback to tmdb id or custom id
            if item.tmdb_id:
                imdb_id = f"tmdb:{item.tmdb_id}"
            else:
                return []

        media_type = "series" if item.is_series or item.is_episode else "movie"
        target_id = imdb_id
        if item.is_episode and item.season is not None and item.episode is not None:
            target_id = f"{imdb_id}:{item.season}:{item.episode}"

        log(f"StremioSource searching: {media_type} / {target_id}", level="info")
        raw_streams = self._client.get_streams(media_type, target_id)
        if not raw_streams:
            return []

        releases: List[StreamRelease] = []
        for s in raw_streams:
            try:
                from resources.lib.rtn import RTN
                meta = RTN.parse(s)

                addon_name = meta.get("addon") or s.get("_addon") or s.get("name") or "Stremio"
                title = s.get("title") or s.get("name") or "Stream"
                title_clean = title.split("\n")[0].strip()

                info_hash = s.get("infoHash") or ""
                file_idx = s.get("fileIdx")
                url = s.get("url") or ""

                quality = meta.get("resolution") or "Unknown"
                codec = meta.get("codec") or ""
                hdr = meta.get("hdr") or ""
                audio = meta.get("audio") or ""
                languages = [meta.get("language")] if meta.get("language") else []
                variant = meta.get("language") or "Other"
                size_formatted = meta.get("size") or ""
                seeds = meta.get("seeds") or 0
                is_cached = meta.get("is_rd") or False
                debrid_prov = meta.get("debrid_badge") or ""

                rel = StreamRelease(
                    source_name=addon_name,
                    title=title_clean,
                    info_hash=info_hash,
                    file_idx=file_idx,
                    size_formatted=size_formatted,
                    seeds=seeds,
                    quality=quality,
                    codec=codec,
                    hdr=hdr,
                    audio_channels=audio,
                    languages=languages,
                    variant=variant,
                    is_debrid_cached=is_cached,
                    debrid_provider=debrid_prov,
                    url=url,
                    extra={"raw": s},
                )
                releases.append(rel)
            except Exception as e:
                log(f"Error converting Stremio stream: {e}", level="debug")

        return releases
