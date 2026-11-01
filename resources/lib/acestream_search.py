# -*- coding: utf-8 -*-
"""
AceStream Search & Trends — Multi-source sports & channel discovery.
Integrates:
  1. search-ace.stream (REST JSON API with DoH anti-blocking)
  2. acestreamid.com (HTML scraping with community votes & real-time dates)
"""
import re
import json
import socket
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

from resources.lib.cache import CacheDB
from resources.lib.logger import log

# Known Cloudflare Anycast IPs for search-ace.stream (used as DoH fallback)
CF_FALLBACK_IPS = ["104.21.44.190", "172.67.203.60"]
DNS_CACHE = {"search-ace.stream": "104.21.44.190"}
_dns_patched = False

SPORTS_KEYWORDS = [
    "futbol", "football", "laliga", "liga", "deport", "movistar", "dazn", "sport",
    "champion", "premier", "f1", "formula", "motogp", "moto", "eurosport", "gol",
    "espn", "arena", "eleven", "sky", "diema", "bein", "match", "bt sport",
    "setanta", "tenis", "tennis", "nba", "basket", "calcio", "bundesliga"
]


def _init_dns_bypass():
    """Bypass ISP DNS blocking (e.g. 127.0.0.1 redirect in Spain) for search-ace.stream.
    Queries Cloudflare/Google DoH and monkeypatches socket.getaddrinfo safely for this domain only.
    """
    global _dns_patched
    if _dns_patched:
        return
    try:
        orig_getaddrinfo = socket.getaddrinfo

        def custom_getaddrinfo(host, port, *args, **kwargs):
            if host == "search-ace.stream":
                real_ip = DNS_CACHE.get("search-ace.stream")
                if not real_ip:
                    # 1. Try Cloudflare DoH (1.1.1.1)
                    try:
                        doh_url = "https://1.1.1.1/dns-query?name=search-ace.stream&type=A"
                        req = urllib.request.Request(
                            doh_url,
                            headers={"accept": "application/dns-json", "User-Agent": "Mozilla/5.0"}
                        )
                        with urllib.request.urlopen(req, timeout=3) as resp:
                            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                            for ans in data.get("Answer", []):
                                if ans.get("type") == 1 and ans.get("data") not in ("127.0.0.1", "0.0.0.0"):
                                    real_ip = ans.get("data")
                                    DNS_CACHE["search-ace.stream"] = real_ip
                                    break
                    except Exception:
                        pass

                    # 2. Try Google DoH (dns.google)
                    if not real_ip:
                        try:
                            doh_url = "https://dns.google/resolve?name=search-ace.stream&type=A"
                            req = urllib.request.Request(
                                doh_url,
                                headers={"User-Agent": "Mozilla/5.0"}
                            )
                            with urllib.request.urlopen(req, timeout=3) as resp:
                                data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                                for ans in data.get("Answer", []):
                                    if ans.get("type") == 1 and ans.get("data") not in ("127.0.0.1", "0.0.0.0"):
                                        real_ip = ans.get("data")
                                        DNS_CACHE["search-ace.stream"] = real_ip
                                        break
                        except Exception:
                            pass

                if not real_ip:
                    real_ip = CF_FALLBACK_IPS[0]

                return orig_getaddrinfo(real_ip, port, *args, **kwargs)

            return orig_getaddrinfo(host, port, *args, **kwargs)

        socket.getaddrinfo = custom_getaddrinfo
        _dns_patched = True
        log("AceStreamSearch: DNS anti-blocking bypass initialized", level="info")
    except Exception as e:
        log(f"AceStreamSearch: DNS bypass initialization error: {e}", level="warning")


