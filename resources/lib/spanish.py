# -*- coding: utf-8 -*-
"""
Spanish Language Detection - Identify Spanish audio/content in stream titles.
Detects: Castellano, Latino, Dual audio, Multi-language, and other common tags.
"""
import re
from resources.lib.logger import log


# Each tuple: (compiled regex, language variant label, confidence boost)
_PATTERNS = [
    # Explicit Spanish tags (highest confidence)
    (re.compile(r"\b(?:ESPANOL|SPANISH)\b", re.IGNORECASE), "ESP", 100),
    (re.compile(r"\b(?:CASTELLANO|CASTELL)\b", re.IGNORECASE), "CAST", 100),
    (re.compile(r"\bCAST\b"), "CAST", 90),
    (re.compile(r"\bLATINO\b", re.IGNORECASE), "LAT", 100),
    (re.compile(r"\bLAT\b"), "LAT", 85),

    # Audio track markers
    (re.compile(r"\b(?:AC3|DTS|AAC|EAC3|TrueHD)[\s._-]*(?:ESP|SPA|CAST|CASTELLANO)\b", re.IGNORECASE), "ESP", 95),
    (re.compile(r"\b(?:ESP|SPA|CAST|CASTELLANO)[\s._-]*(?:AC3|DTS|AAC|EAC3|TrueHD)\b", re.IGNORECASE), "ESP", 95),

    # ISO language codes
    (re.compile(r"\bSPA\b"), "ESP", 80),
    (re.compile(r"\b(?:es|spa)[\s._-](?:ES|MX|AR|CO|CL|PE|VE)\b"), "ESP", 85),

    # Dual / Multi (medium confidence)
    (re.compile(r"\bDUAL\b", re.IGNORECASE), "DUAL", 60),
    (re.compile(r"\bMULTI\b", re.IGNORECASE), "MULTI", 50),
    (re.compile(r"\bMULTi\.?(?:AUDIO|LANG|LANGUAGE)\b", re.IGNORECASE), "MULTI", 55),

    # Spanish release groups
    (re.compile(r"\b(?:EliteTorrent|MejorTorrent|DivXTotaL|NewPCT|ZonaHD)\b", re.IGNORECASE), "ESP", 90),
    (re.compile(r"\b(?:SPANiSH|SPANISH)\b", re.IGNORECASE), "ESP", 95),

    # Subtitled variants (lower priority)
    (re.compile(r"\bSUB[\s._-]*(?:ESP|SPA|SPANISH)\b", re.IGNORECASE), "SubESP", 30),
    (re.compile(r"\b(?:VOSE|V\.?O\.?S\.?E\.?)\b", re.IGNORECASE), "VOSE", 25),
]

_LATAM_PATTERNS = [
    (re.compile(r"\b(?:MX|MEX|MEXICO|MEXICANO)\b", re.IGNORECASE), "LAT-MX", 70),
    (re.compile(r"\b(?:LATAM|LATINOAMERICA)\b", re.IGNORECASE), "LAT", 85),
]


def detect_spanish(title):
    """
    Analyze a stream title for Spanish language indicators.
    Returns dict: is_spanish, variant, confidence, is_sub_only
    """
    if not title:
        return {"is_spanish": False, "variant": "", "confidence": 0, "is_sub_only": False}

    best_variant = ""
    best_confidence = 0
    is_sub_only = False

    for pattern, variant, confidence in _PATTERNS:
        if pattern.search(title):
            if confidence > best_confidence:
                best_confidence = confidence
                best_variant = variant
                is_sub_only = variant in ("SubESP", "VOSE")

    for pattern, variant, confidence in _LATAM_PATTERNS:
        if pattern.search(title):
            if confidence > best_confidence:
                best_confidence = confidence
                best_variant = variant
                is_sub_only = False

    is_spanish = best_confidence >= 50

    return {
        "is_spanish": is_spanish,
        "variant": best_variant,
        "confidence": best_confidence,
        "is_sub_only": is_sub_only,
    }


def get_spanish_label(stream):
    """Get a colored Kodi label for Spanish detection."""
    title = (stream.get("title", "") or stream.get("name", ""))
    info = detect_spanish(title)

    if not info["is_spanish"] and not info["is_sub_only"]:
        return ""

    variant = info["variant"]
    if variant == "CAST":
        return "[COLOR orange][Castellano][/COLOR]"
    elif variant in ("LAT", "LAT-MX"):
        return "[COLOR deepskyblue][Latino][/COLOR]"
    elif variant == "DUAL":
        return "[COLOR gold][Dual Audio][/COLOR]"
    elif variant == "MULTI":
        return "[COLOR mediumpurple][Multi Audio][/COLOR]"
    elif variant in ("SubESP", "VOSE"):
        return "[COLOR lightgreen][Sub Español][/COLOR]"
    elif variant == "ESP":
        return "[COLOR orange][Castellano/ESP][/COLOR]"
    return ""


def get_spanish_boost(stream):
    """Get a numeric boost for sorting. Higher = more likely Spanish."""
    title = (stream.get("title", "") or stream.get("name", ""))
    info = detect_spanish(title)
    return info["confidence"]
