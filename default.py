# -*- coding: utf-8 -*-
"""
Stremio for Kodi — Entry Point
Parses the plugin:// URL and dispatches to the appropriate handler.
"""
import sys
import traceback

try:
    from resources.lib.router import Router
    router = Router()
    router.dispatch(sys.argv)
except Exception as e:
    # Show the EXACT error on screen so user can report it
    error_msg = str(e)
    tb = traceback.format_exc()
    try:
        import xbmc
        xbmc.log(f"[Stremio4Kodi] FATAL: {error_msg}", xbmc.LOGERROR)
        xbmc.log(f"[Stremio4Kodi] {tb}", xbmc.LOGERROR)
    except Exception:
        pass
    try:
        import xbmcgui
        # Show a dialog with the actual error so user can screenshot it
        xbmcgui.Dialog().ok(
            "Stremio4Kodi Error",
            f"Error: {error_msg[:200]}",
        )
    except Exception:
        pass
