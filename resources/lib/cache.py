# -*- coding: utf-8 -*-
"""
CacheDB — SQLite cache + favorites + history + resume positions.
v2: Added resume_positions table for Continue Watching.
"""
import json
import sqlite3
import time
import threading
from resources.lib.config import Config
from resources.lib.logger import log

_local = threading.local()


class CacheDB:
    def __init__(self):
        self.db_path = Config.db_path()
        self._ensure_tables()

    def _conn(self):
        if not hasattr(_local, "conn") or _local.conn is None:
            _local.conn = sqlite3.connect(self.db_path, timeout=10)
            _local.conn.row_factory = sqlite3.Row
            _local.conn.execute("PRAGMA journal_mode=WAL")
            _local.conn.execute("PRAGMA synchronous=NORMAL")
        return _local.conn

    def _ensure_tables(self):
        self._conn().executescript("""
            CREATE TABLE IF NOT EXISTS cache (
                key     TEXT PRIMARY KEY,
                value   TEXT NOT NULL,
                expires REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS favorites (
                imdb_id    TEXT PRIMARY KEY,
                media_type TEXT NOT NULL,
                title      TEXT NOT NULL,
                year       TEXT,
                poster     TEXT,
                added_at   REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS history (
                imdb_id    TEXT PRIMARY KEY,
                media_type TEXT NOT NULL,
                title      TEXT NOT NULL,
                year       TEXT,
                poster     TEXT,
                extra      TEXT,
                watched_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS resume (
                content_id  TEXT PRIMARY KEY,
                media_type  TEXT NOT NULL,
                title       TEXT NOT NULL,
                poster      TEXT,
                imdb_id     TEXT,
                season      INTEGER,
                episode     INTEGER,
                position    REAL NOT NULL,
                duration    REAL NOT NULL,
                percent     REAL NOT NULL,
                updated_at  REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache(expires);
            CREATE INDEX IF NOT EXISTS idx_history_watched ON history(watched_at);
            CREATE INDEX IF NOT EXISTS idx_resume_updated ON resume(updated_at);
            DELETE FROM cache WHERE value = '{}' OR value = '[]' OR value LIKE '%"results": []%' OR value LIKE '%"metas": []%';
        """)
        self._conn().commit()

    # ── Generic cache ──────────────────────────────────────
    def get(self, key):
        try:
            row = self._conn().execute(
                "SELECT value, expires FROM cache WHERE key = ?", (key,)
            ).fetchone()
            if row and row["expires"] > time.time():
                val = json.loads(row["value"])
                if not val or val == {} or val == [] or (isinstance(val, dict) and val.get("results") == []) or (isinstance(val, dict) and val.get("metas") == []):
                    self._conn().execute("DELETE FROM cache WHERE key = ?", (key,))
                    self._conn().commit()
                    return None
                return val
            if row:
                self._conn().execute("DELETE FROM cache WHERE key = ?", (key,))
                self._conn().commit()
        except Exception as e:
            log(f"Cache get error [{key}]: {e}", level="error")
        return None

    def set(self, key, value, ttl=None):
        if not value or value == {} or value == [] or (isinstance(value, dict) and value.get("results") == []) or (isinstance(value, dict) and value.get("metas") == []):
            return
        if ttl is None:
            ttl = Config.cache_ttl_seconds()
        try:
            self._conn().execute(
                "INSERT OR REPLACE INTO cache (key, value, expires) VALUES (?, ?, ?)",
                (key, json.dumps(value, ensure_ascii=False), time.time() + ttl),
            )
            self._conn().commit()
        except Exception as e:
            log(f"Cache set error [{key}]: {e}", level="error")

    def delete(self, key):
        try:
            self._conn().execute("DELETE FROM cache WHERE key = ?", (key,))
            self._conn().commit()
        except Exception:
            pass

    def clear_all(self):
        try:
            self._conn().execute("DELETE FROM cache")
            self._conn().commit()
        except Exception as e:
            log(f"Cache clear error: {e}", level="error")

    def cleanup_expired(self):
        try:
            cur = self._conn().execute("DELETE FROM cache WHERE expires <= ?", (time.time(),))
            self._conn().commit()
            return cur.rowcount
        except Exception:
            return 0

    # ── Favorites ──────────────────────────────────────────
    def add_favorite(self, imdb_id, media_type, title, year="", poster=""):
        try:
            self._conn().execute(
                """INSERT OR REPLACE INTO favorites
                   (imdb_id, media_type, title, year, poster, added_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (imdb_id, media_type, title, year, poster, time.time()),
            )
            self._conn().commit()
        except Exception as e:
            log(f"Fav add error: {e}", level="error")

    def remove_favorite(self, imdb_id):
        try:
            self._conn().execute("DELETE FROM favorites WHERE imdb_id = ?", (imdb_id,))
            self._conn().commit()
        except Exception:
            pass

    def is_favorite(self, imdb_id):
        row = self._conn().execute(
            "SELECT 1 FROM favorites WHERE imdb_id = ?", (imdb_id,)
        ).fetchone()
        return row is not None

    def get_favorites(self, media_type=None):
        if media_type:
            rows = self._conn().execute(
                "SELECT * FROM favorites WHERE media_type=? ORDER BY added_at DESC",
                (media_type,),
            ).fetchall()
        else:
            rows = self._conn().execute(
                "SELECT * FROM favorites ORDER BY added_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    # ── History ────────────────────────────────────────────
    def add_history(self, imdb_id, media_type, title, year="", poster="", extra=None):
        try:
            self._conn().execute(
                """INSERT OR REPLACE INTO history
                   (imdb_id, media_type, title, year, poster, extra, watched_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (imdb_id, media_type, title, year, poster,
                 json.dumps(extra) if extra else None, time.time()),
            )
            self._conn().commit()
        except Exception as e:
            log(f"History error: {e}", level="error")

    def get_history(self, limit=50):
        rows = self._conn().execute(
            "SELECT * FROM history ORDER BY watched_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def clear_history(self):
        self._conn().execute("DELETE FROM history")
        self._conn().commit()

    # ── Resume / Continue Watching ─────────────────────────
    def save_resume(self, content_id, media_type, title, poster, imdb_id,
                    season, episode, position, duration):
        """Save playback position for resume."""
        if duration <= 0:
            return
        percent = (position / duration) * 100
        # If watched > 95%, remove from continue watching
        if percent > 95:
            self.remove_resume(content_id)
            return
        # Only save if > 2% (avoid accidental saves)
        if percent < 2:
            return
        try:
            self._conn().execute(
                """INSERT OR REPLACE INTO resume
                   (content_id, media_type, title, poster, imdb_id,
                    season, episode, position, duration, percent, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (content_id, media_type, title, poster, imdb_id,
                 season, episode, position, duration, percent, time.time()),
            )
            self._conn().commit()
        except Exception as e:
            log(f"Resume save error: {e}", level="error")

    def get_resume(self, content_id):
        """Get resume position for a content_id."""
        try:
            row = self._conn().execute(
                "SELECT * FROM resume WHERE content_id = ?", (content_id,)
            ).fetchone()
            return dict(row) if row else None
        except Exception:
            return None

    def get_continue_watching(self, limit=20):
        """Get all items with resume positions, newest first."""
        rows = self._conn().execute(
            "SELECT * FROM resume WHERE percent < 95 ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def remove_resume(self, content_id):
        try:
            self._conn().execute("DELETE FROM resume WHERE content_id = ?", (content_id,))
            self._conn().commit()
        except Exception:
            pass

    def clear_resume(self):
        self._conn().execute("DELETE FROM resume")
        self._conn().commit()
