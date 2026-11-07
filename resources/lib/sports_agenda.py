# -*- coding: utf-8 -*-
"""
Sports Agenda — Real-time discovery of today's sports events & TV broadcasts.
Scrapes and parses today's televised sports agenda (Fútbol, Baloncesto/NBA, F1, MotoGP, Tenis, etc.)
from futbolenlatv.es/deporte.
Provides:
  - Daily events listing with kickoff time, competition, teams, and broadcast channels.
  - Automatic cross-referencing with AceStream channel names (showing LIVE or UPCOMING match).
  - Search queries generator for AceStream resolution.
"""
import re
import html
from datetime import datetime, timedelta
import urllib.request
import urllib.parse

from resources.lib.cache import CacheDB
from resources.lib.logger import log

AGENDA_URL = "https://www.futbolenlatv.es/deporte"
AGENDA_FALLBACK_URL = "https://www.futbolenlatv.es/"


class SportsAgendaClient:
    def __init__(self):
        self.cache = CacheDB()

    @staticmethod
    def _clean_text(text):
        """Clean HTML tags and decode HTML entities."""
        if not text:
            return ""
        clean = re.sub(r"<[^>]+>", "", text)
        clean = html.unescape(clean)
        return " ".join(clean.split()).strip()

    def fetch_today_events(self, force_refresh=False):
        """
        Fetches today's sports agenda.
        Returns a list of event dictionaries:
        [{
            'time': '16:15',
            'sport': 'Fútbol',
            'competition': 'La Liga EA Sports',
            'title': 'Espanyol - Deportivo',
            'home': 'Espanyol',
            'away': 'Deportivo',
            'channels': ['DAZN LaLiga', 'LaLiga TV Bar']
        }, ...]
        Cached for 30 minutes.
        """
        cache_key = "sports:agenda:today"
        if not force_refresh:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

        raw_html = ""
        for url in [AGENDA_URL, AGENDA_FALLBACK_URL]:
            try:
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
                    }
                )
                with urllib.request.urlopen(req, timeout=6) as resp:
                    if resp.status == 200:
                        raw_html = resp.read().decode("utf-8", errors="ignore")
                        if raw_html:
                            break
            except Exception as e:
                log(f"SportsAgenda: fetch failed for {url}: {e}", level="debug")

        if not raw_html:
            log("SportsAgenda: could not fetch sports agenda", level="warning")
            return []

        events = self._parse_html(raw_html)
        if events:
            # Cache for 30 minutes
            self.cache.set(cache_key, events, ttl=30)
            log(f"SportsAgenda: loaded {len(events)} events for today", level="info")
        return events

    def _parse_html(self, raw_html):
        """Extracts today's events from the HTML."""
        events = []

        # Split into date sections (cabeceraTabla)
        sections = re.split(r"<tr[^>]*class=\"cabeceraTabla[^\"]*\"[^>]*>", raw_html)
        if len(sections) < 2:
            # Fallback if cabeceraTabla is not matched
            today_section = raw_html
        else:
            # The first section after the first cabeceraTabla corresponds to today
            today_section = sections[1]

        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", today_section, re.S)
        current_comp = ""

        for r in rows:
            # Check if there is an embedded competition header
            comp_m = re.search(r"class=\"cabeceraCompe[^\"]*\"[^>]*>.*?<a[^>]*>(.*?)</a>", r, re.S)
            if comp_m:
                current_comp = self._clean_text(comp_m.group(1))
                continue

            time_m = re.search(r"class=\"hora\s*\"[^>]*>\s*([0-9]{2}:[0-9]{2})\s*</td>", r)
            if not time_m:
                continue
            time_str = time_m.group(1).strip()

            # Sport detection
            sport_m = re.search(
                r"title=\"(Fútbol|Baloncesto|Automovilismo|Motociclismo|Tenis|Ciclismo|Balonmano|Pádel|Golf|MMA|Fútbol Sala|Boxeo|Béisbol|Rugby[^\"]*|[^\"]+)\"\s+width=\"22\"",
                r
            )
            sport = sport_m.group(1).strip() if sport_m else "Deportes"

            # Competition label
            comp = current_comp
            if not comp:
                c_lbl = re.search(r"<label[^>]*title=\"([^\"]+)\"", r)
                if not c_lbl:
                    c_lbl = re.search(r"href=\"/competicion/[^\"]+\"[^>]*>([^<]+)</a>", r)
                if c_lbl:
                    comp = self._clean_text(c_lbl.group(1))

            # Teams & match title
            local_m = re.search(r"class=\"local\"[^>]*>.*?<span[^>]*title=\"([^\"]+)\"", r, re.S)
            visit_m = re.search(r"class=\"visitante\"[^>]*>.*?<span[^>]*title=\"([^\"]+)\"", r, re.S)
            name_m = re.search(r"itemprop=\"name\"\s+content=\"([^\"]+)\"", r)

            if local_m and visit_m:
                home = self._clean_text(local_m.group(1))
                away = self._clean_text(visit_m.group(1))
                title = f"{home} - {away}"
            elif name_m:
                title = self._clean_text(name_m.group(1))
                parts = title.split(" - ")
                home = parts[0].strip() if len(parts) > 1 else title
                away = parts[1].strip() if len(parts) > 1 else ""
            else:
                continue

            # Channels broadcasting this event
            canales_block = re.search(r"class=\"canales\"[^>]*>(.*?)</td>", r, re.S)
            channels = []
            if canales_block:
                for c_m in re.finditer(r"<li[^>]*title=\"([^\"]+)\"", canales_block.group(1)):
                    ch_name = self._clean_text(c_m.group(1))
                    ch_name = re.sub(r"\(Ver en directo\)", "", ch_name).strip()
                    if ch_name and ch_name not in channels:
                        channels.append(ch_name)

            events.append({
                "time": time_str,
                "sport": sport,
                "competition": comp or sport,
                "title": title,
                "home": home,
                "away": away,
                "channels": channels
            })

        return events

    def get_categories(self, events=None):
        """Returns sorted list of available sport categories with event count."""
        if events is None:
            events = self.fetch_today_events()
        counts = {}
        for ev in events:
            s = ev.get("sport") or "Otros"
            counts[s] = counts.get(s, 0) + 1
        # Sort by most events descending, but keep Fútbol and Baloncesto on top
        priority = ["Fútbol", "Baloncesto", "Automovilismo", "Motociclismo", "Tenis"]
        def sort_cat(item):
            name, count = item
            p_idx = priority.index(name) if name in priority else 999
            return (p_idx, -count)
        return sorted(counts.items(), key=sort_cat)

    def get_events_by_sport(self, sport=None, events=None):
        """Returns events filtered by sport, sorted chronologically."""
        if events is None:
            events = self.fetch_today_events()
        if not sport or sport.lower() in ("todos", "all"):
            res = list(events)
        else:
            res = [e for e in events if e.get("sport", "").lower() == sport.lower()]
        res.sort(key=lambda x: x.get("time", "99:99"))
        return res

    @staticmethod
    def _normalize_name(name):
        """Strip punctuation and whitespace for fuzzy channel matching."""
        n = re.sub(r"\(.*?\)", "", name)
        n = re.sub(r"[^a-zA-Z0-9]", "", n).lower()
        return n

    def get_event_status(self, time_str):
        """
        Determines if an event is currently LIVE, NEXT, or PAST.
        Returns: ('LIVE', duration_str), ('NEXT', mins_until_str), or None.
        """
        if not time_str or ":" not in time_str:
            return None, ""
        try:
            now = datetime.now()
            h, m = map(int, time_str.split(":"))
            ev_start = now.replace(hour=h, minute=m, second=0, microsecond=0)
            # Duration window: 120 minutes (typical football/basketball match)
            ev_end = ev_start + timedelta(minutes=120)

            if ev_start <= now <= ev_end:
                mins_in = int((now - ev_start).total_seconds() / 60)
                return "LIVE", f"+{mins_in}'"
            elif now < ev_start <= (now + timedelta(minutes=150)):
                mins_left = int((ev_start - now).total_seconds() / 60)
                return "NEXT", f"{time_str}"
        except Exception:
            pass
        return None, ""

    def find_event_for_channel(self, channel_name, events=None):
        """
        Cross-references an AceStream channel title (e.g. 'DAZN LaLiga HD' or 'Movistar Plus+')
        with today's televised sports events.
        Returns the matching event and its status ('LIVE' or 'NEXT') if currently relevant.
        """
        if not channel_name:
            return None

        if events is None:
            events = self.fetch_today_events()
        if not events:
            return None

        norm_ch = self._normalize_name(channel_name)
        if len(norm_ch) < 3:
            return None

        # Check in order: LIVE matches first, then NEXT matches
        live_candidate = None
        next_candidate = None

        for ev in events:
            ev_chans = ev.get("channels", [])
            for c in ev_chans:
                norm_c = self._normalize_name(c)
                if not norm_c or len(norm_c) < 3:
                    continue

                # Match if channel name contains or is contained
                match = (norm_c in norm_ch) or (norm_ch in norm_c)
                # Specific common aliases
                if not match:
                    if ("daznlaliga" in norm_ch and "daznlaliga" in norm_c) or \
                       ("mlaliga" in norm_ch and "mlaliga" in norm_c) or \
                       ("ligadecampeones" in norm_ch and "ligadecampeones" in norm_c) or \
                       ("dazn1" in norm_ch and "dazn1" in norm_c) or \
                       ("dazn2" in norm_ch and "dazn2" in norm_c) or \
                       ("eurosport1" in norm_ch and "eurosport1" in norm_c) or \
                       ("eurosport2" in norm_ch and "eurosport2" in norm_c) or \
                       ("mvamos" in norm_ch and "mvamos" in norm_c) or \
                       ("vamos" in norm_ch and "vamos" in norm_c):
                        match = True

                if match:
                    status, tag_info = self.get_event_status(ev.get("time"))
                    if status == "LIVE":
                        return {"status": "LIVE", "info": tag_info, "event": ev}
                    elif status == "NEXT" and not next_candidate:
                        next_candidate = {"status": "NEXT", "info": tag_info, "event": ev}

        return next_candidate
