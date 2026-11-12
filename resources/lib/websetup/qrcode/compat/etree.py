from __future__ import annotations  # MegaNexus: Kodi on Windows embeds Python 3.8
try:
    import lxml.etree as ET  # type: ignore  # noqa: F401
except ImportError:
    import xml.etree.ElementTree as ET  # type: ignore  # noqa: F401
