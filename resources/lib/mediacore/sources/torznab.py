"""
Torznab / Jackett & Prowlarr Source Provider
Direct integration with Jackett and Prowlarr indexers via standard Torznab XML API.
Inspired by HolyArrs bridges (bridge_jackett.go, bridge_prowlarr.go).
"""

import xml.etree.ElementTree as ET
import urllib.parse
from typing import List, Optional

from resources.lib.mediacore.models import MediaItem, StreamRelease
from resources.lib.mediacore.sources.base import BaseSource
from resources.lib.mediacore.core.http_client import HttpClient
from resources.lib.config import Config
from resources.lib.logger import log


class TorznabSource(BaseSource):
    name = "Torznab"

    def __init__(self):
        self.http = HttpClient(default_timeout=6.0)

    def is_enabled(self) -> bool:
        """Enabled if torznab_enabled setting is true and URL is provided."""
        try:
            return Config.torznab_enabled() and bool(Config.torznab_url())
        except Exception:
            return False

    def _build_url(self, base_url: str, item: MediaItem) -> Optional[str]:
        base_url = base_url.strip().rstrip("/")
        api_key = Config.torznab_apikey().strip()
        if not base_url:
            return None

        # Determine path (Jackett / Prowlarr usually end with /api)
        if not base_url.endswith("/api"):
            base_url = f"{base_url}/api"

        params = {
            "apikey": api_key,
        }

        if item.is_episode and item.season is not None and item.episode is not None:
            params["t"] = "tvsearch"
            params["q"] = item.title
            params["season"] = str(item.season)
            params["ep"] = str(item.episode)
            if item.imdb_id:
                # Strip 'tt' prefix for some torznab indexers or keep as-is
                clean_imdb = item.imdb_id.replace("tt", "")
                params["imdbid"] = clean_imdb
        else:
            params["t"] = "movie"
            params["q"] = f"{item.title} {item.year or ''}".strip()
            if item.imdb_id:
                clean_imdb = item.imdb_id.replace("tt", "")
                params["imdbid"] = clean_imdb

        query_str = urllib.parse.urlencode(params)
        return f"{base_url}?{query_str}"

    def search(self, item: MediaItem) -> List[StreamRelease]:
        if not self.is_enabled():
            return []

        raw_config = Config.torznab_url().replace(";", ",")
        base_urls = [u.strip() for u in raw_config.split(",") if u.strip()]
        if not base_urls:
            return []

        all_releases: List[StreamRelease] = []

        for base_url in base_urls:
            search_url = self._build_url(base_url, item)
            if not search_url:
                continue

            log(f"Torznab searching: {item.title} ({search_url.split('?')[0]})", level="info")
            data, status = self.http.get(search_url, timeout=7.0)
            if not data or status != 200:
                log(f"Torznab query failed for {base_url} (status {status})", level="warning")
                continue

            try:
                root = ET.fromstring(data)
                channel = root.find("channel")
                items = channel.findall("item") if channel is not None else root.findall(".//item")

                for it in items:
                    try:
                        title = it.findtext("title") or "Release"
                        link = it.findtext("link") or ""

                        # Enclosure
                        enclosure = it.find("enclosure")
                        enc_url = enclosure.get("url") if enclosure is not None else ""
                        enc_len = enclosure.get("length") if enclosure is not None else 0

                        url = enc_url or link
                        size_bytes = int(enc_len or 0)

                        # Torznab attributes (support any XML namespace: 2010/etree, 2015/feed, etc.)
                        seeds = 0
                        peers = 0
                        info_hash = ""
                        indexer = it.findtext("prowlarrindexer") or it.findtext("jackettindexer") or "Torznab"

                        for attr in [a for a in it if a.tag.endswith("attr")]:
                            name = attr.get("name")
                            val = attr.get("value")
                            if name == "seeders" and val and val.isdigit():
                                seeds = int(val)
                            elif name == "peers" and val and val.isdigit():
                                peers = int(val)
                            elif name == "infohash" and val:
                                info_hash = val.lower()
                            elif name == "size" and val and val.isdigit() and size_bytes == 0:
                                size_bytes = int(val)
                            elif name == "indexer" and val:
                                indexer = val

                        # Fallback info_hash from magnet URI
                        if not info_hash and "urn:btih:" in url:
                            info_hash = url

                        if not url and not info_hash:
                            continue

                        rel = StreamRelease(
                            source_name=f"Torznab ({indexer})",
                            title=title,
                            info_hash=info_hash,
                            size_bytes=size_bytes,
                            seeds=seeds,
                            peers=peers,
                            url=url,
                            tracker=indexer,
                        )
                        all_releases.append(rel)
                    except Exception as parse_item_err:
                        log(f"Torznab item parse error: {parse_item_err}", level="debug")

            except Exception as xml_err:
                log(f"Torznab XML parse error for {base_url}: {xml_err}", level="warning")

        log(f"Torznab found {len(all_releases)} releases in total for '{item.title}'", level="info")
        return all_releases
