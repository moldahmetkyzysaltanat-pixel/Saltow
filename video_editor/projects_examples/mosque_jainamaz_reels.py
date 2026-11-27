"""Mosque prayer-mat reel. Full voiceover (32.79 s, untouched) + 2 videos + 5 photos.
Minimal motion design, two-font captions with no stroke and no background box."""
import math, os, subprocess, sys
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFilter, ImageFont
sys.path.insert(0, "/home/user/Saltow/video_editor")
sys.path.insert(0, "/tmp/claude-0/-home-user-Saltow/ff4d6f8e-eeda-5c24-9b8f-32a0a8602af8/scratchpad/p4/work")
import build as B
from vedit import neon as N

P = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B.G = os.path.join(P, "g")
B.CLIPFPS.update({"v6": 24, "v7": 30})
W, H, FPS = 1080, 1920, 30
TOTAL = 32.79
clamp, eo, eio, eexpo = B.clamp, B.eo, B.eio, B.eexpo
def back(x, k=1.70158): x = clamp(x); return 1 + (k + 1) * (x - 1) ** 3 + k * (x - 1) ** 2

# ------------------------------------------------------------------ photos with Ken Burns
PH = {i: cv2.imread(os.path.join(B.G, f"p{i}.png")).astype(np.float32) for i in range(1, 6)}   # 1620x2880
def photo(i, p, z0, z1, c0, c1):
    """p: 0..1 progress; z: zoom (1 = whole photo); c: normalised centre (x, y)."""
    img = PH[i]; ih, iw = img.shape[:2]
    k = eio(p); z = z0 + (z1 - z0) * k
    cx = (c0[0] + (c1[0] - c0[0]) * k) * iw; cy = (c0[1] + (c1[1] - c0[1]) * k) * ih
    cw, ch = iw / z, ih / z
    x0 = min(max(cx - cw / 2, 0), iw - cw); y0 = min(max(cy - ch / 2, 0), ih - ch)
    M = np.float32([[W / cw, 0, -x0 * W / cw], [0, H / ch, -y0 * H / ch]])
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_AREA, borderMode=cv2.BORDER_REFLECT)

# shots: video ("v", clip, a, b, s0, speed, z0, z1) or photo ("p", idx, a, b, z0, z1, c0, c1)
SHOTS = [
    ("v", "v7", 0.00, 2.28, 1.2, 1.0, 1.00, 1.07),           # WIDE/MEDIUM: the stack — hook
    ("v", "v6", 2.28, 4.64, 2.4, 0.8, 1.04, 1.12),           # DETAIL: minaret + border  "әдемілігі"
    ("v", "v7", 4.64, 5.72, 11.6, 0.8, 1.06, 1.12),          # DETAIL: fringe
    ("p", 2, 5.72, 7.84, 1.95, 1.75, (.5, .36), (.5, .36)),    # CLOSE: mosque image  "мешіттің бейнесімен"
    ("p", 3, 7.84, 10.40, 1.0, 1.04, (.5, .5), (.5, .5)),    # under the 5-colour collage
    ("p", 2, 10.40, 11.95, 1.12, 1.02, (.5, .48), (.5, .48)),# MEDIUM red
    ("p", 3, 11.95, 12.65, 1.10, 1.03, (.5, .48), (.5, .48)),# gold
    ("p", 5, 12.65, 13.40, 1.10, 1.03, (.5, .48), (.5, .48)),# beige/pink
    ("p", 1, 13.40, 14.50, 1.10, 1.03, (.5, .48), (.5, .48)),# grey-blue
    ("p", 4, 14.50, 15.40, 1.10, 1.03, (.5, .48), (.5, .48)),# black
    ("v", "v6", 15.40, 17.14, 2.6, 0.7, 1.10, 1.18),         # DETAIL texture  "сапасы сөз жоқ"
    ("v", "v7", 17.14, 19.84, 16.6, 1.0, 1.02, 1.08),        # DETAIL fringe + hand  "тоғыз мыңнан сатылған"
    ("v", "v6", 19.84, 22.84, 11.0, 0.9, 1.02, 1.08),        # DETAIL back side + hand  "жеңілдікпен"
    ("v", "v7", 22.84, 26.44, 45.0, 1.0, 1.00, 1.06),        # MEDIUM stack = 10 pcs  "6 000 / он данасы"
    ("v", "v7", 26.44, 29.16, 35.6, 1.0, 1.04, 1.10),        # DETAIL colourful mat  "ойланбай алып алыңыз"
    ("p", 3, 29.16, TOTAL, 1.35, 1.0, (.5, .35), (.5, .5)),  # pull-back to whole mat + end card
]
TRANS = {5.72: ("dissolve", .30), 7.84: ("dissolve", .35), 10.40: ("dissolve", .35), 17.14: ("dissolve", .30),
         26.44: ("slide_up", .32), 29.16: ("dissolve", .40)}

