# -*- coding: utf-8 -*-
"""
Logger — Centralized logging.
"""
import xbmc
import xbmcaddon

ADDON_ID = xbmcaddon.Addon().getAddonInfo("id")

LEVELS = {
    "debug": xbmc.LOGDEBUG,
    "info": xbmc.LOGINFO,
    "warning": xbmc.LOGWARNING,
    "error": xbmc.LOGERROR,
}


def log(message, level="debug"):
    """Log a message with the addon prefix."""
    try:
        setting = (xbmcaddon.Addon().getSetting("log_level") or "Info").lower()
    except Exception:
        setting = "info"

    if setting == "info" and level == "debug":
        return

    xbmc_level = LEVELS.get(level, xbmc.LOGDEBUG)
    xbmc.log(f"[{ADDON_ID}] [{level.upper()}] {message}", xbmc_level)
