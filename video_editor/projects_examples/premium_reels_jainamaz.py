"""Premium Reels edit: prayer-mat sale. Audio = full voice track of the main video (c01).
Renders 1080x1920 @30 fps video track to stdout-pipe ffmpeg."""
import math, os, subprocess, sys
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

P = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G = os.path.join(P, "g")
FONTS = os.path.join(P, "fonts")
W, H, FPS = 1080, 1920, 30
TOTAL = 40.6
OUT = sys.argv[1]
ONLY = [float(x) for x in sys.argv[2:4]] if len(sys.argv) > 3 else None

# ------------------------------------------------------------------ easing
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def eo(x): x = clamp(x); return 1 - (1 - x) ** 3
def eio(x): x = clamp(x); return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def eexpo(x): x = clamp(x); return 1 if x == 1 else 1 - 2 ** (-10 * x)

# ------------------------------------------------------------------ shots (edit times == audio times)
CLIPFPS = {"c05": 30, "c06": 30, "c09": 30, "safi_bottle": 120}
def S(clip, a, b, s0, speed=1.0, z=(1.0, 1.06), pan=(0, 0), ramp=None):
    return dict(clip=clip, a=a, b=b, s0=s0, speed=speed, z=z, pan=pan, ramp=ramp)

SHOTS = [
    S("c01", 0.00, 2.20, 26.2, 0.5, z=(1.00, 1.07)),            # opening: symmetric shelf wall, slow-mo push
    S("c01", 2.20, 4.85, 7.4, 1.0, z=(1.10, 1.02), pan=(30, 0)),
    S("c05", 4.85, 6.60, 0.4, 1.0, z=(1.04, 1.12)),
    S("c06", 6.60, 8.40, 1.4, 1.0, z=(1.12, 1.03)),
    S("safi_bottle", 8.40, 11.00, 0.4, 1.0, z=(1.00, 1.06)),
    S("c01", 11.00, 13.05, 29.6, 1.0, z=(1.16, 1.00)),           # pull back: full shelves -> need space
    S("c07", 13.05, 15.40, 1.0, 1.0, z=(1.02, 1.08)),
    S("c09", 15.40, 18.05, 2.4, 1.0, z=(1.00, 1.05)),
    S("c15", 18.05, 20.55, 1.6, 0.6, z=(1.06, 1.14)),            # slow-mo quality close-up
    S("c04", 20.55, 21.95, 0.2, 0.6, z=(1.00, 1.05)),
    S("c14", 21.95, 24.70, 1.6, 1.0, z=(1.10, 1.00), ramp=[(0, 2.4), (0.45, 0.7), (2.9, 0.7)]),  # speed ramp
    S("c10", 24.70, 26.60, 0.3, 1.0, z=(1.03, 1.08)),
    S("c12", 26.60, 28.50, 5.8, 1.0, z=(1.08, 1.02)),
    S("c11", 28.50, 31.08, 0.5, 1.0, z=(1.02, 1.06)),
    S("c16", 31.08, 32.60, 1.0, 0.8, z=(1.04, 1.10)),
    S("c13", 32.60, 34.70, 2.0, 1.0, z=(1.08, 1.02)),
    S("c17", 34.70, 36.40, 0.5, 1.0, z=(1.02, 1.07)),
    S("c19", 36.40, 38.40, 0.2, 1.0, z=(1.06, 1.01)),
    S("c20", 38.40, TOTAL, 0.3, 0.8, z=(1.00, 1.08)),
]
# transitions at shot boundaries: (time, type, duration)
TRANS = {2.20: ("dissolve", .45), 4.85: ("whip_l", .32), 6.60: ("zoom", .36), 8.40: ("mask", .45),
         11.00: ("whip_r", .32), 13.05: ("zoom", .36), 15.40: ("cut", 0), 18.05: ("slide_up", .38),
         20.55: ("dissolve", .5), 21.95: ("zoom", .30), 24.70: ("whip_l", .30), 26.60: ("cut", 0),
         28.50: ("dissolve", .4), 31.08: ("zoom", .34), 32.60: ("cut", 0), 34.70: ("slide_up", .36),
         36.40: ("cut", 0), 38.40: ("dissolve", .5)}

