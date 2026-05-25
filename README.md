# Stremio for Kodi (plugin.video.stremio4kodi)

Stream movies and TV shows using Stremio community addons with full torrent support via Elementum.

## Features

- Browse movie and series catalogs from Stremio addons (Cinemeta, Torrentio, etc.)
- Global search across all configured addons
- Full series navigation: seasons → episodes → streams
- Torrent resolution via Elementum or Quasar
- Quality filtering and seed-based sorting
- Local favorites and watch history
- SQLite catalog caching with configurable TTL
- Parallel addon querying for speed
- Auto-play mode for the best available stream
- Background service for cache cleanup

---

## Installation Guide

### Prerequisites

1. **Kodi 20 (Nexus)** or **Kodi 21 (Omega)** — tested on both
2. **Elementum addon** installed and configured (for torrent playback)
   - Install from: `https://github.com/elgatito/plugin.video.elementum`
3. **CoreELEC / LibreELEC** recommended but works on any Kodi platform

### Step-by-step Installation

```bash
# 1. Download or clone the addon
git clone https://github.com/stremio4kodi/plugin.video.stremio4kodi.git

# 2. Zip the addon folder
cd plugin.video.stremio4kodi/..
zip -r plugin.video.stremio4kodi.zip plugin.video.stremio4kodi/

# 3. Copy the zip to your Kodi device
scp plugin.video.stremio4kodi.zip root@<coreelec-ip>:/storage/

# 4. In Kodi: Settings → Addons → Install from ZIP file
#    Navigate to the zip and install

# 5. Configure the addon: Addons → Video Addons → Stremio for Kodi → Settings
```

### Manual Installation (no zip)

```bash
# Copy directly to the Kodi addons directory
cp -r plugin.video.stremio4kodi ~/.kodi/addons/

# On CoreELEC:
cp -r plugin.video.stremio4kodi /storage/.kodi/addons/

# Restart Kodi
```

### First Configuration

1. Open **Settings** in the addon
2. Set your **Stremio addon URLs** (pipe-separated):
   ```
   https://v3-cinemeta.strem.io|https://torrentio.strem.fun
   ```
3. Select your **torrent engine** (Elementum recommended)
4. Set **preferred quality** and **sort method**
5. Done! Browse Movies or Series from the main menu.

### Finding Stremio Addon URLs

