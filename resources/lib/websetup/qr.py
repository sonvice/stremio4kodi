# -*- coding: utf-8 -*-
"""Generador de códigos QR en formato PNG puro (100% Python, sin PIL ni binarios C)."""

import os
import struct
import sys
import zlib

_CUR_DIR = os.path.dirname(os.path.abspath(__file__))
if _CUR_DIR not in sys.path:
    sys.path.insert(0, _CUR_DIR)


def _png_from_pixels(pixels, side):
    """Construye un PNG RGBA de 32 bits estándar (8 bits por canal con alfa opaco) para compatibilidad total con Kodi."""
    def chunk(chunk_type, body):
        return struct.pack('>I', len(body)) + chunk_type + body + struct.pack('>I', zlib.crc32(chunk_type + body) & 0xffffffff)

    # Encabezado IHDR: width, height, bit_depth=8, color_type=6 (RGBA), compression=0, filter=0, interlace=0
    ihdr_data = struct.pack('>IIBBBBB', side, side, 8, 6, 0, 0, 0)
    # Cada fila de datos PNG debe ir precedida por un byte de filtro (0 = ninguno)
    raw_data = b''.join(b'\x00' + row for row in pixels)
    idat_data = zlib.compress(raw_data, 9)

    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr_data) + chunk(b'IDAT', idat_data) + chunk(b'IEND', b'')


def generate_qr_png(data, output_path=None, box_size=8, border=3):
    """Genera un archivo de imagen PNG con el código QR para el texto/URL proporcionado.
    
    :param data: Texto o URL a codificar en el QR.
    :param output_path: Ruta del archivo donde guardar el PNG. Si es None, devuelve los bytes.
    :param box_size: Tamaño en píxeles de cada módulo/cuadro del QR.
    :param border: Margen de módulos blancos alrededor del QR.
    :return: Ruta del archivo generado o bytes del PNG.
    """
    _CUR_DIR = os.path.dirname(os.path.abspath(__file__))
    if _CUR_DIR not in sys.path:
        sys.path.insert(0, _CUR_DIR)
    import qrcode

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=1,
        border=border
    )
    qr.add_data(data)
    qr.make(fit=True)

    matrix = qr.get_matrix()
    side = len(matrix) * box_size

    dark_pixel = b'\x00\x00\x00\xff'
    light_pixel = b'\xff\xff\xff\xff'

    pixels = []
    for line in matrix:
        row = b''.join((dark_pixel if is_dark else light_pixel) * box_size for is_dark in line)
        for _ in range(box_size):
            pixels.append(row)

    png_bytes = _png_from_pixels(pixels, side)

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(png_bytes)
        return output_path

    return png_bytes
