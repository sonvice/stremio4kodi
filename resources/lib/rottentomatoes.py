# -*- coding: utf-8 -*-
"""
Rotten Tomatoes & OMDB Client — Provides Tomatometer ratings, audience scores,
awards, and descriptions for movies and series with SQLite caching.
"""
import json
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

from resources.lib.cache import CacheDB
from resources.lib.config import Config
from resources.lib.logger import log

OMDB_API_KEYS = ["trilogy", "b790c0a5", "92791834", "e4776269"]


class RottenTomatoesClient:
    def __init__(self):
        self.cache = CacheDB()

    def get_info(self, title, year="", imdb_id="", media_type="movie"):
        """
        Fetches Rotten Tomatoes score, Metascore, plot, and awards with caching.
        """
        if not Config.rt_enabled():
            return {}

        clean_title = (title or "").strip()
        clean_year = str(year or "").strip()[:4]
        clean_imdb = (imdb_id or "").strip()

        if clean_imdb.startswith("tmdb:"):
            clean_imdb = ""

        cache_key = f"rt_omdb:{clean_imdb or clean_title}:{clean_year}"
        if Config.cache_enabled():
            cached = self.cache.get(cache_key)
            if cached and isinstance(cached, dict):
                return cached

        info = self._fetch_from_api(clean_title, clean_year, clean_imdb)

        if Config.cache_enabled():
            self.cache.set(cache_key, info, ttl_hours=24 * 7)  # 7 days cache

        return info

    def _fetch_from_api(self, title, year, imdb_id):
        res = {
            "rt_score": "",
            "metascore": "",
            "plot": "",
            "awards": "",
            "rated": "",
            "box_office": ""
        }

        # 1. Try with IMDB ID
        if imdb_id and imdb_id.startswith("tt"):
            for key in OMDB_API_KEYS:
                try:
                    url = f"http://www.omdbapi.com/?i={imdb_id}&apikey={key}"
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=2.5) as resp:
                        data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                        if data.get("Response") == "True":
                            self._extract_data(data, res)
                            return res
                except Exception as e:
                    log(f"OMDb lookup error ({key}): {e}", level="debug")

        # 2. Try with Title + Year
        if title:
            q = urllib.parse.quote(title)
            y_param = f"&y={year}" if year else ""
            for key in OMDB_API_KEYS:
                try:
                    url = f"http://www.omdbapi.com/?t={q}{y_param}&apikey={key}"
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=2.5) as resp:
                        data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                        if data.get("Response") == "True":
                            self._extract_data(data, res)
                            return res
                except Exception as e:
                    log(f"OMDb title lookup error ({key}): {e}", level="debug")

        return res

    def _extract_data(self, data, out):
        for r in data.get("Ratings", []):
            if r.get("Source") == "Rotten Tomatoes":
                val = r.get("Value", "").replace("%", "").strip()
                out["rt_score"] = val
            elif r.get("Source") == "Metacritic":
                out["metascore"] = r.get("Value", "").strip()

        plot = data.get("Plot")
        if plot and plot != "N/A":
            out["plot"] = plot

        awards = data.get("Awards")
        if awards and awards != "N/A":
            out["awards"] = awards

        rated = data.get("Rated")
        if rated and rated != "N/A":
            out["rated"] = rated

        box_office = data.get("BoxOffice")
        if box_office and box_office != "N/A":
            out["box_office"] = box_office

    @staticmethod
    def format_rt_tag(rt_score):
        """
        Returns a formatted colored tag for the Kodi list item.
        """
        if not rt_score:
            return ""
        try:
            score_num = int(rt_score)
            if score_num >= 75:
                return f" [COLOR lime]🍅{score_num}%[/COLOR]"
            elif score_num >= 60:
                return f" [COLOR yellow]🍅{score_num}%[/COLOR]"
            else:
                return f" [COLOR lightgreen]🟢{score_num}%[/COLOR]"
        except (ValueError, TypeError):
            return f" [COLOR yellow]🍅{rt_score}[/COLOR]"

    def enrich_items(self, items):
        """
        Enriches a list of items with Rotten Tomatoes data in parallel.
        """
        if not Config.rt_enabled() or not items:
            return items

        def _enrich_single(it):
            title = it.get("original_title") or it.get("title") or it.get("name", "")
            year = it.get("year") or it.get("releaseInfo", "")
            imdb_id = it.get("imdb_id", "")
            media_type = it.get("media_type") or it.get("type", "movie")
            info = self.get_info(title=title, year=year, imdb_id=imdb_id, media_type=media_type)
            if info:
                if info.get("rt_score"):
                    it["rt_score"] = info["rt_score"]
                if info.get("plot") and (not it.get("description") or len(it.get("description")) < 10):
                    it["description"] = info["plot"]
                if info.get("awards"):
                    it["awards"] = info["awards"]
                if info.get("metascore"):
                    it["metascore"] = info["metascore"]
            return it

        with ThreadPoolExecutor(max_workers=min(len(items), 8)) as pool:
            futures = [pool.submit(_enrich_single, item) for item in items]
            for f in as_completed(futures):
                try:
                    f.result()
                except Exception as e:
                    log(f"Error enriching item: {e}", level="debug")

        return items
