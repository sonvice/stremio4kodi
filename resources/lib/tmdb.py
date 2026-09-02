# -*- coding: utf-8 -*-
"""
TMDB Client — Direct integration with The Movie Database API v3.
Provides Trending, Popular, Now Playing, Top Rated, Genres, and Top 100 Recent
for both Movies and TV Shows, in Spanish and English with automatic IMDb ID resolution.
"""
import time
from urllib.parse import urlencode

from resources.lib.config import Config
from resources.lib.cache import CacheDB
from resources.lib.logger import log

DEFAULT_TMDB_KEY = "9d13fcef48d5353656dc4b1146a298ce"

class TMDBClient:
    BASE_URL = "https://api.themoviedb.org/3"

    def __init__(self):
        self.cache = CacheDB()

    @property
    def api_key(self):
        key = Config.tmdb_apikey()
        if not key or not key.strip():
            return DEFAULT_TMDB_KEY
        key = key.strip()
        if key.startswith("eyJ"):
            try:
                import base64, json
                parts = key.split(".")
                if len(parts) >= 2:
                    padding = "=" * (4 - len(parts[1]) % 4)
                    payload = json.loads(base64.b64decode(parts[1] + padding).decode('utf-8'))
                    if payload.get("aud"):
                        return payload["aud"]
            except Exception as e:
                log(f"JWT TMDB parse error: {e}", level="debug")
        return key

    @property
    def language(self):
        lang = Config.language() or "es"
        lang_map = {
            "es": "es-ES",
            "en": "en-US",
            "fr": "fr-FR",
            "de": "de-DE",
            "it": "it-IT",
            "pt": "pt-BR"
        }
        return lang_map.get(lang, "es-ES")

    def _get(self, endpoint, params=None, cache_ttl=21600):
        if params is None:
            params = {}
        params["api_key"] = self.api_key
        if "language" not in params:
            params["language"] = self.language

        query_str = urlencode(params)
        url = f"{self.BASE_URL}{endpoint}?{query_str}"
        cache_key = f"tmdb:{url}"

        if Config.cache_enabled() and cache_ttl > 0:
            cached = self.cache.get(cache_key)
            if cached and isinstance(cached, dict) and (cached.get("results") or cached.get("id") or cached.get("genres") or cached.get("episodes")):
                return cached

        data = self._fetch_url(url)

        # Automatic retry with DEFAULT_TMDB_KEY if custom key failed
        if not data and params.get("api_key") != DEFAULT_TMDB_KEY:
            log("Configured TMDB key failed. Retrying with default TMDB key...", level="info")
            params["api_key"] = DEFAULT_TMDB_KEY
            retry_url = f"{self.BASE_URL}{endpoint}?{urlencode(params)}"
            data = self._fetch_url(retry_url)

        if data and isinstance(data, dict) and (data.get("results") or data.get("id") or data.get("genres") or data.get("episodes")):
            if Config.cache_enabled() and cache_ttl > 0:
                self.cache.set(cache_key, data, ttl=cache_ttl)
            return data

        return {}

    def _fetch_url(self, url):
        # 1. urllib.request
        try:
            import urllib.request, json
            req = urllib.request.Request(url, headers={"User-Agent": "Stremio4Kodi/3.3", "Accept": "application/json"})
            resp = urllib.request.urlopen(req, timeout=Config.stremio_timeout())
            raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            if data and isinstance(data, dict) and (data.get("results") or data.get("id") or data.get("genres") or data.get("episodes")):
                return data
        except Exception as e:
            log(f"TMDB urllib fetch debug [{url[:60]}]: {e}", level="debug")

        # 2. requests
        try:
            import requests
            resp = requests.get(
                url,
                headers={"User-Agent": "Stremio4Kodi/3.3", "Accept": "application/json"},
                timeout=(Config.stremio_timeout(), Config.stremio_timeout() + 5),
                verify=False
            )
            if resp.status_code == 200:
                data = resp.json()
                if data and isinstance(data, dict) and (data.get("results") or data.get("id") or data.get("genres") or data.get("episodes")):
                    return data
        except Exception as e:
            log(f"TMDB requests fetch debug [{url[:60]}]: {e}", level="debug")

        # 3. curl
        try:
            import subprocess, json
            cmd = [
                "curl", "-skL",
                "--connect-timeout", str(Config.stremio_timeout()),
                "--max-time", str(Config.stremio_timeout() + 5),
                "-H", "User-Agent: Stremio4Kodi/3.3",
                "-H", "Accept: application/json",
                url
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=Config.stremio_timeout() + 10)
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout)
                if data and isinstance(data, dict) and (data.get("results") or data.get("id") or data.get("genres") or data.get("episodes")):
                    return data
        except Exception as e:
            log(f"TMDB curl fetch error [{url[:60]}]: {e}", level="error")

        return None

    def parse_item(self, raw, media_type="movie"):
        """Format raw TMDB item into standard dictionary for Stremio4Kodi rendering."""
        tmdb_id = raw.get("id")
        title = raw.get("title") or raw.get("name") or raw.get("original_title") or raw.get("original_name") or "Sin título"
        original_title = raw.get("original_title") or raw.get("original_name") or title
        
        rel_date = raw.get("release_date") or raw.get("first_air_date") or ""
        year = rel_date[:4] if rel_date else ""
        
        poster_path = raw.get("poster_path")
        poster = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ""
        
        backdrop_path = raw.get("backdrop_path")
        backdrop = f"https://image.tmdb.org/t/p/w1280{backdrop_path}" if backdrop_path else ""
        
        vote_avg = raw.get("vote_average", 0)
        rating = f"{vote_avg:.1f}" if vote_avg else ""

        imdb_id = raw.get("imdb_id") or raw.get("external_ids", {}).get("imdb_id", "")

        return {
            "tmdb_id": str(tmdb_id),
            "imdb_id": imdb_id,
            "name": title,
            "title": title,
            "original_title": original_title,
            "year": year,
            "releaseInfo": year,
            "poster": poster,
            "fanart": backdrop,
            "background": backdrop,
            "description": raw.get("overview", ""),
            "imdbRating": rating,
            "type": media_type
        }

    def _parse_results(self, data, media_type):
        results = data.get("results", [])
        parsed = []
        for item in results:
            parsed.append(self.parse_item(item, media_type))
        return parsed

    # ── TMDB ENDPOINTS ─────────────────────────────────────
    def get_trending(self, media_type="movie", time_window="day", page=1):
        data = self._get(f"/trending/{media_type}/{time_window}", {"page": page})
        return self._parse_results(data, media_type), data.get("total_pages", 1)

    def get_popular(self, media_type="movie", page=1):
        data = self._get(f"/{media_type}/popular", {"page": page})
        return self._parse_results(data, media_type), data.get("total_pages", 1)

    def get_now_playing(self, media_type="movie", page=1):
        if media_type == "movie":
            data = self._get("/movie/now_playing", {"page": page, "region": "ES"})
        else:
            data = self._get("/tv/on_the_air", {"page": page})
        return self._parse_results(data, media_type), data.get("total_pages", 1)

    def get_top_rated(self, media_type="movie", page=1):
        data = self._get(f"/{media_type}/top_rated", {"page": page})
        return self._parse_results(data, media_type), data.get("total_pages", 1)

    def get_genres(self, media_type="movie"):
        data = self._get(f"/genre/{media_type}/list")
        genres = data.get("genres", [])
        return sorted(genres, key=lambda g: g.get("name", ""))

    def search_multi(self, query, page=1):
        data = self._get("/search/multi", {"query": query, "page": page})
        results = data.get("results", [])
        parsed = []
        for item in results:
            media_type = item.get("media_type")
            if media_type in ("movie", "tv"):
                mtype = "movie" if media_type == "movie" else "series"
                parsed.append(self.parse_item(item, mtype))
        return parsed, data.get("total_pages", 1)

    def search_movies(self, query, page=1):
        data = self._get("/search/movie", {"query": query, "page": page})
        return self._parse_results(data, "movie"), data.get("total_pages", 1)

    def search_tv(self, query, page=1):
        data = self._get("/search/tv", {"query": query, "page": page})
        return self._parse_results(data, "series"), data.get("total_pages", 1)

    def discover_by_genre(self, media_type, genre_id, page=1):
        params = {
            "with_genres": str(genre_id),
            "sort_by": "popularity.desc",
            "page": page
        }
        data = self._get(f"/discover/{media_type}", params)
        return self._parse_results(data, media_type), data.get("total_pages", 1)

    def get_top_100_recent(self, media_type="movie", page=1):
        """
        Fetch top rated & highly popular movies/shows from recent years (last 5 years).
        5 pages * 20 items per page = 100 items total.
        """
        current_year = int(time.strftime("%Y"))
        min_year = current_year - 4
        
        params = {
            "sort_by": "vote_average.desc",
            "vote_count.gte": "500" if media_type == "movie" else "300",
            "page": page
        }
        if media_type == "movie":
            params["primary_release_date.gte"] = f"{min_year}-01-01"
            params["primary_release_date.lte"] = f"{current_year}-12-31"
        else:
            params["first_air_date.gte"] = f"{min_year}-01-01"
            params["first_air_date.lte"] = f"{current_year}-12-31"

        data = self._get(f"/discover/{media_type}", params)
        return self._parse_results(data, media_type), data.get("total_pages", 5)

    def get_external_ids(self, media_type, tmdb_id):
        data = self._get(f"/{media_type}/{tmdb_id}/external_ids", cache_ttl=86400)
        return data.get("imdb_id", "") or ""

    def find_by_imdb_id(self, imdb_id):
        if not imdb_id or not imdb_id.startswith("tt"):
            return None, None
        data = self._get(f"/find/{imdb_id}", {"external_source": "imdb_id"}, cache_ttl=86400 * 7)
        if not data:
            return None, None
        tv_results = data.get("tv_results", [])
        if tv_results:
            return str(tv_results[0].get("id")), "series"
        movie_results = data.get("movie_results", [])
        if movie_results:
            return str(movie_results[0].get("id")), "movie"
        return None, None

    def get_details(self, media_type, tmdb_id):
        data = self._get(f"/{media_type}/{tmdb_id}", {"append_to_response": "external_ids"}, cache_ttl=21600)
        if not data:
            return None
        item = self.parse_item(data, media_type)
        ext = data.get("external_ids", {})
        if ext.get("imdb_id"):
            item["imdb_id"] = ext["imdb_id"]
        return item, data

    def get_tv_seasons(self, tmdb_id):
        item, data = self.get_details("tv", tmdb_id)
        if not data:
            return [], item
        seasons = data.get("seasons", [])
        valid_seasons = [s for s in seasons if s.get("season_number", 0) > 0]
        return valid_seasons, item

    def get_tv_episodes(self, tmdb_id, season_number):
        item, _ = self.get_details("tv", tmdb_id)
        data = self._get(f"/tv/{tmdb_id}/season/{season_number}", cache_ttl=21600)
        episodes = data.get("episodes", [])
        parsed_episodes = []
        for ep in episodes:
            ep_num = ep.get("episode_number")
            poster_path = ep.get("still_path")
            thumb = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else item.get("poster", "")
            parsed_episodes.append({
                "episode": ep_num,
                "season": season_number,
                "title": ep.get("name") or f"Episodio {ep_num}",
                "overview": ep.get("overview", ""),
                "thumbnail": thumb,
                "air_date": ep.get("air_date", "")
            })
        return parsed_episodes, item

    def get_movie_changes(self, start_date=None, end_date=None, page=1):
        """
        Get a list of movie IDs changed in TMDB (up to 14 days query range).
        Endpoint: /3/movie/changes
        """
        params = {"page": page}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        data = self._get("/movie/changes", params)
        return data.get("results", []), data.get("total_pages", 1)
