# -*- coding: utf-8 -*-
"""
StremioClient — HTTP client for Stremio addon protocol.
v3.2: Fixed streaming platform duplication (group movie+series catalogs).
      Removed livetv methods (replaced by AceStream module).
"""
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote

from resources.lib.config import Config
from resources.lib.cache import CacheDB
from resources.lib.logger import log

try:
    import requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except ImportError:
    pass


class StremioClient:
    def __init__(self):
        self.cache = CacheDB()

    @staticmethod
    def _resolve_addon_url(addon_url):
        if "tmdb-addon" in addon_url and "%7B" not in addon_url and "{" not in addon_url:
            lang = Config.language() or "es"
            lang_map = {"es": "es-ES", "en": "en-US", "fr": "fr-FR",
                        "de": "de-DE", "it": "it-IT", "pt": "pt-BR"}
            lang_code = lang_map.get(lang, f"{lang}-{lang.upper()}")
            import json as jsonlib
            from urllib.parse import quote as urlquote
            config = jsonlib.dumps({"language": lang_code}, separators=(',', ':'))
            addon_url = f"{addon_url}/{urlquote(config)}"
        return addon_url

    def _get(self, url, timeout=None):
        import json as jsonlib
        timeout = timeout or Config.stremio_timeout()
        data = self._get_requests(url, timeout)
        if data is not None:
            return data
        data = self._get_curl(url, timeout)
        if data is not None:
            return data
        return None

    def _get_requests(self, url, timeout):
        import json as jsonlib
        try:
            import requests
            resp = requests.get(
                url,
                headers={
                    "User-Agent": "Stremio4Kodi/3.2",
                    "Accept": "application/json",
                },
                timeout=(timeout, timeout + 5),
                verify=False,
            )
            resp.raise_for_status()
            text = resp.text.strip()
            if not text:
                return None
            if text[0] not in ('{', '['):
                return None
            return jsonlib.loads(text)
        except ImportError:
            pass
        except Exception as e:
            log(f"requests error [{url}]: {e}", level="debug")
        return None

    def _get_curl(self, url, timeout):
        import json as jsonlib
        try:
            import subprocess
            result = subprocess.run(
                ["curl", "-skL", "--connect-timeout", str(timeout),
                 "--max-time", str(timeout + 5),
                 "-H", "User-Agent: Stremio4Kodi/3.2",
                 "-H", "Accept: application/json",
                 url],
                capture_output=True, text=True, timeout=timeout + 10,
            )
            text = result.stdout.strip()
            if not text or text[0] not in ('{', '['):
                return None
            return jsonlib.loads(text)
        except FileNotFoundError:
            pass
        except Exception as e:
            log(f"curl error [{url}]: {e}", level="debug")
        return None

    # ── Manifest ───────────────────────────────────────────
    def get_manifest(self, addon_url):
        addon_url = self._resolve_addon_url(addon_url)
        cache_key = f"manifest:{addon_url}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        data = self._get(f"{addon_url}/manifest.json")
        if data:
            data["_resolved_url"] = addon_url
            self.cache.set(cache_key, data, ttl=86400)
        return data

    def get_all_manifests(self):
        manifests = {}
        urls = Config.stremio_addon_urls()

        if Config.stremio_parallel() and len(urls) > 1:
            with ThreadPoolExecutor(max_workers=min(len(urls), 5)) as pool:
                futures = {pool.submit(self.get_manifest, u): u for u in urls}
                for future in as_completed(futures):
                    url = futures[future]
                    try:
                        m = future.result()
                        if m:
                            resolved = m.get("_resolved_url", self._resolve_addon_url(url))
                            manifests[resolved] = m
                    except Exception as e:
                        log(f"Error fetching manifest for {url}: {e}", level="error")
        else:
            for url in urls:
                resolved = self._resolve_addon_url(url)
                m = self.get_manifest(url)
                if m:
                    manifests[resolved] = m
        return manifests

    # ── Catalogs ───────────────────────────────────────────
    def get_catalog(self, addon_url, media_type, catalog_id, extra=""):
        extra_path = f"/{extra}" if extra else ""
        url = f"{addon_url}/catalog/{media_type}/{catalog_id}{extra_path}.json"

        cache_key = f"catalog:{url}"
        if Config.cache_enabled():
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

        data = self._get(url)
        items = data.get("metas", []) if data else []

        if Config.cache_enabled() and items:
            self.cache.set(cache_key, items)
        return items

    def get_catalogs_for_type(self, media_type):
        catalogs = []
        manifests = self.get_all_manifests()
        for addon_url, manifest in manifests.items():
            for cat in manifest.get("catalogs", []):
                if cat.get("type") == media_type:
                    catalogs.append({
                        "addon_url": addon_url,
                        "addon_name": manifest.get("name", "Unknown"),
                        "catalog_id": cat["id"],
                        "name": cat.get("name", cat["id"]),
                        "extra_supported": cat.get("extraSupported", []),
                        "extra_required": cat.get("extraRequired", []),
                        "genres": cat.get("extra", [{}])[0].get("options", [])
                            if cat.get("extra") else [],
                    })
        return catalogs

    # ── Genres ─────────────────────────────────────────────
    def get_genres(self, media_type):
        all_genres = set()
        catalogs = self.get_catalogs_for_type(media_type)
        for cat in catalogs:
            extras = cat.get("extra_supported", [])
            if "genre" in extras:
                for g in cat.get("genres", []):
                    all_genres.add(g)
        if not all_genres:
            all_genres = {
                "Action", "Adventure", "Animation", "Comedy", "Crime",
                "Documentary", "Drama", "Family", "Fantasy", "History",
                "Horror", "Music", "Mystery", "Romance", "Science Fiction",
                "Thriller", "War", "Western",
            }
        return sorted(all_genres)

    def get_catalog_by_genre(self, media_type, genre):
        all_items = {}
        catalogs = self.get_catalogs_for_type(media_type)
        for cat in catalogs:
            if "genre" in cat.get("extra_supported", []):
                encoded = quote(genre)
                items = self.get_catalog(
                    cat["addon_url"], media_type, cat["catalog_id"],
                    extra=f"genre={encoded}",
                )
                for item in items:
                    iid = item.get("imdb_id") or item.get("id", "")
                    if iid and iid not in all_items:
                        all_items[iid] = item
        return list(all_items.values())

    # ── Search ─────────────────────────────────────────────
    def search(self, query, media_type="movie"):
        results = {}
        urls = Config.stremio_addon_urls()

        def _search_addon(addon_url):
            manifest = self.get_manifest(addon_url)
            if not manifest:
                return []
            resolved_url = manifest.get("_resolved_url", self._resolve_addon_url(addon_url))
            items = []
            for cat in manifest.get("catalogs", []):
                if cat.get("type") != media_type:
                    continue
                extras = cat.get("extraSupported", [])
                if "search" not in extras:
                    continue
                encoded_q = quote(query)
                url = (f"{resolved_url}/catalog/{media_type}/"
                       f"{cat['id']}/search={encoded_q}.json")
                data = self._get(url)
                if data:
                    items.extend(data.get("metas", []))
            return items

        if Config.stremio_parallel() and len(urls) > 1:
            with ThreadPoolExecutor(max_workers=min(len(urls), 4)) as pool:
                futures = {pool.submit(_search_addon, u): u for u in urls}
                for future in as_completed(futures):
                    try:
                        for item in future.result():
                            imdb = item.get("imdb_id") or item.get("id", "")
                            if imdb and imdb not in results:
                                results[imdb] = item
                    except Exception as e:
                        log(f"Search error: {e}", level="error")
        else:
            for url in urls:
                for item in _search_addon(url):
                    imdb = item.get("imdb_id") or item.get("id", "")
                    if imdb and imdb not in results:
                        results[imdb] = item

        return list(results.values())

    # ── Metadata ───────────────────────────────────────────
    def get_meta(self, media_type, imdb_id):
        cache_key = f"meta:{media_type}:{imdb_id}"
        if Config.cache_enabled():
            cached = self.cache.get(cache_key)
            if cached:
                return cached

        best_meta = None
        best_priority = -1

        for addon_url in Config.stremio_addon_urls():
            manifest = self.get_manifest(addon_url)
            if not manifest:
                continue
            types = manifest.get("types", [])
            resources = [r if isinstance(r, str) else r.get("name", "")
                         for r in manifest.get("resources", [])]
            if media_type not in types or "meta" not in resources:
                continue
            resolved_url = manifest.get("_resolved_url", self._resolve_addon_url(addon_url))
            url = f"{resolved_url}/meta/{media_type}/{imdb_id}.json"
            data = self._get(url)
            if data and "meta" in data:
                meta = data["meta"]
                priority = 0
                addon_name = manifest.get("name", "").lower()
                addon_id = manifest.get("id", "").lower()
                if "tmdb" in addon_name or "tmdb" in addon_id:
                    priority = 10
                    if "es" in resolved_url.lower() or "es-es" in resolved_url.lower():
                        priority = 20
                elif "cinemeta" in addon_name or "cinemeta" in addon_id:
                    priority = 5
                if priority > best_priority:
                    best_priority = priority
                    best_meta = meta
                if priority >= 20:
                    break

        if best_meta and Config.cache_enabled():
            self.cache.set(cache_key, best_meta)
        return best_meta

    # ── Streams ────────────────────────────────────────────
    def get_streams(self, media_type, imdb_id):
        cache_key = f"streams:{media_type}:{imdb_id}"
        if Config.cache_enabled():
            cached = self.cache.get(cache_key)
            if cached:
                return cached

        all_streams = []

        def _fetch(addon_url):
            manifest = self.get_manifest(addon_url)
            if not manifest:
                return []
            resources = [r if isinstance(r, str) else r.get("name", "")
                         for r in manifest.get("resources", [])]
            if "stream" not in resources:
                return []
            resolved_url = manifest.get("_resolved_url", self._resolve_addon_url(addon_url))
            url = f"{resolved_url}/stream/{media_type}/{imdb_id}.json"
            data = self._get(url)
            if data:
                streams = data.get("streams", [])
                name = manifest.get("name", "Unknown")
                for s in streams:
                    s["_addon"] = name
                return streams
            return []

        urls = Config.stremio_addon_urls()
        if Config.stremio_parallel() and len(urls) > 1:
            with ThreadPoolExecutor(max_workers=min(len(urls), 4)) as pool:
                futures = {pool.submit(_fetch, u): u for u in urls}
                for f in as_completed(futures):
                    try:
                        all_streams.extend(f.result())
                    except Exception as e:
                        log(f"Stream fetch error: {e}", level="error")
        else:
            for url in urls:
                all_streams.extend(_fetch(url))

        if Config.cache_enabled() and all_streams:
            self.cache.set(cache_key, all_streams, ttl=1800)

        return all_streams

    # ══════════════════════════════════════════════════════
    #  UTILITY — dedup, extra manifests, subtitles
    # ══════════════════════════════════════════════════════

    @staticmethod
    def dedup_items(items):
        try:
            seen = set()
            unique = []
            for item in items:
                iid = item.get("imdb_id") or item.get("id", "")
                if not iid or iid in seen:
                    continue
                seen.add(iid)
                unique.append(item)
            return unique
        except Exception:
            return items

    def _get_extra_manifest(self, url):
        try:
            cache_key = f"manifest:{url}"
            cached = self.cache.get(cache_key)
            if cached:
                return cached
            data = self._get(f"{url}/manifest.json")
            if data:
                data["_resolved_url"] = url
                self.cache.set(cache_key, data, ttl=86400)
            return data
        except Exception as e:
            log(f"Extra manifest error: {e}", level="debug")
            return None

    # ══════════════════════════════════════════════════════
    #  v3.2 FIX: Streaming Platforms — grouped by name
    #  Before: showed "Netflix" twice (movies + series).
    #  Now: groups catalogs by base name, user picks type after.
    # ══════════════════════════════════════════════════════
    def get_streaming_platforms(self):
        """Get streaming platforms, grouped by name to avoid duplicates.
        Returns list: {name, catalogs: [{type, catalog_id, addon_url}]}
        """
        try:
            if not Config.streaming_catalogs_enabled():
                return []
            url = Config.streaming_catalogs_url()
            manifest = self._get_extra_manifest(url)
            if not manifest:
                return []

            resolved = manifest.get("_resolved_url", url)

            # Group catalogs by a "base name" — strip type suffixes
            from collections import OrderedDict
            grouped = OrderedDict()

            for cat in manifest.get("catalogs", []):
                cat_name = cat.get("name", cat["id"])
                cat_type = cat.get("type", "movie")
                cat_id = cat["id"]

                # Normalize platform name: remove trailing type hints
                base_name = cat_name
                # Some catalogs have names like "Netflix - Movies", "Netflix - Series"
                for suffix in (" - Movies", " - Series", " - Peliculas",
                               " - Movie", " - Serie", " Movies", " Series"):
                    if base_name.endswith(suffix):
                        base_name = base_name[:-len(suffix)].strip()
                        break

                if base_name not in grouped:
                    grouped[base_name] = {
                        "name": base_name,
                        "catalogs": [],
                    }
                grouped[base_name]["catalogs"].append({
                    "type": cat_type,
                    "catalog_id": cat_id,
                    "addon_url": resolved,
                    "full_name": cat_name,
                })

            return list(grouped.values())
        except Exception as e:
            log(f"Streaming platforms error: {e}", level="debug")
            return []

    def get_subtitles(self, media_type, imdb_id):
        try:
            if not Config.subs_enabled():
                return []
            subs_url = Config.subs_addon_url()
            url = f"{subs_url}/subtitles/{media_type}/{imdb_id}.json"
            data = self._get(url, timeout=8)
            subs = data.get("subtitles", []) if data else []
            pref_lang = Config.subs_language()
            if pref_lang and subs:
                lang_subs = [s for s in subs if s.get("lang", "").startswith(pref_lang)]
                if lang_subs:
                    subs = lang_subs
            return subs
        except Exception as e:
            log(f"Subtitles error: {e}", level="debug")
            return []