def src_time(sh, u):
    """u = seconds since shot.a (can be negative inside the incoming transition)."""
    if sh["ramp"]:
        pts = sh["ramp"]
        # integrate piecewise-linear speed from 0..u (negative u: first speed)
        if u <= 0: return sh["s0"] + u * pts[0][1]
        acc, steps = 0.0, max(1, int(u * 200))
        for k in range(steps):
            t = (k + .5) * u / steps
            acc += np.interp(t, [p[0] for p in pts], [p[1] for p in pts]) * u / steps
        return sh["s0"] + acc
    return sh["s0"] + u * sh["speed"]

class Reader:
    def __init__(self, clip, t0):
        self.fps = CLIPFPS.get(clip, 60)
        path = os.path.join(G, clip + ".mp4")
        t0 = max(0.0, t0)
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-i", path, "-f", "rawvideo",
                                   "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE, bufsize=10 ** 8)
        self.n = int(round(t0 * self.fps)); self.last = None
    def at(self, t):
        idx = int(round(t * self.fps))
        while self.n <= idx:
            b = self.p.stdout.read(W * H * 3)
            if len(b) < W * H * 3: break
            self.last = np.frombuffer(b, np.uint8).reshape(H, W, 3); self.n += 1
        return self.last
    def close(self): self.p.kill()

def frame_of(sh, te, rd):
    u = te - sh["a"]
    f = rd.at(src_time(sh, u)).astype(np.float32)
    dur = sh["b"] - sh["a"]
    p = eio(clamp(u / dur))
    z = sh["z"][0] + (sh["z"][1] - sh["z"][0]) * p
    dx = sh["pan"][0] * (p - .5); dy = sh["pan"][1] * (p - .5)
    return xform(f, z, dx, dy)

