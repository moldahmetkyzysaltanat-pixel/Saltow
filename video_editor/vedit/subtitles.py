"""Kazakh subtitles -> ASS (burned in with libass) + SRT.

Two looks, both set from config["subtitles"]:
  mode "karaoke": Reels/TikTok style, 2-4 words on screen, the word being spoken is
                  highlighted and pops (default);
  mode "phrase":  one short phrase at a time, *keywords* in the highlight colour.
"""
import re


def ass_color(hex_color, alpha=0):
    h = hex_color.lstrip("#")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H{alpha:02X}{b}{g}{r}".upper()


def ts_ass(t):
    cs = max(0, int(round(t * 100)))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def ts_srt(t):
    ms = max(0, int(round(t * 1000)))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


DEFAULT = {
    "mode": "karaoke", "font": "Inter ExtraBold", "fonts_dir": None, "size": 74, "uppercase": True,
    "color": "#FFFFFF", "highlight": "#FFD84A", "outline": 7, "outline_color": "#000000", "shadow": 2,
    "position_y": 0.73, "max_chars_per_line": 16, "words_per_page": 3, "pop": True, "letter_spacing": 0,
}


# Saved looks. Use in config: "subtitles": {"preset": "neon_lime"} (other keys override the preset).
PRESETS = {
    # reference reel: heavy white uppercase, thin dark edge, the spoken word in neon lime
    "neon_lime": {"mode": "karaoke", "font": "Montserrat Black", "size": 84, "uppercase": True,
                  "color": "#FFFFFF", "highlight": "#D6FD3D", "outline": 3, "outline_color": "#141414",
                  "shadow": 3, "position_y": 0.77, "max_chars_per_line": 15, "words_per_page": 3, "pop": True},
    # premium editorial (prayer-mat reel): no outline, soft shadow, clean phrases
    "premium_editorial": {"mode": "phrase", "font": "Montserrat ExtraBold", "size": 64, "uppercase": False,
                          "color": "#FFFFFF", "highlight": "#F0D296", "outline": 0, "outline_color": "#000000",
                          "shadow": 2, "position_y": 0.68, "max_chars_per_line": 20, "pop": True},
}


def _upper(s, on):
    # Python upper() handles Kazakh letters (ә->Ә, і->І, ...)
    return s.upper() if on else s


def _word_times(start, end, words):
    """Spread a phrase's duration over its words, proportional to word length."""
    lens = [max(2, len(w.replace("*", ""))) for w in words]
    tot = sum(lens)
    out, t = [], start
    for n in lens:
        d = (end - start) * n / tot
        out.append((t, t + d))
        t += d
    return out


def _pages(words, per_page, max_chars):
    pages, cur = [], []
    for i, w in enumerate(words):
        txt = " ".join(words[j] for j in cur + [i]).replace("*", "")
        if cur and (len(cur) >= per_page or len(txt) > max_chars * 2):
            pages.append(cur)
            cur = []
        cur.append(i)
    if cur:
        pages.append(cur)
    return pages


def _lines(idx, words, max_chars):
    lines, cur = [], []
    for i in idx:
        txt = " ".join(words[j] for j in cur + [i]).replace("*", "")
        if cur and len(txt) > max_chars:
            lines.append(cur)
            cur = []
        cur.append(i)
    if cur:
        lines.append(cur)
    return lines


