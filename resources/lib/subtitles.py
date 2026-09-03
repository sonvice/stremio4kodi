# -*- coding: utf-8 -*-
"""
Automatic Subtitle Search, Fetcher & Downloader for Stremio4Kodi.
Queries OpenSubtitles v3 / REST APIs for all languages (with priority for Spanish & English)
and provides on-demand download & player attachment.
"""
import os
import json
import re
import urllib.request
import urllib.parse
from resources.lib.logger import log
from resources.lib.config import Config

SUBTITLE_PROVIDERS = [
    "https://opensubtitles-v3.strem.io",
    "https://opensubtitles.strem.io",
    "https://v3-cinemeta.strem.io",
]

LANG_META = {
    "spa": {"name": "Español (Castellano)", "flag": "🇪🇸", "tag": "ES"},
    "es": {"name": "Español (Castellano)", "flag": "🇪🇸", "tag": "ES"},
    "spl": {"name": "Español (Latino)", "flag": "🇲🇽", "tag": "LAT"},
    "lat": {"name": "Español (Latino)", "flag": "🇲🇽", "tag": "LAT"},
    "eng": {"name": "Inglés (English)", "flag": "🇬🇧", "tag": "EN"},
    "en": {"name": "Inglés (English)", "flag": "🇬🇧", "tag": "EN"},
    "por": {"name": "Portugués", "flag": "🇵🇹", "tag": "PT"},
    "pt": {"name": "Portugués", "flag": "🇵🇹", "tag": "PT"},
    "pob": {"name": "Portugués (Brasil)", "flag": "🇧🇷", "tag": "BR"},
    "fre": {"name": "Francés (Français)", "flag": "🇫🇷", "tag": "FR"},
    "fra": {"name": "Francés (Français)", "flag": "🇫🇷", "tag": "FR"},
    "fr": {"name": "Francés (Français)", "flag": "🇫🇷", "tag": "FR"},
    "ger": {"name": "Alemán (Deutsch)", "flag": "🇩🇪", "tag": "DE"},
    "deu": {"name": "Alemán (Deutsch)", "flag": "🇩🇪", "tag": "DE"},
    "de": {"name": "Alemán (Deutsch)", "flag": "🇩🇪", "tag": "DE"},
    "ita": {"name": "Italiano", "flag": "🇮🇹", "tag": "IT"},
    "it": {"name": "Italiano", "flag": "🇮🇹", "tag": "IT"},
    "rus": {"name": "Ruso", "flag": "🇷🇺", "tag": "RU"},
    "ru": {"name": "Ruso", "flag": "🇷🇺", "tag": "RU"},
    "dan": {"name": "Danés", "flag": "🇩🇰", "tag": "DA"},
    "swe": {"name": "Sueco", "flag": "🇸🇪", "tag": "SV"},
    "nor": {"name": "Noruego", "flag": "🇳🇴", "tag": "NO"},
    "fin": {"name": "Finés", "flag": "🇫🇮", "tag": "FI"},
    "dut": {"name": "Holandés", "flag": "🇳🇱", "tag": "NL"},
    "nld": {"name": "Holandés", "flag": "🇳🇱", "tag": "NL"},
    "pol": {"name": "Polaco", "flag": "🇵🇱", "tag": "PL"},
    "jpn": {"name": "Japonés", "flag": "🇯🇵", "tag": "JA"},
    "kor": {"name": "Coreano", "flag": "🇰🇷", "tag": "KO"},
    "chi": {"name": "Chino", "flag": "🇨🇳", "tag": "ZH"},
    "zho": {"name": "Chino", "flag": "🇨🇳", "tag": "ZH"},
}


def fetch_subtitles_rich(imdb_id, media_type="movie", season=None, episode=None, timeout=6):
    """
    Search OpenSubtitles and return a rich list of subtitle metadata dictionaries.
    Each item contains:
      - id: str
      - lang: str (e.g. 'spa', 'eng')
      - lang_name: str (e.g. 'Español')
      - flag: str (e.g. '🇪🇸')
      - filename: str
      - release: str
      - format: str
      - fps: float or None
      - url: str
    """
    if not imdb_id:
        return []

    base_imdb = imdb_id.split(":")[0] if ":" in imdb_id else imdb_id
    target_id = base_imdb
    if media_type in ("series", "tv") and season and episode:
        target_id = f"{base_imdb}:{season}:{episode}"
    elif ":" in imdb_id:
        target_id = imdb_id

    results = []
    seen_urls = set()

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

            for s in subs:
                url = s.get("url", "")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)

                lang_code = s.get("lang", "").lower()
                meta = LANG_META.get(lang_code, {
                    "name": lang_code.upper() if lang_code else "Desconocido",
                    "flag": "🌐",
                    "tag": lang_code.upper()
                })

                filename = s.get("subtitleFileName") or s.get("movieReleaseName") or f"{lang_code}_{s.get('id', 'sub')}.srt"
                release = s.get("movieReleaseName") or s.get("releaseGroup") or ""
                fmt = s.get("releaseFormat") or ("SRT" if filename.endswith(".srt") else "")
                fps_milli = s.get("fpsMilli")
                fps = round(fps_milli / 1000.0, 3) if fps_milli else None

                results.append({
                    "id": str(s.get("id", len(results))),
                    "lang": lang_code,
                    "lang_name": meta["name"],
                    "flag": meta["flag"],
                    "tag": meta["tag"],
                    "filename": filename,
                    "release": release,
                    "format": fmt,
                    "fps": fps,
                    "url": url,
                })

            if results:
                log(f"Fetched {len(results)} subtitles from {base_url}", level="info")
                break
        except Exception as e:
            log(f"OpenSubtitles fetch error from {base_url}: {e}", level="debug")

    def _sort_key(item):
        lang = item["lang"]
        if lang in ("spa", "es", "spl", "lat"):
            return 0
        if lang in ("eng", "en"):
            return 1
        return 2

    results.sort(key=_sort_key)
    return results


