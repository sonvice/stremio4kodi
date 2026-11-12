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
            return xbmcaddon.Addon().getAddonInfo('path')
        except Exception:
            try:
                return xbmcaddon.Addon(ADDON_ID).getAddonInfo('path')
            except Exception:
                pass
    p = os.path.abspath(__file__)
    for _ in range(4):
        p = os.path.dirname(p)
    return p


def _get_temp_qr_path():
    addon_path = _get_addon_path()
    return os.path.join(addon_path, 'resources', 'media', 'qr_code.png')


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
        self.setProperty('stremio4kodi.status', '• Esperando conexion del movil...')

        addon_path = _get_addon_path()
        media_dir = os.path.join(addon_path, 'resources', 'media')

        # 1. Overlay 100% opaco oscurecido (ID 198)
        try:
            ctrl_overlay = self.getControl(198)
            if ctrl_overlay:
                ctrl_overlay.setImage(os.path.join(media_dir, 'overlay.png'))
        except Exception:
            pass

        # 2. Tarjeta principal sólida 100% opaca (ID 199)
        try:
            ctrl_card = self.getControl(199)
            if ctrl_card:
                ctrl_card.setImage(os.path.join(media_dir, 'card_bg.png'))
        except Exception:
            pass

        # 3. Imagen del código QR (ID 200)
        try:
            ctrl_qr = self.getControl(200)
            if ctrl_qr:
                ctrl_qr.setImage(os.path.join(media_dir, 'qr_code.png'))
        except Exception:
            pass

        # 4. Botón interactivo con la URL (ID 101)
        try:
            ctrl_url = self.getControl(101)
            if ctrl_url and self.setup_url:
                ctrl_url.setLabel(self.setup_url)
        except Exception:
            pass

        # 6. Estado en vivo (ID 203)
        try:
            ctrl_status = self.getControl(203)
            if ctrl_status:
                ctrl_status.setLabel('[COLOR FFFFDD00]• Esperando conexion del movil...[/COLOR]')
        except Exception:
            pass

        try:
            self.setFocusId(100)
        except Exception:
            pass

    def close(self):
        self.is_active = False
        self.cancelled = True
        if self.server:
            try:
                self.server.stop()
            except Exception:
                pass
        try:
            super().close()
        except Exception:
            pass

    def onClick(self, controlId):
        if controlId == 100:  # Botón Cerrar / Cancelar
            self.close()
        elif controlId == 101:  # Botón URL
            if xbmcgui:
                try:
                    xbmcgui.Dialog().notification("Stremio4Kodi", "Abre esta direccion en tu navegador movil", xbmcgui.NOTIFICATION_INFO, 3000)
                except Exception:
                    pass

    def onAction(self, action):
        action_id = action.getId() if hasattr(action, 'getId') else 0
        # 9: BACK, 10: PREVIOUS_MENU, 13: STOP, 92: NAV_BACK, 110: CONTEXT
        if action_id in (9, 10, 13, 92, 110, 216, 247, 257, 275, 61448, 61467):
            self.close()

    def run_monitor(self):
        """Monitorea periódicamente las acciones del móvil: guardados sucesivos, finalización o inactividad."""
        monitor = xbmc.Monitor() if xbmc else None
        last_seen_count = 0

        while self.is_active and not self.cancelled:
            if monitor and monitor.abortRequested():
                self.close()
                break

            # 1. Cierre solicitado desde el móvil ("Terminar y Cerrar en TV")
            if self.server and getattr(self.server, 'is_finished', False):
                try:
                    ctrl_status = self.getControl(203)
                    if ctrl_status:
                        ctrl_status.setLabel('[COLOR FF00E676]• Configuracion finalizada desde el movil[/COLOR]')
                except Exception:
                    pass
                if xbmc:
                    xbmc.sleep(1200)
                self.close()
                break

            # 2. Guardado sucesivo (Multi-Save): actualiza la TV sin cerrar la sesión
            current_count = getattr(self.server, 'save_count', 0) if self.server else 0
            if current_count > last_seen_count:
                last_seen_count = current_count
                save_time = getattr(self.server, 'last_save_time', '')
                time_str = f" ({save_time})" if save_time else ""
                status_text = f"• Guardado{time_str} • Sesion activa"
                self.setProperty('stremio4kodi.status', status_text)
                try:
                    ctrl_status = self.getControl(203)
                    if ctrl_status:
                        ctrl_status.setLabel(f'[COLOR FF00E676]{status_text}[/COLOR]')
                except Exception:
                    pass

            # 3. Timeout de seguridad por inactividad prolongada (15 minutos)
            if self.server and (time.time() - getattr(self.server, 'last_activity', time.time()) > 900):
                if xbmc:
                    xbmc.log("[Stremio4Kodi] WebSetup: Cerrado por inactividad (15 min).", xbmc.LOGINFO)
                self.close()
                break

            if xbmc:
                xbmc.sleep(200)
            else:
                time.sleep(0.2)


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
    finally:
        # Al salir, asegurar que el servidor web se apaga de forma instantánea
        server.stop()
        if os.path.exists(qr_path):
            try:
                os.remove(qr_path)
            except Exception:
                pass
        try:
            del dialog
        except Exception:
            pass

    return True
