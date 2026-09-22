# -*- coding: utf-8 -*-
"""
Service — Background monitor for:
  1. Cache cleanup
  2. Resume position tracking (Continue Watching)
  3. Auto-next episode
  4. Auto subtitle search
"""
import json
import xbmc
import xbmcgui
import xbmcaddon

from resources.lib.cache import CacheDB
from resources.lib.config import Config
from resources.lib.logger import log

CLEANUP_INTERVAL = 3600  # 1 hour
MONITOR_INTERVAL = 5     # Check playback every 5 seconds


class PlaybackMonitor(xbmc.Player):
    """Monitors active playback for resume tracking and auto-next."""

    def __init__(self, cache):
        super().__init__()
        self.cache = cache
        self._playing = False
        self._subs_searched = False
        self._last_scrobble_time = 0
        self._last_pos = 0.0
        self._last_dur = 0.0
        self._auto_next_lock = False
        self._auto_next_notified = False
        self._auto_next_in_progress = False
        self._last_reopen_time = 0.0

    def onPlayBackStarted(self):
        """Called when playback starts."""
        self._playing = True
        self._subs_searched = False
        self._auto_next_lock = False
        self._auto_next_notified = False
        self._auto_next_in_progress = False
        self._last_reopen_time = 0.0
        self._last_pos = 0.0
        self._last_dur = 0.0
        log("Playback started", level="info")
        self._scrobble("start", 0.0)

    def _stop_engine_torrents(self):
        """Stop background torrent downloads when user stops playback."""
        import threading
        def _stop():
            import urllib.request, json
            # Stop Torrest active torrents
            try:
                req = urllib.request.Request("http://127.0.0.1:61235/torrents", headers={"User-Agent": "Kodi"})
                with urllib.request.urlopen(req, timeout=1.5) as r:
                    torrents = json.loads(r.read().decode())
                    for t in torrents:
                        ih = t.get("info_hash")
                        if ih:
                            del_req = urllib.request.Request(f"http://127.0.0.1:61235/torrents/{ih}?delete=true", method="DELETE")
                            urllib.request.urlopen(del_req, timeout=1.5)
                            log(f"Stopped Torrest session: {ih}", level="info")
            except Exception:
                pass

            # Pause Elementum active torrents
            try:
                urllib.request.urlopen("http://127.0.0.1:65220/torrents/pause", timeout=1.5)
            except Exception:
                pass

        threading.Thread(target=_stop, daemon=True).start()

    def onPlayBackStopped(self):
        """Called when user stops playback."""
        self._save_position()
        self._playing = False
        log("Playback stopped", level="info")
        self._scrobble("stop")
        self._stop_engine_torrents()

        ratio = 0.0
        if self._last_dur > 0:
            ratio = self._last_pos / self._last_dur

        if ratio < 0.92 and Config.reopen_streams_on_cancel():
            self._reopen_streams()

    def onPlayBackEnded(self):
        """Called when playback reaches the end."""
        self._playing = False
        log("Playback ended", level="info")

        ratio = 0.0
        if self._last_dur > 0:
            ratio = self._last_pos / self._last_dur

        if ratio >= 0.92:
            self._mark_completed()
            self._scrobble("stop", 100.0)
            self._stop_engine_torrents()
            if Config.auto_next_episode() and not self._auto_next_lock:
                self._auto_next_lock = True
                self._try_next_episode()
        else:
            log(f"Playback ended prematurely at {ratio*100:.1f}%, preserving resume position", level="info")
            self._save_position()
            self._scrobble("stop", ratio * 100.0)
            if Config.stall_recovery_dialog():
                self._handle_playback_stall(ratio)

    def onPlayBackPaused(self):
        self._save_position()
        self._scrobble("pause")

    def onPlayBackResumed(self):
        self._scrobble("start")

    def tick(self):
        """Called periodically from the main service loop."""
        if not self._playing:
            return
        if not self.isPlaying():
            self._playing = False
            return

        try:
            # Auto-search subtitles once
            if not self._subs_searched and Config.subs_auto_search():
                if self.isPlaying() and self.getTime() > 5:
                    self._subs_searched = True
                    # Trigger Kodi's built-in subtitle search
                    xbmc.executebuiltin("ActivateWindow(SubtitleSearch)")
                    log("Auto subtitle search triggered", level="info")

            # Save position periodically
            self._save_position()

            # Periodic Trakt scrobble (every 60 seconds)
            import time
            if time.time() - self._last_scrobble_time > 60:
                self._scrobble("start")

            # Check for auto-next trigger
            if Config.auto_next_episode():
                self._check_auto_next()

        except Exception as e:
            log(f"Monitor tick error: {e}", level="debug")

    def _scrobble(self, action, progress=None):
        """Send scrobble progress to Trakt."""
        try:
            from resources.lib.trakt import Trakt
            trakt = Trakt()
            if not trakt.is_configured():
                return
            context = self.cache.get("_playback_context")
            if not context:
                return
            
            imdb_id = context.get("content_id") or context.get("imdb_id")
            if not imdb_id:
                return
            media_type = context.get("media_type", "movie")
            
            if progress is None:
                try:
                    pos = self.getTime()
                    dur = self.getTotalTime()
                    if dur > 0:
                        progress = (pos / dur) * 100
                    else:
                        progress = 0.0
                except Exception:
                    progress = 0.0
            
            progress = max(0.0, min(100.0, float(progress)))
            
            trakt.scrobble_action(action, imdb_id, media_type, progress)
            
            import time
            self._last_scrobble_time = time.time()
        except Exception as e:
            log(f"Trakt scrobble helper error: {e}", level="debug")

    def _save_position(self):
        """Save current playback position for resume."""
        if not Config.resume_enabled():
            return

        try:
            if self.isPlaying():
                pos = self.getTime()
                dur = self.getTotalTime()
            else:
                pos = self._last_pos
                dur = self._last_dur

            if not pos or not dur or dur <= 0:
                return

            self._last_pos = pos
            self._last_dur = dur

            context = self.cache.get("_playback_context")
            if not context:
                return

            self.cache.save_resume(
                content_id=context.get("content_id", ""),
                media_type=context.get("media_type", "movie"),
                title=context.get("title", ""),
                poster=context.get("poster", ""),
                imdb_id=context.get("imdb_id", ""),
                season=int(context.get("season") or 0),
                episode=int(context.get("episode") or 0),
                position=pos,
                duration=dur,
            )
        except Exception as e:
            log(f"Save position error: {e}", level="debug")

    def _mark_completed(self):
        """Remove from continue watching when fully watched."""
        try:
            context = self.cache.get("_playback_context")
            if context:
                self.cache.remove_resume(context.get("content_id", ""))
        except Exception:
            pass

    def _check_auto_next(self):
        """Check if we should trigger auto-next episode."""
        if self._auto_next_notified:
            return
        try:
            if not self.isPlaying():
                return
            pos = self.getTime()
            dur = self.getTotalTime()
            if dur <= 0:
                return

            percent = (pos / dur) * 100
            threshold = Config.auto_next_percent()

            if percent >= threshold:
                self._auto_next_notified = True
                context = self.cache.get("_playback_context")
                if context and context.get("media_type") == "series":
                    ep = int(context.get("episode") or 0)
                    if ep > 0:
                        # Show notification about next episode
                        next_ep = ep + 1
                        title = context.get("title", "")
                        ui_note = f"Siguiente: Episodio {next_ep}"
                        xbmcgui.Dialog().notification(
                            "Auto-Next", ui_note,
                            xbmcgui.NOTIFICATION_INFO, 5000
                        )
        except Exception:
            pass

    def _try_next_episode(self):
        """Try to play the next episode after current one ends."""
        if self._auto_next_in_progress:
            return
        self._auto_next_in_progress = True
        try:
            context = self.cache.get("_playback_context")
            if not context or context.get("media_type") != "series":
                return

            imdb_id = context.get("imdb_id", "")
            season = int(context.get("season") or 0)
            episode = int(context.get("episode") or 0)

            if not imdb_id or not season or not episode:
                return

            next_ep = episode + 1
            next_id = f"{imdb_id}:{season}:{next_ep}"

            # Check if next episode exists by looking for streams
            from resources.lib.stremio import StremioClient
            client = StremioClient()
            streams = client.get_streams("series", next_id)

            if streams:
                log(f"Auto-next: playing S{season:02d}E{next_ep:02d}", level="info")

                # Build plugin URL for next episode
                base = f"plugin://{Config.ADDON_ID}"
                title = context.get("title", "").rsplit(" S", 1)[0]
                next_title = f"{title} S{season:02d}E{next_ep:02d}"

                # Ask user with a 10-second countdown
                countdown = 10
                dialog = xbmcgui.DialogProgress()
                dialog.create("Siguiente Episodio",
                              f"Reproduciendo {next_title} en {countdown}s...")

                for i in range(countdown):
                    if dialog.iscanceled():
                        dialog.close()
                        return
                    xbmc.sleep(1000)
                    remaining = countdown - i - 1
                    dialog.update(
                        int(((i + 1) / countdown) * 100),
                        f"Reproduciendo {next_title} en {remaining}s..."
                    )

                dialog.close()

                # Navigate to streams for next episode
                url = (
                    f"{base}?action=streams"
                    f"&imdb_id={next_id}&media_type=series"
                    f"&title={next_title}"
                    f"&series_imdb={imdb_id}"
                    f"&season={season}&episode={next_ep}"
                )
                xbmc.executebuiltin(f"Container.Update({url})")

            else:
                log(f"Auto-next: no streams for S{season:02d}E{next_ep:02d}", level="info")

        except Exception as e:
            log(f"Auto-next error: {e}", level="error")
        finally:
            self._auto_next_in_progress = False

    def _reopen_streams(self):
        """Reopen streams selection dialog after premature stop or cancellation."""
        import time
        if time.time() - getattr(self, "_last_reopen_time", 0) < 3.0:
            return
        self._last_reopen_time = time.time()

        try:
            context = self.cache.get("_playback_context")
            if not context:
                return

            media_type = context.get("media_type", "movie")
            if media_type not in ["movie", "series"]:
                return

            content_id = context.get("content_id", "")
            title = context.get("title", "")
            series_imdb = context.get("imdb_id", "")
            season = context.get("season", "")
            episode = context.get("episode", "")
            poster = context.get("poster", "")

            if not content_id and not title:
                return

            from urllib.parse import quote
            base = f"plugin://{Config.ADDON_ID}"
            url = (
                f"{base}?action=streams"
                f"&imdb_id={content_id}&media_type={media_type}"
                f"&title={quote(title)}"
                f"&series_imdb={series_imdb}"
                f"&season={season}&episode={episode}"
                f"&poster={quote(poster)}"
            )

            log("Reopening streams list after stopped/cancelled playback", level="info")
            def _delayed_open():
                xbmc.sleep(600)
                xbmc.executebuiltin(f"Container.Update({url})")

            import threading
            threading.Thread(target=_delayed_open, daemon=True).start()
        except Exception as e:
            log(f"Reopen streams error: {e}", level="debug")

    def _handle_playback_stall(self, ratio=0.0):
        """Offer recovery options when playback closes prematurely due to timeout or underrun."""
        import time
        if time.time() - getattr(self, "_last_stall_dialog_time", 0) < 5.0:
            return
        self._last_stall_dialog_time = time.time()

        def _stall_dialog():
            import time
            time.sleep(0.6)
            context = self.cache.get("_playback_context")
            if not context:
                return

            percent_str = f" al {int(ratio * 100)}%" if ratio > 0.01 else ""
            options = [
                "🔄 Reanudar reproducción (Misma fuente)",
                "📂 Elegir otra fuente (Buscar streams)",
                "❌ Salir"
            ]
            choice = xbmcgui.Dialog().select(
                f"⚠️ Reproducción interrumpida{percent_str}",
                options
            )
            if choice == 0:
                last_url = self.cache.get("_last_played_url")
                if last_url:
                    log(f"Resuming stalled stream: {last_url[:100]}", level="info")
                    if last_url.startswith("plugin://"):
                        xbmc.executebuiltin(f'PlayMedia("{last_url}")')
                    else:
                        xbmc.Player().play(last_url)
            elif choice == 1:
                self._reopen_streams()

        import threading
        threading.Thread(target=_stall_dialog, daemon=True).start()