Visit [stremio-addons.net](https://stremio-addons.net/) or the Stremio addon catalog to find community addon URLs. Copy the base URL (before `/manifest.json`).

Popular addons:
| Addon | URL | Purpose |
|-------|-----|---------|
| Cinemeta | `https://v3-cinemeta.strem.io` | Metadata & catalogs |
| Torrentio | `https://torrentio.strem.fun` | Torrent streams |
| The Movie Database | `https://94c8cb9f702d-tmdb-addon.baby-beamup.club` | TMDB catalogs |

---

## Architecture & Module Reference

```
plugin.video.stremio4kodi/
├── addon.xml                  # Kodi addon descriptor
├── default.py                 # Entry point (3 lines)
├── service.py                 # Background cache cleanup service
├── resources/
│   ├── settings.xml           # User-configurable settings
│   ├── media/
│   │   └── icon.png           # Addon icon
│   ├── language/
│   │   ├── resource.language.en_gb/strings.po
│   │   └── resource.language.es_es/strings.po
│   └── lib/
│       ├── __init__.py
│       ├── config.py          # Typed settings access
│       ├── logger.py          # Centralized logging
│       ├── cache.py           # SQLite DB (cache + favorites + history)
│       ├── stremio.py         # Stremio HTTP API client
│       ├── torrent.py         # Stream → playable URL resolver
│       ├── ui.py              # ListItem/dialog builders
│       └── router.py          # URL dispatcher (all navigation logic)
```

### Module Details

#### `config.py` — Settings Access
Typed static methods that read `settings.xml` values. Every other module imports `Config` instead of touching `xbmcaddon.Addon()` directly. This provides a single source of truth and makes testing easier.

#### `logger.py` — Logging
Wraps `xbmc.log()` with the addon prefix and respects the user's log level setting. All modules call `log()` instead of using `print()` or `xbmc.log()` directly.

#### `cache.py` — SQLite Database
Three tables:
- **cache**: Generic key/value store with TTL expiration. Used for catalogs, metadata, stream lists, and manifests.
- **favorites**: User-saved movies and series with poster art.
- **history**: Recently watched items with timestamps.

Uses WAL journal mode for concurrent read/write safety and thread-local connections.

#### `stremio.py` — Stremio Client
Implements the [Stremio Addon Protocol v3](https://github.com/Stremio/stremio-addon-sdk/blob/master/docs/protocol.md):
- `get_manifest()` — Fetch addon capabilities
- `get_catalog()` — List items from a catalog with pagination
- `get_catalogs_for_type()` — Discover all catalogs across addons
- `search()` — Global search with deduplication by IMDb ID
- `get_meta()` — Detailed metadata (videos/episodes for series)
- `get_streams()` — Aggregated, sorted stream list from all addons

Supports parallel querying via `ThreadPoolExecutor` when enabled.

#### `torrent.py` — Stream Resolver
Converts Stremio stream objects into Kodi-playable URLs:
- `magnet:` URIs → `plugin://plugin.video.elementum/play?uri=...`
- HTTP `.torrent` files → same pattern
- Direct HTTP streams → pass through
- `infoHash` fields → constructs magnet with trackers

Also handles quality filtering, seed count extraction, and display label formatting.

#### `ui.py` — UI Builders
Pure helper functions—no state:
- `add_directory_item()` — Build a folder or playable ListItem with art, info tags, context menu
- `end_directory()` — Finalize a directory listing
- `show_notification()`, `show_input()`, `show_select()`, `show_progress()` — Dialog wrappers

#### `router.py` — URL Dispatcher
The brain of the addon. Parses `sys.argv`, extracts the `action` parameter, and dispatches to the right handler. Contains all 16 action handlers:

| Action | Screen |
|--------|--------|
| *(empty)* | Main menu |
| `movies` | Movie catalog list |
| `series` | Series catalog list |
| `catalog` | Items in a catalog |
| `seasons` | Season list |
| `episodes` | Episode list |
| `streams` | Stream selection |
| `play` | Resolve & play |
| `search` | Search dialog |
| `search_results` | Search results |
| `favorites` | Favorites list |
| `toggle_favorite` | Add/remove favorite |
| `history` | Watch history |
| `clear_cache` | Wipe cache |
| `clear_history` | Wipe history |
| `settings` | Open settings |

---

## Navigation Flow

```
Main Menu
├── Movies → Catalog list → Items → [Stream selection] → Play
├── Series → Catalog list → Items → Seasons → Episodes → [Stream selection] → Play
├── Search → [Type selector] → Results → ...
├── Favorites → Items → ...
├── History → Items → ...
└── Settings
```

---

## Torrent Engine Setup

### Elementum (recommended)

1. Install from the Elementum repository
2. Configure: set download path, connection limits
3. The addon will automatically route `magnet:` and `.torrent` links to Elementum

### Quasar (alternative)

1. Install Quasar
2. Change **Torrent engine** to "Quasar" in addon settings

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No catalogs found | Check addon URLs in Settings. Ensure they end without `/` |
| Streams don't play | Verify Elementum is installed and working independently |
| AceStream doesn't play (Mobile/Android) | Change **AceStream Engine** from `Plexus` to `AceStream` or `AceWeb` in the addon settings. |
| "Stream not found" / "No streams found" (CoreELEC / Kodi 19) | 1. Go to settings and select **Clear cache** to wipe corrupt data.<br>2. Older Pythons on Kodi 19 might have SSL issues; make sure your Stremio URLs are correct and accessible.<br>3. Verify Elementum is active. |
| Slow loading | Enable "Parallel addon queries" in settings |
| Stale data | Clear cache from Settings or reduce Cache TTL |
| Debug logging | Set Log Level to "Debug" in settings, check `kodi.log` |

---

## Contributing

Contributions are welcome! Anyone is free to download, modify, and contribute to this project. If you make improvements or distribute this project, please ensure the original author is credited.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 
You are completely free to use, modify, and distribute this software, provided that you include the original copyright notice and credit the author.
