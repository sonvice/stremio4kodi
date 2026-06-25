# -*- coding: utf-8 -*-
"""
Bitsearch DHT Search Client.
Queries the public Bitsearch API to search torrents indexed from the Kademlia DHT.
"""
import json
import urllib.parse
from resources.lib.logger import log

class BitsearchClient:
    def __init__(self):
        pass

    def search(self, query):
        """
        Search torrents on bitsearch.eu API.
        Returns a list of stream dicts compatible with TorrentResolver/Router.
        """
        encoded_q = urllib.parse.quote(query)
        # API Endpoint: sort by seeders to get the most active torrents first
        url = f"https://bitsearch.eu/api/v1/search?q={encoded_q}&sort=seeders&limit=50"
        
        log(f"Bitsearch querying: {url}", level="info")
        
        data = self._get(url)
        if not data or not data.get("success"):
            log("Bitsearch search failed or success is False", level="warning")
            return []
            
        results = data.get("results", [])
        streams = []
        for item in results:
            infohash = item.get("infohash") or item.get("infoHash")
            if not infohash:
                continue
            
            size_bytes = item.get("size", 0)
            size_gb = size_bytes / (1024 * 1024 * 1024)
            size_str = f"{size_gb:.2f} GB" if size_gb >= 1 else f"{size_bytes / (1024 * 1024):.2f} MB"
            
            seeds = item.get("seeders", 0)
            
            # Format title exactly like other streams in the plugin:
            # - Name: "DHT | Category"
            # - Title: Raw title + Seeds + Size info
            streams.append({
                "name": f"DHT | {item.get('category', 'Video')}",
                "title": f"{item.get('title')}\n👤 {seeds} | 📥 {size_str}",
                "infoHash": infohash,
                "seeds": seeds,
                "size": size_bytes,
                "_addon": "Bitsearch DHT"
            })
            
        return streams

    def _get(self, url):
        # HTTP client fallback: try Python requests first, then subprocess curl
        try:
            import requests
            resp = requests.get(url, headers={"User-Agent": "Stremio4Kodi/3.2"}, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            log(f"Bitsearch requests error: {e}", level="debug")
            
        try:
            import subprocess
            result = subprocess.run(
                ["curl", "-skL", "--connect-timeout", "10",
                 "-H", "User-Agent: Stremio4Kodi/3.2",
                 url],
                capture_output=True, text=True, timeout=15
            )
            if result.stdout:
                return json.loads(result.stdout)
        except Exception as e:
            log(f"Bitsearch curl error: {e}", level="debug")
            
        return None
