# -*- coding: utf-8 -*-
"""
Router — URL dispatcher v3.2.
v3.2: AceStream support (replaces Live TV), fixed platform duplication,
      manual acestream hash/URL input.
"""
import sys
import json
from urllib.parse import parse_qs, urlencode, quote

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon

from resources.lib.stremio import StremioClient
from resources.lib.torrent import TorrentResolver
from resources.lib.debrid import RealDebrid
from resources.lib.trakt import Trakt
from resources.lib.cache import CacheDB
from resources.lib.config import Config
from resources.lib.logger import log
from resources.lib import ui
from resources.lib.dht_search import BitsearchClient


class Router:
    def __init__(self):
        self.stremio = StremioClient()
        self.resolver = TorrentResolver()
        self.rd = RealDebrid()
        self.trakt = Trakt()
        self.cache = CacheDB()
        self.bitsearch = BitsearchClient()

    def dispatch(self, argv):
        self.base_url = argv[0]
        self.handle = int(argv[1])
        self.params = {}

        if len(argv) > 2 and argv[2]:
            self.params = {k: v[0] for k, v in parse_qs(argv[2].lstrip("?")).items()}

        action = self.params.get("action", "")
        log(f"Dispatch: {action} | {self.params}", level="debug")

        routes = {
            "":                self._main_menu,
            "movies":          self._movies,
            "series":          self._series,
            "catalog":         self._catalog,
            "genres":          self._genres,
            "genre_list":      self._genre_list,
            "seasons":         self._seasons,
            "episodes":        self._episodes,
            "streams":         self._streams,
            "play":            self._play,
            "search":          self._search,
            "search_results":  self._search_results,
            "dht_search":      self._dht_search,
            "trending":        self._trending,
            "manual_torrent":  self._manual_torrent,
            "favorites":       self._favorites,
            "toggle_favorite": self._toggle_favorite,
            "history":         self._history,
            "continue_watching": self._continue_watching,
            "trakt_menu":      self._trakt_menu,
            "trakt_auth":      self._trakt_auth,
            "trakt_watchlist": self._trakt_watchlist,
            "trakt_recommendations": self._trakt_recommendations,
            "trakt_trending":  self._trakt_trending,
            "trakt_add":       self._trakt_add,
            "trakt_remove":    self._trakt_remove,
            "clear_cache":     self._clear_cache,
            "clear_history":   self._clear_history,
            "settings":        self._settings,
            # v3 routes
            "platforms":           self._platforms,
            "platform_type":       self._platform_type,
            "platform_catalog":    self._platform_catalog,
            # v3.2: AceStream (replaces livetv)
            "acestream":           self._acestream,
            "acestream_group":     self._acestream_group,
            "acestream_play":      self._acestream_play,
            "acestream_refresh":   self._acestream_refresh,
            "acestream_all":       self._acestream_all,
            "acestream_manual":    self._acestream_manual,
        }

        handler = routes.get(action, self._main_menu)
        try:
            handler()
        except Exception as e:
            log(f"Error [{action}]: {e}", level="error")
            import traceback
            log(traceback.format_exc(), level="error")
            ui.show_notification(str(e), icon=xbmcgui.NOTIFICATION_ERROR)

    # ══════════════════════════════════════════════════════
    #  MAIN MENU
    # ══════════════════════════════════════════════════════
    def _main_menu(self):
        items = [
            ("Peliculas",           "movies",             "DefaultMovies.png"),
            ("Series",              "series",             "DefaultTVShows.png"),
            ("Buscar",              "search",             "DefaultAddonsSearch.png"),
            ("Buscador DHT",        "dht_search",         "DefaultAddonsSearch.png"),
            ("Trending Torrents",   "trending",           "DefaultTVShows.png"),
            ("Generos",             "genres",             "DefaultGenre.png"),
        ]

        # v3: Streaming Platforms
        try:
            if Config.streaming_catalogs_enabled():
                items.append(("Plataformas (Netflix, HBO, Disney+...)", "platforms", "DefaultStudios.png"))
        except Exception:
            pass

        # v3.2: AceStream (replaces Live TV)
        try:
            if Config.acestream_enabled():
                items.append(("AceStream / TV en Directo", "acestream", "DefaultPVRTVChannels.png"))
        except Exception:
            pass

        items.extend([
            ("Seguir viendo",       "continue_watching",  "DefaultInProgressShows.png"),
            ("Favoritos",           "favorites",          "DefaultFavourites.png"),
            ("Historial",           "history",            "DefaultRecentlyAddedEpisodes.png"),
            ("Pegar Magnet/Torrent","manual_torrent",     "DefaultNetwork.png"),
        ])

        if Config.trakt_enabled():
            items.append(("Trakt", "trakt_menu", "DefaultAddonProgram.png"))

        items.append(("Ajustes", "settings", "DefaultAddonProgram.png"))

        for label, action, icon in items:
            ui.add_directory_item(
                handle=self.handle, label=label, action=action,
                base_url=self.base_url, icon=icon,
            )
        ui.end_directory(self.handle, content_type="")

    # ══════════════════════════════════════════════════════
    #  MOVIES / SERIES
    # ══════════════════════════════════════════════════════
    def _movies(self):
        self._list_catalogs("movie")

    def _series(self):
        self._list_catalogs("series")

    def _list_catalogs(self, media_type):
        catalogs = self.stremio.get_catalogs_for_type(media_type)
        if not catalogs:
            ui.show_notification("No catalogs found. Check addon URLs.")
            ui.end_directory(self.handle)
            return
        for cat in catalogs:
            label = f"{cat['name']} ({cat['addon_name']})"
            ui.add_directory_item(
                handle=self.handle, label=label, action="catalog",
                base_url=self.base_url,
                icon="DefaultMovies.png" if media_type == "movie" else "DefaultTVShows.png",
                media_type=media_type,
                addon_url=cat["addon_url"], catalog_id=cat["catalog_id"],
            )
        ui.end_directory(self.handle)

    # ══════════════════════════════════════════════════════
    #  CATALOG
    # ══════════════════════════════════════════════════════
    def _catalog(self):
        addon_url = self.params.get("addon_url", "")
        catalog_id = self.params.get("catalog_id", "")
        media_type = self.params.get("media_type", "movie")
        skip = int(self.params.get("skip", "0"))

        extra = f"skip={skip}" if skip > 0 else ""
        items = self.stremio.get_catalog(addon_url, media_type, catalog_id, extra)

        if not items:
            ui.show_notification("No items found.")
            ui.end_directory(self.handle)
            return

        items = self.stremio.dedup_items(items)
        self._render_item_list(items, media_type)

        per_page = Config.items_per_page()
        if len(items) >= per_page:
            ui.add_directory_item(
                handle=self.handle, label="[B]>> Siguiente pagina[/B]",
                action="catalog", base_url=self.base_url,
                media_type=media_type, addon_url=addon_url,
                catalog_id=catalog_id, skip=str(skip + per_page),
            )

        content = "movies" if media_type == "movie" else "tvshows"
        ui.end_directory(self.handle, content_type=content)

    # ══════════════════════════════════════════════════════
    #  GENRES
    # ══════════════════════════════════════════════════════
    def _genres(self):
        ui.add_directory_item(
            handle=self.handle, label="Generos de Peliculas", action="genre_list",
            base_url=self.base_url, media_type="movie", icon="DefaultMovies.png",
        )
        ui.add_directory_item(
            handle=self.handle, label="Generos de Series", action="genre_list",
            base_url=self.base_url, media_type="series", icon="DefaultTVShows.png",
        )
        ui.end_directory(self.handle)

    def _genre_list(self):
        media_type = self.params.get("media_type", "movie")
        genre = self.params.get("genre", "")

        if genre:
            items = self.stremio.get_catalog_by_genre(media_type, genre)
            if not items:
                ui.show_notification(f"No results for genre: {genre}")
                ui.end_directory(self.handle)
                return
            items = self.stremio.dedup_items(items)
            self._render_item_list(items, media_type)
            content = "movies" if media_type == "movie" else "tvshows"
            ui.end_directory(self.handle, content_type=content)
        else:
            genres = self.stremio.get_genres(media_type)
            for g in genres:
                ui.add_directory_item(
                    handle=self.handle, label=g, action="genre_list",
                    base_url=self.base_url, media_type=media_type,
                    genre=g, icon="DefaultGenre.png",
                )
            ui.end_directory(self.handle)

    # ══════════════════════════════════════════════════════
    #  SEASONS / EPISODES
    # ══════════════════════════════════════════════════════
    def _seasons(self):
        imdb_id = self.params.get("imdb_id", "")
        title = self.params.get("title", "")

        meta = self.stremio.get_meta("series", imdb_id)
        if not meta:
            ui.show_notification("No se pudo cargar la serie.")
            ui.end_directory(self.handle)
            return

        videos = meta.get("videos", [])
        seasons = sorted(set(v.get("season", 0) for v in videos if v.get("season")))

        if not seasons:
            self.params["season"] = "1"
            self._episodes()
            return

        for sn in seasons:
            ec = sum(1 for v in videos if v.get("season") == sn)
            label = f"Temporada {sn} ({ec} episodios)"
            ui.add_directory_item(
                handle=self.handle, label=label, action="episodes",
                base_url=self.base_url, icon="DefaultTVShows.png",
                poster=meta.get("poster", ""), fanart=meta.get("background", ""),
                imdb_id=imdb_id, media_type="series",
                season=str(sn), title=title,
            )
        ui.end_directory(self.handle, content_type="seasons")

    def _episodes(self):
        imdb_id = self.params.get("imdb_id", "")
        season = int(self.params.get("season", "1"))
        title = self.params.get("title", "")

        meta = self.stremio.get_meta("series", imdb_id)
        if not meta:
            ui.show_notification("No se pudo cargar episodios.")
            ui.end_directory(self.handle)
            return

        episodes = sorted(
            [v for v in meta.get("videos", []) if v.get("season") == season],
            key=lambda v: v.get("episode", 0),
        )

        if not episodes:
            ui.show_notification("No hay episodios.")
            ui.end_directory(self.handle)
            return

        for ep in episodes:
            ep_num = ep.get("episode", 0)
            ep_title = ep.get("title", ep.get("name", f"Episodio {ep_num}"))
            ep_id = ep.get("id", f"{imdb_id}:{season}:{ep_num}")

            resume_info = ""
            if Config.resume_enabled():
                r = self.cache.get_resume(ep_id)
                if r:
                    resume_info = f" [COLOR yellow][{int(r['percent'])}%][/COLOR]"

            label = f"{ep_num}. {ep_title}{resume_info}"

            ui.add_directory_item(
                handle=self.handle, label=label, action="streams",
                base_url=self.base_url, icon="DefaultTVShows.png",
                poster=ep.get("thumbnail", meta.get("poster", "")),
                fanart=meta.get("background", ""),
                plot=ep.get("overview", ""),
                imdb_id=ep_id, media_type="series",
                title=f"{title} S{season:02d}E{ep_num:02d}",
                series_imdb=imdb_id, season=str(season), episode=str(ep_num),
            )

        ui.end_directory(self.handle, content_type="episodes")

    # ══════════════════════════════════════════════════════
    #  STREAMS
    # ══════════════════════════════════════════════════════
    def _streams(self):
        imdb_id = self.params.get("imdb_id", "")
        media_type = self.params.get("media_type", "movie")
        title = self.params.get("title", "")

        xbmcplugin.endOfDirectory(self.handle, succeeded=False)
        xbmc.sleep(300)

        try:
            # 1. First query DHT Search using the query title
            log(f"DHT resolving stream first for: {title}", level="info")
            category = "movies" if media_type == "movie" else "series"
            streams = self.bitsearch.search(title, category)

            # 2. Fallback to Stremio Addons if no DHT streams found
            if not streams:
                log(f"DHT returned no results for: {title}. Falling back to Stremio addons", level="info")
                streams = self.stremio.get_streams(media_type, imdb_id)

            if not streams:
                ui.show_notification("No se encontraron streams.")
                return

            if self.rd.is_configured():
                streams = self.rd.tag_cached_streams(streams)

            streams = self.resolver.filter_by_quality(streams)
            streams = self.resolver.filter_spanish(streams)
            streams = self.resolver.sort_streams(streams)

            if Config.torrent_autoplay() and streams:
                self._launch_stream(streams[0], imdb_id, media_type, title)
                return

            labels = []
            for stream in streams:
                quality = self.resolver.get_quality_label(stream)
                seeds = self.resolver.get_seeds_label(stream)
                size = self.resolver.get_size_label(stream)
                addon_name = stream.get("_addon", "")
                rd_label = self.resolver.get_rd_label(stream)
                esp_label = self.resolver.get_spanish_tag(stream)

                stream_title = stream.get("title", "") or stream.get("name", "Unknown")
                line1 = stream_title.split("\n")[0][:80]

                parts = []
                if esp_label:
                    parts.append(esp_label)
                if rd_label:
                    parts.append(rd_label)
                if quality:
                    parts.append(quality)
                parts.append(line1)
                if seeds:
                    parts.append(seeds)
                if size:
                    parts.append(size)
                if addon_name:
                    parts.append(f"[{addon_name}]")

                labels.append("  ".join(parts))

            choice = xbmcgui.Dialog().select(
                f"Streams para: {title}" if title else "Seleccionar stream",
                labels,
            )

            if choice < 0:
                return

            self._launch_stream(streams[choice], imdb_id, media_type, title)

        except Exception as e:
            log(f"Stream error: {e}", level="error")
            ui.show_notification(str(e), icon=xbmcgui.NOTIFICATION_ERROR)

    # ══════════════════════════════════════════════════════
    #  PLAY
    # ══════════════════════════════════════════════════════
    def _play(self):
        imdb_id = self.params.get("imdb_id", "")
        media_type = self.params.get("media_type", "movie")
        title = self.params.get("title", "")

        xbmcplugin.endOfDirectory(self.handle, succeeded=False)
        xbmc.sleep(300)

        # 1. First query DHT Search using the query title
        log(f"DHT resolving stream first for direct play: {title}", level="info")
        category = "movies" if media_type == "movie" else "series"
        streams = self.bitsearch.search(title, category)

        # 2. Fallback to Stremio Addons if no DHT streams found
        if not streams:
            log(f"DHT returned no results for direct play: {title}. Falling back to Stremio addons", level="info")
            streams = self.stremio.get_streams(media_type, imdb_id)

        if not streams:
            ui.show_notification("No streams found.")
            return

        if self.rd.is_configured():
            streams = self.rd.tag_cached_streams(streams)

        streams = self.resolver.filter_by_quality(streams)
        streams = self.resolver.filter_spanish(streams)
        streams = self.resolver.sort_streams(streams)

        self._launch_stream(streams[0], imdb_id, media_type, title)

    def _launch_stream(self, stream, imdb_id, media_type, title):
        playable_url = self.resolver.resolve(stream)
        if not playable_url:
            ui.show_notification("No se pudo resolver el stream.")
            return

        try:
            base_imdb = imdb_id.split(":")[0] if ":" in imdb_id else imdb_id
            self.cache.add_history(base_imdb, media_type, title,
                                   stream.get("_poster", ""))
        except Exception:
            pass

        context = {
            "content_id": imdb_id,
            "media_type": media_type,
            "title": title,
            "poster": "",
            "imdb_id": self.params.get("series_imdb", "") or imdb_id,
            "season": self.params.get("season", ""),
            "episode": self.params.get("episode", ""),
        }
        self.cache.set("_playback_context", context, ttl=7200)

        if Config.trakt_enabled() and media_type == "movie":
            try:
                self.trakt.mark_watched(imdb_id.split(":")[0], media_type)
            except Exception:
                pass

        subtitle_url = None
        try:
            subs = self.stremio.get_subtitles(media_type, imdb_id)
            if subs and subs[0].get("url"):
                subtitle_url = subs[0]["url"]
        except Exception:
            pass

        if playable_url.startswith("plugin://"):
            log(f"PlayMedia -> {playable_url[:100]}", level="info")
            xbmc.executebuiltin(f'PlayMedia("{playable_url}")')
        else:
            log(f"Player.play -> {playable_url[:100]}", level="info")
            li = xbmcgui.ListItem(label=title, path=playable_url)
            if subtitle_url:
                try:
                    li.setSubtitles([subtitle_url])
                except Exception:
                    pass
            xbmc.Player().play(playable_url, li)

    # ══════════════════════════════════════════════════════
    #  MANUAL TORRENT / MAGNET
    # ══════════════════════════════════════════════════════
    def _manual_torrent(self):
        xbmcplugin.endOfDirectory(self.handle, succeeded=False)
        xbmc.sleep(200)

        text = ui.show_input("Pegar Magnet o URL de torrent")
        if not text:
            return

        text = text.strip()
        if not (text.startswith("magnet:") or text.startswith("http")):
            ui.show_notification("Formato no valido. Usa magnet: o http://")
            return

        ui.show_notification("Resolviendo...", time=2000)
        playable_url, url_type = self.resolver.resolve_magnet(text)

        if not playable_url:
            ui.show_notification("No se pudo resolver.")
            return

        log(f"Manual play ({url_type}): {playable_url}", level="info")

        if playable_url.startswith("plugin://"):
            xbmc.executebuiltin(f'PlayMedia("{playable_url}")')
        else:
            li = xbmcgui.ListItem(label="Manual Torrent", path=playable_url)
            xbmc.Player().play(playable_url, li)

    # ══════════════════════════════════════════════════════
    #  DHT SEARCH
    # ══════════════════════════════════════════════════════
    def _dht_search(self):
        xbmcplugin.endOfDirectory(self.handle, succeeded=False)
        xbmc.sleep(200)

        query = ui.show_input("Buscar Torrent en DHT (ej: Iron Man 1080p)")
        if not query:
            return

        categories = [
            "• 🎬 Películas (Video)",
            "• 📺 Series (TV)",
            "• 🎵 Música"
        ]
        cat_choice = xbmcgui.Dialog().select("Seleccionar Categoría", categories)
        if cat_choice < 0:
            return

        category_map = {
            0: "movies",
            1: "series",
            2: "music"
        }
        category = category_map[cat_choice]

        dialog = xbmcgui.DialogProgress()
        dialog.create("DHT Search", f'Buscando "{query}" en Kademlia DHT...')
        dialog.update(10)

        try:
            streams = self.bitsearch.search(query, category)
            dialog.update(40, "Comprobando caché Real-Debrid...")

            if self.rd.is_configured():
                streams = self.rd.tag_cached_streams(streams)

            dialog.update(60, "Filtrando y Ordenando...")

            if not streams:
                dialog.close()
                ui.show_notification("No se encontraron torrents en DHT.")
                return

            streams = self.resolver.filter_by_quality(streams)
            streams = self.resolver.filter_spanish(streams)
            streams = self.resolver.sort_streams(streams)

            dialog.update(90, f"{len(streams)} torrents listos")
            dialog.close()

            labels = []
            for stream in streams:
                quality = self.resolver.get_quality_label(stream)
                seeds = self.resolver.get_seeds_label(stream)
                size = self.resolver.get_size_label(stream)
                addon_name = stream.get("_addon", "")
                rd_label = self.resolver.get_rd_label(stream)
                esp_label = self.resolver.get_spanish_tag(stream)

                stream_title = stream.get("title", "") or stream.get("name", "Unknown")
                line1 = stream_title.split("\n")[0][:80]

                parts = []
                if esp_label:
                    parts.append(esp_label)
                if rd_label:
                    parts.append(rd_label)
                if quality:
                    parts.append(quality)
                parts.append(line1)
                if seeds:
                    parts.append(seeds)
                if size:
                    parts.append(size)
                if addon_name:
                    parts.append(f"[{addon_name}]")

                labels.append("  ".join(parts))

            choice = xbmcgui.Dialog().select(
                f"Resultados DHT: {query}",
                labels,
            )

            if choice < 0:
                return

            self._launch_dht_stream(streams[choice], query)

        except Exception as e:
            try:
                dialog.close()
            except Exception:
                pass
            log(f"DHT Search error: {e}", level="error")
            ui.show_notification(str(e), icon=xbmcgui.NOTIFICATION_ERROR)

    def _launch_dht_stream(self, stream, title):
        playable_url = self.resolver.resolve(stream)
        if not playable_url:
            ui.show_notification("No se pudo resolver el torrent.")
            return

        # Clean title to use the actual stream name if available
        stream_title = stream.get("title", "") or stream.get("name", "") or title
        stream_title = stream_title.split("\n")[0]

        if playable_url.startswith("plugin://"):
            log(f"DHT PlayMedia -> {playable_url[:100]}", level="info")
            xbmc.executebuiltin(f'PlayMedia("{playable_url}")')
        else:
            log(f"DHT Player.play -> {playable_url[:100]}", level="info")
            li = xbmcgui.ListItem(label=stream_title, path=playable_url)
            xbmc.Player().play(playable_url, li)

    # ══════════════════════════════════════════════════════
    #  TRENDING TORRENTS
    # ══════════════════════════════════════════════════════
    def _trending(self):
        xbmcplugin.endOfDirectory(self.handle, succeeded=False)
        xbmc.sleep(200)

        choice = xbmcgui.Dialog().select(
            "Seleccionar Categoría Trending",
            ["Top Torrents (Últimas 48h)", "Torrents Más Recientes (Nuevos)"]
        )
        if choice < 0:
            return

        trend_type = "48h" if choice == 0 else "recent"
        title_label = "Top 48h" if choice == 0 else "Recientes"

        dialog = xbmcgui.DialogProgress()
        dialog.create("Trending Torrents", f"Obteniendo {title_label}...")
        dialog.update(20)

        try:
            streams = self.bitsearch.trending(trend_type)
            dialog.update(40, "Comprobando caché Real-Debrid...")

            if self.rd.is_configured():
                streams = self.rd.tag_cached_streams(streams)

            dialog.update(60, "Filtrando y Ordenando...")

            if not streams:
                dialog.close()
                ui.show_notification("No se encontraron torrents en tendencias.")
                return

            streams = self.resolver.filter_by_quality(streams)
            streams = self.resolver.filter_spanish(streams)
            streams = self.resolver.sort_streams(streams)

            dialog.update(90, f"{len(streams)} torrents listos")
            dialog.close()

            labels = []
            for stream in streams:
                quality = self.resolver.get_quality_label(stream)
                seeds = self.resolver.get_seeds_label(stream)
                size = self.resolver.get_size_label(stream)
                addon_name = stream.get("_addon", "")
                rd_label = self.resolver.get_rd_label(stream)
                esp_label = self.resolver.get_spanish_tag(stream)

                stream_title = stream.get("title", "") or stream.get("name", "Unknown")
                line1 = stream_title.split("\n")[0][:80]

                parts = []
                if esp_label:
                    parts.append(esp_label)
                if rd_label:
                    parts.append(rd_label)
                if quality:
                    parts.append(quality)
                parts.append(line1)
                if seeds:
                    parts.append(seeds)
                if size:
                    parts.append(size)
                if addon_name:
                    parts.append(f"[{addon_name}]")

                labels.append("  ".join(parts))

            selected = xbmcgui.Dialog().select(
                f"Trending Torrents ({title_label})",
                labels,
            )

            if selected < 0:
                return

            self._launch_dht_stream(streams[selected], title_label)

        except Exception as e:
            try:
                dialog.close()
            except Exception:
                pass
            log(f"Trending Torrents error: {e}", level="error")
            ui.show_notification(str(e), icon=xbmcgui.NOTIFICATION_ERROR)

    # ══════════════════════════════════════════════════════
    #  SEARCH
    # ══════════════════════════════════════════════════════
    def _search(self):
        xbmcplugin.endOfDirectory(self.handle, succeeded=False)
        xbmc.sleep(200)

        query = ui.show_input("Buscar peliculas y series")
        if not query:
            return

        choice = ui.show_select("Buscar en:", ["Peliculas", "Series", "Ambos"])
        if choice < 0:
            return

        type_map = {0: "movie", 1: "series", 2: "both"}
        url = ui.build_url(
            self.base_url, action="search_results",
            query=query, search_type=type_map[choice],
        )
        xbmc.executebuiltin(f"Container.Update({url})")

    def _search_results(self):
        query = self.params.get("query", "")
        search_type = self.params.get("search_type", "movie")
        if not query:
            ui.end_directory(self.handle)
            return

        dialog = xbmcgui.DialogProgress()
        dialog.create("Buscando", f'"{query}"...')
        dialog.update(10)

        all_results = []
        if search_type in ("movie", "both"):
            dialog.update(30, "Peliculas...")
            all_results.extend(
                [(r, "movie") for r in self.stremio.search(query, "movie")]
            )
        if search_type in ("series", "both"):
            dialog.update(60, "Series...")
            all_results.extend(
                [(r, "series") for r in self.stremio.search(query, "series")]
            )

        dialog.close()

        if not all_results:
            ui.show_notification(f'Sin resultados para "{query}"')
            ui.end_directory(self.handle)
            return

        seen = set()
        for item, mt in all_results:
            imdb_id = item.get("imdb_id") or item.get("id", "")
            if imdb_id in seen:
                continue
            seen.add(imdb_id)

            name = item.get("name", "Unknown")
            year = str(item.get("releaseInfo", item.get("year", "")))
            poster = item.get("poster", "")
            plot = item.get("description", "")

            tag = "[PELICULA]" if mt == "movie" else "[SERIE]"
            label = f"{tag} {name} ({year})" if year else f"{tag} {name}"
            click = "streams" if mt == "movie" else "seasons"

            ctx = self._make_fav_context(imdb_id, mt, name, year, poster)

            ui.add_directory_item(
                handle=self.handle, label=label, action=click,
                base_url=self.base_url, poster=poster, plot=plot,
                year=year, imdb_id=imdb_id, media_type=mt,
                context_menu=ctx, title=name,
            )

        ui.end_directory(self.handle, content_type="videos")

    # ══════════════════════════════════════════════════════
    #  CONTINUE WATCHING
    # ══════════════════════════════════════════════════════
    def _continue_watching(self):
        items = self.cache.get_continue_watching(limit=20)
        if not items:
            ui.show_notification("Nada en 'Seguir viendo'.")
            ui.end_directory(self.handle)
            return

        for item in items:
            pct = int(item["percent"])
            title = item["title"]
            label = f"{title} [COLOR yellow][{pct}%][/COLOR]"

            ui.add_directory_item(
                handle=self.handle, label=label, action="streams",
                base_url=self.base_url,
                poster=item.get("poster", ""),
                imdb_id=item["content_id"],
                media_type=item["media_type"],
                title=title,
            )

        ui.end_directory(self.handle, content_type="videos")

    # ══════════════════════════════════════════════════════
    #  FAVORITES
    # ══════════════════════════════════════════════════════
    def _favorites(self):
        favs = self.cache.get_favorites()
        if not favs:
            ui.show_notification("No hay favoritos.")
            ui.end_directory(self.handle)
            return

        for fav in favs:
            imdb_id = fav["imdb_id"]
            mt = fav["media_type"]
            title = fav["title"]
            year = fav.get("year", "")
            poster = fav.get("poster", "")
            label = f"{title} ({year})" if year else title
            click = "streams" if mt == "movie" else "seasons"
            ctx_url = ui.build_url(
                self.base_url, action="toggle_favorite",
                imdb_id=imdb_id, media_type=mt,
                title=title, year=year, poster=poster,
            )
            ctx = [("Quitar de Favoritos", f"RunPlugin({ctx_url})")]

            ui.add_directory_item(
                handle=self.handle, label=label, action=click,
                base_url=self.base_url, poster=poster, year=year,
                imdb_id=imdb_id, media_type=mt, context_menu=ctx, title=title,
            )

        ui.end_directory(self.handle, content_type="videos")

    def _toggle_favorite(self):
        imdb_id = self.params.get("imdb_id", "")
        mt = self.params.get("media_type", "movie")
        title = self.params.get("title", "")
        year = self.params.get("year", "")
        poster = self.params.get("poster", "")

        if self.cache.is_favorite(imdb_id):
            self.cache.remove_favorite(imdb_id)
            ui.show_notification(f"Eliminado: {title}")
        else:
            self.cache.add_favorite(imdb_id, mt, title, year, poster)
            ui.show_notification(f"Agregado: {title}")
        xbmc.executebuiltin("Container.Refresh")

    # ══════════════════════════════════════════════════════
    #  HISTORY
    # ══════════════════════════════════════════════════════
    def _history(self):
        items = self.cache.get_history(limit=50)
        if not items:
            ui.show_notification("No hay historial.")
            ui.end_directory(self.handle)
            return

        for item in items:
            label = item["title"]
            click = "streams" if item["media_type"] == "movie" else "seasons"
            ui.add_directory_item(
                handle=self.handle, label=label, action=click,
                base_url=self.base_url, poster=item.get("poster", ""),
                imdb_id=item["imdb_id"], media_type=item["media_type"],
                title=item["title"],
            )

        ui.add_directory_item(
            handle=self.handle, label="[COLOR red]Borrar historial[/COLOR]",
            action="clear_history", base_url=self.base_url,
        )
        ui.end_directory(self.handle, content_type="videos")

    # ══════════════════════════════════════════════════════
    #  TRAKT
    # ══════════════════════════════════════════════════════
    def _trakt_menu(self):
        items = [
            ("Mi Watchlist - Peliculas", "trakt_watchlist", "movie"),
            ("Mi Watchlist - Series",    "trakt_watchlist", "series"),
            ("Recomendaciones",          "trakt_recommendations", ""),
            ("Trending - Peliculas",     "trakt_trending",  "movie"),
            ("Trending - Series",        "trakt_trending",  "series"),
            ("Autorizar Trakt...",       "trakt_auth",      ""),
        ]
        for label, action, mt in items:
            ui.add_directory_item(
                handle=self.handle, label=label, action=action,
                base_url=self.base_url, media_type=mt,
            )
        ui.end_directory(self.handle)

    def _trakt_auth(self):
        xbmcplugin.endOfDirectory(self.handle, succeeded=False)
        xbmc.sleep(200)
        self.trakt.device_auth()

    def _trakt_watchlist(self):
        mt = self.params.get("media_type", "movie")
        api_type = "movies" if mt == "movie" else "shows"
        items = self.trakt.get_watchlist(api_type)
        if not items:
            ui.show_notification("Watchlist vacia.")
            ui.end_directory(self.handle)
            return
        self._render_trakt_items(items)
        ui.end_directory(self.handle, content_type="videos")

    def _trakt_recommendations(self):
        movies = self.trakt.get_recommendations("movies", limit=15)
        shows = self.trakt.get_recommendations("shows", limit=15)
        items = movies + shows
        if not items:
            ui.show_notification("No hay recomendaciones.")
            ui.end_directory(self.handle)
            return
        self._render_trakt_items(items)
        ui.end_directory(self.handle, content_type="videos")

    def _trakt_trending(self):
        mt = self.params.get("media_type", "movie")
        api_type = "movies" if mt == "movie" else "shows"
        items = self.trakt.get_trending(api_type, limit=25)
        if not items:
            ui.show_notification("No trending data.")
            ui.end_directory(self.handle)
            return
        self._render_trakt_items(items)
        ui.end_directory(self.handle, content_type="videos")

    def _trakt_add(self):
        imdb_id = self.params.get("imdb_id", "")
        mt = self.params.get("media_type", "movie")
        self.trakt.add_to_watchlist(imdb_id, mt)
        ui.show_notification("Agregado a Trakt Watchlist")

    def _trakt_remove(self):
        imdb_id = self.params.get("imdb_id", "")
        mt = self.params.get("media_type", "movie")
        self.trakt.remove_from_watchlist(imdb_id, mt)
        ui.show_notification("Eliminado de Trakt Watchlist")
        xbmc.executebuiltin("Container.Refresh")

    def _render_trakt_items(self, items):
        for item in items:
            imdb_id = item.get("imdb_id", "")
            mt = item.get("media_type", "movie")
            title = item.get("title", "Unknown")
            year = item.get("year", "")

            poster = ""
            meta = self.stremio.get_meta(mt, imdb_id) if imdb_id else None
            if meta:
                poster = meta.get("poster", "")
                title = meta.get("name", title)

            tag = "[PELICULA]" if mt == "movie" else "[SERIE]"
            label = f"{tag} {title} ({year})" if year else f"{tag} {title}"
            click = "streams" if mt == "movie" else "seasons"

            ctx = self._make_fav_context(imdb_id, mt, title, year, poster)
            trakt_ctx_url = ui.build_url(
                self.base_url, action="trakt_remove",
                imdb_id=imdb_id, media_type=mt,
            )
            ctx.append(("Quitar de Trakt Watchlist", f"RunPlugin({trakt_ctx_url})"))

            ui.add_directory_item(
                handle=self.handle, label=label, action=click,
                base_url=self.base_url, poster=poster, year=year,
                imdb_id=imdb_id, media_type=mt, context_menu=ctx, title=title,
            )

    # ══════════════════════════════════════════════════════
    #  v3.2 FIX: STREAMING PLATFORMS (no duplicates)
    #  Now shows grouped platforms with sub-menu for type.
    # ══════════════════════════════════════════════════════
    def _platforms(self):
        try:
            platforms = self.stremio.get_streaming_platforms()
            if not platforms:
                ui.show_notification("No se pudieron cargar las plataformas.")
                ui.end_directory(self.handle)
                return

            for plat in platforms:
                name = plat["name"]
                catalogs = plat["catalogs"]

                # If only one catalog, go directly to it
                if len(catalogs) == 1:
                    cat = catalogs[0]
                    ui.add_directory_item(
                        handle=self.handle, label=name, action="platform_catalog",
                        base_url=self.base_url,
                        media_type=cat["type"],
                        catalog_id=cat["catalog_id"],
                        addon_url=cat["addon_url"],
                        icon="DefaultStudios.png",
                    )
                else:
                    # Multiple catalogs (movie + series) → show sub-menu
                    # Encode catalogs list as JSON in a param
                    import json as jsonlib
                    catalogs_json = jsonlib.dumps(catalogs, separators=(',', ':'))
                    ui.add_directory_item(
                        handle=self.handle, label=name, action="platform_type",
                        base_url=self.base_url,
                        platform_name=name,
                        catalogs_data=catalogs_json,
                        icon="DefaultStudios.png",
                    )
            ui.end_directory(self.handle)
        except Exception as e:
            log(f"Platforms error: {e}", level="error")
            ui.show_notification("Error cargando plataformas.")
            ui.end_directory(self.handle)

    def _platform_type(self):
        """Sub-menu: choose Movies or Series for a platform."""
        try:
            import json as jsonlib
            platform_name = self.params.get("platform_name", "")
            catalogs_json = self.params.get("catalogs_data", "[]")
            catalogs = jsonlib.loads(catalogs_json)

            if not catalogs:
                ui.show_notification("No hay catalogos.")
                ui.end_directory(self.handle)
                return

            type_labels = {"movie": "Peliculas", "series": "Series"}
            for cat in catalogs:
                cat_type = cat.get("type", "movie")
                label = f"{platform_name} — {type_labels.get(cat_type, cat_type.title())}"
                ui.add_directory_item(
                    handle=self.handle, label=label, action="platform_catalog",
                    base_url=self.base_url,
                    media_type=cat_type,
                    catalog_id=cat["catalog_id"],
                    addon_url=cat["addon_url"],
                    icon="DefaultStudios.png",
                )
            ui.end_directory(self.handle)
        except Exception as e:
            log(f"Platform type error: {e}", level="error")
            ui.show_notification("Error.")
            ui.end_directory(self.handle)

    def _platform_catalog(self):
        try:
            addon_url = self.params.get("addon_url", "")
            catalog_id = self.params.get("catalog_id", "")
            media_type = self.params.get("media_type", "movie")
            skip = int(self.params.get("skip", "0"))

            extra = f"skip={skip}" if skip > 0 else ""
            items = self.stremio.get_catalog(addon_url, media_type, catalog_id, extra)

            if not items:
                ui.show_notification("No items found.")
                ui.end_directory(self.handle)
                return

            items = self.stremio.dedup_items(items)
            self._render_item_list(items, media_type)

            per_page = Config.items_per_page()
            if len(items) >= 10:
                ui.add_directory_item(
                    handle=self.handle, label="[B]>> Siguiente pagina[/B]",
                    action="platform_catalog", base_url=self.base_url,
                    media_type=media_type, addon_url=addon_url,
                    catalog_id=catalog_id, skip=str(skip + per_page),
                )

            content = "movies" if media_type == "movie" else "tvshows"
            ui.end_directory(self.handle, content_type=content)
        except Exception as e:
            log(f"Platform catalog error: {e}", level="error")
            ui.show_notification("Error cargando catalogo.")
            ui.end_directory(self.handle)

    # ══════════════════════════════════════════════════════
    #  v3.2 NEW: ACESTREAM — Replaces Live TV
    # ══════════════════════════════════════════════════════
    def _acestream(self):
        """AceStream main menu: groups + utilities."""
        try:
            from resources.lib.acestream import AceStreamClient
            ace = AceStreamClient()

            # Show loading notification
            ui.show_notification("Cargando canales AceStream...", time=2000)

            channels = ace.fetch_channels()
            if not channels:
                ui.show_notification("No se pudieron cargar canales AceStream.")
                # Still show utility options
                ui.add_directory_item(
                    handle=self.handle,
                    label="[COLOR yellow]Pegar hash/enlace AceStream[/COLOR]",
                    action="acestream_manual", base_url=self.base_url,
                    icon="DefaultNetwork.png",
                )
                ui.add_directory_item(
                    handle=self.handle,
                    label="[COLOR cyan]Refrescar lista[/COLOR]",
                    action="acestream_refresh", base_url=self.base_url,
                    icon="DefaultAddonProgram.png",
                )
                ui.end_directory(self.handle)
                return

            groups = ace.get_groups(channels)

            # Header: show all channels
            total = len(channels)
            ui.add_directory_item(
                handle=self.handle,
                label=f"[B]Todos los canales ({total})[/B]",
                action="acestream_all", base_url=self.base_url,
                icon="DefaultPVRTVChannels.png",
            )

            # Groups
            for group in groups:
                count = group["count"]
                name = group["name"]
                logo = group.get("logo", "")
                label = f"{name} ({count})"
                ui.add_directory_item(
                    handle=self.handle, label=label, action="acestream_group",
                    base_url=self.base_url,
                    poster=logo,
                    group_name=name,
                    icon="DefaultPVRTVChannels.png",
                )

            # Utilities at the bottom
            ui.add_directory_item(
                handle=self.handle,
                label="[COLOR yellow]Pegar hash/enlace AceStream[/COLOR]",
                action="acestream_manual", base_url=self.base_url,
                icon="DefaultNetwork.png",
            )
            ui.add_directory_item(
                handle=self.handle,
                label="[COLOR cyan]Refrescar lista[/COLOR]",
                action="acestream_refresh", base_url=self.base_url,
                icon="DefaultAddonProgram.png",
            )

            ui.end_directory(self.handle)
        except Exception as e:
            log(f"AceStream error: {e}", level="error")
            import traceback
            log(traceback.format_exc(), level="error")
            ui.show_notification(f"Error AceStream: {str(e)[:60]}")
            ui.end_directory(self.handle)

    def _acestream_group(self):
        """Show channels in a specific group."""
        try:
            from resources.lib.acestream import AceStreamClient
            ace = AceStreamClient()
            group_name = self.params.get("group_name", "")

            channels = ace.fetch_channels()
            group_channels = ace.get_channels_by_group(group_name, channels)

            if not group_channels:
                ui.show_notification(f"No hay canales en {group_name}.")
                ui.end_directory(self.handle)
                return

            for ch in group_channels:
                title = ch.get("title", "Canal")
                ace_hash = ch.get("hash", "")
                logo = ch.get("logo", "")

                ui.add_directory_item(
                    handle=self.handle, label=title, action="acestream_play",
                    base_url=self.base_url,
                    poster=logo,
                    ace_hash=ace_hash,
                    title=title,
                    is_folder=False,
                    icon="DefaultPVRTVChannels.png",
                )

            ui.end_directory(self.handle, content_type="videos")
        except Exception as e:
            log(f"AceStream group error: {e}", level="error")
            ui.show_notification("Error cargando grupo.")
            ui.end_directory(self.handle)

    def _acestream_all(self):
        """Show ALL acestream channels in a flat list."""
        try:
            from resources.lib.acestream import AceStreamClient
            ace = AceStreamClient()
            channels = ace.fetch_channels()

            if not channels:
                ui.show_notification("No hay canales.")
                ui.end_directory(self.handle)
                return

            for ch in channels:
                title = ch.get("title", "Canal")
                ace_hash = ch.get("hash", "")
                logo = ch.get("logo", "")
                group = ch.get("group", "")

                label = f"[{group}] {title}" if group else title

                ui.add_directory_item(
                    handle=self.handle, label=label, action="acestream_play",
                    base_url=self.base_url,
                    poster=logo,
                    ace_hash=ace_hash,
                    title=title,
                    is_folder=False,
                    icon="DefaultPVRTVChannels.png",
                )

            ui.end_directory(self.handle, content_type="videos")
        except Exception as e:
            log(f"AceStream all error: {e}", level="error")
            ui.show_notification("Error.")
            ui.end_directory(self.handle)

    def _acestream_play(self):
        """Play an AceStream channel by hash."""
        try:
            from resources.lib.acestream import AceStreamClient

            ace_hash = self.params.get("ace_hash", "")
            title = self.params.get("title", "AceStream")

            if not ace_hash:
                ui.show_notification("Hash no valido.")
                return

            xbmcplugin.endOfDirectory(self.handle, succeeded=False)
            xbmc.sleep(200)

            play_url = AceStreamClient.build_play_url(ace_hash, title)
            log(f"AceStream play: {play_url[:100]}", level="info")

            if play_url.startswith("plugin://"):
                xbmc.executebuiltin(f'PlayMedia("{play_url}")')
            elif play_url.startswith("acestream://"):
                # On Android: launch AceStream app via intent
                try:
                    if xbmc.getCondVisibility("System.Platform.Android"):
                        intent_url = (
                            f"StartAndroidActivity(org.acestream.media,"
                            f"android.intent.action.VIEW,,"
                            f"acestream://{ace_hash})"
                        )
                        xbmc.executebuiltin(intent_url)
                        return
                except Exception:
                    pass

                # Fallback: try playing the acestream:// URL directly
                li = xbmcgui.ListItem(label=title, path=play_url)
                xbmc.Player().play(play_url, li)
            elif play_url.startswith("http"):
                # AceWeb: need to wait for engine to connect to P2P peers
                # and start buffering before we can play
                import requests
                engine = Config.acestream_engine()
                if engine == "AceWeb":
                    ui.show_notification("Conectando a peers...", time=5000)
                    # First check engine is alive
                    port = Config.acestream_engine_port()
                    try:
                        check = requests.get(
                            f"http://127.0.0.1:{port}/webui/api/service?method=get_version",
                            timeout=3
                        )
                        log(f"AceWeb engine check: {check.status_code}", level="info")
                    except Exception as ve:
                        ui.show_notification(f"Motor AceWeb no responde en puerto {port}")
                        log(f"AceWeb engine not responding: {ve}", level="error")
                        return

                    # Use the stat URL to start the stream and wait for it
                    stat_url = (f"http://127.0.0.1:{port}/ace/getstream"
                                f"?id={ace_hash}")
                    stream_url = None
                    try:
                        # Request the stream - follow redirects to get final URL
                        resp = requests.get(stat_url, timeout=60, stream=True,
                                            allow_redirects=True)
                        if resp.status_code == 200:
                            # The final URL after redirects is the actual stream
                            stream_url = resp.url
                            resp.close()
                            log(f"AceWeb stream URL resolved: {stream_url[:100]}", level="info")
                        else:
                            log(f"AceWeb stream error: HTTP {resp.status_code}", level="error")
                            resp.close()
                    except requests.exceptions.Timeout:
                        ui.show_notification("Timeout conectando al stream P2P")
                        return
                    except Exception as se:
                        log(f"AceWeb stream request error: {se}", level="error")
                        # Fall back to direct URL
                        stream_url = play_url

                    if stream_url:
                        li = xbmcgui.ListItem(label=title, path=stream_url)
                        li.setInfo("video", {"title": title})
                        li.setMimeType("video/mp2t")
                        li.setContentLookup(False)
                        xbmc.Player().play(stream_url, li)
                    else:
                        ui.show_notification("No se pudo obtener el stream")
                else:
                    li = xbmcgui.ListItem(label=title, path=play_url)
                    xbmc.Player().play(play_url, li)
            else:
                ui.show_notification("Motor AceStream no reconocido.")

        except Exception as e:
            log(f"AceStream play error: {e}", level="error")
            ui.show_notification(f"Error: {str(e)[:60]}")

    def _acestream_manual(self):
        """Manually enter an AceStream hash or URL."""
        try:
            xbmcplugin.endOfDirectory(self.handle, succeeded=False)
            xbmc.sleep(200)

            text = ui.show_input("Pegar hash AceStream o acestream://")
            if not text:
                return

            text = text.strip()

            # Clean up the input
            if text.startswith("acestream://"):
                ace_hash = text.replace("acestream://", "").strip()
            elif text.startswith("http") and "acestream" in text.lower():
                # Might be a URL with hash parameter
                import re
                match = re.search(r'(?:infohash|id|hash)=([a-fA-F0-9]{40})', text)
                if match:
                    ace_hash = match.group(1)
                else:
                    ui.show_notification("No se encontro un hash valido en la URL.")
                    return
            elif len(text) == 40 and all(c in '0123456789abcdefABCDEF' for c in text):
                # Raw 40-char hex hash
                ace_hash = text
            else:
                ui.show_notification("Formato no valido. Usa un hash de 40 chars o acestream://")
                return

            from resources.lib.acestream import AceStreamClient
            play_url = AceStreamClient.build_play_url(ace_hash, "Manual AceStream")
            log(f"AceStream manual play: {play_url[:100]}", level="info")

            if play_url.startswith("plugin://"):
                xbmc.executebuiltin(f'PlayMedia("{play_url}")')
            elif play_url.startswith("http"):
                li = xbmcgui.ListItem(label="AceStream Manual", path=play_url)
                xbmc.Player().play(play_url, li)
            else:
                # acestream:// or other
                li = xbmcgui.ListItem(label="AceStream Manual", path=play_url)
                xbmc.Player().play(play_url, li)

        except Exception as e:
            log(f"AceStream manual error: {e}", level="error")
            ui.show_notification(f"Error: {str(e)[:60]}")

    def _acestream_refresh(self):
        """Force refresh AceStream channel list."""
        try:
            xbmcplugin.endOfDirectory(self.handle, succeeded=False)
            xbmc.sleep(200)

            from resources.lib.acestream import AceStreamClient
            ace = AceStreamClient()

            # Clear cache
            self.cache.delete("acestream:channels")

            ui.show_notification("Descargando lista actualizada...", time=3000)

            channels = ace.fetch_channels(force_refresh=True)
            if channels:
                ui.show_notification(f"Cargados {len(channels)} canales!", time=3000)
            else:
                ui.show_notification("No se pudieron cargar canales.", time=3000)

            # Refresh the container
            xbmc.sleep(1000)
            xbmc.executebuiltin("Container.Refresh")

        except Exception as e:
            log(f"AceStream refresh error: {e}", level="error")
            ui.show_notification(f"Error: {str(e)[:60]}")

    # ══════════════════════════════════════════════════════
    #  UTILITIES
    # ══════════════════════════════════════════════════════
    def _render_item_list(self, items, media_type):
        for item in items:
            imdb_id = item.get("imdb_id") or item.get("id", "")
            title = item.get("name", "Unknown")
            year = str(item.get("releaseInfo", item.get("year", "")))
            poster = item.get("poster", "")
            plot = item.get("description", "")

            rating = item.get("imdbRating", "")
            rating_tag = ""
            if rating:
                try:
                    r = float(rating)
                    if r >= 7.5:
                        rating_tag = f" [COLOR gold]★{rating}[/COLOR]"
                    elif r >= 5.0:
                        rating_tag = f" [COLOR yellow]★{rating}[/COLOR]"
                    else:
                        rating_tag = f" [COLOR grey]★{rating}[/COLOR]"
                except (ValueError, TypeError):
                    pass

            label = f"{title} ({year}){rating_tag}" if year else f"{title}{rating_tag}"
            click = "streams" if media_type == "movie" else "seasons"
            ctx = self._make_fav_context(imdb_id, media_type, title, year, poster)

            if rating and plot:
                plot = f"IMDB: {rating}/10\n{plot}"
            elif rating:
                plot = f"IMDB: {rating}/10"

            ui.add_directory_item(
                handle=self.handle, label=label, action=click,
                base_url=self.base_url, poster=poster,
                fanart=item.get("background", item.get("fanart", "")),
                plot=plot, year=year, imdb_id=imdb_id,
                media_type=media_type, context_menu=ctx, title=title,
                rating=rating,
            )

    def _make_fav_context(self, imdb_id, media_type, title, year, poster):
        fav_label = "Quitar de Favoritos" if self.cache.is_favorite(imdb_id) \
            else "Agregar a Favoritos"
        fav_url = ui.build_url(
            self.base_url, action="toggle_favorite",
            imdb_id=imdb_id, media_type=media_type,
            title=title, year=year, poster=poster,
        )
        ctx = [(fav_label, f"RunPlugin({fav_url})")]

        if Config.trakt_enabled():
            trakt_url = ui.build_url(
                self.base_url, action="trakt_add",
                imdb_id=imdb_id, media_type=media_type,
            )
            ctx.append(("Agregar a Trakt Watchlist", f"RunPlugin({trakt_url})"))

        return ctx

    def _clear_cache(self):
        self.cache.clear_all()
        ui.show_notification("Cache limpiada!")

    def _clear_history(self):
        self.cache.clear_history()
        ui.show_notification("Historial borrado!")
        xbmc.executebuiltin("Container.Refresh")

    def _settings(self):
        xbmcplugin.endOfDirectory(self.handle, succeeded=False)
        xbmc.sleep(100)
        xbmcaddon.Addon().openSettings()