class VR:
    def __init__(self, sh, t0):
        self.sh = sh; self.r = B.Reader(sh[1], max(0.0, sh[4] + (t0 - sh[2]) * sh[5] - .05))
    def frame(self, te):
        _, clip, a, b, s0, sp, z0, z1 = self.sh
        f = self.r.at(s0 + (te - a) * sp).astype(np.float32)
        p = eio(clamp((te - a) / (b - a)))
        return B.xform(f, z0 + (z1 - z0) * p)
    def close(self): self.r.close()

def shot_frame(i, te, rd):
    sh = SHOTS[i]
    if sh[0] == "p":
        _, idx, a, b, z0, z1, c0, c1 = sh
        return photo(idx, clamp((te - a) / (b - a)), z0, z1, c0, c1)
    if i not in rd: rd[i] = VR(sh, te)
    return rd[i].frame(te)

# ------------------------------------------------------------------ captions (2 fonts, NO stroke, NO box)
FD = "/home/user/Saltow/video_editor/fonts"
SANS = {600: os.path.join(FD, "Montserrat-SemiBold.ttf"), 800: os.path.join(FD, "Montserrat-ExtraBold.ttf"),
        900: os.path.join(FD, "Montserrat-Black.ttf")}
SERIF = os.path.join(FD, "CormorantGaramond-SemiBoldItalic.ttf")
WHITE, CREAM, LIME = (255, 255, 255), (255, 255, 255), N.LIME
def T(text, t, kind="sans", size=58, w=800, color=WHITE): return (text, t, kind, size, w, color)
CAPS = [
    (1.06, 2.26, [[T("Мына", 1.06, size=54, w=600)], [T("жайнамаздардың", 1.62, size=74, w=900)]]),
    (2.28, 4.62, [[T("әдемілігі", 2.28, "serif", 110, color=CREAM)], [T("көздің жауын", 3.02, size=60), T("алады,", 3.92, size=60)]]),
    (4.22, 5.66, [[T("білем.", 4.22, "serif", 96, color=CREAM)]]),
    (5.72, 7.82, [[T("Мешіттің", 5.72, size=62, w=900)], [T("бейнесімен бейнеленген", 6.50, "serif", 84, color=CREAM)]]),
    (7.84, 10.30, [[T("5 түрлі түсте", 7.84, size=70, w=900)], [T("жайнамаз", 9.18, "serif", 100, color=LIME)]]),
    (10.46, 11.92, [[T("Қызыл десеңіз —", 10.46, size=56, w=800)], [T("қызыл түсі,", 11.38, "serif", 96, color=CREAM)]]),
    (12.02, 12.64, [[T("сары,", 12.02, size=92, w=900)]]),
    (12.68, 13.40, [[T("розовый,", 12.68, size=92, w=900)]]),
    (13.42, 14.50, [[T("көгілдір,", 13.42, size=92, w=900)]]),
    (14.52, 15.38, [[T("көмір түсімен.", 14.52, "serif", 104, color=CREAM)]]),
    (15.40, 17.12, [[T("Сапасы —", 15.40, size=64, w=900)], [T("енді сөз жоқ.", 16.34, "serif", 100, color=LIME)]]),
    (17.14, 19.82, [[T("Бұл жайнамаздар", 17.14, size=56, w=800)], [T("тоғыз мыңнан", 18.56, "serif", 96, color=CREAM)], [T("сатылған,", 19.28, size=56, w=800)]]),
    (19.84, 22.82, [[T("қазір де", 19.84, size=56, w=800)], [T("жеңілдікпен", 21.10, "serif", 100, color=LIME)], [T("бар болғаны", 21.84, size=56, w=800)]]),
    (22.84, 24.90, [[T("6 мың теңгеге", 22.84, size=78, w=900)], [T("алып кетесіз,", 23.80, "serif", 92, color=CREAM)]]),
    (24.92, 26.44, [[T("он данасы —", 24.92, "serif", 92, color=CREAM)], [T("6 000 теңге.", 25.58, size=82, w=900)]]),
    (27.26, 29.14, [[T("Ойланбай", 27.26, size=74, w=900)], [T("алып алыңыз,", 27.80, "serif", 96, color=CREAM)]]),
    (29.16, 31.20, [[T("сапасы —", 29.16, size=62, w=800)], [T("енді сөз жоқ.", 30.22, "serif", 104, color=LIME)]]),
]
_c = {}
class Spr:
    def __init__(self, im):
        a = np.asarray(im.convert("RGBA")).astype(np.float32)
        self.rgb = a[..., :3][..., ::-1].copy(); self.a = a[..., 3:4] / 255.0; self.h, self.w = a.shape[:2]
