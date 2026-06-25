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

    def onPlayBackStarted(self):
        """Called when playback starts."""
        self._playing = True
        self._subs_searched = False
        log("Playback started", level="info")
        self._scrobble("start", 0.0)

    def onPlayBackStopped(self):
        """Called when user stops playback."""
        self._save_position()
        self._playing = False
        log("Playback stopped", level="info")
        self._scrobble("stop")

    def onPlayBackEnded(self):
        """Called when playback reaches the end."""
        self._playing = False
        self._mark_completed()
        log("Playback ended", level="info")
        self._scrobble("stop", 100.0)

        # Auto-next episode
        if Config.auto_next_episode():
            self._try_next_episode()

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
        if not self.isPlaying():
            return

        try:
            pos = self.getTime()
            dur = self.getTotalTime()
            if dur <= 0:
                return

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


class StremioService(xbmc.Monitor):
    """Main service: runs cache cleanup and playback monitor."""

    def __init__(self):
        super().__init__()
        self.cache = CacheDB()
        self.player = PlaybackMonitor(self.cache)
        log("Service v2 started", level="info")

    def run(self):
        tick_counter = 0
        while not self.abortRequested():
            if self.waitForAbort(MONITOR_INTERVAL):
                break

            # Playback monitor tick
            try:
                self.player.tick()
            except Exception:
                pass

            # Cache cleanup every hour
            tick_counter += 1
            if tick_counter >= (CLEANUP_INTERVAL // MONITOR_INTERVAL):
                tick_counter = 0
                try:
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