class AceStreamSearchClient:
    def __init__(self):
        self.cache = CacheDB()
        _init_dns_bypass()

    @staticmethod
    def clean_title(title):
        """Sanitize channel titles by removing promotional URLs, trackers, and noise."""
        if not title:
            return "AceStream"
        # Remove URLs
        t = re.sub(r"https?://\S+", "", title)
        # Remove known spam hostnames & tags
        t = re.sub(
            r"(?i)\b(elcano\.top|zeronet|shickat\.online|shickat\.blog|shickat|ipfs\.io|ipns|NEW ERA)\b",
            "",
            t,
        )
        # Clean special separators and brackets
        t = re.sub(r"[\|\(\)\[\]\<\>\-]+", " ", t)
        t = " ".join(t.split())
        return t if t else title.strip()

    @staticmethod
    def is_sports_channel(title):
        """Check if title matches any sports keywords."""
        t = title.lower()
        return any(k in t for k in SPORTS_KEYWORDS)

    # ══════════════════════════════════════════════════════
    #  SOURCE 1: search-ace.stream (JSON API)
    # ══════════════════════════════════════════════════════
    def fetch_search_ace(self, query, timeout=4):
        """Query search-ace.stream JSON API."""
        _init_dns_bypass()
        try:
            url = f"https://search-ace.stream/search?query={urllib.parse.quote(query)}"
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                    results = []
                    for item in data:
                        cid = item.get("content_id", "").strip().lower()
                        name = item.get("name", "").strip()
                        if cid and len(cid) == 40:
                            clean_t = self.clean_title(name)
                            results.append({
                                "title": clean_t,
                                "raw_title": name,
                                "hash": cid,
                                "group": "Deportes" if self.is_sports_channel(name) else "En Directo",
                                "logo": "",
                                "tvg_id": "",
                                "source": "SearchAce",
                                "ups": 0,
                                "downs": 0,
                                "date": "",
                            })
                    return results
        except Exception as e:
            log(f"AceStreamSearch: search-ace.stream query '{query}' failed: {e}", level="debug")
        return []

    # ══════════════════════════════════════════════════════
    #  SOURCE 2: acestreamid.com (HTML Scraper)
    # ══════════════════════════════════════════════════════
    def fetch_acestreamid(self, query="", timeout=4):
        """Query or scrape acestreamid.com."""
        try:
            if query:
                url = f"https://acestreamid.com/search/?{urllib.parse.urlencode({'channel': query})}"
            else:
                url = "https://acestreamid.com/"
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
                blocks = re.findall(
                    r'<li class=\"collection-item acestreamidID\s*\">.*?</li>',
                    html,
                    re.S,
                )
                results = []
                for b in blocks:
                    title_m = re.search(r'title=\"([^\"]+)\"', b)
                    hash_m = re.search(r'acestream://([a-f0-9]{40})', b, re.I)
                    up_m = re.search(
                        r'fa-thumbs-up.*?<span class=\"[^\"]*votes_count[^\"]*\">(\d+)</span>',
                        b,
                        re.S,
                    )
                    down_m = re.search(
                        r'fa-thumbs-down.*?<span class=\"[^\"]*votes_count[^\"]*\">(\d+)</span>',
                        b,
                        re.S,
                    )
                    time_m = re.search(r'datetime=\"([^\"]+)\"', b)

                    if title_m and hash_m:
                        raw_title = title_m.group(1).strip()
                        clean_t = self.clean_title(raw_title)
                        h = hash_m.group(1).strip().lower()
                        ups = int(up_m.group(1)) if up_m else 0
                        downs = int(down_m.group(1)) if down_m else 0
                        dt = time_m.group(1) if time_m else ""
                        results.append({
                            "title": clean_t,
                            "raw_title": raw_title,
                            "hash": h,
                            "group": "Deportes" if self.is_sports_channel(raw_title) else "En Directo",
                            "logo": "",
                            "tvg_id": "",
                            "source": "AceStreamID",
                            "ups": ups,
                            "downs": downs,
                            "date": dt,
                        })
                return results
        except Exception as e:
            log(f"AceStreamSearch: acestreamid.com fetch failed: {e}", level="debug")
        return []

    # ══════════════════════════════════════════════════════
    #  TRENDING SPORTS (Fútbol & Deportes en directo)
    # ══════════════════════════════════════════════════════
    def get_trending_sports(self, force_refresh=False):
        """Fetch real-time trending sports channels from both sources.
        Combines top-voted active channels from acestreamid.com and key sports queries from search-ace.stream.
        """
        cache_key = "acestream:trends:sports"
        if not force_refresh:
            cached = self.cache.get(cache_key)
            if cached:
                return cached

        all_channels = []
        queries = ["sport", "dazn", "laliga"]

        with ThreadPoolExecutor(max_workers=4) as executor:
            future_ace_id = executor.submit(self.fetch_acestreamid, "")
            futures_search = [executor.submit(self.fetch_search_ace, q) for q in queries]

            try:
                all_channels.extend(future_ace_id.result())
            except Exception as e:
                log(f"AceStreamSearch: trending acestreamid error: {e}", level="warning")

            for f in as_completed(futures_search):
                try:
                    all_channels.extend(f.result())
                except Exception as e:
                    log(f"AceStreamSearch: trending search_ace error: {e}", level="warning")

        # Deduplicate and filter sports only
        seen_hashes = set()
        filtered = []
        for ch in all_channels:
            h = ch.get("hash", "").lower()
            if not h or h in seen_hashes:
                continue
            seen_hashes.add(h)
            if self.is_sports_channel(ch.get("raw_title", "") or ch.get("title", "")):
                filtered.append(ch)

        # Sort: items with positive net votes first, then alphabetically
        def sort_key(item):
            score = item.get("ups", 0) - item.get("downs", 0)
            return (-score, item.get("title", "").lower())

        filtered.sort(key=sort_key)

        # Cache for 15 minutes (live trends rotate quickly)
        if filtered:
            self.cache.set(cache_key, filtered, ttl=15)

        return filtered

    # ══════════════════════════════════════════════════════
    #  SEARCH — Multi-source concurrent query
    # ══════════════════════════════════════════════════════
    def search(self, query, force_refresh=False):
        """Search active channels across search-ace.stream and acestreamid.com."""
        clean_q = query.strip()
        if not clean_q:
            return []

        cache_key = f"acestream:search:{clean_q.lower()}"
        if not force_refresh:
            cached = self.cache.get(cache_key)
            if cached:
                return cached

        results = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            f_search_ace = executor.submit(self.fetch_search_ace, clean_q)
            f_acestreamid = executor.submit(self.fetch_acestreamid, clean_q)

            for f in as_completed([f_search_ace, f_acestreamid]):
                try:
                    results.extend(f.result())
                except Exception as e:
                    log(f"AceStreamSearch: search worker error: {e}", level="warning")

        # Deduplicate by hash
        seen_hashes = set()
        unique = []
        for ch in results:
            h = ch.get("hash", "").lower()
            if not h or h in seen_hashes:
                continue
            seen_hashes.add(h)
            unique.append(ch)

        # Sort: positive votes first, then title
        def sort_key(item):
            score = item.get("ups", 0) - item.get("downs", 0)
            return (-score, item.get("title", "").lower())

        unique.sort(key=sort_key)

        # Cache search results for 10 minutes
        if unique:
            self.cache.set(cache_key, unique, ttl=10)

        return unique
