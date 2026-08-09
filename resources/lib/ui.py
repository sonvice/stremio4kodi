# -*- coding: utf-8 -*-
"""
UI — Helper functions for building Kodi ListItems and dialogs.

Centralizes all UI construction so the router stays clean.
"""
import xbmcgui
import xbmcplugin
from urllib.parse import urlencode

from resources.lib.logger import log


def build_url(base_url, **params):
    """Build a plugin:// URL with query parameters."""
    return f"{base_url}?{urlencode(params)}"


def add_directory_item(handle, label, action, base_url, is_folder=True,
                       icon="DefaultFolder.png", fanart="", poster="",
                       plot="", year="", imdb_id="", media_type="",
                       context_menu=None, **extra_params):
    """
    Add a navigable directory item (folder or playable).

    Args:
        handle:       Kodi plugin handle (int).
        label:        Display text.
        action:       Router action name.
        base_url:     Plugin base URL.
        is_folder:    True for folders, False for playable items.
        icon:         Thumbnail path or Kodi icon name.
        poster:       Poster image URL.
        plot:         Description / synopsis.
        context_menu: List of (label, action_string) tuples.
        **extra_params: Additional URL params (imdb_id, media_type, etc.)
    """
    # Remove non-URL params that should NOT go into the URL
    rating = extra_params.pop("rating", "")
    genres = extra_params.pop("genres", "")

    params = {"action": action}
    if imdb_id:
        params["imdb_id"] = imdb_id
    if media_type:
        params["media_type"] = media_type
    params.update(extra_params)

    url = build_url(base_url, **params)

    li = xbmcgui.ListItem(label=label)

    # Art
    art = {"icon": icon}
    if poster:
        art["thumb"] = poster
        art["poster"] = poster
    if fanart:
        art["fanart"] = fanart
    li.setArt(art)

    # Info
    try:
        info_tag = li.getVideoInfoTag()
        if plot:
            try:
                info_tag.setPlot(str(plot))
            except Exception:
                pass
        if year:
            try:
                info_tag.setYear(int(year))
            except Exception:
                pass
        if media_type in ("movie", "series", "tvshow"):
            try:
                info_tag.setMediaType("movie" if media_type == "movie" else "tvshow")
            except Exception:
                pass
        if imdb_id:
            try:
                info_tag.setIMDBNumber(str(imdb_id))
            except Exception:
                pass
        if rating:
            try:
                info_tag.setRating(float(rating), votes=0, type="imdb", isdefault=True)
            except Exception:
                pass
        if genres:
            try:
                genre_list = [g.strip() for g in str(genres).split(",") if g.strip()]
                if genre_list:
                    info_tag.setGenres(genre_list)
            except Exception:
                pass
    except Exception as e:
        log(f"InfoTag error (non-fatal): {e}", level="debug")

    # Context menu
    if context_menu:
        li.addContextMenuItems(context_menu)

    # Playable flag
    if not is_folder:
        li.setProperty("IsPlayable", "true")

    xbmcplugin.addDirectoryItem(
        handle=handle,
        url=url,
        listitem=li,
        isFolder=is_folder,
    )


def add_stream_item(handle, stream, base_url, resolver, imdb_id, media_type,
                    meta_title=""):
    """
    Add a playable stream item with quality/seeds labels.
    """
    quality = resolver.get_quality_label(stream)
    seeds = resolver.get_seeds_label(stream)
    size = resolver.get_size_label(stream)

    title = stream.get("title", "") or stream.get("name", "Unknown source")
    title_short = title.split("\n")[0][:80]

    addon_name = stream.get("_addon", "")
    label_parts = [quality, title_short]
    if seeds:
        label_parts.append(seeds)
    if size:
        label_parts.append(f"[COLOR silver]{size}[/COLOR]")
    if addon_name:
        label_parts.append(f"[COLOR grey][{addon_name}][/COLOR]")

    label = "  ".join(p for p in label_parts if p)

    url = build_url(
        base_url,
        action="play",
        imdb_id=imdb_id,
        media_type=media_type,
        stream_idx="__IDX__",
        title=meta_title,
    )

    li = xbmcgui.ListItem(label=label)
    li.setProperty("IsPlayable", "true")

    info_tag = li.getVideoInfoTag()
    info_tag.setPlot(title)

    xbmcplugin.addDirectoryItem(
        handle=handle,
        url=url,
        listitem=li,
        isFolder=False,
    )


def end_directory(handle, content_type="videos", sort_methods=None,
                  update_listing=False, cache_to_disc=True):
    """Finalize the directory listing."""
    if content_type:
        xbmcplugin.setContent(handle, content_type)

    if sort_methods:
        for method in sort_methods:
            xbmcplugin.addSortMethod(handle, method)
    else:
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_UNSORTED)

    xbmcplugin.endOfDirectory(
        handle,
        succeeded=True,
        updateListing=update_listing,
        cacheToDisc=cache_to_disc,
    )


def show_notification(message, heading="Stremio4Kodi", icon=xbmcgui.NOTIFICATION_INFO,
                      time=3000):
    """Display a Kodi notification popup."""
    xbmcgui.Dialog().notification(heading, message, icon, time)


def show_ok_dialog(heading, message):
    xbmcgui.Dialog().ok(heading, message)


def show_input(heading="Search", input_type=xbmcgui.INPUT_ALPHANUM):
    """Show a keyboard input dialog and return the text."""
    return xbmcgui.Dialog().input(heading, type=input_type)


def show_select(heading, options):
    """Show a selection dialog. Returns selected index or -1."""
    return xbmcgui.Dialog().select(heading, options)


def show_progress(heading, message=""):
    """Create and return a progress dialog."""
    dialog = xbmcgui.DialogProgress()
    dialog.create(heading, message)
    return dialog
