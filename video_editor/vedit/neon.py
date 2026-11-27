"""NEON LIME style: dark UI, neon-lime accent, heavy uppercase headlines.

Saved from the reference reel the user liked (talking head + "НЕ ҮШІН" headline,
Instagram stat card, wallet card, checklist, "ПОЗИЦИЯ" tree). All sizes are for 1080x1920.

Every builder returns a PIL RGBA image; Renderer animates them (pop, slide, draw-on).
Graphics config types (source times, see config.neon.example.json):
  neon_headline  {word, label, frame: true, accent: "?"}
  neon_tag       {text, color: "lime"|"red"}
  neon_label     {text}
  neon_stat      {title, sub, value, icon: "instagram"|"play"}
  neon_wallet    {title, currency, value, cross: true}
  neon_checklist {title, items: [[time, text, ok]]}
  neon_tree      {root, items: [[time, text, icon]]}
  neon_arrow     {length}
  neon_counter   {from, to, suffix}
  neon_interlude {}              full-screen dark background instead of the footage
"""
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts")
BLACK = os.path.join(FONT_DIR, "Montserrat-Black.ttf")
XBOLD = os.path.join(FONT_DIR, "Montserrat-ExtraBold.ttf")
SEMI = os.path.join(FONT_DIR, "Montserrat-SemiBold.ttf")

LIME = (214, 253, 57)
BG = (17, 17, 17)
CARD = (24, 24, 24)
BORDER = (68, 68, 68)
WHITE = (255, 255, 255)
GREY = (150, 150, 150)
RED = (232, 52, 66)

_f = {}


def font(path, size):
    k = (path, size)
    if k not in _f:
        _f[k] = ImageFont.truetype(path, size)
    return _f[k]


def glow(im, color=LIME, radius=18, strength=0.55):
    """Neon glow: blurred copy of the coloured pixels behind the image."""
    a = np.asarray(im).astype(np.float32)
    col = np.array(color, np.float32)
    near = (np.abs(a[..., :3] - col).sum(-1) < 90) & (a[..., 3] > 0)
    g = Image.new("RGBA", im.size, color + (0,))
    g.putalpha(Image.fromarray((near * 255 * strength).astype(np.uint8)))
    g = g.filter(ImageFilter.GaussianBlur(radius))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    out.alpha_composite(g)
    out.alpha_composite(im)
    return out


def pad(im, p=40):
    out = Image.new("RGBA", (im.width + 2 * p, im.height + 2 * p), (0, 0, 0, 0))
    out.alpha_composite(im, (p, p))
    return out


def shadow(im, radius=14, alpha=150, off=(0, 6)):
    a = im.split()[3].point(lambda v: v * alpha // 255)
    sh = Image.new("RGBA", im.size, (0, 0, 0, 255))
    sh.putalpha(a)
    sh = sh.filter(ImageFilter.GaussianBlur(radius))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    out.alpha_composite(sh, off)
    out.alpha_composite(im)
    return out


# ------------------------------------------------------------------ text pieces
def headline(word, label=None, frame=True, accent=None, size=150):
    """Small lime label + huge white uppercase word with a dark edge, lime selection frame."""
    word = word.upper()
    fw = font(BLACK, size)
    bb = fw.getbbox(word)
    ww, wh = bb[2] - bb[0], bb[3] - bb[1]
    acc_w = int(size * 0.55) if accent else 0
    lab_h = int(size * 0.42) if label else 0
    W, H = ww + 120 + acc_w, wh + lab_h + 120
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x0, y0 = 60, 60 + lab_h
    if label:
        d.text((x0 + 10, 30), label, font=font(SEMI, int(size * 0.3)), fill=LIME)
    d.text((x0 - bb[0], y0 - bb[1]), word, font=fw, fill=WHITE, stroke_width=4, stroke_fill=(20, 20, 20))
    if frame:
        fx0, fy0, fx1, fy1 = x0 - 18, y0 - 18, x0 + ww + 18, y0 + wh + 18
        d.rectangle([fx0, fy0, fx1, fy1], outline=LIME, width=4)
        hs = 11
        for cx, cy in ((fx0, fy0), (fx1, fy0), (fx0, fy1), (fx1, fy1)):
            d.rectangle([cx - hs, cy - hs, cx + hs, cy + hs], fill=LIME)
    if accent:
        d.text((x0 + ww + 34, y0 - bb[1] - size * 0.05), accent, font=font(BLACK, int(size * 1.05)), fill=LIME)
    return shadow(glow(im, radius=14, strength=0.45))


def tag(text, color="lime", size=48):
    bgc = LIME if color == "lime" else RED
    fg = BG if color == "lime" else WHITE
    f = font(XBOLD, size)
    bb = f.getbbox(text)
    w, h = bb[2] - bb[0] + size, int(size * 1.45)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=int(h * 0.22), fill=bgc)
    d.text((w / 2, h / 2), text, font=f, fill=fg, anchor="mm")
    return glow(pad(im), color=bgc, radius=20, strength=0.5)


