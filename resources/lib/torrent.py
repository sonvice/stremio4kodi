# -*- coding: utf-8 -*-
"""
TorrentResolver — Resolve streams via Elementum, Quasar, or Real-Debrid.
v2: Added RD support. RD cached streams become direct HTTP = instant play.
"""
import re
from urllib.parse import quote

from resources.lib.config import Config
from resources.lib.debrid import RealDebrid
from resources.lib.spanish import detect_spanish, get_spanish_label, get_spanish_boost
from resources.lib.logger import log

QUALITY_PATTERNS = {
    "4K":    re.compile(r"(2160p|4k|uhd)", re.IGNORECASE),
    "1080p": re.compile(r"1080p", re.IGNORECASE),
    "720p":  re.compile(r"720p", re.IGNORECASE),
    "480p":  re.compile(r"(480p|sd)", re.IGNORECASE),
}

TRACKERS = [
    "udp://tracker.opentrackr.org:1337/announce",
    "udp://open.stealth.si:80/announce",
    "udp://tracker.torrent.eu.org:451/announce",
    "udp://tracker.openbittorrent.com:6969/announce",
    "udp://exodus.desync.com:6969/announce",
]


class TorrentResolver:
    def __init__(self):
        self.engine = Config.torrent_engine()
        self.rd = RealDebrid()

    def resolve(self, stream):
        """
        Resolve a stream dict to a playable URL.
        Priority: Real-Debrid (always tried first) > Elementum/Quasar > Direct HTTP
        """
        url = stream.get("url", "")
        info_hash = stream.get("infoHash", "")
        file_idx = stream.get("fileIdx")

        # ── Try Real-Debrid first for ANY hash (cache API is unreliable) ──
        if info_hash and self.rd.is_configured():
            log(f"Resolving via Real-Debrid: {info_hash}", level="info")
            rd_url = self.rd.resolve(info_hash, file_idx)
            if rd_url:
                return rd_url
            log("RD resolve failed, falling back to torrent engine", level="warning")

        # ── infoHash → magnet → engine ─────────────────────
        if info_hash:
            magnet = self._build_magnet(info_hash, stream)
            return self._to_engine_url(magnet, stream)

        # ── magnet: link ───────────────────────────────────
        if url.startswith("magnet:"):
            # Try RD if enabled
            if self.rd.is_configured():
                rd_url = self.rd.resolve(url, file_idx)
                if rd_url:
                    return rd_url
            return self._to_engine_url(url, stream)

        # ── HTTP .torrent file ─────────────────────────────
        if url.startswith("http") and ".torrent" in url:
            return self._to_engine_url(url, stream)

        # ── Direct HTTP stream ─────────────────────────────
        if url.startswith("http"):
            return url

        log(f"Unresolvable: {stream.get('title', '?')}", level="warning")
        return None

    def resolve_magnet(self, magnet_uri):
        """Resolve a raw magnet URI (from manual input)."""
        if self.rd.is_configured():
            rd_url = self.rd.resolve(magnet_uri)
            if rd_url:
                return rd_url, "direct"
        engine_url = self._to_engine_url(magnet_uri, {})
        return engine_url, "plugin"

    def _to_engine_url(self, uri, stream):
        encoded = quote(uri, safe="")
        file_idx = stream.get("fileIdx") if isinstance(stream, dict) else None

        if self.engine == "Elementum":
            base = f"plugin://plugin.video.elementum/play?uri={encoded}"
            if file_idx is not None:
                base += f"&oindex={file_idx}"
            return base
        elif self.engine == "Quasar":
            base = f"plugin://plugin.video.quasar/play?uri={encoded}"
            if file_idx is not None:
                base += f"&index={file_idx}"
            return base
        return uri

    def _build_magnet(self, info_hash, stream):
        title = stream.get("title", "") or stream.get("name", "Unknown")
        dn = re.sub(r"\[.*?\]", "", title.split("\n")[0]).strip()
        dn = re.sub(r"\s+", ".", dn)[:100]

        magnet = f"magnet:?xt=urn:btih:{info_hash}&dn={quote(dn, safe='')}"
        for tr in TRACKERS:
            magnet += f"&tr={quote(tr, safe='')}"
        return magnet

    # ── Sorting & Filtering ────────────────────────────────
    def filter_by_quality(self, streams):
        preferred = Config.torrent_quality()
        if preferred == "Any":
            return streams
        pattern = QUALITY_PATTERNS.get(preferred)
        if not pattern:
            return streams
        filtered = [
            s for s in streams
            if pattern.search(s.get("title", "") or s.get("name", ""))
        ]
        return filtered if filtered else streams

    def filter_spanish(self, streams):
        """Filter/tag streams based on Spanish language preference."""
        mode = Config.spanish_filter_mode()
        if mode == "off":
            return streams

        for s in streams:
            title = s.get("title", "") or s.get("name", "")
            s["_spanish"] = detect_spanish(title)

        if mode == "only":
            variant_pref = Config.spanish_variant()
            filtered = []
            for s in streams:
                info = s.get("_spanish", {})
                if not info.get("is_spanish"):
                    continue
                if variant_pref == "castellano" and info.get("variant") not in ("CAST", "ESP"):
                    continue
                if variant_pref == "latino" and info.get("variant") not in ("LAT", "LAT-MX"):
                    continue
                if variant_pref == "dual" and info.get("variant") != "DUAL":
                    continue
                filtered.append(s)
            return filtered if filtered else streams

        return streams

    def sort_streams(self, streams):
        """Sort by: Spanish boost > RD cached > user preference."""
        sort_by = Config.torrent_sort()
        spanish_on = Config.spanish_boost() and Config.spanish_filter_mode() != "off"

        def _sort_key(s):
            esp_boost = 0
            if spanish_on:
                esp_score = get_spanish_boost(s)
                if esp_score >= 50:
                    esp_boost = esp_score * 10000

            rd_boost = 1000000 if s.get("_rd_cached") and Config.rd_priority() else 0

            if sort_by == "Seeds":
                return esp_boost + rd_boost + self._extract_seeds(s)
            elif sort_by == "Quality":
                return esp_boost + rd_boost + self._quality_score(s)
            elif sort_by == "Size":
                return esp_boost + rd_boost + self._extract_size_gb(s)
            return esp_boost + rd_boost

        return sorted(streams, key=_sort_key, reverse=True)

    def _extract_seeds(self, s):
        seeds = s.get("seeds", 0)
        if not seeds:
            title = s.get("title", "") or s.get("name", "")
            match = re.search(r"(?:👤|seeds?[:\s])\s*(\d+)", title, re.IGNORECASE)
            if match:
                seeds = int(match.group(1))
        return seeds

    def _quality_score(self, s):
        title = (s.get("title", "") or s.get("name", "")).lower()
        if "2160p" in title or "4k" in title:
            return 4
        if "1080p" in title:
            return 3
        if "720p" in title:
            return 2
        if "480p" in title:
            return 1
        return 0

    def _extract_size_gb(self, s):
        title = s.get("title", "") or s.get("name", "")
        match = re.search(r"([\d.]+)\s*GB", title, re.IGNORECASE)
        if match:
            return float(match.group(1))
        match = re.search(r"([\d.]+)\s*MB", title, re.IGNORECASE)
        if match:
            return float(match.group(1)) / 1024
        return 0

    # ── Display labels ─────────────────────────────────────
    def get_quality_label(self, stream):
        title = (stream.get("title", "") or stream.get("name", "")).lower()
        if "2160p" in title or "4k" in title:
            return "[COLOR gold]4K[/COLOR]"
        if "1080p" in title:
            return "[COLOR lime]1080p[/COLOR]"
        if "720p" in title:
            return "[COLOR cyan]720p[/COLOR]"
        if "480p" in title:
            return "[COLOR grey]480p[/COLOR]"
        return ""

    def get_seeds_label(self, stream):
        seeds = self._extract_seeds(stream)
        if seeds > 50:
            return f"[COLOR lime]S:{seeds}[/COLOR]"
        elif seeds > 5:
            return f"[COLOR yellow]S:{seeds}[/COLOR]"
        elif seeds > 0:
            return f"[COLOR red]S:{seeds}[/COLOR]"
        return ""

    def get_size_label(self, stream):
        title = stream.get("title", "") or stream.get("name", "")
        match = re.search(r"([\d.]+\s*(?:GB|MB))", title, re.IGNORECASE)
        return match.group(1) if match else ""

    def get_rd_label(self, stream):
        if stream.get("_rd_cached"):
            return "[COLOR magenta][RD+][/COLOR]"
        return ""

    def get_spanish_tag(self, stream):
        return get_spanish_label(stream)
