# -*- coding: utf-8 -*-
"""
Trakt — Sync watchlist, mark watched, get recommendations.

Uses Trakt API v2. User needs a Trakt account and provides
either a Client ID + device auth, or a direct access token.
"""
import time
import requests
import xbmcgui
import xbmcaddon

from resources.lib.config import Config
from resources.lib.logger import log

TRAKT_API = "https://api.trakt.tv"


class Trakt:
    """Trakt.tv API client."""

    def __init__(self):
        self.client_id = Config.trakt_clientid()
        self.token = Config.trakt_token()
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "trakt-api-version": "2",
            "trakt-api-key": self.client_id,
            "User-Agent": "Stremio4Kodi/2.0",
        })
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"

    def is_configured(self):
        return Config.trakt_enabled() and bool(self.client_id) and bool(self.token)

    # ── Device Authentication Flow ─────────────────────────
    def device_auth(self):
        """
        Start device authentication flow.
        Shows a code for the user to enter at trakt.tv/activate.
        Saves the token to settings on success.
        """
        if not self.client_id:
            xbmcgui.Dialog().ok(
                "Trakt",
                "Set your Trakt Client ID in settings first.\n"
                "Get one at trakt.tv/oauth/applications"
            )
            return False

        try:
            # Step 1: Get device code
            resp = requests.post(
                f"{TRAKT_API}/oauth/device/code",
                json={"client_id": self.client_id},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

            code = data["user_code"]
            verify_url = data["verification_url"]
            device_code = data["device_code"]
            interval = data.get("interval", 5)
            expires = data.get("expires_in", 600)

            # Step 2: Show code to user
            dialog = xbmcgui.DialogProgress()
            dialog.create(
                "Trakt Authorization",
                f"Go to: {verify_url}\nEnter code: {code}"
            )

            # Step 3: Poll for authorization
            start = time.time()
            while time.time() - start < expires:
                if dialog.iscanceled():
                    dialog.close()
                    return False

                elapsed = int(time.time() - start)
                pct = int((elapsed / expires) * 100)
                dialog.update(pct, f"Go to: {verify_url}\nEnter code: {code}\nWaiting...")

                time.sleep(interval)

                poll_resp = requests.post(
                    f"{TRAKT_API}/oauth/device/token",
                    json={
                        "code": device_code,
                        "client_id": self.client_id,
                    },
                    timeout=10,
                )

                if poll_resp.status_code == 200:
                    token_data = poll_resp.json()
                    access_token = token_data["access_token"]

                    # Save token
                    addon = xbmcaddon.Addon()
                    addon.setSetting("trakt_token", access_token)
                    self.token = access_token
                    self.session.headers["Authorization"] = f"Bearer {access_token}"

                    dialog.close()
                    xbmcgui.Dialog().ok("Trakt", "Authorization successful!")
                    return True

                elif poll_resp.status_code == 400:
                    # Pending — continue polling
                    continue
                elif poll_resp.status_code == 410:
                    dialog.close()
                    xbmcgui.Dialog().ok("Trakt", "Code expired. Try again.")
                    return False

            dialog.close()
            xbmcgui.Dialog().ok("Trakt", "Timeout. Try again.")
            return False

        except Exception as e:
            log(f"Trakt auth error: {e}", level="error")
            xbmcgui.Dialog().ok("Trakt", f"Error: {e}")
            return False

    # ── Watchlist ──────────────────────────────────────────
    def get_watchlist(self, media_type="movies"):
        """Get user's watchlist. media_type: 'movies' or 'shows'."""
        if not self.is_configured():
            return []
        try:
            resp = self.session.get(
                f"{TRAKT_API}/sync/watchlist/{media_type}",
                timeout=10,
            )
            resp.raise_for_status()
            items = resp.json()

            results = []
            for item in items:
                obj = item.get("movie") or item.get("show", {})
                ids = obj.get("ids", {})
                results.append({
                    "title": obj.get("title", "Unknown"),
                    "year": str(obj.get("year", "")),
                    "imdb_id": ids.get("imdb", ""),
                    "media_type": "movie" if "movie" in item else "series",
                })
            return results
        except Exception as e:
            log(f"Trakt watchlist error: {e}", level="error")
            return []

    def add_to_watchlist(self, imdb_id, media_type="movie"):
        """Add item to Trakt watchlist."""
        if not self.is_configured():
            return
        key = "movies" if media_type == "movie" else "shows"
        try:
            self.session.post(
                f"{TRAKT_API}/sync/watchlist",
                json={key: [{"ids": {"imdb": imdb_id}}]},
                timeout=10,
            )
        except Exception as e:
            log(f"Trakt add watchlist error: {e}", level="error")

    def remove_from_watchlist(self, imdb_id, media_type="movie"):
        """Remove item from Trakt watchlist."""
        if not self.is_configured():
            return
        key = "movies" if media_type == "movie" else "shows"
        try:
            self.session.post(
                f"{TRAKT_API}/sync/watchlist/remove",
                json={key: [{"ids": {"imdb": imdb_id}}]},
                timeout=10,
            )
        except Exception as e:
            log(f"Trakt remove watchlist error: {e}", level="error")

    # ── Mark as watched ────────────────────────────────────
    def mark_watched(self, imdb_id, media_type="movie"):
        """Mark an item as watched on Trakt."""
        if not self.is_configured() or not Config.trakt_sync_watched():
            return
        key = "movies" if media_type == "movie" else "shows"
        try:
            self.session.post(
                f"{TRAKT_API}/sync/history",
                json={key: [{"ids": {"imdb": imdb_id}}]},
                timeout=10,
            )
            log(f"Trakt marked watched: {imdb_id}", level="info")
        except Exception as e:
            log(f"Trakt mark watched error: {e}", level="error")

    # ── Recommendations ────────────────────────────────────
    def get_recommendations(self, media_type="movies", limit=20):
        """Get personalized recommendations."""
        if not self.is_configured():
            return []
        try:
            resp = self.session.get(
                f"{TRAKT_API}/recommendations/{media_type}",
                params={"limit": limit},
                timeout=10,
            )
            if resp.status_code == 200:
                items = resp.json()
                results = []
                for obj in items:
                    ids = obj.get("ids", {})
                    results.append({
                        "title": obj.get("title", ""),
                        "year": str(obj.get("year", "")),
                        "imdb_id": ids.get("imdb", ""),
                        "media_type": "movie" if media_type == "movies" else "series",
                    })
                return results
        except Exception as e:
            log(f"Trakt recommendations error: {e}", level="error")
        return []

    # ── Trending ───────────────────────────────────────────
    def get_trending(self, media_type="movies", limit=20):
        """Get trending items."""
        try:
            resp = self.session.get(
                f"{TRAKT_API}/{media_type}/trending",
                params={"limit": limit},
                headers={
                    "Content-Type": "application/json",
                    "trakt-api-version": "2",
                    "trakt-api-key": self.client_id,
                },
                timeout=10,
            )
            if resp.status_code == 200:
                items = resp.json()
                results = []
                for item in items:
                    obj = item.get("movie") or item.get("show", {})
                    ids = obj.get("ids", {})
                    results.append({
                        "title": obj.get("title", ""),
                        "year": str(obj.get("year", "")),
                        "imdb_id": ids.get("imdb", ""),
                        "watchers": item.get("watchers", 0),
                        "media_type": "movie" if "movie" in item else "series",
                    })
                return results
        except Exception as e:
            log(f"Trakt trending error: {e}", level="error")
        return []

    # ── Scrobbling / Real-time Sync ────────────────────────
    def scrobble_action(self, action, imdb_id, media_type, progress):
        """
        Scrobble action: 'start', 'pause', or 'stop'.
        progress: float percentage (0.0 to 100.0)
        """
        if not self.is_configured():
            return
        key = "movie" if media_type == "movie" else "episode"
        try:
            self.session.post(
                f"{TRAKT_API}/scrobble/{action}",
                json={
                    key: {"ids": {"imdb": imdb_id}},
                    "progress": progress
                },
                timeout=10,
            )
            log(f"Trakt scrobble {action}: {imdb_id} ({progress}%)", level="info")
        except Exception as e:
            log(f"Trakt scrobble error: {e}", level="error")