def fetch_subtitles(imdb_id, media_type="movie", season=None, episode=None, timeout=5):
    """
    Backwards-compatible wrapper returning a list of URLs (Spanish + English).
    """
    rich = fetch_subtitles_rich(imdb_id, media_type, season, episode, timeout=timeout)
    return [r["url"] for r in rich if r.get("lang") in ("spa", "es", "spl", "lat", "eng", "en")]


# Alias for backwards compatibility
fetch_spanish_subtitles = fetch_subtitles


def download_subtitle_file(url, filename=None):
    """
    Downloads a subtitle file from the given URL and saves it to local Kodi temp/subtitles directory.
    Returns the absolute local path to the .srt file, or None on error.
    """
    try:
        import xbmcvfs
        temp_dir = xbmcvfs.translatePath("special://temp/subtitles/")
    except Exception:
        import tempfile
        temp_dir = os.path.join(tempfile.gettempdir(), "stremio_subtitles")

    os.makedirs(temp_dir, exist_ok=True)

    if not filename:
        filename = "subtitle.srt"
    else:
        filename = re.sub(r'[\\/*?:"<>|]', "", filename)
        if not filename.endswith(".srt"):
            filename += ".srt"

    local_path = os.path.join(temp_dir, filename)

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Accept": "*/*"
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read()

        with open(local_path, "wb") as f:
            f.write(content)

        log(f"Subtitle successfully downloaded to {local_path} ({len(content)} bytes)", level="info")
        return local_path
    except Exception as e:
        log(f"Error downloading subtitle from {url}: {e}", level="error")
        return None


def apply_subtitle_to_player(local_path):
    """
    Injects and enables the local subtitle file in the currently running Kodi Player.
    """
    try:
        import xbmc
        player = xbmc.Player()
        if player.isPlaying():
            player.setSubtitles(local_path)
            player.showSubtitles(True)
            log(f"Subtitle injected to active player: {local_path}", level="info")
            return True
        return False
    except Exception as e:
        log(f"Error injecting subtitle to player: {e}", level="error")
        return False


def prepare_subtitles_for_playback(imdb_id, media_type="movie", season=None, episode=None, max_per_lang=2):
    """
    Fetches rich subtitle listings from OpenSubtitles, downloads the top Spanish and English
    subtitles in parallel, and saves them with clean, descriptive filenames:
      e.g. 'Español (Castellano) - Las.Tortugas.Ninja.S01E01.1080p.spa.srt'
    Returns a list of local absolute file paths ready for Kodi's setSubtitles().
    """
    from concurrent.futures import ThreadPoolExecutor

    rich_subs = fetch_subtitles_rich(imdb_id, media_type, season, episode, timeout=6)
    if not rich_subs:
        return []

    es_subs = [s for s in rich_subs if s.get("lang") in ("spa", "es", "spl", "lat")][:max_per_lang]
    en_subs = [s for s in rich_subs if s.get("lang") in ("eng", "en")][:max_per_lang]
    selected = es_subs + en_subs

    downloaded_paths = []

    def _worker(s):
        fn = s.get("filename", "")
        clean_fn = re.sub(r"\.srt$", "", fn, flags=re.I)
        clean_fn = re.sub(r"[^\w\.\-\s]", "", clean_fn).strip()
        clean_fn = clean_fn[:45]
        lang = s.get("lang", "es")
        lang_name = s.get("lang_name", "Subtítulo")
        target_name = f"{lang_name} - {clean_fn}.{lang}.srt"
        return download_subtitle_file(s.get("url"), target_name)

    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(_worker, selected))
            for p in results:
                if p and os.path.exists(p):
                    downloaded_paths.append(p)
    except Exception as e:
        log(f"Error in prepare_subtitles_for_playback: {e}", level="debug")

    return downloaded_paths

