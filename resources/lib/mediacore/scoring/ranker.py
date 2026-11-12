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
        raw_dict = {
            "title": release.title,
            "name": release.source_name,
            "size": release.size_bytes,
            "seeds": release.seeds,
            "url": release.url,
            "infoHash": release.info_hash,
        }
        RTN.normalize_stream(raw_dict)

        if not release.quality or release.quality == "Unknown":
            release.quality = raw_dict.get("_quality", "Unknown")
        if not release.codec:
            release.codec = raw_dict.get("_codec", "")
        if not release.hdr:
            release.hdr = raw_dict.get("_hdr", "")
        if not release.audio_channels:
            release.audio_channels = raw_dict.get("_audio", "")
        if not release.languages:
            release.languages = raw_dict.get("_languages", [])
        if not release.variant or release.variant == "Other":
            release.variant = raw_dict.get("_variant", "Other")
        if not release.size_formatted:
            release.size_formatted = raw_dict.get("_size", "")
        if not release.seeds and raw_dict.get("_seeds"):
            release.seeds = raw_dict.get("_seeds", 0)

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
            ranked.sort(key=lambda r: (r.is_debrid_cached, r.score, r.seeds), reverse=True)
        elif sort_by == "size":
            ranked.sort(key=lambda r: (r.is_debrid_cached, r.size_bytes), reverse=True)
        else:
            # Default "seeds" / smart score
            ranked.sort(key=lambda r: (r.is_debrid_cached, r.score, r.seeds), reverse=True)

        log(f"ScoringEngine ranked {len(ranked)} releases (from {len(releases)} raw)", level="info")
        return ranked
