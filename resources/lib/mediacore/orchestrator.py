"""
MediaCore Orchestrator - Central Brain of Stremio for Kodi.
Implements the 'One UI, One Media Core' architecture inspired by HolyArrs.
Coordinates Metadata Hub, Sources Hub, Scoring Engine, and Playback Hub.
"""

from typing import List, Optional, Dict, Any

from resources.lib.mediacore.models import MediaItem, StreamRelease, PlaybackResult
from resources.lib.mediacore.metadata.manager import MetadataManager
from resources.lib.mediacore.sources.manager import SourcesManager
from resources.lib.mediacore.scoring.ranker import ScoringEngine
from resources.lib.mediacore.playback.manager import PlaybackManager
from resources.lib.cache import CacheDB
from resources.lib.config import Config
from resources.lib.logger import log


class MediaCore:
    """The central orchestrator connecting all layers."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MediaCore, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self.metadata = MetadataManager()
        self.sources = SourcesManager()
        self.scoring = ScoringEngine()
        self.playback = PlaybackManager()
        self.cache = CacheDB()
        self._initialized = True
        log("MediaCore Orchestrator initialized (One UI, One Media Core)", level="info")

    def get_metadata(self, media_type: str, item_id: str) -> Optional[MediaItem]:
        """Fetches metadata for a movie or TV show."""
        return self.metadata.get_item(media_type, item_id)

    def get_streams(self, item: MediaItem) -> List[StreamRelease]:
        """
        Orchestrates stream discovery and ranking for a media item:
        1. Checks local cache.
        2. Queries all enabled sources in parallel (Stremio addons, Torznab/Jackett/Prowlarr, DHT).
        3. Normalizes, deduplicates, and ranks streams according to user preferences.
        4. Caches and returns final list.
        """
        cache_key = f"mediacore:streams:{item.media_type}:{item.imdb_id or item.tmdb_id}:{item.season}:{item.episode}"
        if Config.cache_enabled():
            cached = self.cache.get(cache_key)
            if cached and isinstance(cached, list):
                log(f"MediaCore returning {len(cached)} cached streams for '{item.title}'", level="info")
                return [StreamRelease(**s) for s in cached]

        log(f"MediaCore fetching streams for: {item}", level="info")
        raw_releases = self.sources.search_all(item)
        if not raw_releases:
            log(f"MediaCore found 0 releases across all sources for '{item.title}'", level="warning")
            return []

        # Process and rank through Scoring Engine
        ranked = self.scoring.process_and_rank(raw_releases)

        if Config.cache_enabled() and ranked:
            self.cache.set(cache_key, [r.to_dict() for r in ranked], ttl=1800)

        log(f"MediaCore returning {len(ranked)} ranked streams for '{item.title}'", level="info")
        return ranked

    def resolve_playback(self, release: StreamRelease) -> PlaybackResult:
        """
        Resolves stream release into a playable Kodi URL using the prioritized
        playback pipeline (TorrServer -> Real-Debrid / Multi-Debrid -> Elementum).
        """
        log(f"MediaCore resolving playback for: {release.title} ({release.source_name})", level="info")
        return self.playback.resolve(release)

    def check_engines_health(self) -> Dict[str, Any]:
        """Returns the real-time status of all engines for the UI status manager."""
        return {
            "torrserver": {
                "alive": self.playback.torrserver.is_alive(timeout=0.8),
                "host": self.playback.torrserver.host,
                "port": self.playback.torrserver.port,
            },
            "elementum": {
                "alive": self.playback.elementum.is_alive(timeout=1.0),
            },
            "debrid": {
                "configured": self.playback.debrid.is_configured(),
                "provider": self.playback.debrid._client.get_active_provider_name() if self.playback.debrid.is_configured() else "Ninguno",
            },
            "acestream": {
                "alive": self.playback.acestream.is_alive(timeout=1.0),
                "engine": Config.acestream_engine(),
            },
            "torznab": {
                "enabled": self.sources.torznab.is_enabled(),
                "url": Config.torznab_url() if self.sources.torznab.is_enabled() else "",
            },
        }
