# -*- coding: utf-8 -*-
"""
Automatic Subtitle Search and Fetcher for Stremio4Kodi.
Queries OpenSubtitles REST API & Stremio Subtitle Addons for Spanish subtitles (spa / es).
"""
import urllib.request
import json
import re
from resources.lib.logger import log
from resources.lib.config import Config

SUBTITLE_PROVIDERS = [
    "https://opensubtitles.strem.io",
    "https://v3-cinemeta.strem.io",
]

def fetch_subtitles(imdb_id, media_type="movie", season=None, episode=None, timeout=5):
    """
    Search and return a list of Spanish and English subtitle URLs for a given IMDb ID.
    Returns list of URLs: ["https://...", ...]
    """
    if not imdb_id:
        return []

    target_id = imdb_id
    if media_type in ("series", "tv") and season and episode:
        target_id = f"{imdb_id}:{season}:{episode}"

    es_sub_urls = []
    en_sub_urls = []

    for base_url in SUBTITLE_PROVIDERS:
        try:
            endpoint = f"{base_url}/subtitles/{media_type}/{target_id}.json"
            req = urllib.request.Request(
                endpoint,
                headers={
                    "User-Agent": "Stremio4Kodi/3.5",
                    "Accept": "application/json"
                }
            )
            resp = urllib.request.urlopen(req, timeout=timeout)
            data = json.loads(resp.read().decode("utf-8"))
            subs = data.get("subtitles", [])
            for sub in subs:
                lang = sub.get("lang", "").lower()
                url = sub.get("url", "")
                if not url:
                    continue
                if lang.startswith("spa") or lang.startswith("es"):
                    if url not in es_sub_urls:
                        es_sub_urls.append(url)
                elif lang.startswith("eng") or lang.startswith("en"):
                    if url not in en_sub_urls:
                        en_sub_urls.append(url)
            if es_sub_urls or en_sub_urls:
                log(f"Found subtitles (ES: {len(es_sub_urls)}, EN: {len(en_sub_urls)}) from {base_url}", level="info")
                break
        except Exception as e:
            log(f"Subtitle fetch error from {base_url}: {e}", level="debug")

    return es_sub_urls + en_sub_urls

# Alias for backwards compatibility
fetch_spanish_subtitles = fetch_subtitles
