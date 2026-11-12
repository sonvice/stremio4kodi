"""
MediaCore Data Models - Unified Domain Models for Kodi
Inspired by HolyArrs architecture: One UI, One Media Core.
"""

import re
from typing import Dict, Any, List, Optional


class MediaItem:
    """Unified metadata item for movies, TV series, seasons, and episodes."""

    def __init__(
        self,
        media_type: str = "movie",
        title: str = "",
        year: Optional[int] = None,
        ids: Optional[Dict[str, Any]] = None,
        overview: str = "",
        poster: str = "",
        backdrop: str = "",
        rating: float = 0.0,
        votes: int = 0,
        rt_score: str = "",
        rt_audience: str = "",
        rt_consensus: str = "",
        genres: Optional[List[str]] = None,
        cast: Optional[List[str]] = None,
        director: str = "",
        duration: int = 0,
        season: Optional[int] = None,
        episode: Optional[int] = None,
        episode_title: str = "",
        raw_data: Optional[Dict[str, Any]] = None,
    ):
        self.media_type = media_type.lower()
        self.title = title
        self.year = int(year) if year and str(year).isdigit() else None
        self.ids = ids or {}
        self.overview = overview
        self.poster = poster
        self.backdrop = backdrop
        self.rating = float(rating or 0.0)
        self.votes = int(votes or 0)
        self.rt_score = rt_score
        self.rt_audience = rt_audience
        self.rt_consensus = rt_consensus
        self.genres = genres or []
        self.cast = cast or []
        self.director = director
        self.duration = int(duration or 0)
        self.season = int(season) if season is not None else None
        self.episode = int(episode) if episode is not None else None
        self.episode_title = episode_title
        self.raw_data = raw_data or {}

    @property
    def imdb_id(self) -> str:
        return str(self.ids.get("imdb") or "").strip()

    @property
    def tmdb_id(self) -> Optional[int]:
        val = self.ids.get("tmdb")
        return int(val) if val and str(val).isdigit() else None

    @property
    def tvdb_id(self) -> Optional[int]:
        val = self.ids.get("tvdb")
        return int(val) if val and str(val).isdigit() else None

    @property
    def is_episode(self) -> bool:
        return self.media_type == "episode" or (self.season is not None and self.episode is not None)

    @property
    def is_movie(self) -> bool:
        return self.media_type == "movie"

    @property
    def is_series(self) -> bool:
        return self.media_type in ("tvshow", "series", "tv")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "media_type": self.media_type,
            "title": self.title,
            "year": self.year,
            "ids": self.ids,
            "overview": self.overview,
            "poster": self.poster,
            "backdrop": self.backdrop,
            "rating": self.rating,
            "votes": self.votes,
            "rt_score": self.rt_score,
            "rt_audience": self.rt_audience,
            "rt_consensus": self.rt_consensus,
            "genres": self.genres,
            "cast": self.cast,
            "director": self.director,
            "duration": self.duration,
            "season": self.season,
            "episode": self.episode,
            "episode_title": self.episode_title,
        }

    def __repr__(self) -> str:
        ep_info = f" S{self.season:02d}E{self.episode:02d}" if self.season and self.episode else ""
        return f"<MediaItem {self.media_type.upper()}: '{self.title}'{ep_info} ({self.year}) IDs={self.ids}>"


