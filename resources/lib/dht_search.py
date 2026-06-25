# -*- coding: utf-8 -*-
"""
DHT & Public Index Search Engine.
Queries Bitsearch, Apibay (The Pirate Bay) and SolidTorrents in parallel.
"""
import json
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from resources.lib.logger import log

class BitsearchClient:
    def __init__(self):
        pass

    def trending(self, trend_type="48h"):
        """
        Get trending torrents from Apibay precompiled JSON.
        Types: "48h" (Top 48 hours), "recent" (Top recent)
        """
        if trend_type == "recent":
            url = "https://apibay.org/precompiled/data_top100_recent.json"
        else:
            url = "https://apibay.org/precompiled/data_top100_48h.json"
            
        log(f"Fetching trending torrents: {url}", level="info")
        data = self._get_json(url)
        if not data or not isinstance(data, list):
            log("Trending request failed or data is not a list", level="warning")
            return []
            
        streams = []
        for item in data:
            infohash = item.get("info_hash") or item.get("infoHash")
            if not infohash or infohash == "0000000000000000000000000000000000000000":
                continue
            try:
                size = int(item.get("size") or 0)
            except Exception:
                size = 0
            try:
                seeds = int(item.get("seeders") or 0)
            except Exception:
                seeds = 0
                
            streams.append(self._format_stream(
                title=item.get("name", "Unknown"),
                infohash=infohash,
                size=size,
                seeds=seeds,
                source="Apibay Trending",
                category="Top"
            ))
            
        return streams

    def search(self, query):
        """
        Search torrents across Bitsearch, Apibay and SolidTorrents in parallel.
        Returns a merged, deduped list of streams.
        """
        log(f"Multi-search query: '{query}'", level="info")
        
        funcs = [
            (self._search_bitsearch, "Bitsearch"),
            (self._search_apibay, "Apibay"),
            (self._search_solidtorrents, "SolidTorrents")
        ]
        
        all_streams = []
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {pool.submit(func, query): name for func, name in funcs}
            for f in as_completed(futures):
                name = futures[f]
                try:
                    results = f.result()
                    all_streams.extend(results)
                    log(f"Search source '{name}' returned {len(results)} results", level="info")
                except Exception as e:
                    log(f"Search source '{name}' failed: {e}", level="error")

        # Deduplicate by infohash (case-insensitive)
        seen = set()
        unique_streams = []
        for s in all_streams:
            h = s.get("infoHash", "").lower()
            if not h or h in seen:
                continue
            seen.add(h)
            unique_streams.append(s)
            
        log(f"Multi-search completed: {len(unique_streams)} unique results", level="info")
        return unique_streams

    def _search_bitsearch(self, query):
        encoded_q = urllib.parse.quote(query)
        url = f"https://bitsearch.eu/api/v1/search?q={encoded_q}&sort=seeders&limit=50"
        data = self._get_json(url)
        if not data or not data.get("success"):
            return []
            
        results = data.get("results", [])
        streams = []
        for item in results:
            infohash = item.get("infohash") or item.get("infoHash")
            if not infohash:
                continue
            size = int(item.get("size") or 0)
            seeds = int(item.get("seeders") or 0)
            streams.append(self._format_stream(
                title=item.get("title", "Unknown"),
                infohash=infohash,
                size=size,
                seeds=seeds,
                source="Bitsearch",
                category=item.get("category", "Video")
            ))
        return streams

    def _search_apibay(self, query):
        # The Pirate Bay API
        encoded_q = urllib.parse.quote(query)
        url = f"https://apibay.org/q.php?q={encoded_q}"
        data = self._get_json(url)
        if not data or not isinstance(data, list):
            return []
            
        # Apibay returns [{"id":"0","name":"No results found",...}] if nothing found
        if len(data) == 1 and data[0].get("id") == "0":
            return []

        streams = []
        for item in data:
            infohash = item.get("info_hash") or item.get("infoHash")
            if not infohash or infohash == "0000000000000000000000000000000000000000":
                continue
            try:
                size = int(item.get("size") or 0)
            except Exception:
                size = 0
            try:
                seeds = int(item.get("seeders") or 0)
            except Exception:
                seeds = 0
                
            streams.append(self._format_stream(
                title=item.get("name", "Unknown"),
                infohash=infohash,
                size=size,
                seeds=seeds,
                source="Apibay",
                category="Torrent"
            ))
        return streams

    def _search_solidtorrents(self, query):
        encoded_q = urllib.parse.quote(query)
        url = f"https://solidtorrents.net/api/v1/search?q={encoded_q}&sort=seeders&limit=50"
        data = self._get_json(url)
        if not data or "results" not in data:
            return []
            
        results = data.get("results", [])
        streams = []
        for item in results:
            infohash = item.get("infohash") or item.get("infoHash")
            if not infohash:
                continue
            size = int(item.get("size") or 0)
            seeds = int(item.get("seeders") or 0)
            streams.append(self._format_stream(
                title=item.get("title", "Unknown"),
                infohash=infohash,
                size=size,
                seeds=seeds,
                source="SolidTorrents",
                category="Torrent"
            ))
        return streams

    def _format_stream(self, title, infohash, size, seeds, source, category):
        size_gb = size / (1024 * 1024 * 1024)
        size_str = f"{size_gb:.2f} GB" if size_gb >= 1 else f"{size / (1024 * 1024):.2f} MB"
        return {
            "name": f"DHT | {category}",
            "title": f"{title}\n👤 {seeds} | 📥 {size_str} ({source})",
            "infoHash": infohash,
            "seeds": seeds,
            "size": size,
            "_addon": source
        }

    def _get_json(self, url):
        try:
            import requests
            resp = requests.get(url, headers={"User-Agent": "Stremio4Kodi/3.2"}, timeout=8)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            log(f"HTTP GET requests error [{url[:60]}]: {e}", level="debug")
            
        try:
            import subprocess
            result = subprocess.run(
                ["curl", "-skL", "--connect-timeout", "8",
                 "-H", "User-Agent: Stremio4Kodi/3.2",
                 url],
                capture_output=True, text=True, timeout=12
            )
            if result.stdout:
                return json.loads(result.stdout)
        except Exception as e:
            log(f"HTTP GET curl error [{url[:60]}]: {e}", level="debug")
            
        return None
