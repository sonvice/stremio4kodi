# -*- coding: utf-8 -*-
"""
Dependencies & Engine Manager — Stremio for Kodi.
Handles automatic detection, user confirmation dialogs, and seamless
installation of playback engines (Elementum & Horus for AceStream).
"""
import io
import json
import os
import platform
import socket
import struct
import sys
import urllib.request
import zipfile

import xbmc
import xbmcgui
import xbmcvfs

from resources.lib.cache import CacheDB
from resources.lib.config import Config
from resources.lib.logger import log

ELEMENTUM_VERSION = "0.1.117"
HORUS_URL = "https://cdn.jsdelivr.net/gh/logon84/script.module.horus@main/script.module.horus.zip"
HORUS_FALLBACK = "https://raw.githubusercontent.com/logon84/script.module.horus/main/script.module.horus.zip"
ELEMENTUM_REPO_URL = "https://github.com/ElementumOrg/repository.elementumorg/releases/download/v0.0.8/repository.elementumorg-0.0.8.zip"
ELEMENTUM_REPO_FALLBACK = "https://cdn.jsdelivr.net/gh/ElementumOrg/repository.elementumorg@master/repository.elementumorg-0.0.8.zip"


def is_elementum_installed():
    """Check if plugin.video.elementum is installed in Kodi."""
    try:
        return bool(xbmc.getCondVisibility("System.HasAddon(plugin.video.elementum)"))
    except Exception:
        return False


def is_horus_installed():
    """Check if script.module.horus is installed in Kodi."""
    try:
        return bool(xbmc.getCondVisibility("System.HasAddon(script.module.horus)"))
    except Exception:
        return False


def ensure_kodi_settings_for_elementum():
    """
    Enables Kodi's internal JSON-RPC TCP server (port 9090) and remote control.
    Elementum requires this service to communicate with Kodi.
    """
    try:
        # Start Kodi's built-in JSON-RPC server directly
        xbmc.startServer(xbmc.SERVER_JSONRPCSERVER, True)
    except Exception as e:
        log(f"Notice startServer JSON-RPC: {e}", level="debug")

    try:
        # Enable remote control (port 9090 for Elementum) and disable HTTP webserver
        for setting, val in [
            ("services.esenabled", True),
            ("services.esallinterfaces", True),
            ("services.webserver", False),
            ("services.webserverauthentication", False),
        ]:
            xbmc.executeJSONRPC(json.dumps({
                "jsonrpc": "2.0",
                "method": "Settings.SetSettingValue",
                "params": {"setting": setting, "value": val},
                "id": 1
            }))
    except Exception as e:
        log(f"Notice setting JSON-RPC values: {e}", level="debug")