def xform(f, z, dx=0, dy=0, rot=0):
    if abs(z - 1) < 1e-4 and dx == 0 and dy == 0 and rot == 0: return f
    M = cv2.getRotationMatrix2D((W / 2, H / 2), rot, z); M[0, 2] += dx; M[1, 2] += dy
    return cv2.warpAffine(f, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

def hblur(f, k):
    k = int(k)
    return f if k < 3 else cv2.blur(f, (k, 1))
def vblur(f, k):
    k = int(k)
    return f if k < 3 else cv2.blur(f, (1, k))

def transition(kind, x, A, B):
    """x in [0,1]; A outgoing, B incoming (float32 frames)."""
    if kind == "dissolve":
        m = eio(x); return A * (1 - m) + B * m
    if kind in ("whip_l", "whip_r"):
        s = -1 if kind == "whip_l" else 1
        m = eio(x); blur = 140 * math.sin(math.pi * x)
        a = hblur(xform(A, 1.0, s * W * 0.55 * m), blur)
        b = hblur(xform(B, 1.0, -s * W * 0.55 * (1 - m)), blur)
        return a * (1 - eio((x - .35) / .3)) + b * eio((x - .35) / .3)
    if kind == "zoom":
        m = eio(x); bl = 1 + 22 * math.sin(math.pi * x)
        a = cv2.GaussianBlur(xform(A, 1 + 0.45 * m), (0, 0), bl)
        b = cv2.GaussianBlur(xform(B, 1.35 - 0.35 * m), (0, 0), bl)
        k = eio((x - .3) / .4); return a * (1 - k) + b * k
    if kind == "slide_up":
        m = eio(x); bl = 90 * math.sin(math.pi * x)
        a = vblur(xform(A, 1.0, 0, -H * 0.35 * m), bl); b = vblur(xform(B, 1.0, 0, H * 0.35 * (1 - m)), bl)
        k = eio((x - .3) / .4); return a * (1 - k) + b * k
    if kind == "mask":                      # soft circular mask reveal from centre
        r = eo(x) * math.hypot(W, H) * 0.6
        yy, xx = np.ogrid[:H, :W]
        d = np.sqrt((xx - W / 2) ** 2 + (yy - H * 0.45) ** 2)
        m = np.clip((r - d) / 120 + .5, 0, 1)[..., None].astype(np.float32)
        return A * (1 - m) + B * m
    return B

# ------------------------------------------------------------------ typography
SANS = os.path.join(FONTS, "Montserrat.ttf")
SERIF_I = os.path.join(FONTS, "CormorantGaramond-Italic.ttf")
_fc = {}
def font(kind, size, weight=None):
    key = (kind, size, weight)
    if key not in _fc:
        f = ImageFont.truetype(SANS if kind == "sans" else SERIF_I, size)
        try:
            f.set_variation_by_axes([weight if kind == "sans" else 650])
        except Exception:
            pass
        _fc[key] = f
    return _fc[key]

WHITE = (255, 255, 255); CREAM = (255, 249, 238); GOLD = (240, 210, 150)

# tokens: (text, kind, size, weight, color, t_in)
def T(text, t, kind="sans", size=56, weight=600, color=WHITE): return (text, kind, size, weight, color, t)

# Cards: (t_start, t_end, y_center, lines=[ [tokens...], ... ], extras)
CARDS = [
    (0.00, 3.30, 1220, [[T("Бізге дүкенге келіп", 0.00, size=44, weight=500)],
                        [T("«арзан жайнамаз", 1.78, "serif", 104, color=CREAM)],
                        [T("бар ма?»", 2.84, "serif", 104, color=CREAM)]]),
    (3.34, 4.86, 1240, [[T("деп сұрайтындар", 3.34, size=44, weight=500)],
                        [T("ӨТЕ КӨП", 4.06, size=124, weight=800)]]),
    (4.86, 8.38, 1200, [[T("Қараңыздар,", 4.86, "serif", 96, color=CREAM)],
                        [T("қандай жайнамаздарды", 5.70, size=46, weight=500)],
                        [T("АКЦИЯҒА", 7.26, size=118, weight=800), ],
                        [T("бердік", 7.88, "serif", 80, color=GOLD)]]),
    (8.44, 11.26, 1220, [[T("Бізге", 8.44, size=46, weight=500)],
                         [T("SAFI", 9.72, size=150, weight=800)],
                         [T("өнімдері келе жатыр", 10.12, "serif", 82, color=CREAM)]]),
    (11.28, 13.05, 1230, [[T("бізге барынша", 11.28, size=46, weight=500)],
                          [T("ОРЫН БОСАТУ", 11.96, size=104, weight=800)],
                          [T("керек.", 12.74, "serif", 80, color=GOLD)]]),
    (13.06, 15.02, 1230, [[T("Бірақ бұл жайнамаздардың", 13.06, size=46, weight=500)],
                          [T("барлығы", 14.48, "serif", 96, color=CREAM)]]),
    (15.06, 18.06, 1060, [[T("4 500 ₸", 15.06, size=128, weight=800)],
                          [T("3 500 ₸", 16.36, size=128, weight=800)],
                          [T("бағамен сатылған", 17.56, "serif", 78, color=CREAM)]]),
    (18.08, 20.50, 1220, [[T("сапасы", 18.08, "serif", 96, color=CREAM)],
                          [T("ӨТЕ КҮШТІ", 18.94, size=124, weight=800)],
                          [T("жайнамаздар", 19.72, size=46, weight=500)]]),
    (21.92, 24.70, 1280, [[T("Қазір барлығы", 21.92, "serif", 96, color=CREAM)]]),
    (24.70, 27.94, 880, [[T("10 дана алсаңыз", 24.70, size=60, weight=600)]]),
    (27.94, 31.08, 1220, [[T("өзіңіз қалаған бағаға", 28.52, "serif", 90, color=CREAM)],
                          [T("САТА БЕРЕ АЛАСЫЗ", 29.92, size=82, weight=800)]]),
    (31.08, 32.26, 1230, [[T("Барлығы", 31.08, size=46, weight=500)],
                          [T("ТҮРІК ӨНІМІ", 31.66, size=118, weight=800)]]),
    (32.28, 34.00, 1220, [[T("қараңызшы,", 32.28, size=46, weight=500)],
                          [T("қандай әдемі түрлер!", 33.08, "serif", 100, color=CREAM)]]),
    (34.69, 37.44, 1220, [[T("Барлығының суретін", 34.69, size=46, weight=500)],
                          [T("алғыңыз келсе", 35.74, "serif", 100, color=CREAM)]]),
    (37.46, 39.30, 1250, [[T("TELEGRAM-ға", 37.46, size=112, weight=800)],
                          [T("саламыз", 38.08, "serif", 92, color=GOLD)]]),
]

_spr = {}
def word_sprite(text, kind, size, weight, color):
    key = (text, kind, size, weight, color)
    if key in _spr: return _spr[key]
    f = font(kind, size, weight)
    bb = f.getbbox(text)
    w, h = bb[2] - bb[0] + 60, int(size * 1.5) + 40
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.text((30 - bb[0], 20 + size * 0.1), text, font=f, fill=color + (255,))
    # very soft shadow (no outline)
    a = im.split()[3]
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); sh.putalpha(a.point(lambda v: v * 130 // 255))
    sh = sh.filter(ImageFilter.GaussianBlur(12))
    base = Image.new("RGBA", im.size, (0, 0, 0, 0)); base.alpha_composite(sh, (0, 4)); base.alpha_composite(im)
    arr = np.asarray(base).astype(np.float32)
    spr = (arr[..., :3][..., ::-1].copy(), arr[..., 3:4] / 255.0, w, h, bb[2] - bb[0])
    _spr[key] = spr
    return spr

def blit(fr, spr, x0, y0, alpha=1.0, scale=1.0):
    rgb, a, w, h = spr[0], spr[1], spr[2], spr[3]
    if alpha <= 0.003: return
    if abs(scale - 1) > 1e-3:
        w2, h2 = max(1, int(w * scale)), max(1, int(h * scale))
        rgb = cv2.resize(rgb, (w2, h2)); a = cv2.resize(a[..., 0], (w2, h2))[..., None]
        x0 += (w - w2) / 2; y0 += (h - h2) / 2; w, h = w2, h2
    x0, y0 = int(round(x0)), int(round(y0))
    fx0, fy0, fx1, fy1 = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if fx1 <= fx0 or fy1 <= fy0: return
    sa = a[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0] * alpha
    fr[fy0:fy1, fx0:fx1] = fr[fy0:fy1, fx0:fx1] * (1 - sa) + rgb[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0] * sa

def backdrop(fr, cx, cy, w, h, a):
    """Soft frosted dark panel behind text (background opacity, no outline)."""
    if a <= 0.01: return
    q = 4
    m = np.zeros((H // q, W // q), np.float32)
    x0, x1 = int((cx - w / 2) / q), int((cx + w / 2) / q); y0, y1 = int((cy - h / 2) / q), int((cy + h / 2) / q)
    m[max(0, y0):max(0, y1), max(0, x0):max(0, x1)] = 1
    m = cv2.GaussianBlur(m, (0, 0), 70 / q)
    m = cv2.resize(m, (W, H))[..., None] * a
    y0p, y1p = max(0, int(cy - h / 2 - 220)), min(H, int(cy + h / 2 + 220))
    reg = fr[y0p:y1p]
    blur = cv2.GaussianBlur(reg, (0, 0), 18)
    mm = m[y0p:y1p]
    fr[y0p:y1p] = reg * (1 - mm) + blur * 0.42 * mm

def draw_cards(fr, te):
    for (a, b, yc, lines) in CARDS:
        if not (a - 0.05 <= te < b + 0.25): continue
        out = 1 - eio((te - b) / 0.25) if te > b else 1.0
        # layout: lines stacked, each line centred
        heights = [max(tok[2] for tok in ln) * 1.12 for ln in lines]
        y = yc - sum(heights) / 2
        widest = max(sum(word_sprite(t[0], t[1], t[2], t[3], t[4])[4] for t in ln) + 22 * (len(ln) - 1) for ln in lines)
        backdrop(fr, W / 2, yc, min(W - 40, widest + 160), sum(heights) + 90, 0.85 * out * clamp((te - a) / 0.3))
        for ln, lh in zip(lines, heights):
            sprs = [word_sprite(tok[0], tok[1], tok[2], tok[3], tok[4]) for tok in ln]
            gap = 22
            totw = sum(s[4] for s in sprs) + gap * (len(sprs) - 1)
            x = W / 2 - totw / 2
            for tok, s in zip(ln, sprs):
                d = te - tok[5]
                if d >= 0:
                    k = eexpo(d / 0.45)
                    big = tok[2] >= 100
                    rise = (1 - k) * (34 if big else 22)
                    sc = (0.92 + 0.08 * k) if big else 1.0
                    blit(fr, s, x - 30, y + (lh - s[3]) / 2 + rise, alpha=clamp(d / 0.22) * out, scale=sc)
                x += s[4] + gap
            y += lh

# ------------------------------------------------------------------ motion graphics
def line(fr, p0, p1, prog, color=(255, 255, 255), th=4, alpha=1.0):
    if prog <= 0 or alpha <= 0: return
    x = p0[0] + (p1[0] - p0[0]) * prog; y = p0[1] + (p1[1] - p0[1]) * prog
    ov = fr.copy()
    cv2.line(ov, (int(p0[0]), int(p0[1])), (int(x), int(y)), color, th, cv2.LINE_AA)
    cv2.addWeighted(ov, alpha, fr, 1 - alpha, 0, fr)

def text_center(fr, txt, kind, size, weight, color, cx, cy, alpha=1.0, scale=1.0):
    s = word_sprite(txt, kind, size, weight, color)
    blit(fr, s, cx - s[4] / 2 - 30, cy - s[3] / 2, alpha, scale)

def money(v): return f"{int(round(v)):,}".replace(",", " ") + " ₸"

def draw_graphics(fr, te):
    # thin underline under ӨТЕ КӨП / ОРЫН БОСАТУ / ӨТЕ КҮШТІ
    for t0, t1, y, half in ((4.30, 4.86, 1318, 230), (12.20, 13.05, 1290, 330), (19.20, 20.50, 1268, 300)):
        if t0 <= te < t1 + .25:
            out = 1 - eio((te - t1) / .25) if te > t1 else 1
            line(fr, (W / 2 - half, y), (W / 2 + half, y), eo((te - t0) / .5), GOLD[::-1], 3, .9 * out)
    # SAFI: minimal arrow sweeping in
    if 10.12 <= te < 11.3:
        k = eo((te - 10.12) / .5); out = 1 - eio((te - 11.05) / .25)
        line(fr, (W / 2 - 300, 1330), (W / 2 + 300, 1330), k, GOLD[::-1], 3, .9 * out)
    # prices: struck through as the voice says "сатылған"; later recalled above the hero price
    if 15.0 <= te < 18.3:
        pass
    if 17.56 <= te < 18.3:
        out = 1 - eio((te - 18.06) / .25)
        for i, y in enumerate((980, 1123)):
            line(fr, (W / 2 - 250, y), (W / 2 + 250, y - 10), eo((te - 17.6 - i * .12) / .35), (80, 80, 235), 7, .95 * out)
    # HERO: 1 800 ₸ count-down with crossed old prices
    if 21.92 <= te < 24.95:
        out = 1 - eio((te - 24.70) / .25) if te > 24.70 else 1
        ka = clamp((te - 22.0) / .3)
        backdrop(fr, W / 2, 880, 860, 460, .9 * out * ka)
        text_center(fr, "4 500 ₸", "serif", 80, 500, CREAM, W / 2 - 180, 760, ka * out)
        text_center(fr, "3 500 ₸", "serif", 80, 500, CREAM, W / 2 + 180, 760, ka * out)
        for i, cx in enumerate((W / 2 - 170, W / 2 + 170)):
            line(fr, (cx - 110, 768), (cx + 110, 754), eo((te - 22.5 - i * .15) / .3), (80, 80, 235), 5, .95 * out)
        if te >= 23.30:
            p = eexpo((te - 23.30) / .75); p = 1.0 if p > 0.96 else p
            v = 4500 + (1800 - 4500) * p
            text_center(fr, money(round(v / 50) * 50 if p < 1 else 1800), "sans", 190, 800, WHITE,
                        W / 2, 980, clamp((te - 23.3) / .15) * out, 0.9 + 0.1 * eo((te - 23.3) / .5))
    # equation 10 × 1 800 = 18 000 ₸
    if 24.70 <= te < 28.2:
        out = 1 - eio((te - 27.94) / .25) if te > 27.94 else 1
        backdrop(fr, W / 2, 1140, 760, 360, .85 * out * clamp((te - 25.0) / .3))
        text_center(fr, "10 × 1 800 ₸", "serif", 92, 500, CREAM, W / 2, 1060, clamp((te - 25.0) / .3) * out)
        line(fr, (W / 2 - 280, 1128), (W / 2 + 280, 1128), eo((te - 25.6) / .5), GOLD[::-1], 3, .9 * out)
        if te >= 26.50:
            p = eexpo((te - 26.5) / .7); p = 1.0 if p > 0.96 else p
            text_center(fr, money(round(1800 + (18000 - 1800) * p, -2)), "sans", 150, 800, WHITE,
                        W / 2, 1220, clamp((te - 26.5) / .15) * out, .9 + .1 * eo((te - 26.5) / .5))
    # TÜRKİYE tag
    if 31.66 <= te < 32.3:
        out = 1 - eio((te - 32.05) / .25)
        line(fr, (W / 2 - 300, 1305), (W / 2 + 300, 1305), eo((te - 31.7) / .45), GOLD[::-1], 3, .9 * out)
    # Telegram: minimal paper plane + dotted path
    if 37.40 <= te < 39.5:
        out = 1 - eio((te - 39.25) / .25) if te > 39.25 else 1
        k = eo((te - 37.45) / .7)
        cx, cy = W / 2 + 260 * k - 130, 1010 - 90 * k
        pts = np.array([[0, 0], [-80, 28], [-46, 0], [-80, -28]], np.float32)
        ang = -0.32
        R = np.array([[math.cos(ang), -math.sin(ang)], [math.sin(ang), math.cos(ang)]], np.float32)
        poly = (pts @ R.T + [cx + 40, cy]).astype(np.int32)
        ov = fr.copy(); cv2.fillPoly(ov, [poly], (255, 255, 255), cv2.LINE_AA)
        cv2.addWeighted(ov, .95 * out * clamp((te - 37.45) / .2), fr, 1 - .95 * out * clamp((te - 37.45) / .2), 0, fr)
        for j in range(10):
            q = j / 10
            if q > k: break
            px = W / 2 - 130 + 260 * q - 60; py = 1010 - 90 * q + 18
            cv2.circle(fr, (int(px), int(py)), 3, (255, 255, 255), -1, cv2.LINE_AA)
    # end card
    if te >= 39.30:
        d = te - 39.30
        k = eio(d / .5)
        fr *= 1 - .35 * k
        backdrop(fr, W / 2, 1040, 860, 520, .8 * k)
        text_center(fr, "1 800 ₸", "sans", 200, 800, WHITE, W / 2, 900, clamp(d / .2), .92 + .08 * eo(d / .5))
        text_center(fr, "барлық жайнамаздар", "serif", 86, 500, CREAM, W / 2, 1060, clamp((d - .25) / .25))
        line(fr, (W / 2 - 200, 1135), (W / 2 + 200, 1135), eo((d - .35) / .5), GOLD[::-1], 3, .9)
        text_center(fr, "10 дана — 18 000 ₸", "sans", 46, 600, WHITE, W / 2, 1195, clamp((d - .5) / .25))

# legibility gradient (lower half) - background opacity instead of outlines
yy = np.linspace(0, 1, H)[:, None, None].astype(np.float32)
GRAD = (1 - 0.42 * np.clip((yy - 0.45) / 0.35, 0, 1) ** 1.3)
TOPG = (1 - 0.22 * np.clip((0.18 - yy) / 0.18, 0, 1))

# ------------------------------------------------------------------ render
def main():
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "15",
                            "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709",
                            "-colorspace", "bt709", OUT], stdin=subprocess.PIPE)
    readers = {}
    n0, n1 = 0, int(round(TOTAL * FPS))
    if ONLY: n0, n1 = int(ONLY[0] * FPS), int(ONLY[1] * FPS)
    for n in range(n0, n1):
        te = n / FPS
        active = []
        for i, sh in enumerate(SHOTS):
            tin = TRANS.get(sh["a"], ("cut", 0))[1] / 2
            tout = TRANS.get(sh["b"], ("cut", 0))[1] / 2
            if sh["a"] - tin <= te < sh["b"] + tout:
                active.append(i)
        frames = {}
        for i in active:
            sh = SHOTS[i]
            if i not in readers:
                readers[i] = Reader(sh["clip"], src_time(sh, te - sh["a"]) - 0.05)
            frames[i] = frame_of(sh, te, readers[i])
        for i in list(readers):
            if i not in active: readers.pop(i).close()
        if len(active) == 1:
            fr = frames[active[0]]
        else:
            i, j = active[0], active[1]
            kind, dur = TRANS[SHOTS[i]["b"]]
            x = (te - (SHOTS[i]["b"] - dur / 2)) / dur
            fr = transition(kind, clamp(x), frames[i], frames[j])
        fr = fr * GRAD * TOPG
        draw_cards(fr, te)
        draw_graphics(fr, te)
        if te < 0.6:                       # opening: vertical mask reveal from black
            m = eo(te / 0.6); h2 = int(H / 2 * m)
            mask = np.zeros((H, 1, 1), np.float32); mask[H // 2 - h2:H // 2 + h2] = 1
            fr = fr * mask
        if te > TOTAL - 0.35: fr *= clamp((TOTAL - te) / 0.35)
        enc.stdin.write(np.clip(fr, 0, 255).astype(np.uint8).tobytes())
        if n % 150 == 0: print(f"{te:5.1f}s", flush=True)
    enc.stdin.close(); enc.wait()

if __name__ == "__main__":
    main()
