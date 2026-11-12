# -*- coding: utf-8 -*-
"""Diálogo en pantalla para el emparejamiento y configuración móvil vía código QR."""

import os
import time

try:
    import xbmc
    import xbmcaddon
    import xbmcgui
    import xbmcvfs
except ImportError:
    xbmc = None
    xbmcaddon = None
    xbmcgui = None
    xbmcvfs = None

from .qr import generate_qr_png
from .server import SetupServer, lan_ip

ADDON_ID = 'plugin.video.stremio4kodi'


def _get_addon_path():
    if xbmcaddon:
        try:
            return xbmcaddon.Addon(ADDON_ID).getAddonInfo('path')
        except Exception:
            pass
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _get_temp_qr_path():
    if xbmcvfs:
        try:
            temp_dir = xbmcvfs.translatePath('special://temp/')
            return os.path.join(temp_dir, 'stremio4kodi_qr.png')
        except Exception:
            pass
    return '/tmp/stremio4kodi_qr.png'


class QRSetupWindow(xbmcgui.WindowXMLDialog if xbmcgui else object):
    """Ventana modal de Kodi con el código QR y estado de sincronización en tiempo real."""

    def __init__(self, *args, **kwargs):
        if xbmcgui:
            super().__init__(*args)
        self.qr_path = kwargs.get('qr_path', '')
        self.setup_url = kwargs.get('setup_url', '')
        self.server = kwargs.get('server', None)
        self.cancelled = False
        self.is_active = True

    def onInit(self):
        self.setProperty('stremio4kodi.qr', self.qr_path)
        self.setProperty('stremio4kodi.url', self.setup_url)
        self.setProperty('stremio4kodi.status', 'Esperando conexion del movil...')
        try:
            self.setFocusId(100)
        except Exception:
            pass

    def onClick(self, controlId):
        if controlId == 100:  # Botón Cerrar
            self.cancelled = True
            self.is_active = False
            self.close()
        elif controlId == 101:  # Botón URL
            if xbmcgui:
                try:
                    # Copiar URL o mostrar notificación
                    xbmcgui.Dialog().notification("Stremio4Kodi", "Abre esta direccion en tu navegador movil", xbmcgui.NOTIFICATION_INFO, 3000)
                except Exception:
                    pass

    def onAction(self, action):
        action_id = action.getId() if hasattr(action, 'getId') else 0
        # 9: BACK, 10: PREVIOUS_MENU, 92: NAV_BACK
        if action_id in (9, 10, 92, 216, 247, 257, 275, 61448, 61467):
            self.cancelled = True
            self.is_active = False
            self.close()

    def run_monitor(self):
        """Monitorea periódicamente si el móvil ha guardado la configuración para cerrar automáticamente."""
        while self.is_active and not self.cancelled:
            if self.server and getattr(self.server, 'is_saved', False):
                self.setProperty('stremio4kodi.status', '[OK] Ajustes guardados correctamente desde el movil!')
                xbmc.sleep(2000)
                self.close()
                break
            xbmc.sleep(300)


def show_mobile_setup():
    """Lanza el servidor HTTP y abre la ventana del código QR."""
    host = lan_ip()
    if host.startswith('127.'):
        if xbmcgui:
            xbmcgui.Dialog().ok(
                "Configurar desde el movil",
                "Este dispositivo no parece estar conectado a una red local o Wi-Fi.\n"
                "Conectalo a la misma red que tu telefono y vuelve a intentarlo."
            )
        return False

    # Iniciar servidor HTTP local
    server = SetupServer()
    try:
        server.start()
    except Exception as e:
        if xbmcgui:
            xbmcgui.Dialog().ok(
                "Error Servidor Web",
                f"No se pudo iniciar el servicio de configuracion movil:\n{e}"
            )
        return False

    setup_url = server.get_url()
    qr_path = _get_temp_qr_path()

    # Generar el archivo de imagen PNG con el código QR
    try:
        generate_qr_png(setup_url, qr_path, box_size=8, border=3)
    except Exception as e:
        server.stop()
        if xbmcgui:
            xbmcgui.Dialog().ok("Error QR", f"No se pudo generar la imagen del codigo QR:\n{e}")
        return False

    addon_path = _get_addon_path()

    # Intentar abrir la ventana XML con estilo nativo
    dialog = None
    try:
        dialog = QRSetupWindow(
            'stremio4kodi_qr_setup.xml',
            addon_path,
            'Default',
            '1080i',
            qr_path=qr_path,
            setup_url=setup_url,
            server=server
        )
        # Mostrar diálogo no bloqueante para poder monitorear cambios
        dialog.show()
        dialog.run_monitor()
    except Exception as e:
        if xbmc:
            xbmc.log(f"[Stremio4Kodi] Fallback dialog notice: {e}", xbmc.LOGWARNING)
        # Fallback para skins no compatibles con XML dialogs
        if xbmcgui:
            dlg = xbmcgui.DialogProgress()
            dlg.create("Configuracion desde el Movil (QR)", f"Abre en el movil:\n{setup_url}\n\nEsperando a que guardes los ajustes...")
            while not dlg.iscanceled() and not server.is_saved:
                xbmc.sleep(500)
            dlg.close()

    # Al salir, asegurar que el servidor web se apaga
    server.stop()
    if os.path.exists(qr_path):
        try:
            os.remove(qr_path)
        except Exception:
            pass

    return True