def check_jsonrpc_port():
    """Checks if Kodi's JSON-RPC server is reachable on port 9090."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1.5)
        res = s.connect_ex(("127.0.0.1", 9090))
        s.close()
        return res == 0
    except Exception:
        return False


def get_system_arch():
    """
    Detects Kodi platform and bitness to pick the matching Elementum binary package.
    Important: checks process pointer size to distinguish 32-bit vs 64-bit Kodi
    on Android and Windows.
    """
    is_64 = (struct.calcsize("P") * 8 == 64)

    # 1. Android (Mobiles, Tablets, Android TV, Fire TV)
    if xbmc.getCondVisibility("System.Platform.Android"):
        m = platform.machine().lower()
        if "x86" in m or "i686" in m:
            return "android_x64" if is_64 else "android_x86"
        # On ARM, use the exact bitness of the Kodi process
        return "android_arm64" if is_64 else "android_arm"

    # 2. Windows
    if xbmc.getCondVisibility("System.Platform.Windows"):
        return "windows_x64" if is_64 else "windows_x86"

    # 3. macOS / Darwin
    if xbmc.getCondVisibility("System.Platform.OSX"):
        m = platform.machine().lower()
        if "arm" in m or "aarch" in m:
            return "darwin_arm64"
        return "darwin_x64"

    # 4. Raspberry Pi
    if xbmc.getCondVisibility("System.Platform.Linux.RaspberryPi"):
        m = platform.machine().lower()
        if "aarch64" in m or "arm64" in m or is_64:
            return "linux_arm64"
        return "linux_armv7"

    # 5. Linux / CoreELEC / LibreELEC
    if xbmc.getCondVisibility("System.Platform.Linux"):
        m = platform.machine().lower()
        if "aarch64" in m or "arm64" in m:
            return "linux_arm64"
        elif "armv7" in m or ("arm" in m and not is_64):
            return "linux_armv7"
        elif "x86_64" in m or "amd64" in m:
            return "linux_x64" if is_64 else "linux_x86"
        elif "x86" in m or "i686" in m:
            return "linux_x86"
        return "linux_arm64" if is_64 else "linux_x64"

    return "android_arm64" if is_64 else "android_arm"


def download_and_extract(url, target_dir, dialog_title="Descargando...", fallback_urls=None):
    """
    Downloads a zip file with progress reporting and extracts it into target_dir.
    Restores POSIX execution permissions (0755) on binaries and shared libraries.
    """
    dp = xbmcgui.DialogProgress()
    dp.create("Stremio for Kodi", dialog_title)

    urls = [url] + (fallback_urls or [])
    last_error = ""

    for attempt_url in urls:
        if dp.iscanceled():
            dp.close()
            return False

        try:
            dp.update(5, f"Conectando con el servidor...\n{attempt_url[:55]}...")
            req = urllib.request.Request(
                attempt_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Kodi/21"}
            )
            with urllib.request.urlopen(req, timeout=35) as resp:
                total_len = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                chunks = []
                chunk_size = 65536

                while True:
                    if dp.iscanceled():
                        dp.close()
                        return False

                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    downloaded += len(chunk)

                    if total_len > 0:
                        pct = min(92, int(downloaded * 88 / total_len) + 5)
                        mb_down = downloaded / (1024 * 1024)
                        mb_total = total_len / (1024 * 1024)
                        dp.update(pct, f"{dialog_title}\nDescargando: {mb_down:.1f} MB de {mb_total:.1f} MB ({pct}%)")
                    else:
                        mb_down = downloaded / (1024 * 1024)
                        dp.update(45, f"{dialog_title}\nDescargando: {mb_down:.1f} MB...")

                data = b"".join(chunks)

            dp.update(95, "Extrayendo archivos y configurando permisos...")
            z = zipfile.ZipFile(io.BytesIO(data))
            for info in z.infolist():
                if info.filename.startswith("/") or ".." in info.filename:
                    continue
                extracted_path = z.extract(info, target_dir)

                # Ensure execution bit (0o755) is preserved for binaries and libraries
                perm = (info.external_attr >> 16) & 0o777
                if perm:
                    try:
                        os.chmod(extracted_path, perm)
                    except Exception:
                        pass
                elif "/bin/" in info.filename or info.filename.endswith((".so", ".sh", "elementum")):
                    try:
                        os.chmod(extracted_path, 0o755)
                    except Exception:
                        pass

            dp.update(100, "¡Instalación completada!")
            xbmc.sleep(400)
            dp.close()
            return True

        except Exception as e:
            last_error = str(e)
            log(f"Download/extract error from {attempt_url}: {e}", level="warning")

    dp.close()
    xbmcgui.Dialog().ok(
        "Error de Descarga",
        f"No se pudo descargar el complemento.\n\nError: {last_error[:160]}"
    )
    return False


def activate_addon(addon_id):
    """Instructs Kodi to scan local add-ons and enable the target add-on."""
    xbmc.executebuiltin("UpdateLocalAddons")
    xbmc.sleep(800)
    try:
        xbmc.executeJSONRPC(json.dumps({
            "jsonrpc": "2.0",
            "method": "Addons.SetAddonEnabled",
            "params": {"addonid": addon_id, "enabled": True},
            "id": 1
        }))
    except Exception as e:
        log(f"Error enabling addon {addon_id}: {e}", level="debug")
    xbmc.executebuiltin("UpdateAddonRepos")


def install_elementum():
    """
    Installs Elementum matching the system architecture, configures Kodi remote control,
    and installs the ElementumOrg repository for automatic updates.
    """
    addons_path = xbmcvfs.translatePath("special://home/addons/")
    arch = get_system_arch()
    log(f"Installing Elementum v{ELEMENTUM_VERSION} for architecture: {arch}", level="info")

    # 1. Enable Kodi JSON-RPC server and remote control permissions
    ensure_kodi_settings_for_elementum()

    # 2. Clean up any stale lockfile from previous failed daemon runs
    try:
        profile_dir = xbmcvfs.translatePath("special://profile/addon_data/plugin.video.elementum/")
        if profile_dir:
            lockfile = os.path.join(profile_dir, ".lockfile")
            if os.path.exists(lockfile):
                os.remove(lockfile)
    except Exception:
        pass

    url = (
        f"https://github.com/elgatito/plugin.video.elementum/releases/download/"
        f"v{ELEMENTUM_VERSION}/plugin.video.elementum-{ELEMENTUM_VERSION}.{arch}.zip"
    )
    fallback = [
        f"https://elementum.surge.sh/plugin.video.elementum-{ELEMENTUM_VERSION}.{arch}.zip",
        f"https://github.com/elgatito/plugin.video.elementum/releases/download/v{ELEMENTUM_VERSION}/plugin.video.elementum-{ELEMENTUM_VERSION}.zip"
    ]

    ok = download_and_extract(
        url,
        addons_path,
        dialog_title=f"Instalando Elementum ({arch})...",
        fallback_urls=fallback
    )
    if not ok:
        return False

    # Also install repository.elementumorg so user gets future updates automatically
    try:
        download_and_extract(
            ELEMENTUM_REPO_URL,
            addons_path,
            dialog_title="Instalando repositorio de Elementum...",
            fallback_urls=[ELEMENTUM_REPO_FALLBACK]
        )
        activate_addon("repository.elementumorg")
    except Exception as e:
        log(f"ElementumOrg repo install notice: {e}", level="debug")

    activate_addon("plugin.video.elementum")

    # Ensure remote control is active
    ensure_kodi_settings_for_elementum()

    # Check if JSON-RPC port is open
    if not check_jsonrpc_port():
        # Inform the user how to enable control in Kodi settings if Android blocked it
        xbmcgui.Dialog().ok(
            "Ajuste Necesario en Kodi",
            "Elementum se ha instalado, pero necesita que actives el control remoto:\n\n"
            "Ve a: Ajustes (Rueda) > Servicios > Control\n"
            "Y activa:\n"
            "• 'Permitir control remoto desde aplicaciones en este sistema'\n"
            "• 'Permitir control remoto desde aplicaciones en otros sistemas'"
        )

    xbmcgui.Dialog().notification(
        "Stremio for Kodi",
        "✅ Elementum instalado correctamente",
        xbmcgui.NOTIFICATION_INFO,
        4000
    )
    return True


def install_horus():
    """Installs Horus (script.module.horus) for AceStream playback."""
    addons_path = xbmcvfs.translatePath("special://home/addons/")
    log("Installing Horus for AceStream playback", level="info")

    ok = download_and_extract(
        HORUS_URL,
        addons_path,
        dialog_title="Instalando Horus (AceStream)...",
        fallback_urls=[HORUS_FALLBACK]
    )
    if not ok:
        return False

    activate_addon("script.module.horus")

    xbmcgui.Dialog().notification(
        "Stremio for Kodi",
        "✅ Horus instalado correctamente",
        xbmcgui.NOTIFICATION_INFO,
        4000
    )

    if xbmc.getCondVisibility("System.Platform.Android"):
        xbmcgui.Dialog().ok(
            "AceStream en Android",
            "Horus se ha instalado con éxito en Kodi.\n\n"
            "📱 Requisito en móviles Android / TV Box:\n"
            "Para reproducir emisiones deportivas en directo, asegúrate de tener instalada en tu móvil la app gratuita 'AceStream Engine' (o AceStream Media)."
        )
    return True


def prompt_install_elementum():
    """Shows a dialog asking the user if they want to install Elementum."""
    dialog = xbmcgui.Dialog()
    confirm = dialog.yesno(
        "Motor Torrent Requerido",
        "Para reproducir películas y series por Torrent se necesita el motor Elementum.\n\n"
        "¿Deseas descargarlo e instalarlo automáticamente ahora?",
        yeslabel="Instalar Elementum",
        nolabel="Cancelar"
    )
    if confirm:
        return install_elementum()
    return False


def prompt_install_horus():
    """Shows a dialog asking the user if they want to install Horus."""
    dialog = xbmcgui.Dialog()
    confirm = dialog.yesno(
        "Motor AceStream Requerido",
        "Para reproducir emisiones de AceStream (fútbol y directos) se necesita el complemento Horus.\n\n"
        "¿Deseas descargarlo e instalarlo automáticamente ahora?",
        yeslabel="Instalar Horus",
        nolabel="Cancelar"
    )
    if confirm:
        return install_horus()
    return False


def check_engines_prompt():
    """
    Called on startup or when opening the main menu.
    Detects if required engines are missing on a fresh device (e.g. mobile)
    and prompts the user gracefully once.
    """
    has_elementum = is_elementum_installed()
    has_horus = is_horus_installed()

    cache = CacheDB()
    if cache.get("_dep_engines_prompted"):
        return

    # If both engines are already present, mark as prompted and return
    if has_elementum and has_horus:
        cache.set("_dep_engines_prompted", True, ttl=86400 * 30)
        return

    # If TorrServer or Real-Debrid is already configured and elementum is missing, user might not need Elementum
    rd_configured = bool(Config.rd_token())
    torr_configured = (Config.torrent_engine() == "TorrServer")

    if has_elementum and (torr_configured or rd_configured):
        cache.set("_dep_engines_prompted", True, ttl=86400 * 30)
        return

    opts = []
    actions = []

    if not has_elementum and not has_horus:
        opts.append("🚀 Instalar ambos (Elementum + Horus) [Recomendado]")
        actions.append("both")
    if not has_elementum:
        opts.append("🎬 Instalar Elementum (Para Películas y Series)")
        actions.append("elementum")
    if not has_horus:
        opts.append("⚽ Instalar Horus (Para AceStream / TV en Directo)")
        actions.append("horus")
    opts.append("⏭️ No instalar ahora (Configurar más tarde)")
    actions.append("skip")

    dialog = xbmcgui.Dialog()
    idx = dialog.select("Stremio for Kodi — Motores de Reproducción", opts)

    cache.set("_dep_engines_prompted", True, ttl=86400 * 30)

    if idx < 0 or actions[idx] == "skip":
        return

    chosen = actions[idx]
    if chosen == "both":
        install_elementum()
        install_horus()
    elif chosen == "elementum":
        install_elementum()
    elif chosen == "horus":
        install_horus()