def label(text, size=46):
    f = font(SEMI, size)
    bb = f.getbbox(text)
    im = Image.new("RGBA", (bb[2] - bb[0] + 20, int(size * 1.5)), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((10 - bb[0], size * 0.2), text, font=f, fill=LIME, stroke_width=2, stroke_fill=(16, 16, 16))
    return shadow(glow(pad(im), radius=12, strength=0.6), radius=10, alpha=230, off=(0, 3))


def big_text(text, size=120, color=WHITE, edge=True, max_w=960):
    f = font(BLACK, size)
    bb = f.getbbox(text)
    while bb[2] - bb[0] > max_w and size > 30:          # auto-fit long numbers
        size = int(size * 0.92); f = font(BLACK, size); bb = f.getbbox(text)
    im = Image.new("RGBA", (bb[2] - bb[0] + 40, bb[3] - bb[1] + 40), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((20 - bb[0], 20 - bb[1]), text, font=f, fill=color,
                            stroke_width=4 if edge else 0, stroke_fill=(20, 20, 20))
    im = pad(im)
    return shadow(glow(im, radius=16, strength=0.5) if color == LIME else im)


# ------------------------------------------------------------------ icons
def _instagram(size):
    s = size * 4
    grad = Image.new("RGBA", (s, s))
    g = np.zeros((s, s, 4), np.uint8)
    yy, xx = np.mgrid[0:s, 0:s] / s
    t = np.clip((xx * 0.4 + (1 - yy) * 0.6), 0, 1)[..., None]
    c0, c1, c2 = np.array([254, 218, 117]), np.array([214, 41, 118]), np.array([79, 91, 213])
    col = np.where(t < .5, c0 + (c1 - c0) * (t / .5), c1 + (c2 - c1) * ((t - .5) / .5))
    g[..., :3] = col.astype(np.uint8); g[..., 3] = 255
    grad = Image.fromarray(g)
    m = Image.new("L", (s, s), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, s - 1, s - 1], radius=int(s * .24), fill=255)
    grad.putalpha(m)
    d = ImageDraw.Draw(grad)
    lw = int(s * .075)
    d.rounded_rectangle([s * .2, s * .2, s * .8, s * .8], radius=int(s * .17), outline=WHITE, width=lw)
    d.ellipse([s * .35, s * .35, s * .65, s * .65], outline=WHITE, width=lw)
    d.ellipse([s * .66, s * .27, s * .74, s * .35], fill=WHITE)
    return grad.resize((size, size), Image.LANCZOS)


def _icon(kind, size, color=LIME):
    s = size * 4
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    lw = int(s * .09)
    if kind == "wallet":
        d.rounded_rectangle([s * .08, s * .2, s * .92, s * .82], radius=int(s * .12), outline=color, width=lw)
        d.rounded_rectangle([s * .55, s * .42, s * .92, s * .62], radius=int(s * .06), outline=color, width=lw)
    elif kind == "target":
        for r in (.46, .3):
            d.ellipse([s * (.5 - r), s * (.5 - r), s * (.5 + r), s * (.5 + r)], outline=color, width=lw)
        d.ellipse([s * .4, s * .4, s * .6, s * .6], fill=color)
    elif kind == "user":
        d.ellipse([s * .3, s * .1, s * .7, s * .5], outline=color, width=lw)
        d.arc([s * .12, s * .52, s * .88, s * 1.25], 180, 360, fill=color, width=lw)
    elif kind == "play":
        d.polygon([(s * .2, s * .12), (s * .88, s * .5), (s * .2, s * .88)], fill=color)
    elif kind == "check":
        d.rounded_rectangle([0, 0, s - 1, s - 1], radius=int(s * .18), fill=(46, 200, 90))
        d.line([(s * .22, s * .52), (s * .43, s * .72), (s * .8, s * .3)], fill=WHITE, width=lw, joint="curve")
    elif kind == "cross":
        d.rounded_rectangle([0, 0, s - 1, s - 1], radius=int(s * .18), fill=RED)
        d.line([(s * .27, s * .27), (s * .73, s * .73)], fill=WHITE, width=lw)
        d.line([(s * .73, s * .27), (s * .27, s * .73)], fill=WHITE, width=lw)
    elif kind == "telegram":
        d.ellipse([0, 0, s - 1, s - 1], fill=(42, 171, 238))
        d.polygon([(s * .2, s * .5), (s * .76, s * .27), (s * .66, s * .76), (s * .48, s * .62)], fill=WHITE)
        d.polygon([(s * .42, s * .58), (s * .48, s * .76), (s * .54, s * .66)], fill=(200, 225, 245))
    elif kind == "bigx":
        lw2 = int(s * .13)
        d.line([(s * .1, s * .1), (s * .9, s * .9)], fill=color, width=lw2)
        d.line([(s * .9, s * .1), (s * .1, s * .9)], fill=color, width=lw2)
    return im.resize((size, size), Image.LANCZOS)


# ------------------------------------------------------------------ cards
def _card(w, h, border=BORDER, bw=2, fill=CARD):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([0, 0, w - 1, h - 1], radius=34, fill=fill + (245,), outline=border, width=bw)
    return im


def stat_card(title="Reels", sub="· қаралым", value="1 000 000 000", icon="instagram"):
    w, h = 900, 240
    im = _card(w, h)
    d = ImageDraw.Draw(im)
    ic = _instagram(140) if icon == "instagram" else _icon(icon, 130)
    im.alpha_composite(ic, (34, (h - ic.height) // 2))
    d.text((210, 52), title, font=font(SEMI, 38), fill=(200, 200, 200))
    tw = font(SEMI, 38).getlength(title)
    d.text((210 + tw + 16, 56), sub, font=font(SEMI, 34), fill=LIME)
    d.polygon([(212, 128), (252, 150), (212, 172)], fill=WHITE)
    d.text((270, 118), value, font=font(XBOLD, 64), fill=WHITE)
    return shadow(pad(im), 24, 160)


def wallet_card(title="шотың", currency="KZT", value="0 ₸", cross=True):
    w, h = 650, 330
    im = _card(w, h, border=(235, 235, 235), bw=3, fill=(16, 16, 16))
    d = ImageDraw.Draw(im)
    im.alpha_composite(_icon("wallet", 70), (40, 40))
    d.text((130, 46), title, font=font(XBOLD, 46), fill=WHITE)
    d.text((w - 40, 50), currency, font=font(XBOLD, 34), fill=GREY, anchor="ra")
    d.text((40, 160), value, font=font(BLACK, 110), fill=LIME)
    if cross:
        im.alpha_composite(_icon("bigx", 170), (w - 230, 120))
    return shadow(glow(pad(im), radius=16, strength=0.45), 24, 160)


def check_row(text, ok):
    w, h = 560, 84
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=16, fill=(245, 245, 245))
    im.alpha_composite(_icon("check" if ok else "cross", 46), (20, 19))
    d.text((84, h / 2), text, font=font(XBOLD, 36), fill=(20, 20, 20), anchor="lm")
    return im


def checklist_frame(n):
    w, h = 620, 50 + n * 104
    return shadow(pad(_card(w, h, border=(120, 120, 120), bw=3, fill=(30, 30, 30))), 24, 160)


def tree_item(text, icon="user"):
    w, h = 520, 100
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=24, fill=(22, 22, 22), outline=LIME, width=4)
    im.alpha_composite(_icon(icon, 52), (28, 24))
    d.text((100, h / 2), text, font=font(XBOLD, 38), fill=WHITE, anchor="lm")
    return glow(pad(im), radius=18, strength=0.45)


def tree_root(text, label_text=None):
    im = headline(text, label=label_text, frame=True, size=120)
    ic = _icon("target", 90)
    out = Image.new("RGBA", (im.width + 110, im.height), (0, 0, 0, 0))
    out.alpha_composite(glow(pad(ic, 20), radius=12), (0, im.height // 2 - 55 + (20 if label_text else 0)))
    out.alpha_composite(im, (110, 0))
    return out


def interlude_bg(W, H, t=0.0):
    """Dark #111 background, soft lime glow from the bottom and a few drifting square particles."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    g = np.exp(-(((xx - W * .5) / (W * .55)) ** 2 + ((yy - H * .62) / (H * .35)) ** 2))
    fr = np.zeros((H, W, 3), np.float32) + np.array(BG[::-1], np.float32)
    fr += g[..., None] * np.array([20, 34, 22], np.float32)       # BGR: faint lime haze
    rng = np.random.default_rng(5)
    for _ in range(7):
        x, y = rng.uniform(.08, .92) * W, rng.uniform(.1, .9) * H
        y += math.sin(t * 1.3 + x) * 14
        s = int(rng.uniform(9, 15))
        fr[int(y):int(y) + s, int(x):int(x) + s] = np.array(LIME[::-1], np.float32)
    return fr


def follow_cta(handle="@zamzam_muslim_products", line="Жазылыңыз", sub="жаңа жайнамаздар · жеңілдіктер"):
    """End-of-video subscribe CTA: avatar ring + handle + lime 'follow' button (growth rule #6)."""
    fh = font(XBOLD, 46); fs = font(SEMI, 32); fb = font(BLACK, 46)
    w = int(max(560, fh.getlength(handle) + 220)); h = 330
    im = Image.new("RGBA", (w + 80, h + 80), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([40, 40, 40 + w, 40 + h], radius=40, fill=CARD + (245,), outline=BORDER, width=2)
    ig = _instagram(120)
    d.ellipse([62, 62, 202, 202], outline=LIME, width=5)
    im.alpha_composite(ig, (72, 72))
    d.text((228, 92), handle, font=fh, fill=WHITE)
    d.text((228, 152), sub, font=fs, fill=GREY)
    bw = w - 60; bx0 = 70; by0 = 40 + h - 120
    d.rounded_rectangle([bx0, by0, bx0 + bw, by0 + 90], radius=26, fill=LIME)
    d.text((bx0 + bw / 2, by0 + 45), line.upper() + "  +", font=fb, fill=BG, anchor="mm")
    return shadow(glow(im, radius=18, strength=0.45), 24, 170)