def build(subs, timeline, cfg, width, height, ass_path, srt_path):
    """subs: [{start, end, kk}] in SOURCE time; timeline maps to edited time."""
    cfg = cfg or {}
    c = {**DEFAULT, **PRESETS.get(cfg.get("preset"), {}), **cfg}
    if c.get("preset") and not cfg.get("fonts_dir"):
        import os
        c["fonts_dir"] = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts")
    margin_v = int(height * (1 - c["position_y"]))
    style = (f"Style: KZ,{c['font']},{c['size']},{ass_color(c['color'])},{ass_color(c['color'])},"
             f"{ass_color(c['outline_color'])},{ass_color('#000000', 0x80)},0,0,0,0,100,100,"
             f"{c['letter_spacing']},0,1,{c['outline']},{c['shadow']},2,60,60,{margin_v},1")
    head = ("[Script Info]\nScriptType: v4.00+\n"
            f"PlayResX: {width}\nPlayResY: {height}\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n"
            "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
            "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, "
            "Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n" + style + "\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    hi = ass_color(c["highlight"])
    base = ass_color(c["color"])

    # edited-time windows, no overlaps
    items = []
    for sb in subs:
        if not sb.get("kk", "").strip():
            continue
        a, b = timeline.e(sb["start"]), timeline.e(sb["end"]) + 0.10
        if b - a > 0.15:
            items.append([a, b, sb["kk"].strip()])
    items.sort()
    for i in range(len(items) - 1):
        nxt = items[i + 1][0]
        if items[i][1] > nxt - 0.02 or nxt - items[i][1] < 0.3:
            items[i][1] = nxt - 0.02

    events, srt = [], []
    for n, (a, b, text) in enumerate(items):
        srt.append(f"{n + 1}\n{ts_srt(a)} --> {ts_srt(b)}\n{text.replace('*', '')}\n")
        words = text.split()
        flags = _kw_flags(words)
        if c["mode"] == "phrase":
            lines = _lines(list(range(len(words))), words, c["max_chars_per_line"] + 10)
            body = "\\N".join(" ".join(_kw(words[j], flags[j], base, hi, c["uppercase"]) for j in ln) for ln in lines)
            pop = "{\\fad(70,60)\\fscx86\\fscy86\\t(0,140,\\fscx100\\fscy100)}" if c["pop"] else ""
            events.append(f"Dialogue: 0,{ts_ass(a)},{ts_ass(b)},KZ,,0,0,0,,{pop}{body}")
            continue
        wt = _word_times(a, b - 0.08, words)
        for page in _pages(words, c["words_per_page"], c["max_chars_per_line"]):
            p0, p1 = wt[page[0]][0], (wt[page[-1]][1] if page[-1] < len(words) - 1 else b)
            lines = _lines(page, words, c["max_chars_per_line"])
            for k, wi in enumerate(page):
                t0 = p0 if k == 0 else wt[wi][0]
                t1 = p1 if k == len(page) - 1 else wt[page[k + 1]][0]
                parts = []
                for ln in lines:
                    toks = []
                    for j in ln:
                        w = _upper(words[j].replace("*", ""), c["uppercase"])
                        if j == wi:
                            anim = "\\fscx112\\fscy112\\t(0,90,\\fscx100\\fscy100)" if c["pop"] else ""
                            toks.append(f"{{\\c{hi}{anim}}}{w}{{\\c{base}\\fscx100\\fscy100}}")
                        elif flags[j]:
                            toks.append(f"{{\\c{hi}}}{w}{{\\c{base}}}")
                        else:
                            toks.append(w)
                    parts.append(" ".join(toks))
                intro = "{\\fad(60,0)\\fscx88\\fscy88\\t(0,120,\\fscx100\\fscy100)}" if (k == 0 and c["pop"]) else ""
                events.append(f"Dialogue: 0,{ts_ass(t0)},{ts_ass(t1)},KZ,,0,0,0,,{intro}" + "\\N".join(parts))

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(head + "\n".join(events) + "\n")
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt))
    return len(items)


def _kw_flags(words):
    """Which words sit inside *...* (a highlight may span several words)."""
    flags, on = [], False
    for w in words:
        n = w.count("*")
        if n >= 2:            # *word* (possibly with a suffix: *Safi*-ді)
            flags.append(True)
        elif n == 1 and not on:
            on = True
            flags.append(True)
        elif n == 1:
            flags.append(True)
            on = False
        else:
            flags.append(on)
    return flags


def _kw(word, flag, base, hi, upper):
    w = _upper(word.replace("*", ""), upper)
    return f"{{\\c{hi}}}{w}{{\\c{base}}}" if flag else w
