# -*- coding: utf-8 -*-
"""
RTN (Release Torrent Normalizer) — Smart stream metadata parsing and formatting.
Inspired by RTN (Rank Torrent Name) used in Comet and top-tier Stremio addons.
Extracts resolution, HDR/DV, source, video codec, audio codec & channels,
language classification (Castellano/Latino/Dual/Multi/VOSE/V.O.), seeds, and size.
Generates rich, consistent, colorized Kodi display labels.
"""
import re


class RTN:
    # ── Resolution Patterns ────────────────────────────────
    RES_PATTERNS = [
        (re.compile(r"\b(?:2160p?|4k|uhd)\b", re.I), "4K", 400),
        (re.compile(r"\b(?:1080p?|fhd)\b", re.I), "1080p", 300),
        (re.compile(r"\b(?:720p?|hd)\b", re.I), "720p", 200),
        (re.compile(r"\b(?:480p?|576p?|sd)\b", re.I), "480p", 100),
    ]

    # ── Dynamic Range & HDR ────────────────────────────────
    HDR_PATTERNS = [
        (re.compile(r"\b(?:dv|dovi|dolby[\s._-]?vision)\b", re.I), "DV"),
        (re.compile(r"\b(?:hdr10\+|hdr10plus)\b", re.I), "HDR10+"),
        (re.compile(r"\b(?:hdr10|hdr)\b", re.I), "HDR"),
    ]

    # ── Source / Edition ───────────────────────────────────
    SOURCE_PATTERNS = [
        (re.compile(r"\b(?:remux|bdremux|uhdremux)\b", re.I), "REMUX", 60),
        (re.compile(r"\b(?:bluray|blu-ray|bdrip|brrip)\b", re.I), "BluRay", 45),
        (re.compile(r"\b(?:web-?dl|webrip)\b", re.I), "WEB-DL", 35),
        (re.compile(r"\b(?:hdtv|pdtv|dsr)\b", re.I), "HDTV", 20),
        (re.compile(r"\b(?:cam|camrip|ts|telesync|hdcam|hd-ts)\b", re.I), "CAM", -500),
    ]

    # ── Video Codec ────────────────────────────────────────
    CODEC_PATTERNS = [
        (re.compile(r"\b(?:av1|av01)\b", re.I), "AV1"),
        (re.compile(r"\b(?:hevc|x265|h\.?265)\b", re.I), "HEVC"),
        (re.compile(r"\b(?:x264|h\.?264|avc)\b", re.I), "AVC"),
        (re.compile(r"\b(?:xvid|divx)\b", re.I), "XviD"),
    ]

    # ── Audio Codec ────────────────────────────────────────
    AUDIO_PATTERNS = [
        (re.compile(r"\b(?:atmos)\b", re.I), "Atmos"),
        (re.compile(r"\b(?:truehd)\b", re.I), "TrueHD"),
        (re.compile(r"\b(?:dts[\s._-]?(?:hd|ma|x)|dts[\s._-]?lossless)\b", re.I), "DTS-HD"),
        (re.compile(r"\b(?:dts)\b", re.I), "DTS"),
        (re.compile(r"\b(?:eac3|e-ac-3|e-ac-3[\s._-]?joc|ddp|dd\+|dolby[\s._-]?digital[\s._-]?plus)\b", re.I), "EAC3"),
        (re.compile(r"\b(?:ac3|dd5\.1|dolby[\s._-]?digital)\b", re.I), "AC3"),
        (re.compile(r"\b(?:aac|flac)\b", re.I), "AAC"),
    ]

    # ── Audio Channels ─────────────────────────────────────
    CHANNELS_PATTERNS = [
        (re.compile(r"\b(?:7[\s._-]?[1ch]|7channel|8ch)\b", re.I), "7.1"),
        (re.compile(r"\b(?:5[\s._-]?[1ch]|5channel|6ch)\b", re.I), "5.1"),
        (re.compile(r"\b(?:2[\s._-]?[0ch]|stereo)\b", re.I), "2.0"),
    ]

    # ── Language Detection Patterns ────────────────────────
    PAT_VOSE = re.compile(
        r"\b(?:SUB[\s._-]*(?:ESP|SPA|SPANISH|ESPANOL)|VOSE|V\.?O\.?S\.?E\.?|SUBTITULADO)\b",
        re.I
    )
    PAT_CAST = re.compile(
        r"\b(?:CASTELLANO|CASTELL|ELITETORRENT|MEJORTORRENT|DIVXTOTAL|NEWPCT|ZONAHD|CINECALIDAD|DESCARGAS2020|GRANTORRENT|ESTRENOSDTL|PCTRELOAD)\b",
        re.I
    )
    PAT_LAT = re.compile(
        r"\b(?:LATINO|LATAM|CINECALIDAD|HDCINEPEQUE)\b",
        re.I
    )
    PAT_DUAL = re.compile(
        r"\b(?:DUAL|DUAL[\s._-]?AUDIO|LATINO[\s._-]?INGLES|CASTELLANO[\s._-]?INGLES|ESP[\s._-]?ENG)\b",
        re.I
    )
    PAT_MULTI = re.compile(
        r"\b(?:MULTI|MULTi[\s._-]?(?:AUDIO|LANG|LANGUAGE))\b",
        re.I
    )
    PAT_ESP_AUDIO = re.compile(
        r"(?<!sub[\s._-])(?<!subtitulos[\s._-])\b(?:espanol|spanish|cast|esp|spa)\b(?!\s*subs?)",
        re.I
    )

    @classmethod
    def normalize_stream(cls, s):
        """
        Ensures stream dict has populated 'title', 'size', and 'seeds'
        regardless of whether it comes from Comet, Torrentio, Peerflix, or DHT.
        """
        if not isinstance(s, dict):
            return s

        title = s.get("title") or ""
        desc = s.get("description") or ""
        beh_file = s.get("behaviorHints", {}).get("filename") or ""

        # Normalize title / filename
        if not title:
            if beh_file:
                s["title"] = beh_file
            elif desc:
                for line in desc.splitlines():
                    clean_l = line.strip().lstrip("📄 ").strip()
                    if clean_l and not clean_l.startswith(("📹", "🔊", "⭐", "👤", "💾", "🔎")):
                        s["title"] = clean_l
                        break
            if not s.get("title") and s.get("name"):
                s["title"] = s["name"]

        # Normalize size
        if not s.get("size"):
            v_size = s.get("behaviorHints", {}).get("videoSize")
            if v_size and isinstance(v_size, (int, float)) and v_size > 0:
                gb = v_size / (1024 ** 3)
                s["size"] = f"{gb:.1f} GB"
            else:
                combined = f"{s.get('title', '')} {desc} {s.get('name', '')}"
                m = re.search(r"(?:💾|\bsize\s*[:=]?\s*)\s*([\d.]+\s*(?:GB|MB))", combined, re.I)
                if not m:
                    m = re.search(r"\b([\d.]+\s*(?:GB|MB))\b", combined, re.I)
                if m:
                    s["size"] = m.group(1).strip()

        # Normalize seeds
        if s.get("seeds") is None and s.get("seeders") is None:
            combined = f"{s.get('title', '')} {desc} {s.get('name', '')}"
            m = re.search(r"(?:👤|\bseeds?\s*[:=]?\s*|\bseeders?\s*[:=]?\s*|\[s:\s*)\s*(\d+)", combined, re.I)
            if m:
                try:
                    s["seeds"] = int(m.group(1))
                except Exception:
                    pass

        return s

    @classmethod
    def parse(cls, s):
        """
        Parses stream metadata into structured attributes.
        """
        cls.normalize_stream(s)

        title = str(s.get("title") or "")
        desc = str(s.get("description") or "")
        name = str(s.get("name") or "")
        raw_text = f"{title} {desc} {name}"

        # 1. Resolution
        res = ""
        res_rank = 0
        for pat, r_name, r_score in cls.RES_PATTERNS:
            if pat.search(raw_text):
                res = r_name
                res_rank = r_score
                break

        # 2. Dynamic Range & HDR
        hdr_tags = []
        is_dv = bool(re.search(r"\b(?:dv|dovi|dolby[\s._-]?vision)\b", raw_text, re.I))
        is_hdr10p = bool(re.search(r"\b(?:hdr10\+|hdr10plus)\b", raw_text, re.I))
        is_hdr = bool(re.search(r"\b(?:hdr10|hdr)\b", raw_text, re.I))

        if is_dv and (is_hdr or is_hdr10p):
            hdr_tags.append("DV HDR")
        elif is_dv:
            hdr_tags.append("DV")
        elif is_hdr10p:
            hdr_tags.append("HDR10+")
        elif is_hdr:
            hdr_tags.append("HDR")

        if re.search(r"\b(?:10[\s._-]?bits?|hi10p?)\b", raw_text, re.I):
            hdr_tags.append("10bit")

        # 3. Source
        source = ""
        source_rank = 0
        for pat, s_name, s_score in cls.SOURCE_PATTERNS:
            if pat.search(raw_text):
                source = s_name
                source_rank = s_score
                break

        # 4. Video Codec
        codec = ""
        for pat, c_name in cls.CODEC_PATTERNS:
            if pat.search(raw_text):
                codec = c_name
                break

        # 5. Audio Codec & Channels
        audio_codec = ""
        for pat, a_name in cls.AUDIO_PATTERNS:
            if pat.search(raw_text):
                audio_codec = a_name
                break

        channels = ""
        for pat, ch_name in cls.CHANNELS_PATTERNS:
            if pat.search(raw_text):
                channels = ch_name
                break

        # 6. Language Variant
        lang = "VO"
        has_vose = bool(cls.PAT_VOSE.search(raw_text))
        has_cast = bool(cls.PAT_CAST.search(raw_text))
        has_lat = bool(cls.PAT_LAT.search(raw_text))
        has_dual = bool(cls.PAT_DUAL.search(raw_text))
        has_multi = bool(cls.PAT_MULTI.search(raw_text))
        has_esp = bool(cls.PAT_ESP_AUDIO.search(raw_text))

        if has_vose and not (has_cast or has_lat or has_dual):
            lang = "VOSE"
        elif has_dual or (has_cast and has_lat):
            lang = "DUAL"
        elif has_cast:
            lang = "CAST"
        elif has_lat:
            lang = "LAT"
        elif has_multi:
            lang = "MULTI"
        elif has_vose:
            lang = "VOSE"
        elif has_esp:
            lang = "CAST"

        # 7. Seeds, Size & Flags
        seeds = s.get("seeds")
        if seeds is None:
            seeds = s.get("seeders") or 0
        try:
            seeds = int(seeds)
        except Exception:
            seeds = 0

        size = s.get("size") or ""
        is_rd = bool(s.get("_rd_cached"))
        addon = s.get("_addon") or ""
        if not addon:
            # Detect addon from name/description if missing
            if "comet" in raw_text.lower():
                addon = "Comet"
            elif "torrentio" in raw_text.lower():
                addon = "Torrentio"
            elif "peerflix" in raw_text.lower():
                addon = "Peerflix"

        return {
            "resolution": res,
            "hdr": " ".join(hdr_tags),
            "source": source,
            "codec": codec,
            "audio": f"{audio_codec} {channels}".strip(),
            "language": lang,
            "seeds": seeds,
            "size": size,
            "is_rd": is_rd,
            "addon": addon,
            "quality_rank": res_rank + source_rank
        }

    @classmethod
    def format_label(cls, s, file_target=""):
        """
        Produces a rich, colored Kodi string for the stream selection dialog.
        """
        meta = cls.parse(s)
        parts = []

        # 1. Language Tag (Prominent & Colored)
        lang = meta["language"]
        if lang == "CAST":
            parts.append("[COLOR orange][B]Castellano[/B][/COLOR]")
        elif lang == "LAT":
            parts.append("[COLOR deepskyblue][B]Latino[/B][/COLOR]")
        elif lang == "DUAL":
            parts.append("[COLOR gold][B]Dual Audio[/B][/COLOR]")
        elif lang == "MULTI":
            parts.append("[COLOR mediumpurple][B]Multi Audio[/B][/COLOR]")
        elif lang == "VOSE":
            parts.append("[COLOR lightgreen][B]VOSE[/B][/COLOR]")
        else:
            parts.append("[COLOR white][V.O.][/COLOR]")

        # 2. Real-Debrid badge
        if meta["is_rd"]:
            parts.append("[COLOR magenta][B][RD+][/B][/COLOR]")

        # 3. Quality & Source Block (e.g. [4K DV REMUX], [1080p WEB-DL])
        qual_parts = []
        res = meta["resolution"]
        if res == "4K":
            qual_parts.append("[COLOR gold][B]4K[/B][/COLOR]")
        elif res == "1080p":
            qual_parts.append("[COLOR lime]1080p[/COLOR]")
        elif res == "720p":
            qual_parts.append("[COLOR cyan]720p[/COLOR]")
        elif res == "480p":
            qual_parts.append("[COLOR grey]480p[/COLOR]")

        if meta["hdr"]:
            qual_parts.append(f"[COLOR plum]{meta['hdr']}[/COLOR]")

        if meta["source"]:
            if meta["source"] == "REMUX":
                qual_parts.append("[COLOR springgreen][B]REMUX[/B][/COLOR]")
            elif meta["source"] == "CAM":
                qual_parts.append("[COLOR red][B]CAM[/B][/COLOR]")
            else:
                qual_parts.append(f"[COLOR skyblue]{meta['source']}[/COLOR]")

        if qual_parts:
            parts.append(f"[{' '.join(qual_parts)}]")

        # 4. Codecs & Audio Block (e.g. [HEVC] [Atmos 5.1])
        tech_parts = []
        if meta["codec"]:
            tech_parts.append(f"[COLOR khaki]{meta['codec']}[/COLOR]")
        if meta["audio"]:
            tech_parts.append(f"[COLOR dodgerblue]{meta['audio']}[/COLOR]")
        if tech_parts:
            parts.append(" ".join(tech_parts))

        # 5. Clean Title Line or Targeted File Line
        if file_target:
            parts.append(file_target)
        else:
            title = s.get("title") or s.get("name") or "Unknown"
            lines = [l.strip() for l in str(title).splitlines() if l.strip()]
            clean_title = lines[0] if lines else str(title)
            clean_title = re.sub(
                r"\[(?:4k|1080p|720p|hevc|x265|x264|castellano|latino|dual|vose|torrentio|comet)\]",
                "",
                clean_title,
                flags=re.I
            ).strip()
            parts.append(clean_title[:55])

        # 6. Seeds (Colored)
        seeds = meta["seeds"]
        if seeds >= 50:
            parts.append(f"[COLOR lime]👤 {seeds}[/COLOR]")
        elif seeds >= 10:
            parts.append(f"[COLOR yellow]👤 {seeds}[/COLOR]")
        elif seeds > 0:
            parts.append(f"[COLOR orange]👤 {seeds}[/COLOR]")
        else:
            parts.append("[COLOR red]👤 0[/COLOR]")

        # 7. Size
        if meta["size"]:
            parts.append(f"💾 {meta['size']}")

        # 8. Addon tag
        if meta["addon"]:
            parts.append(f"[COLOR grey][{meta['addon']}][/COLOR]")

        return "  ".join(parts)

    @classmethod
    def get_quality_score(cls, s):
        """
        Returns numeric score for smart sorting:
        4K Remux (460) > 4K Web (435) > 1080p Remux (360) > 1080p Web (335) > 720p (220)
        Penalizes CAM/Telesync heavily (-500).
        """
        meta = cls.parse(s)
        return meta["quality_rank"]
