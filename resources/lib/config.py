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

    DEFAULT_ADDON_URLS = [
        "https://v3-cinemeta.strem.io",
        "https://94c8cb9f702d-tmdb-addon.baby-beamup.club",
        "https://torrentio.strem.fun",
        "https://cometa.stremx.net",
        "https://peerflix.mov",
        "https://mediafusion.elfhosted.com",
    ]

    # ── Stremio ────────────────────────────────────────────
    @staticmethod
    def comet_custom_manifest():
        raw = ADDON.getSetting("comet_custom_manifest") or ""
        return raw.strip()

    @staticmethod
    def stremio_addon_urls():
        custom_comet = Config.comet_custom_manifest()

        raw = ADDON.getSetting("stremio_addons") or ""
        if ";;" in raw:
            urls = [u.strip().rstrip("/") for u in raw.split(";;") if u.strip()]
        elif raw:
            import re
            parts = re.split(r'\|(?=https?://)', raw)
            urls = [u.strip().rstrip("/") for u in parts if u.strip()]
        else:
            urls = list(Config.DEFAULT_ADDON_URLS)

        # Handle custom Comet manifest URL
        if custom_comet:
            # Replace public instance with user-configured private manifest
            urls = [u for u in urls if "cometa.stremx.net" not in u]
            if custom_comet not in urls:
                urls.insert(0, custom_comet)
        else:
            # Ensure Comet instance is available even if an older default string was cached
            if urls and not any("comet" in u.lower() for u in urls):
                urls.append("https://cometa.stremx.net")

        return urls

    @staticmethod
    def stremio_timeout():
        val = ADDON.getSetting("stremio_timeout")
        return int(val) if val else 10

    @staticmethod
    def stremio_parallel():
        return ADDON.getSetting("stremio_parallel") == "true"

    # ── Torznab (Jackett & Prowlarr) ────────────────────────
    @staticmethod
    def torznab_enabled():
        return ADDON.getSetting("torznab_enabled") == "true"

    @staticmethod
    def torznab_url():
        return ADDON.getSetting("torznab_url") or ""

    @staticmethod
    def torznab_apikey():
        return ADDON.getSetting("torznab_apikey") or ""

    # ── Torrents ───────────────────────────────────────────
    @staticmethod
    def torrent_engine():
        return ADDON.getSetting("torrent_engine") or "TorrServer"

    @staticmethod
    def torrserver_host():
        raw = ADDON.getSetting("torrserver_host") or "127.0.0.1"
        cleaned = raw.strip().replace("http://", "").replace("https://", "").rstrip("/")
        if ":" in cleaned:
            return cleaned.split(":")[0].strip()
        return cleaned or "127.0.0.1"

    @staticmethod
    def torrserver_port():
        raw_host = ADDON.getSetting("torrserver_host") or ""
        if ":" in raw_host:
            parts = raw_host.strip().replace("http://", "").replace("https://", "").rstrip("/").split(":")
            if len(parts) > 1 and parts[1].isdigit():
                return parts[1].strip()
        raw = ADDON.getSetting("torrserver_port") or "8090"
        return raw.strip() or "8090"

    @staticmethod
    def torrserver_auth():
        return ADDON.getSetting("torrserver_auth") == "true"

    @staticmethod
    def torrserver_user():
        return ADDON.getSetting("torrserver_user") or ""

    @staticmethod
    def torrserver_pass():
        return ADDON.getSetting("torrserver_pass") or ""

    @staticmethod
    def elementum_auto_heal():
        return ADDON.getSetting("elementum_auto_heal") != "false"

    @staticmethod
    def torrent_preflight_check():
        return ADDON.getSetting("torrent_preflight_check") != "false"

    @staticmethod
    def torrent_sort():
        return ADDON.getSetting("torrent_sort") or "Seeds"

    @staticmethod
    def torrent_quality():
        return ADDON.getSetting("torrent_quality") or "1080p"

    @staticmethod
    def torrent_autoplay():
        return ADDON.getSetting("torrent_autoplay") == "true"

    @staticmethod
    def pack_select_mode():
        return "Reproducir episodio actual"

    # ── Debrid Providers (Multi-Debrid) ───────────────────
    @staticmethod
    def rd_enabled():
        return ADDON.getSetting("rd_enabled") == "true"

    @staticmethod
    def rd_apikey():
        return ADDON.getSetting("rd_apikey") or ""

    @staticmethod
    def alldebrid_enabled():
        return ADDON.getSetting("alldebrid_enabled") == "true"

    @staticmethod
    def alldebrid_apikey():
        return ADDON.getSetting("alldebrid_apikey") or ""

    @staticmethod
    def premiumize_enabled():
        return ADDON.getSetting("premiumize_enabled") == "true"

    @staticmethod
    def premiumize_apikey():
        return ADDON.getSetting("premiumize_apikey") or ""

    @staticmethod
    def torbox_enabled():
        return ADDON.getSetting("torbox_enabled") == "true"

    @staticmethod
    def torbox_apikey():
        return ADDON.getSetting("torbox_apikey") or ""

    @staticmethod
    def debridlink_enabled():
        return ADDON.getSetting("debridlink_enabled") == "true"

    @staticmethod
    def debridlink_apikey():
        return ADDON.getSetting("debridlink_apikey") or ""

    @staticmethod
    def rd_priority():
        return ADDON.getSetting("rd_priority") != "false"

    @staticmethod
    def strict_debrid():
        return ADDON.getSetting("strict_debrid") == "true"

    @staticmethod
    def debrid_configured():
        return (
            (Config.rd_enabled() and bool(Config.rd_apikey())) or
            (Config.alldebrid_enabled() and bool(Config.alldebrid_apikey())) or
            (Config.premiumize_enabled() and bool(Config.premiumize_apikey())) or
            (Config.torbox_enabled() and bool(Config.torbox_apikey())) or
            (Config.debridlink_enabled() and bool(Config.debridlink_apikey()))
        )

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

    @staticmethod
    def reopen_streams_on_cancel():
        return ADDON.getSetting("reopen_streams_on_cancel") == "true"

    @staticmethod
    def stall_recovery_dialog():
        return False

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
    def acestream_engine_host():
        try:
            val = ADDON.getSetting("acestream_host")
            return val.strip() if val and val.strip() else "127.0.0.1"
        except Exception:
            return "127.0.0.1"

    acestream_host = acestream_engine_host

    @staticmethod
    def acestream_engine_port():
        try:
            val = ADDON.getSetting("acestream_port")
            return int(val) if val else 6878
        except Exception:
            return 6878

    acestream_port = acestream_engine_port

    @staticmethod
    def acestream_cache_ttl():
        try:
            val = ADDON.getSetting("acestream_cache_ttl")
            return int(val) * 60 if val else 1800
        except Exception:
            return 1800

    @staticmethod
    def acestream_check_health():
        try:
            return ADDON.getSetting("acestream_check_health") != "false"
        except Exception:
            return True

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

    # ══════════════════════════════════════════════════════
    #  v3.5.6 — Rotten Tomatoes & Ratings Integration
    # ══════════════════════════════════════════════════════
    @staticmethod
    def rt_enabled():
        try:
            return ADDON.getSetting("rt_enabled") != "false"
        except Exception:
            return True

    @staticmethod
    def rt_show_consensus():
        try:
            return ADDON.getSetting("rt_show_consensus") != "false"
        except Exception:
            return True

