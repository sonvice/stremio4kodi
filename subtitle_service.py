# -*- coding: utf-8 -*-
"""
OpenSubtitles v3 Subtitle Provider for Kodi.
Implements the xbmc.subtitle.module extension point.
Allows Kodi's native Subtitle Search window (OSD / 'T' key)
to search and download subtitles from OpenSubtitles v3 (Stremio)
without requiring any account, login, or API key.
"""
import os
import re
import sys
import json
import urllib.parse
import urllib.request
import xbmc
import xbmcgui
import xbmcplugin

from resources.lib.logger import log
from resources.lib.subtitles import (
    fetch_subtitles_rich,
    download_subtitle_file,
    LANG_META
)


def _get_current_media_info():
    """
    Extracts IMDB ID, media type, season, episode, and title
    from Kodi's active player or Stremio4kodi shared window properties.
    """
    info = {
        "imdb_id": None,
        "media_type": "movie",
        "season": None,
        "episode": None,
        "title": "",
        "year": ""
    }

    try:
        window = xbmcgui.Window(10000)
        cached_imdb = window.getProperty("stremio4kodi.current_imdb")
        if cached_imdb:
            info["imdb_id"] = cached_imdb
            info["media_type"] = window.getProperty("stremio4kodi.current_type") or "movie"
            info["season"] = window.getProperty("stremio4kodi.current_season") or None
            info["episode"] = window.getProperty("stremio4kodi.current_episode") or None
            info["title"] = window.getProperty("stremio4kodi.current_title") or ""
            return info
    except Exception:
        pass

    # Read from Kodi's VideoPlayer info labels
    try:
        imdb_label = xbmc.getInfoLabel("VideoPlayer.IMDBNumber")
        if imdb_label:
            imdb_clean = imdb_label.strip()
            if imdb_clean.startswith("tt"):
                info["imdb_id"] = imdb_clean
            elif imdb_clean.isdigit():
                info["imdb_id"] = f"tt{imdb_clean}"
    except Exception:
        pass

    try:
        tv_show = xbmc.getInfoLabel("VideoPlayer.TVShowTitle")
        title = xbmc.getInfoLabel("VideoPlayer.Title")
        season = xbmc.getInfoLabel("VideoPlayer.Season")
        episode = xbmc.getInfoLabel("VideoPlayer.Episode")
        year = xbmc.getInfoLabel("VideoPlayer.Year")

        if tv_show:
            info["media_type"] = "series"
            info["title"] = tv_show
            info["season"] = season if season and season.isdigit() else None
            info["episode"] = episode if episode and episode.isdigit() else None
        else:
            info["media_type"] = "movie"
            info["title"] = title

        info["year"] = year
    except Exception:
        pass

    # If still no imdb_id, attempt to search Cinemeta by title
    if not info["imdb_id"] and info["title"]:
        resolved = _resolve_imdb_by_title(info["title"], info["media_type"], info["year"])
        if resolved:
            info["imdb_id"] = resolved

    return info


