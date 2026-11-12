from __future__ import annotations  # MegaNexus: Kodi on Windows embeds Python 3.8
# Try to import png library.
PngWriter = None

try:
    from png import Writer as PngWriter  # type: ignore  # noqa: F401
except ImportError:  # pragma: no cover
    pass
