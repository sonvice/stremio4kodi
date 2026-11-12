"""
Scoring & Ranker Engine
Deduplicates releases across sources, applies RTN normalization,
and ranks streams based on user language (Castellano/Latino/VOSE), quality, and seeds.
"""

from typing import List, Dict
from resources.lib.mediacore.models import StreamRelease
from resources.lib.rtn import RTN
from resources.lib.spanish import detect_spanish, get_spanish_boost
from resources.lib.config import Config
from resources.lib.logger import log


class ScoringEngine:
    """Processes, enriches, deduplicates, and ranks stream releases."""

    def __init__(self):
        pass

    def normalize(self, release: StreamRelease):
        """Enriches release with RTN metadata if not already present."""
        raw_dict = dict(release.extra.get("raw") or {})
        if not raw_dict.get("title"):
            raw_dict["title"] = release.title
        if not raw_dict.get("name"):
            raw_dict["name"] = release.source_name
        if not raw_dict.get("seeds"):
            raw_dict["seeds"] = release.seeds
        if not raw_dict.get("size"):
            raw_dict["size"] = release.size_bytes or release.size_formatted

        meta = RTN.parse(raw_dict)

        if not release.quality or release.quality == "Unknown":
            release.quality = meta.get("resolution") or "Unknown"
        if not release.codec:
            release.codec = meta.get("codec") or ""
        if not release.hdr:
            release.hdr = meta.get("hdr") or ""
        if not release.audio_channels:
            release.audio_channels = meta.get("audio") or ""
        if not release.languages:
            release.languages = [meta.get("language")] if meta.get("language") else []
        if not release.variant or release.variant in ("Other", "VO", "V.O."):
            release.variant = meta.get("language") or release.variant or "V.O."
        if not release.size_formatted:
            release.size_formatted = meta.get("size") or ""
        if not release.seeds:
            release.seeds = meta.get("seeds") or 0
        if not release.is_debrid_cached:
            release.is_debrid_cached = meta.get("is_rd") or False
        if not release.debrid_provider:
            release.debrid_provider = meta.get("debrid_badge") or ""

        # Build colored Kodi display label
        badge = RTN.format_label(raw_dict)
        release.display_title = badge or release.title

    def deduplicate(self, releases: List[StreamRelease]) -> List[StreamRelease]:
        """
        Deduplicates releases by infoHash.
        If the same torrent is found on multiple sources (e.g. Torrentio and Jackett),
        merges them, takes max seeds, and credits all sources.
        """
        by_hash: Dict[str, StreamRelease] = {}
        unique_others: List[StreamRelease] = []

        for rel in releases:
            h = rel.info_hash
            if not h:
                unique_others.append(rel)
                continue

            if h in by_hash:
                existing = by_hash[h]
                # Merge sources
                if rel.source_name not in existing.source_name:
                    existing.source_name = f"{existing.source_name} / {rel.source_name}"
                # Max seeds
                if rel.seeds > existing.seeds:
                    existing.seeds = rel.seeds
                if rel.is_debrid_cached:
                    existing.is_debrid_cached = True
                    existing.debrid_provider = rel.debrid_provider
            else:
                by_hash[h] = rel

        return list(by_hash.values()) + unique_others

    def process_and_rank(self, releases: List[StreamRelease]) -> List[StreamRelease]:
        """Full pipeline: normalize -> deduplicate -> score & sort."""
        if not releases:
            return []

        # 1. Normalize each release with RTN
        for rel in releases:
            self.normalize(rel)

        # 2. Deduplicate
        deduped = self.deduplicate(releases)

        # 3. Calculate score for each release
        sort_by = (Config.torrent_sort() or "Seeds").lower()
        pref_quality = Config.torrent_quality() or "1080p"
        spanish_boost = Config.spanish_boost()
        filter_mode = Config.spanish_filter_mode()  # "boost", "only", "off"
        pref_variant = Config.spanish_variant()     # "all", "castellano", "latino", "dual"

        ranked: List[StreamRelease] = []
        for rel in deduped:
            # Language filter check ("only" mode)
            if filter_mode == "only" and rel.variant not in ("Castellano", "Latino", "Dual", "VOSE"):
                continue

            score = 0.0

            # Quality scoring
            q_scores = {"4K": 400, "1080p": 300, "720p": 200, "480p": 100, "Unknown": 50, "CAM": -500}
            base_q = q_scores.get(rel.quality, 50)
            score += base_q

            # Preferred quality bonus
            if rel.quality == pref_quality:
                score += 150

            # Spanish audio bonus
            if spanish_boost and filter_mode != "off":
                if rel.variant == "Castellano":
                    score += 500 if pref_variant in ("all", "castellano") else 200
                elif rel.variant == "Latino":
                    score += 500 if pref_variant in ("all", "latino") else 200
                elif rel.variant == "Dual":
                    score += 450
                elif rel.variant == "VOSE":
                    score += 100

            # Debrid cached bonus
            if rel.is_debrid_cached:
                score += 600

            # Seeds bonus (logarithmic scaling)
            import math
            if rel.seeds > 0:
                score += math.log10(rel.seeds + 1) * 50

            rel.score = score
            ranked.append(rel)

        # Sort according to setting
        if sort_by == "quality":
            ranked.sort(key=lambda r: (r.is_debrid_cached, 1 if r.seeds > 0 else 0, r.score, r.seeds), reverse=True)
        elif sort_by == "size":
            ranked.sort(key=lambda r: (r.is_debrid_cached, 1 if r.seeds > 0 else 0, r.size_bytes, r.seeds), reverse=True)
        else:
            # Default "seeds": Prioritizes cached debrid first, then active seeds (highest seeds first), then score
            ranked.sort(key=lambda r: (r.is_debrid_cached, 1 if r.seeds > 0 else 0, r.seeds, r.score), reverse=True)

        log(f"ScoringEngine ranked {len(ranked)} releases (from {len(releases)} raw)", level="info")
        return ranked