def _resolve_imdb_by_title(title, media_type="movie", year=None):
    """Query Cinemeta catalog search to resolve title -> IMDb ID."""
    if not title:
        return None
    try:
        c_type = "series" if media_type in ("series", "tv") else "movie"
        url = f"https://v3-cinemeta.strem.io/catalog/{c_type}/top/search={urllib.parse.quote(title)}.json"
        req = urllib.request.Request(url, headers={"User-Agent": "Stremio4Kodi/3.7"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            metas = data.get("metas", [])
            if metas:
                if year:
                    for m in metas:
                        if str(year) in str(m.get("releaseInfo", "")):
                            return m.get("imdb_id") or m.get("id")
                return metas[0].get("imdb_id") or metas[0].get("id")
    except Exception as e:
        log(f"Error resolving IMDb ID for '{title}': {e}", level="debug")
    return None


def handle_search(handle, params):
    """Handle Kodi's subtitle search request."""
    info = _get_current_media_info()
    imdb_id = info["imdb_id"]
    media_type = info["media_type"]
    season = info["season"]
    episode = info["episode"]

    log(f"OpenSubtitles search: id={imdb_id} type={media_type} s={season} e={episode}", level="info")

    if not imdb_id:
        log("No IMDb ID found for active media", level="warning")
        xbmcplugin.endOfDirectory(handle)
        return

    # Languages requested by Kodi (e.g. "Spanish,English")
    raw_langs = params.get("languages", "")
    requested_langs = [l.strip().lower() for l in raw_langs.split(",") if l.strip()]

    subs = fetch_subtitles_rich(imdb_id, media_type, season, episode, timeout=8)
    if not subs:
        log(f"No subtitles found in OpenSubtitles for {imdb_id}", level="info")
        xbmcplugin.endOfDirectory(handle)
        return

    # Filter / sort by requested languages if specified
    def _rank(item):
        lang = item.get("lang", "").lower()
        if lang in ("spa", "es", "spl", "lat"):
            return 0
        if lang in ("eng", "en"):
            return 1
        return 2

    subs.sort(key=_rank)

    for s in subs:
        lang_code = s.get("lang", "").lower()
        meta = LANG_META.get(lang_code, {})
        lang_name = meta.get("name") or s.get("lang_name") or lang_code.upper()
        flag = meta.get("flag") or s.get("flag") or "🌐"
        clean_fn = s.get("filename", "subtitle.srt")

        # Format label and label2 for Kodi's subtitle dialog:
        # Label: Language name
        # Label2: Subtitle release / filename
        label = f"{flag} {lang_name}"
        label2 = clean_fn

        li = xbmcgui.ListItem(label=label, label2=label2)
        li.setProperty("sync", "true")
        
        is_hi = "sdh" in clean_fn.lower() or "hi" in clean_fn.lower()
        li.setProperty("hearing_imp", "true" if is_hi else "false")
        
        li.setArt({"icon": "5"})

        download_url = f"{sys.argv[0]}?action=download&sub_url={urllib.parse.quote_plus(s['url'])}&filename={urllib.parse.quote_plus(clean_fn)}"
        xbmcplugin.addDirectoryItem(handle=handle, url=download_url, listitem=li, isFolder=False)

    xbmcplugin.endOfDirectory(handle)


def handle_manualsearch(handle, params):
    """Handle Kodi's manual subtitle search query."""
    searchstring = params.get("searchstring", "")
    if not searchstring:
        kb = xbmc.Keyboard("", "Buscar subtítulos (Título o IMDb tt...)")
        kb.doModal()
        if kb.isConfirmed():
            searchstring = kb.getText()
        else:
            xbmcplugin.endOfDirectory(handle)
            return

    if not searchstring:
        xbmcplugin.endOfDirectory(handle)
        return

    imdb_id = None
    media_type = "movie"
    season = None
    episode = None

    if searchstring.strip().startswith("tt"):
        imdb_id = searchstring.strip()
    else:
        # Detect S01E01 pattern if typed by user
        se_match = re.search(r's(\d+)\s*e(\d+)', searchstring, re.IGNORECASE)
        if se_match:
            media_type = "series"
            season = se_match.group(1)
            episode = se_match.group(2)
            title_clean = re.sub(r's\d+\s*e\d+.*', '', searchstring, flags=re.IGNORECASE).strip()
            imdb_id = _resolve_imdb_by_title(title_clean, "series")
        else:
            imdb_id = _resolve_imdb_by_title(searchstring, "movie")
            if not imdb_id:
                imdb_id = _resolve_imdb_by_title(searchstring, "series")
                if imdb_id:
                    media_type = "series"

    if not imdb_id:
        try:
            xbmcgui.Dialog().notification("OpenSubtitles", "No se encontró el título", xbmcgui.NOTIFICATION_INFO, 2500)
        except Exception:
            pass
        xbmcplugin.endOfDirectory(handle)
        return

    subs = fetch_subtitles_rich(imdb_id, media_type, season, episode, timeout=8)
    for s in subs:
        lang_code = s.get("lang", "").lower()
        meta = LANG_META.get(lang_code, {})
        lang_name = meta.get("name") or s.get("lang_name") or lang_code.upper()
        flag = meta.get("flag") or s.get("flag") or "🌐"
        clean_fn = s.get("filename", "subtitle.srt")

        label = f"{flag} {lang_name}"
        label2 = clean_fn

        li = xbmcgui.ListItem(label=label, label2=label2)
        li.setProperty("sync", "true")
        is_hi = "sdh" in clean_fn.lower() or "hi" in clean_fn.lower()
        li.setProperty("hearing_imp", "true" if is_hi else "false")
        li.setArt({"icon": "5"})

        download_url = f"{sys.argv[0]}?action=download&sub_url={urllib.parse.quote_plus(s['url'])}&filename={urllib.parse.quote_plus(clean_fn)}"
        xbmcplugin.addDirectoryItem(handle=handle, url=download_url, listitem=li, isFolder=False)

    xbmcplugin.endOfDirectory(handle)


def handle_download(handle, params):
    """Download the selected subtitle file and deliver it to Kodi's player."""
    sub_url = urllib.parse.unquote_plus(params.get("sub_url", ""))
    filename = urllib.parse.unquote_plus(params.get("filename", "subtitle.srt"))

    if not sub_url:
        log("No subtitle URL provided for download", level="error")
        xbmcplugin.endOfDirectory(handle)
        return

    log(f"Downloading subtitle: {filename} from {sub_url}", level="info")
    local_path = download_subtitle_file(sub_url, filename)

    if local_path and os.path.exists(local_path):
        li = xbmcgui.ListItem(label=local_path)
        xbmcplugin.addDirectoryItem(handle=handle, url=local_path, listitem=li, isFolder=False)
        log(f"Subtitle delivered to Kodi: {local_path}", level="info")

        # Directly inject to active player as well for instantaneous playback sync
        try:
            player = xbmc.Player()
            if player.isPlaying():
                player.setSubtitles(local_path)
                player.showSubtitles(True)
                log(f"Direct player.setSubtitles applied: {local_path}", level="info")
        except Exception as e:
            log(f"Direct setSubtitles warning: {e}", level="debug")
    else:
        log("Failed to download subtitle file", level="error")

    xbmcplugin.endOfDirectory(handle)


def handle_action(handle, params):
    """Entry point when invoked with handle and params."""
    action = params.get("action", "")
    log(f"subtitle_service dispatch: action='{action}'", level="info")

    if action == "search":
        handle_search(handle, params)
    elif action == "manualsearch":
        handle_manualsearch(handle, params)
    elif action == "download":
        handle_download(handle, params)
    else:
        xbmcplugin.endOfDirectory(handle)


if __name__ == "__main__":
    try:
        handle = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else -1
        qs = sys.argv[2].lstrip("?") if len(sys.argv) > 2 else ""
        params = {k: v[0] for k, v in urllib.parse.parse_qs(qs).items()}
        handle_action(handle, params)
    except Exception as e:
        log(f"Exception in subtitle_service main: {e}", level="error")
        if len(sys.argv) > 1 and sys.argv[1].isdigit():
            try:
                xbmcplugin.endOfDirectory(int(sys.argv[1]))
            except Exception:
                pass