class StreamRelease:
    """Normalized stream release coming from any source (Stremio, Torznab, DHT, AceStream)."""

    def __init__(
        self,
        source_name: str = "Unknown",
        title: str = "",
        display_title: str = "",
        info_hash: str = "",
        file_idx: Optional[int] = None,
        size_bytes: int = 0,
        size_formatted: str = "",
        seeds: int = 0,
        peers: int = 0,
        quality: str = "Unknown",
        codec: str = "",
        hdr: str = "",
        audio_channels: str = "",
        languages: Optional[List[str]] = None,
        variant: str = "Other",
        is_debrid_cached: bool = False,
        debrid_provider: str = "",
        url: str = "",
        tracker: str = "",
        score: float = 0.0,
        extra: Optional[Dict[str, Any]] = None,
    ):
        self.source_name = source_name
        self.title = title or "Stream"
        self.display_title = display_title or self.title
        # Normalize infoHash to lowercase 40 chars
        self.info_hash = self._normalize_hash(info_hash or (url if "urn:btih:" in url else ""))
        self.file_idx = file_idx
        self.size_bytes = int(size_bytes or 0)
        self.size_formatted = size_formatted or self._format_bytes(self.size_bytes)
        self.seeds = int(seeds or 0)
        self.peers = int(peers or 0)
        self.quality = quality
        self.codec = codec
        self.hdr = hdr
        self.audio_channels = audio_channels
        self.languages = languages or []
        self.variant = variant
        self.is_debrid_cached = bool(is_debrid_cached)
        self.debrid_provider = debrid_provider
        self.url = url
        self.tracker = tracker
        self.score = float(score)
        self.extra = extra or {}

    @staticmethod
    def _normalize_hash(raw: str) -> str:
        if not raw:
            return ""
        match = re.search(r"urn:btih:([a-fA-F0-9]{40}|[a-zA-Z2-7]{32})", raw, re.I)
        if match:
            h = match.group(1)
        else:
            h = raw.strip()
        if len(h) == 40 and all(c in "0123456789abcdefABCDEF" for c in h):
            return h.lower()
        elif len(h) == 32:
            import base64
            try:
                return base64.b32decode(h.upper()).hex().lower()
            except Exception:
                return h.lower()
        return h.lower()

    @staticmethod
    def _format_bytes(bytes_num: int) -> str:
        if not bytes_num or bytes_num <= 0:
            return ""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if bytes_num < 1024.0:
                return f"{bytes_num:.1f} {unit}"
            bytes_num /= 1024.0
        return f"{bytes_num:.1f} PB"

    @property
    def magnet_uri(self) -> str:
        if self.url and self.url.startswith("magnet:"):
            return self.url
        if self.info_hash:
            import urllib.parse
            name = urllib.parse.quote(self.title)
            return f"magnet:?xt=urn:btih:{self.info_hash}&dn={name}"
        return ""

    @property
    def is_torrent(self) -> bool:
        return bool(self.info_hash or (self.url and (self.url.startswith("magnet:") or ".torrent" in self.url)))

    @property
    def is_live(self) -> bool:
        return "acestream" in self.source_name.lower() or (self.url and self.url.startswith("acestream://"))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_name": self.source_name,
            "title": self.title,
            "display_title": self.display_title,
            "info_hash": self.info_hash,
            "file_idx": self.file_idx,
            "size_bytes": self.size_bytes,
            "size_formatted": self.size_formatted,
            "seeds": self.seeds,
            "peers": self.peers,
            "quality": self.quality,
            "codec": self.codec,
            "hdr": self.hdr,
            "audio_channels": self.audio_channels,
            "languages": self.languages,
            "variant": self.variant,
            "is_debrid_cached": self.is_debrid_cached,
            "debrid_provider": self.debrid_provider,
            "url": self.url,
            "tracker": self.tracker,
            "score": self.score,
            "extra": self.extra,
        }

    def __repr__(self) -> str:
        debrid = f" [{self.debrid_provider} CACHED]" if self.is_debrid_cached else ""
        return f"<StreamRelease '{self.title}' ({self.quality} {self.variant}) Seeds={self.seeds}{debrid} Source={self.source_name}>"


class PlaybackResult:
    """Result of stream resolution ready for Kodi's player."""

    def __init__(
        self,
        success: bool = False,
        url: str = "",
        provider: str = "",
        title: str = "",
        is_live: bool = False,
        headers: Optional[Dict[str, str]] = None,
        message: str = "",
        error: str = "",
        media_type: str = "video",
    ):
        self.success = bool(success)
        self.url = url
        self.provider = provider
        self.title = title
        self.is_live = bool(is_live)
        self.headers = headers or {}
        self.message = message
        self.error = error
        self.media_type = media_type

    def __bool__(self) -> bool:
        return self.success and bool(self.url)

    def __repr__(self) -> str:
        status = "OK" if self.success else f"FAIL ({self.error})"
        return f"<PlaybackResult {status} via {self.provider}: {self.url[:60]}...>"
