# -*- coding: utf-8 -*-
"""
VPNManager — Intelligent VPN bypass for P2P torrent streaming on CoreELEC / Linux.
- Detects active VPN connection via connmanctl.
- Temporarily disconnects VPN when launching Elementum/P2P torrents to unlock open ports, UPnP, and maximum direct ISP fiber speeds.
- Automatically reconnects VPN when torrent playback ends or when accessing AceStream / Live TV.
"""
import os
import subprocess
from resources.lib.logger import log
from resources.lib.cache import CacheDB
from resources.lib.config import Config

CONNMANCTL_BIN = "/usr/bin/connmanctl"


class VPNManager:
    @staticmethod
    def is_available():
        return os.path.exists(CONNMANCTL_BIN)

    @classmethod
    def get_active_vpn(cls):
        """Returns the service ID of currently connected VPN or None."""
        if not cls.is_available():
            return None
        try:
            out = subprocess.check_output([CONNMANCTL_BIN, "services"], timeout=3).decode("utf-8")
            for line in out.splitlines():
                if "* R" in line and "vpn_" in line:
                    parts = line.strip().split()
                    return parts[-1]
        except Exception as e:
            log(f"Error checking active VPN: {e}", level="debug")
        return None

    @classmethod
    def disconnect_for_p2p(cls):
        """Disconnects VPN before launching P2P stream if enabled."""
        if not Config.vpn_torrent_bypass():
            return
        if not cls.is_available():
            return

        active_vpn = cls.get_active_vpn()
        if not active_vpn:
            return

        cache = CacheDB()
        cache.set("_paused_vpn_service", active_vpn, ttl=86400)
        log(f"Pausing VPN {active_vpn} for P2P streaming...", level="info")
        try:
            subprocess.run([CONNMANCTL_BIN, "disconnect", active_vpn], timeout=5)
            import xbmcgui
            xbmcgui.Dialog().notification(
                "Stremio4Kodi ⚡",
                "VPN pausada: Máxima velocidad P2P fibra directa",
                xbmcgui.NOTIFICATION_INFO,
                3000
            )
        except Exception as e:
            log(f"Failed to disconnect VPN: {e}", level="warning")

    @classmethod
    def restore_vpn(cls):
        """Restores VPN if it was previously disconnected for P2P."""
        if not cls.is_available():
            return

        cache = CacheDB()
        paused_vpn = cache.get("_paused_vpn_service")
        if not paused_vpn:
            return

        cache.delete("_paused_vpn_service")
        log(f"Restoring VPN {paused_vpn}...", level="info")
        try:
            subprocess.run([CONNMANCTL_BIN, "connect", paused_vpn], timeout=8)
            import xbmcgui
            xbmcgui.Dialog().notification(
                "Stremio4Kodi 🛡️",
                "VPN reconectada: Protección activa",
                xbmcgui.NOTIFICATION_INFO,
                3000
            )
        except Exception as e:
            log(f"Failed to reconnect VPN: {e}", level="warning")

    @classmethod
    def ensure_vpn_for_acestream(cls):
        """Ensures VPN is active for AceStream to bypass ISP blocks."""
        if not cls.is_available():
            return

        cache = CacheDB()
        paused_vpn = cache.get("_paused_vpn_service")
        if paused_vpn:
            cls.restore_vpn()
            return

        # If no VPN is connected, check if any VPN service is available in ConnMan
        if not cls.get_active_vpn():
            try:
                out = subprocess.check_output([CONNMANCTL_BIN, "services"], timeout=3).decode("utf-8")
                for line in out.splitlines():
                    if "vpn_" in line:
                        service = line.strip().split()[-1]
                        log(f"Connecting VPN {service} for AceStream...", level="info")
                        subprocess.run([CONNMANCTL_BIN, "connect", service], timeout=8)
                        break
            except Exception as e:
                log(f"Error ensuring VPN for AceStream: {e}", level="debug")
