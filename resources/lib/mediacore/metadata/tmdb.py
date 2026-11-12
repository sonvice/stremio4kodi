"""
TMDB Metadata Provider
Converts TMDB API results into unified MediaItem objects.
"""

from typing import List, Optional
from resources.lib.mediacore.models import MediaItem
from resources.lib.mediacore.metadata.base import BaseMetadataProvider
from resources.lib.tmdb import TMDBClient
from resources.lib.logger import log


class TmdbMetadataProvider(BaseMetadataProvider):
    name = "TMDB"

    def __init__(self):
        self._client = TMDBClient()

    def _to_media_item(self, raw: dict, media_type: str = "movie") -> MediaItem:
        title = raw.get("title") or raw.get("name") or "Sin título"
        date_str = raw.get("release_date") or raw.get("first_air_date") or ""
        year = None
        if date_str and len(date_str) >= 4 and date_str[:4].isdigit():
            year = int(date_str[:4])

        tmdb_id = raw.get("id")
        imdb_id = raw.get("imdb_id") or raw.get("external_ids", {}).get("imdb_id") or ""
        tvdb_id = raw.get("external_ids", {}).get("tvdb_id")

        ids = {}
        if tmdb_id:
            ids["tmdb"] = tmdb_id
        if imdb_id:
            ids["imdb"] = imdb_id
        if tvdb_id:
            ids["tvdb"] = tvdb_id

        poster_path = raw.get("poster_path") or ""
        poster = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ""

        backdrop_path = raw.get("backdrop_path") or ""
        backdrop = f"https://image.tmdb.org/t/p/original{backdrop_path}" if backdrop_path else ""

        genres = [g.get("name") for g in raw.get("genres", []) if isinstance(g, dict) and g.get("name")]
        cast = []
        credits = raw.get("credits", {})
        if credits and "cast" in credits:
            cast = [c.get("name") for c in credits.get("cast", [])[:5] if c.get("name")]

        return MediaItem(
            media_type="movie" if media_type == "movie" else "tvshow",
            title=title,
            year=year,
            ids=ids,
            overview=raw.get("overview") or "",
            poster=poster,
            backdrop=backdrop,
            rating=raw.get("vote_average") or 0.0,
            votes=raw.get("vote_count") or 0,
            genres=genres,
            cast=cast,
            duration=raw.get("runtime") or 0,
            raw_data=raw,
        )

    def get_item(self, media_type: str, item_id: str) -> Optional[MediaItem]:
        t = "movie" if media_type == "movie" else "tv"
        try:
            # item_id can be tmdb_id or imdb_id
            if str(item_id).isdigit():
                raw = self._client.get_movie_details(int(item_id)) if t == "movie" else self._client.get_show_details(int(item_id))
            else:
                raw = self._client.find_by_imdb(item_id, media_type=t)
            if raw:
                return self._to_media_item(raw, media_type)
        except Exception as e:
            log(f"TMDB get_item error ({media_type}/{item_id}): {e}", level="warning")
        return None

    def search(self, query: str, media_type: str = "movie") -> List[MediaItem]:
        t = "movie" if media_type == "movie" else "tv"
        raw_list = self._client.search(query, media_type=t)
        return [self._to_media_item(r, media_type) for r in raw_list if r]

    def get_trending(self, media_type: str = "movie", page: int = 1) -> List[MediaItem]:
        t = "movie" if media_type == "movie" else "tv"
        raw_list = self._client.get_trending(media_type=t, page=page)
        return [self._to_media_item(r, media_type) for r in raw_list if r]

    def get_popular(self, media_type: str = "movie", page: int = 1) -> List[MediaItem]:
        t = "movie" if media_type == "movie" else "tv"
        raw_list = self._client.get_popular(media_type=t, page=page)
        return [self._to_media_item(r, media_type) for r in raw_list if r]