class StremioService(xbmc.Monitor):
    """Main service: runs cache cleanup and playback monitor."""

    def __init__(self):
        super().__init__()
        self.cache = CacheDB()
        self.player = PlaybackMonitor(self.cache)
        log("Service v2 started", level="info")

    def _clean_abandoned_torrents(self):
        """Clean leftover torrents from previous sessions if Kodi is not currently playing."""
        if xbmc.Player().isPlaying():
            return
        import urllib.request, json
        # Clean Torrest
        try:
            req = urllib.request.Request("http://127.0.0.1:61235/torrents", headers={"User-Agent": "Kodi"})
            with urllib.request.urlopen(req, timeout=1.5) as r:
                torrents = json.loads(r.read().decode())
                for t in torrents:
                    ih = t.get("info_hash")
                    if ih:
                        del_req = urllib.request.Request(f"http://127.0.0.1:61235/torrents/{ih}?delete=true", method="DELETE")
                        urllib.request.urlopen(del_req, timeout=1.5)
                        log(f"Auto-cleaned abandoned Torrest session: {ih}", level="info")
        except Exception:
            pass

        # Clean Elementum
        try:
            req = urllib.request.Request("http://127.0.0.1:65220/torrents", headers={"User-Agent": "Kodi"})
            with urllib.request.urlopen(req, timeout=1.5) as r:
                data = json.loads(r.read().decode())
                items = data.get("items", [])
                if items:
                    urllib.request.urlopen("http://127.0.0.1:65220/torrents/pause", timeout=1.5)
                    log(f"Auto-paused {len(items)} abandoned Elementum torrents", level="info")
        except Exception:
            pass

    def run(self):
        # Initial cleanup after 5s wait for engines to initialize
        if not self.waitForAbort(5):
            self._clean_abandoned_torrents()

        tick_counter = 0
        while not self.abortRequested():
            if self.waitForAbort(MONITOR_INTERVAL):
                break

            # Playback monitor tick
            try:
                self.player.tick()
            except Exception:
                pass

            # Cache cleanup and torrent watchdog every hour
            tick_counter += 1
            if tick_counter >= (CLEANUP_INTERVAL // MONITOR_INTERVAL):
                tick_counter = 0
                try:
                    self._clean_abandoned_torrents()
                    removed = self.cache.cleanup_expired()
                    if removed > 0:
                        log(f"Cache cleanup: {removed} entries removed", level="info")
                except Exception:
                    pass

        log("Service stopped", level="info")


if __name__ == "__main__":
    try:
        service = StremioService()
        service.run()
    except Exception as e:
        try:
            import xbmc
            xbmc.log(f"[Stremio4Kodi] Service error: {e}", xbmc.LOGERROR)
        except Exception:
            pass
