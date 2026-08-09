# -*- coding: utf-8 -*-
"""
Config — Centralized settings access.
v3.2: Replaced live TV with AceStream, fixed platforms.
"""
import os
import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon()


class Config:
    ADDON_ID = ADDON.getAddonInfo("id")
    ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo("path"))
    DATA_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo("profile"))
    os.makedirs(DATA_PATH, exist_ok=True)

    # ── Stremio ────────────────────────────────────────────
    @staticmethod
    def stremio_addon_urls():
        raw = ADDON.getSetting("stremio_addons") or ""
        if ";;" in raw:
            urls = [u.strip().rstrip("/") for u in raw.split(";;") if u.strip()]
        else:
            import re
            parts = re.split(r'\|(?=https?://)', raw)
            urls = [u.strip().rstrip("/") for u in parts if u.strip()]
        return urls

    @staticmethod
    def stremio_timeout():
        val = ADDON.getSetting("stremio_timeout")
        return int(val) if val else 10

    @staticmethod
    def stremio_parallel():
        return ADDON.getSetting("stremio_parallel") == "true"

    # ── Torrents ───────────────────────────────────────────
    @staticmethod
    def torrent_engine():
        return ADDON.getSetting("torrent_engine") or "Elementum"

    @staticmethod
    def torrent_sort():
        return ADDON.getSetting("torrent_sort") or "Seeds"

    @staticmethod
    def torrent_quality():
        return ADDON.getSetting("torrent_quality") or "1080p"

    @staticmethod
    def torrent_autoplay():
        return ADDON.getSetting("torrent_autoplay") == "true"

    # ── Real-Debrid ────────────────────────────────────────
    @staticmethod
    def rd_enabled():
        return ADDON.getSetting("rd_enabled") == "true"

    @staticmethod
    def rd_apikey():
        return ADDON.getSetting("rd_apikey") or ""

    @staticmethod
    def rd_priority():
        return ADDON.getSetting("rd_priority") == "true"

    @staticmethod
    def strict_debrid():
        return ADDON.getSetting("strict_debrid") == "true"

    # ── Trakt ──────────────────────────────────────────────
    @staticmethod
    def trakt_enabled():
        return ADDON.getSetting("trakt_enabled") == "true"

    @staticmethod
    def trakt_clientid():
        return ADDON.getSetting("trakt_clientid") or ""

    @staticmethod
    def trakt_token():
        return ADDON.getSetting("trakt_token") or ""

    @staticmethod
    def trakt_sync_watched():
        return ADDON.getSetting("trakt_sync_watched") == "true"

    # ── Spanish preference ───────────────────────────────
    @staticmethod
    def spanish_boost():
        return ADDON.getSetting("spanish_boost") != "false"

    @staticmethod
    def spanish_filter_mode():
        return ADDON.getSetting("spanish_filter_mode") or "boost"

    @staticmethod
    def spanish_variant():
        return ADDON.getSetting("spanish_variant") or "all"

    # ── Subtitles ──────────────────────────────────────────
    @staticmethod
    def subs_auto_search():
        return ADDON.getSetting("subs_auto_search_v2") == "true"

    @staticmethod
    def subs_language():
        return ADDON.getSetting("subs_language") or "es"

    # ── Playback ───────────────────────────────────────────
    @staticmethod
    def auto_next_episode():
        return ADDON.getSetting("auto_next_episode") == "true"

    @staticmethod
    def auto_next_percent():
        val = ADDON.getSetting("auto_next_percent")
        return int(val) if val else 90

    @staticmethod
    def resume_enabled():
        return ADDON.getSetting("resume_enabled") == "true"

    # ── Cache ──────────────────────────────────────────────
    @staticmethod
    def cache_enabled():
        return ADDON.getSetting("cache_enabled") != "false"

    @staticmethod
    def cache_ttl_seconds():
        val = ADDON.getSetting("cache_ttl")
        return int(val) * 3600 if val else 21600

    # ── General ────────────────────────────────────────────
    @staticmethod
    def language():
        return ADDON.getSetting("language") or "en"

    @staticmethod
    def items_per_page():
        val = ADDON.getSetting("items_per_page")
        return int(val) if val else 25

    @staticmethod
    def log_level():
        return (ADDON.getSetting("log_level") or "Info").lower()

    @staticmethod
    def db_path():
        return os.path.join(Config.DATA_PATH, "stremio4kodi.db")

    # ══════════════════════════════════════════════════════
    #  v3 — Streaming Catalogs, Subs addon
    # ══════════════════════════════════════════════════════
    @staticmethod
    def streaming_catalogs_enabled():
        try:
            return ADDON.getSetting("streaming_catalogs_enabled") == "true"
        except Exception:
            return True

    @staticmethod
    def streaming_catalogs_url():
        try:
            val = ADDON.getSetting("streaming_catalogs_url")
            return val.rstrip("/") if val else "https://7a82163c306e-stremio-netflix-catalog-addon.baby-beamup.club"
        except Exception:
            return "https://7a82163c306e-stremio-netflix-catalog-addon.baby-beamup.club"

    @staticmethod
    def subs_enabled():
        try:
            return ADDON.getSetting("subs_enabled") != "false"
        except Exception:
            return True

    @staticmethod
    def subs_addon_url():
        try:
            val = ADDON.getSetting("subs_addon_url")
            return val.rstrip("/") if val else "https://opensubtitles-v3.strem.io"
        except Exception:
            return "https://opensubtitles-v3.strem.io"

    # ══════════════════════════════════════════════════════
    #  v3.2 — AceStream (replaces Live TV)
    # ══════════════════════════════════════════════════════
    @staticmethod
    def acestream_enabled():
        try:
            return ADDON.getSetting("acestream_enabled") == "true"
        except Exception:
            return True

    @staticmethod
    def acestream_urls():
        try:
            raw = ADDON.getSetting("acestream_urls") or ""
            if not raw.strip():
                return [
                    "https://ipfs.io/ipns/k51qzi5uqu5di462t7j4vu4akwfhvtjhy88qbupktvoacqfqe9uforjvhyi4wr/hashes.json"
                ]
            urls = [u.strip() for u in raw.split(";;") if u.strip()]
            return urls
        except Exception:
            return []

    @staticmethod
    def acestream_engine():
        try:
            return ADDON.getSetting("acestream_engine") or "Plexus"
        except Exception:
            return "Plexus"

    @staticmethod
    def acestream_engine_port():
        try:
            val = ADDON.getSetting("acestream_port")
            return int(val) if val else 6878
        except Exception:
            return 6878

    @staticmethod
    def acestream_cache_ttl():
        try:
            val = ADDON.getSetting("acestream_cache_ttl")
            return int(val) * 60 if val else 1800
        except Exception:
            return 1800

    # ── Backward compatibility ──
    @staticmethod
    def livetv_enabled():
        return Config.acestream_enabled()

    @staticmethod
    def livetv_url():
        return ""

    # ══════════════════════════════════════════════════════
    #  v3.3 — TMDB Integration
    # ══════════════════════════════════════════════════════
    @staticmethod
    def tmdb_enabled():
        try:
            return ADDON.getSetting("tmdb_enabled") != "false"
        except Exception:
            return True

    @staticmethod
    def tmdb_apikey():
        try:
            return ADDON.getSetting("tmdb_apikey") or ""
        except Exception:
            return ""

