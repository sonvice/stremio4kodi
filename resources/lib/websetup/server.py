# -*- coding: utf-8 -*-
"""Servidor HTTP local efímero para la configuración remota vía móvil en Stremio4Kodi."""

import hmac
import json
import os
import secrets
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

try:
    import xbmc
    import xbmcaddon
    import xbmcgui
    ADDON_ID = 'plugin.video.stremio4kodi'
except ImportError:
    xbmc = None
    xbmcaddon = None
    xbmcgui = None
    ADDON_ID = 'plugin.video.stremio4kodi'

DEFAULT_PORT = 52025
IDLE_TIMEOUT_SECONDS = 15 * 60  # 15 minutos sin peticiones apaga el servidor
MAX_BODY_BYTES = 128 * 1024     # 128 KB de payload máximo
HTML_PAGE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'index.html')


def lan_ip():
    """Detecta la dirección IP local de este dispositivo en la red WiFi/Ethernet."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.255.255.255', 1))
            return s.getsockname()[0]
        finally:
            s.close()
    except OSError:
        return '127.0.0.1'


def _get_setting(key, default=''):
    if xbmcaddon:
        try:
            return xbmcaddon.Addon(ADDON_ID).getSetting(key)
        except Exception:
            return default
    return default


def _set_setting(key, value):
    if xbmcaddon:
        try:
            # En Kodi los booleanos se guardan como "true" o "false"
            if isinstance(value, bool):
                str_val = "true" if value else "false"
            else:
                str_val = str(value)
            xbmcaddon.Addon(ADDON_ID).setSetting(key, str_val)
        except Exception as e:
            if xbmc:
                xbmc.log(f"[Stremio4Kodi] WebSetup: Error guardando setting {key}: {e}", xbmc.LOGWARNING)


class SetupRequestHandler(BaseHTTPRequestHandler):
    """Manejador HTTP para la Web UI móvil de configuración."""

    def log_message(self, format, *args):
        # Silenciar logs ruidosos en stdout; solo loguear en xbmc si es necesario
        if xbmc:
            xbmc.log(f"[Stremio4Kodi] WebSetup HTTP: {format % args}", xbmc.LOGDEBUG)

    def _verify_token(self):
        """Verifica que el parámetro 'k' coincida con el token de sesión en tiempo constante."""
        url_parts = urlsplit(self.path)
        params = parse_qs(url_parts.query)
        provided_token = params.get('k', [''])[0]
        expected_token = getattr(self.server, 'session_token', '')
        if not expected_token or not hmac.compare_digest(provided_token, expected_token):
            self.send_error(403, "Forbidden: Clave de sesion invalida o ausente.")
            return False
        self.server.last_activity = time.time()
        return True

    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self._verify_token():
            return

        url_parts = urlsplit(self.path)
        path = url_parts.path.rstrip('/')

        if path == '' or path == '/index.html':
            # Servir la Web UI móvil
            if os.path.exists(HTML_PAGE_PATH):
                with open(HTML_PAGE_PATH, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(content)))
                self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404, "Web UI index.html not found.")
            return

        if path == '/api/ping':
            self._send_json({"ok": True, "status": "online", "time": time.time()})
            return

        if path == '/api/config':
            # Exportar configuración actual de Kodi al móvil
            config_data = {
                # Motores & Prioridades
                "torrent_engine": _get_setting("torrent_engine", "TorrServer"),
                "torrserver_host": _get_setting("torrserver_host", "127.0.0.1"),
                "torrserver_port": _get_setting("torrserver_port", "8090"),
                "torrserver_auth": _get_setting("torrserver_auth", "false") == "true",
                "torrserver_user": _get_setting("torrserver_user", ""),
                "torrserver_pass": _get_setting("torrserver_pass", ""),
                "torrent_sort": _get_setting("torrent_sort", "Seeds"),
                "torrent_quality": _get_setting("torrent_quality", "1080p"),
                "torrent_autoplay": _get_setting("torrent_autoplay", "false") == "true",
                "torrent_preflight_check": _get_setting("torrent_preflight_check", "true") == "true",

                # Debrid
                "rd_priority": _get_setting("rd_priority", "true") == "true",
                "strict_debrid": _get_setting("strict_debrid", "false") == "true",
                "rd_enabled": _get_setting("rd_enabled", "false") == "true",
                "rd_apikey": _get_setting("rd_apikey", ""),
                "alldebrid_enabled": _get_setting("alldebrid_enabled", "false") == "true",
                "alldebrid_apikey": _get_setting("alldebrid_apikey", ""),
                "premiumize_enabled": _get_setting("premiumize_enabled", "false") == "true",
                "premiumize_apikey": _get_setting("premiumize_apikey", ""),
                "torbox_enabled": _get_setting("torbox_enabled", "false") == "true",
                "torbox_apikey": _get_setting("torbox_apikey", ""),
                "debridlink_enabled": _get_setting("debridlink_enabled", "false") == "true",
                "debridlink_apikey": _get_setting("debridlink_apikey", ""),

                # Stremio & Comet
                "comet_custom_manifest": _get_setting("comet_custom_manifest", ""),
                "stremio_addons": _get_setting("stremio_addons", ""),
                "streaming_catalogs_enabled": _get_setting("streaming_catalogs_enabled", "true") == "true",

                # Torznab (Jackett / Prowlarr)
                "torznab_enabled": _get_setting("torznab_enabled", "false") == "true",
                "torznab_url": _get_setting("torznab_url", ""),
                "torznab_apikey": _get_setting("torznab_apikey", ""),

                # Idioma & Preferencias
                "language": _get_setting("language", "es"),
                "spanish_boost": _get_setting("spanish_boost", "true") == "true",
                "spanish_filter_mode": _get_setting("spanish_filter_mode", "boost"),
                "spanish_variant": _get_setting("spanish_variant", "all"),
            }
            self._send_json({"ok": True, "config": config_data})
            return

        self.send_error(404, "Endpoint no encontrado.")

    def do_POST(self):
        if not self._verify_token():
            return

        url_parts = urlsplit(self.path)
        path = url_parts.path.rstrip('/')

        if path == '/api/save':
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length <= 0 or content_length > MAX_BODY_BYTES:
                self.send_error(400, "Payload invalido o demasiado grande.")
                return

            body = self.rfile.read(content_length)
            try:
                payload = json.loads(body.decode('utf-8'))
            except Exception as e:
                self.send_error(400, f"JSON malformado: {e}")
                return

            settings = payload.get("settings", {})
            saved_count = 0

            # Guardar cada ajuste recibido en Kodi
            for key, val in settings.items():
                _set_setting(key, val)
                saved_count += 1

            self.server.is_saved = True
            if hasattr(self.server, 'wrapper'):
                self.server.wrapper.is_saved = True
            self.server.last_saved_time = time.time()

            if xbmc and xbmcgui:
                try:
                    dialog = xbmcgui.Dialog()
                    dialog.notification(
                        "Stremio4Kodi",
                        "Ajustes recibidos y guardados desde el movil",
                        xbmcgui.NOTIFICATION_INFO,
                        4000
                    )
                except Exception:
                    pass

            self._send_json({
                "ok": True,
                "message": f"Se han guardado correctamente {saved_count} ajustes en Kodi.",
                "saved_count": saved_count
            })
            return

        self.send_error(404, "Endpoint no encontrado.")


class SetupServer:
    """Gestiona el ciclo de vida del servidor HTTP efímero."""

    def __init__(self, port=DEFAULT_PORT):
        self.host = lan_ip()
        self.port = port
        self.session_token = secrets.token_urlsafe(16)
        self.httpd = None
        self.thread = None
        self.is_saved = False
        self.is_closed = False
        self.last_activity = time.time()

    def get_url(self):
        return f"http://{self.host}:{self.port}/?k={self.session_token}"

    def start(self):
        """Inicia el servidor en un hilo secundario daemon."""
        # Si el puerto está ocupado, buscar puerto disponible
        for attempt_port in [self.port, self.port + 1, self.port + 2, 0]:
            try:
                self.httpd = ThreadingHTTPServer((self.host, attempt_port), SetupRequestHandler)
                self.port = self.httpd.server_address[1]
                break
            except OSError:
                continue

        if not self.httpd:
            raise OSError(f"No se pudo enlazar el servidor web en {self.host}")

        self.httpd.session_token = self.session_token
        self.httpd.last_activity = self.last_activity
        self.httpd.is_saved = False
        self.httpd.wrapper = self

        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        return self

    def _run(self):
        if xbmc:
            xbmc.log(f"[Stremio4Kodi] WebSetup activo en {self.get_url()}", xbmc.LOGINFO)
        try:
            self.httpd.serve_forever(poll_interval=0.2)
        except Exception:
            pass

    def stop(self):
        """Detiene y libera el servidor de forma instantánea y segura (sin esperas ni cuelgues)."""
        if self.is_closed:
            return
        self.is_closed = True
        httpd = self.httpd
        if httpd:
            try:
                # shutdown() despierta inmediatamente a serve_forever y sale al instante
                httpd.shutdown()
            except Exception:
                pass
            try:
                httpd.server_close()
            except Exception:
                pass
            self.httpd = None
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=0.3)