def spr(key, fn):
    if key not in _c: _c[key] = Spr(fn())
    return _c[key]
def blit(fr, s, cx, cy, scale=1.0, alpha=1.0):
    if alpha <= .003 or scale <= .02: return
    rgb, a, w, h = s.rgb, s.a, s.w, s.h
    if abs(scale - 1) > 1e-3:
        w, h = max(1, int(s.w * scale)), max(1, int(s.h * scale))
        rgb = cv2.resize(rgb, (w, h)); a = cv2.resize(a[..., 0], (w, h))[..., None]
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    fx0, fy0, fx1, fy1 = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if fx1 <= fx0 or fy1 <= fy0: return
    sa = a[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0] * alpha
    fr[fy0:fy1, fx0:fx1] = fr[fy0:fy1, fx0:fx1] * (1 - sa) + rgb[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0] * sa
def word(text, kind, size, w, color):
    def mk():
        f = ImageFont.truetype(SANS[w] if kind == "sans" else SERIF, size)
        bb = f.getbbox(text)
        im = Image.new("RGBA", (bb[2] - bb[0] + 60, int(size * 1.45) + 40), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((30 - bb[0], 20 + size * .08), text, font=f, fill=color + (255,))
        sh = Image.new("RGBA", im.size, (0, 0, 0, 255)); sh.putalpha(im.split()[3].point(lambda v: v * 215 // 255))
        sh = sh.filter(ImageFilter.GaussianBlur(16))          # soft drop shadow only (no stroke, no box)
        out = Image.new("RGBA", im.size, (0, 0, 0, 0)); out.alpha_composite(sh, (0, 5)); out.alpha_composite(im)
        return out
    return spr(("w", text, kind, size, w, color), mk)
def captions(fr, te, yc=1480):
    for a, b, lines in CAPS:
        if not (a - .02 <= te < b + .18): continue
        out = 1 - eio((te - b) / .18) if te > b else 1
        hs = [max(t[3] for t in ln) * 1.08 for ln in lines]
        y = yc - sum(hs) / 2
        for ln, lh in zip(lines, hs):
            ss = [word(t[0], t[2], t[3], t[4], t[5]) for t in ln]
            tot = sum(s.w - 60 for s in ss) + 18 * (len(ss) - 1); x = W / 2 - tot / 2
            for t, s in zip(ln, ss):
                d = te - t[1]
                if d >= 0:
                    k = eexpo(d / .4); big = t[3] >= 90
                    blit(fr, s, x + (s.w - 60) / 2, y + lh / 2 + (1 - k) * (26 if big else 16), (.92 + .08 * k) if big else 1, clamp(d / .18) * out)
                x += s.w - 60 + 18
            y += lh

# ------------------------------------------------------------------ minimal motion design
def fadeio(te, a, b, fin=.18, fout=.22):
    if te < a or te > b + fout: return 0
    return clamp((te - a) / fin) * (1 - eio((te - b) / fout) if te > b else 1)
def ln(fr, p0, p1, k, th=4, alpha=1.0, color=N.LIME):
    if k <= 0 or alpha <= 0: return
    x = p0[0] + (p1[0] - p0[0]) * k; y = p0[1] + (p1[1] - p0[1]) * k
    ov = fr.copy(); cv2.line(ov, (int(p0[0]), int(p0[1])), (int(x), int(y)), color[::-1], th, cv2.LINE_AA)
    cv2.addWeighted(ov, alpha, fr, 1 - alpha, 0, fr)
def ring(fr, c, r, k, alpha, th=4):
    if k <= 0: return
    ov = fr.copy(); cv2.ellipse(ov, (int(c[0]), int(c[1])), (int(r), int(r)), -90, 0, 360 * k, N.LIME[::-1], th, cv2.LINE_AA)
    cv2.addWeighted(ov, alpha, fr, 1 - alpha, 0, fr)

THUMBS = {}
def thumb(i):
    if i not in THUMBS:
        im = Image.open(os.path.join(B.G, f"p{i}.png")).crop((180, 280, 1440, 2600)).resize((196, 360), Image.LANCZOS)
        card = Image.new("RGBA", (196, 360)); m = Image.new("L", (196, 360), 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, 195, 359], radius=18, fill=255)
        card.paste(im.convert("RGBA"), (0, 0), m)
        THUMBS[i] = Spr(N.shadow(N.pad(card, 24), 16, 170, (0, 8)))
    return THUMBS[i]
SW = {"қызыл": (196, 36, 48), "сары": (205, 162, 60), "розовый": (200, 160, 150), "көгілдір": (150, 168, 185), "көмір": (35, 35, 38)}
def dot(name, active):
    def mk():
        im = Image.new("RGBA", (110, 110), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.ellipse([15, 15, 95, 95], fill=SW[name] + (255,), outline=(255, 255, 255, 255), width=4)
        if active: d.ellipse([5, 5, 105, 105], outline=N.LIME + (255,), width=4)
        return N.shadow(im, 8, 160, (0, 3))
    return spr(("dot", name, active), mk)

def motion(fr, te):
    # pointer to the mosque image
    a = fadeio(te, 6.2, 7.80)
    if a:
        c = (W * .5, 940); ring(fr, c, 330, eo((te - 6.2) / .6), a)
        ln(fr, (c[0] + 233, c[1] - 233), (c[0] + 330, c[1] - 380), eo((te - 6.6) / .35), 4, a)
        if te > 6.9: blit(fr, spr("lb1", lambda: N.label("мешіт бейнесі", 44)), c[0] + 300, c[1] - 430, 1, a * clamp((te - 6.9) / .2))
    # 5 colours collage (blurred background + 5 mats appear one by one, big "5")
    a = fadeio(te, 7.84, 10.30, .25, .3)
    if a:
        bg = cv2.GaussianBlur(fr, (0, 0), 25) * .45
        fr[:] = fr * (1 - a) + bg * a
        blit(fr, spr("five", lambda: N.big_text("5", 260, N.LIME, edge=False)), W / 2, 470, .85 + .15 * back((te - 7.9) / .4), a)
        blit(fr, spr("five_l", lambda: N.label("түрлі түс", 50)), W / 2, 640, 1, a * clamp((te - 8.3) / .2))
        order = [2, 3, 5, 1, 4]
        for j, i in enumerate(order):
            d = te - (8.0 + j * .16)
            if d < 0: continue
            x = W / 2 + (j - 2) * 205; y = 950 + (0 if j % 2 == 0 else 40)
            blit(fr, thumb(i), x, y + 80 * (1 - eo(d / .45)), 1, a * clamp(d / .2))
    # colour dots: light up as each colour is named
    names = [("қызыл", 10.46, 15.40), ("сары", 12.02, 15.40), ("розовый", 12.68, 15.40), ("көгілдір", 13.42, 15.40), ("көмір", 14.52, 15.40)]
    a = fadeio(te, 10.46, 15.35)
    if a:
        for j, (nm, t0, _) in enumerate(names):
            d = te - t0
            if d < 0: continue
            nxt = names[j + 1][1] if j + 1 < len(names) else 15.4
            active = t0 <= te < nxt
            blit(fr, dot(nm, active), W / 2 + (j - 2) * 120, 300, (1.12 if active else 1) * (.6 + .4 * back(d / .35)), a * clamp(d / .15))
    # price: was 9 000 -> now 6 000 for 10 pcs
    a = fadeio(te, 18.56, 26.44)
    if a:
        k9 = clamp((te - 18.56) / .25)
        s9 = spr("p9", lambda: N.big_text("9 000 ₸", 110, (235, 235, 235), edge=False))
        y9 = 520 if te < 22.84 else 520 - 120 * eo((te - 22.84) / .4)
        sc9 = 1 if te < 22.84 else 1 - .35 * eo((te - 22.84) / .4)
        blit(fr, s9, W / 2, y9, sc9, a * k9)
        if te >= 21.1:
            tw = s9.w * sc9 / 2 - 50
            ln(fr, (W / 2 - tw, y9 + 4), (W / 2 + tw, y9 - 10), eo((te - 21.1) / .35), 7, a, (232, 52, 66))
        if te >= 21.1 and te < 22.84:
            blit(fr, spr("disc", lambda: N.tag("жеңілдік", size=46)), W / 2, 660, back((te - 21.1) / .35), a)
        if te >= 22.84:
            p = eexpo((te - 22.84) / .7); p = 1 if p > .96 else p
            v = int(round((9000 + (6000 - 9000) * p) / 100) * 100); txt = f"{v:,}".replace(",", " ") + " ₸"
            blit(fr, spr(("p6", txt), lambda: N.big_text(txt, 190, N.LIME, edge=False)), W / 2, 600, .9 + .1 * back((te - 22.84) / .4), a * clamp((te - 22.84) / .12))
        if te >= 24.92:
            blit(fr, spr("ten", lambda: N.tag("10 ДАНА", size=56)), W / 2, 790, back((te - 24.92) / .35), a)
    # end card
    if te >= 31.25:
        d = te - 31.25
        fr *= 1 - .3 * eio(d / .5)
        blit(fr, spr("e1", lambda: N.big_text("6 000 ₸", 200, N.LIME, edge=False)), W / 2, 780, .9 + .1 * back(d / .4), clamp(d / .15))
        blit(fr, spr("e2", lambda: N.tag("10 ДАНА", size=56)), W / 2, 960, back((d - .25) / .35), clamp((d - .25) / .15))
        blit(fr, spr("e3", lambda: N.label("5 түрлі түс · мешіт бейнесі", 44)), W / 2, 1080, 1, clamp((d - .45) / .2))

# ------------------------------------------------------------------ render
def main(out):
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "15",
                            "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709",
                            "-colorspace", "bt709", out], stdin=subprocess.PIPE)
    yy = np.linspace(0, 1, H)[:, None, None].astype(np.float32)
    grade = (1 - .55 * np.clip((yy - .55) / .30, 0, 1) ** 1.1) * (1 - .12 * np.clip((.12 - yy) / .12, 0, 1))
    rd = {}
    for n in range(int(round(TOTAL * FPS))):
        te = n / FPS
        act = [i for i, sh in enumerate(SHOTS)
               if sh[2] - TRANS.get(sh[2], ("cut", 0))[1] / 2 <= te < sh[3] + TRANS.get(sh[3], ("cut", 0))[1] / 2]
        fs = {i: shot_frame(i, te, rd) for i in act}
        for i in list(rd):
            if i not in act: rd.pop(i).close()
        if len(act) == 1: fr = fs[act[0]]
        else:
            i, j = act[0], act[1]
            kind, dur = TRANS[SHOTS[i][3]]
            fr = B.transition(kind, clamp((te - (SHOTS[i][3] - dur / 2)) / dur), fs[i], fs[j])
        fr = fr * grade
        motion(fr, te)
        captions(fr, te)
        if te < .35: fr *= eo(te / .35)
        if te > TOTAL - .3: fr *= clamp((TOTAL - te) / .3)
        enc.stdin.write(np.clip(fr, 0, 255).astype(np.uint8).tobytes())
        if n % 150 == 0: print(f"{te:5.1f}s", flush=True)
    enc.stdin.close(); enc.wait()

if __name__ == "__main__":
    main(sys.argv[1])
