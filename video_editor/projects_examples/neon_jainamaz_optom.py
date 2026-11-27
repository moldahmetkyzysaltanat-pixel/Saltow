"""Prayer-mat wholesale reel — NEON LIME motion design + two-font (no outline) captions.
Main footage/voice: v1. Inserts: v2..v7. Edit times below are AFTER filler-pause removal."""
import math, os, subprocess, sys
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFilter, ImageFont
sys.path.insert(0, "/home/user/Saltow/video_editor")
sys.path.insert(0, "/tmp/claude-0/-home-user-Saltow/ff4d6f8e-eeda-5c24-9b8f-32a0a8602af8/scratchpad/p4/work")
import build as B
from vedit import neon as N

P = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B.G = os.path.join(P, "g")
B.CLIPFPS.update({"v7": 30, "v7d": 30})
W, H, FPS = 1080, 1920, 30
SEGS = [[0, 2.18], [2.62, 6.52], [7.12, 9.12], [9.42, 10.24], [10.88, 12.57], [13.31, 20.08], [20.87, 25.06]]
VOICE_LEN = sum(b - a for a, b in SEGS)          # 21.55
OUTRO = 1.30
TOTAL = VOICE_LEN + OUTRO
clamp, eo, eio, eexpo = B.clamp, B.eo, B.eio, B.eexpo
def back(x, k=1.70158): x = clamp(x); return 1 + (k + 1) * (x - 1) ** 3 + k * (x - 1) ** 2

S = B.S
SHOTS = [
    S("v1", 0.00, 2.40, 0.0, 1.0, z=(1.00, 1.08)),                       # WIDE  opening: wall of mats
    S("v7", 2.40, 4.00, 0.5, 1.0, z=(1.02, 1.08)),                       # MEDIUM stack + hand (4K)
    S("v1", 4.00, 5.95, 10.0, 1.0, z=(1.45, 1.52), pan=(-260, 0)),       # CLOSE tracking pan "қараңыз түстері"
    S("v5", 5.95, 6.65, 0.3, 1.0, z=(1.05, 1.10)),                       # DETAIL бордовый
    S("v2", 6.65, 7.25, 0.4, 1.0, z=(1.05, 1.10)),                       # DETAIL жасыл
    S("v6", 7.25, 8.10, 0.4, 1.0, z=(1.05, 1.10)),                       # DETAIL көк
    S("v4", 8.10, 8.95, 0.4, 1.0, z=(1.05, 1.10)),                       # DETAIL голубой
    S("v3", 8.95, 10.30, 0.5, 0.9, z=(1.04, 1.12)),                      # DETAIL ашық бордо
    S("v1", 10.30, 12.10, 14.0, 1.0, z=(1.14, 1.00)),                    # WIDE pull-back "барлығы бар"
    S("v7d", 12.10, 13.90, 1.0, 1.0, z=(1.00, 1.07)),                    # DETAIL 4K stack "оптом 800"
    S("v7", 13.90, 16.90, 2.0, 0.6, z=(1.10, 1.16)),                     # under interlude
    S("v1", 16.90, 18.30, 20.0, 1.0, z=(1.32, 1.40)),                    # CLOSE punch "үлгеріп қалыңыз"
    S("v6", 18.30, 19.70, 1.5, 0.7, z=(1.04, 1.10)),                     # DETAIL slow-mo "фотосын"
    S("v4", 19.70, VOICE_LEN, 1.2, 0.8, z=(1.02, 1.08)),                 # DETAIL "telegram"
    S("v2", VOICE_LEN, TOTAL, 1.5, 0.8, z=(1.00, 1.05)),                 # outro (under interlude)
]
TRANS = {2.40: ("zoom", .34), 4.00: ("whip_l", .30), 10.30: ("zoom", .34), 12.10: ("whip_r", .30),
         13.90: ("dissolve", .30), 16.90: ("dissolve", .30), 18.30: ("slide_up", .34),
         19.70: ("dissolve", .40), VOICE_LEN: ("dissolve", .40)}

# ------------------------------------------------------------------ sprites / drawing
class Spr:
    def __init__(self, im):
        a = np.asarray(im.convert("RGBA")).astype(np.float32)
        self.rgb = a[..., :3][..., ::-1].copy(); self.a = a[..., 3:4] / 255.0
        self.h, self.w = a.shape[:2]
_c = {}
def spr(key, fn):
    if key not in _c: _c[key] = Spr(fn())
    return _c[key]
def blit(fr, s, cx, cy, scale=1.0, alpha=1.0):
    if alpha <= 0.003 or scale <= 0.02: return
    rgb, a, w, h = s.rgb, s.a, s.w, s.h
    if abs(scale - 1) > 1e-3:
        w, h = max(1, int(s.w * scale)), max(1, int(s.h * scale))
        rgb = cv2.resize(rgb, (w, h)); a = cv2.resize(a[..., 0], (w, h))[..., None]
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    fx0, fy0, fx1, fy1 = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if fx1 <= fx0 or fy1 <= fy0: return
    sa = a[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0] * alpha
    fr[fy0:fy1, fx0:fx1] = fr[fy0:fy1, fx0:fx1] * (1 - sa) + rgb[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0] * sa
def fadeio(te, a, b, fin=.15, fout=.22):
    if te < a or te > b + fout: return 0
    return clamp((te - a) / fin) * (1 - eio((te - b) / fout) if te > b else 1)
def line(fr, p0, p1, k, th=5, alpha=1.0, color=N.LIME):
    if k <= 0 or alpha <= 0: return
    x = p0[0] + (p1[0] - p0[0]) * k; y = p0[1] + (p1[1] - p0[1]) * k
    ov = fr.copy(); cv2.line(ov, (int(p0[0]), int(p0[1])), (int(x), int(y)), color[::-1], th, cv2.LINE_AA)
    cv2.addWeighted(ov, alpha, fr, 1 - alpha, 0, fr)

# ------------------------------------------------------------------ captions: two fonts, NO outline
FD = "/home/user/Saltow/video_editor/fonts"
SANS = {600: os.path.join(FD, "Montserrat-SemiBold.ttf"), 800: os.path.join(FD, "Montserrat-ExtraBold.ttf"),
        900: os.path.join(FD, "Montserrat-Black.ttf")}
SERIF = os.path.join(FD, "CormorantGaramond-SemiBoldItalic.ttf")
WHITE, CREAM, LIME = (255, 255, 255), (255, 249, 238), N.LIME
def T(text, t, kind="sans", size=54, w=600, color=WHITE): return (text, t, kind, size, w, color)

CAPS = [
    (0.00, 1.84, [[T("Және де бізден", 0.00, size=50)], [T("«жиынға» деп", 1.00, "serif", 104, color=CREAM)]]),
    (1.86, 3.08, [[T("өте", 1.86, size=56), T("КӨП", 2.46, size=120, w=900)], [T("сұрайды:", 2.72, "serif", 92, color=CREAM)]]),
    (3.10, 4.56, [[T("қатты", 3.10, size=54)], [T("қымбат емес", 3.48, "serif", 104, color=LIME)], [T("жайнамаздар", 4.00, size=60, w=800)]]),
    (4.58, 5.95, [[T("бар ма? — деп.", 4.58, size=52)], [T("Қараңыз, түстері:", 5.02, "serif", 96, color=CREAM)]]),
    (5.98, 6.68, [[T("БОРДОВЫЙ", 5.98, size=112, w=900)]]),
    (6.70, 7.28, [[T("ЖАСЫЛ", 6.70, size=128, w=900)]]),
    (7.30, 8.17, [[T("КӨК", 7.30, size=140, w=900)]]),
    (8.19, 9.00, [[T("ГОЛУБОЙ", 8.19, size=120, w=900)]]),
    (9.02, 10.36, [[T("бордовыйдың", 9.02, size=64, w=800)], [T("ашығы", 9.66, "serif", 120, color=LIME)]]),
    (10.38, 11.64, [[T("барлығы", 10.38, "serif", 104, color=CREAM)], [T("БАР", 11.08, size=140, w=900)]]),
    (11.66, 13.94, [[T("бар болғаны", 11.66, size=52), T("оптом", 12.18, "serif", 84, color=LIME)],
                    [T("800 теңгеден", 12.98, size=96, w=900)]]),
    (13.96, 16.90, [[T("10 дана алсаңыз,", 13.96, size=54)], [T("барлығы небәрі", 15.00, "serif", 88, color=CREAM)],
                    [T("8 000 теңге", 15.50, size=100, w=900)]]),
    (17.36, 18.35, [[T("ҮЛГЕРІП", 17.36, size=120, w=900)], [T("қалыңыз!", 17.79, "serif", 104, color=LIME)]]),
    (18.37, 21.40, [[T("Фотосын", 18.37, size=56, w=800)], [T("Telegram-каналға", 19.83, "serif", 96, color=CREAM)],
                    [T("саламыз", 20.59, size=56, w=800)]]),
]

def word_spr(text, kind, size, w, color):
    def mk():
        f = ImageFont.truetype(SANS[w] if kind == "sans" else SERIF, size)
        bb = f.getbbox(text)
        im = Image.new("RGBA", (bb[2] - bb[0] + 60, int(size * 1.45) + 40), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((30 - bb[0], 20 + size * .08), text, font=f, fill=color + (255,))
        a = im.split()[3]
        sh = Image.new("RGBA", im.size, (0, 0, 0, 255)); sh.putalpha(a.point(lambda v: v * 120 // 255))
        sh = sh.filter(ImageFilter.GaussianBlur(12))
        out = Image.new("RGBA", im.size, (0, 0, 0, 0)); out.alpha_composite(sh, (0, 4)); out.alpha_composite(im)
        return out
    return spr(("w", text, kind, size, w, color), mk)

def frosted(fr, cx, cy, w, h, a):
    if a <= .01: return
    q = 4
    m = np.zeros((H // q, W // q), np.float32)
    m[max(0, int((cy - h / 2) / q)):int((cy + h / 2) / q), max(0, int((cx - w / 2) / q)):int((cx + w / 2) / q)] = 1
    m = cv2.resize(cv2.GaussianBlur(m, (0, 0), 70 / q), (W, H))[..., None] * a
    y0, y1 = max(0, int(cy - h / 2 - 220)), min(H, int(cy + h / 2 + 220))
    reg = fr[y0:y1]; mm = m[y0:y1]
    fr[y0:y1] = reg * (1 - mm) + cv2.GaussianBlur(reg, (0, 0), 18) * 0.40 * mm

def captions(fr, te, yc=1450):
    for a, b, lines in CAPS:
        if not (a - .02 <= te < b + .2): continue
        out = 1 - eio((te - b) / .2) if te > b else 1
        hs = [max(t[3] for t in ln) * 1.1 for ln in lines]
        sps = [[word_spr(t[0], t[2], t[3], t[4], t[5]) for t in ln] for ln in lines]
        widest = max(sum(s.w - 60 for s in ln) + 20 * (len(ln) - 1) for ln in sps)
        frosted(fr, W / 2, yc, min(W - 40, widest + 170), sum(hs) + 90, .85 * out * clamp((te - a) / .25))
        y = yc - sum(hs) / 2
        for ln, sl, lh in zip(lines, sps, hs):
            tot = sum(s.w - 60 for s in sl) + 20 * (len(sl) - 1)
            x = W / 2 - tot / 2
            for t, s in zip(ln, sl):
                d = te - t[1]
                if d >= 0:
                    k = eexpo(d / .42); big = t[3] >= 100
                    blit(fr, s, x + (s.w - 60) / 2, y + lh / 2 + (1 - k) * (30 if big else 18),
                         (.9 + .1 * k) if big else 1, clamp(d / .2) * out)
                x += s.w - 60 + 20
            y += lh

# ------------------------------------------------------------------ NEON motion design
COLORS = [(6.00, "бордо", (128, 22, 40)), (6.70, "жасыл", (22, 110, 60)), (7.30, "көк", (24, 34, 120)),
          (8.19, "голубой", (86, 140, 200)), (9.02, "ашық бордо", (176, 96, 104))]
def chip(name, rgb):
    wd = int(110 + N.font(N.XBOLD, 34).getlength(name))
    im = Image.new("RGBA", (wd, 96), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, wd - 1, 95], radius=22, fill=(22, 22, 22, 240), outline=N.LIME, width=3)
    d.rounded_rectangle([16, 18, 76, 78], radius=14, fill=rgb + (255,), outline=(255, 255, 255), width=2)
    d.text((92, 48), name, font=N.font(N.XBOLD, 34), fill=(255, 255, 255), anchor="lm")
    return N.glow(N.pad(im), radius=16, strength=.4)

INTERLUDES = [(13.90, 16.90), (VOICE_LEN, TOTAL)]
def interlude(fr, te):
    for a, b in INTERLUDES:
        if a - .2 <= te < b + .2:
            k = eio((te - a + .2) / .35) if b >= TOTAL else min(eio((te - a + .2) / .35), eio((b + .2 - te) / .35))
            fr[:] = fr * (1 - k) + N.interlude_bg(W, H, te) * k

def motion(fr, te):
    a = fadeio(te, .55, 1.84)
    if a: blit(fr, spr("h1", lambda: N.headline("жиынға", label="бізден сұрайды", size=140)), W / 2, 640,
               .85 + .15 * back((te - .55) / .38), a)
    a = fadeio(te, 2.46, 3.08)
    if a: blit(fr, spr("t2", lambda: N.tag("ӨТЕ КӨП", size=70)), W / 2, 700, back((te - 2.46) / .35), a)
    a = fadeio(te, 3.48, 4.56)
    if a:
        blit(fr, spr("h3", lambda: N.headline("қымбат", frame=True, size=140)), W / 2, 620, .85 + .15 * back((te - 3.48) / .38), a)
        if te >= 3.74:
            blit(fr, spr("t3", lambda: N.tag("ЕМЕС", color="red", size=64)), W / 2 + 230, 770, back((te - 3.74) / .3), a)
    a = fadeio(te, 5.02, 5.95)
    if a: blit(fr, spr("l4", lambda: N.label("қараңыз", 54)), W / 2, 560, 1, a)
    # palette: chips appear on every spoken colour, then "барлығы бар"
    a = fadeio(te, 5.95, 11.64)
    if a:
        blit(fr, spr("l5", lambda: N.label("түстері", 50)), W / 2, 300, 1, a)
        pos = [(W / 2 - 170, 420), (W / 2 + 170, 420), (W / 2 - 170, 540), (W / 2 + 170, 540), (W / 2, 660)]
        for (t0, nm, rgb), (x, y) in zip(COLORS, pos):
            d = te - t0
            if d >= 0:
                blit(fr, spr(("chip", nm), lambda nm=nm, rgb=rgb: chip(nm, rgb)), x, y + 24 * (1 - eo(d / .3)),
                     .85 + .15 * back(d / .35), clamp(d / .12) * a)
        if te >= 11.08:
            blit(fr, spr("t5", lambda: N.tag("БАРЛЫҒЫ БАР", size=56)), W / 2, 800, back((te - 11.08) / .35), a)
    # price 800 ₸
    a = fadeio(te, 12.18, 13.90)
    if a:
        blit(fr, spr("l6", lambda: N.label("оптом баға", 52)), W / 2, 520, 1, a)
        if te >= 12.98:
            p = eexpo((te - 12.98) / .6); p = 1 if p > .96 else p
            txt = f"{int(round(800 * p / 10) * 10)} ₸"
            blit(fr, spr(("c6", txt), lambda: N.big_text(txt, 220, N.LIME, edge=False)), W / 2, 720,
                 .9 + .1 * back((te - 12.98) / .4), a * clamp((te - 12.98) / .1))
    # interlude: 10 × 800 = 8 000 ₸
    a = fadeio(te, 13.96, 16.90)
    if a:
        blit(fr, spr("l7", lambda: N.label("көтерме", 50)), W / 2, 280, 1, a)
        blit(fr, spr("s7", lambda: N.stat_card("Жайнамаз", "· 800 ₸", "10 дана", "play")), W / 2,
             470 + 60 * (1 - eo((te - 13.96) / .45)), 1, a)
        d = te - 14.48
        if d > 0:
            ov = fr.copy(); k = eo(d / .4); L = 140
            cv2.line(ov, (W // 2, 620), (W // 2, int(620 + L * k)), N.LIME[::-1], 5, cv2.LINE_AA)
            if k > .8:
                cv2.line(ov, (W // 2 - 20, 620 + L - 22), (W // 2, 620 + L), N.LIME[::-1], 5, cv2.LINE_AA)
                cv2.line(ov, (W // 2 + 20, 620 + L - 22), (W // 2, 620 + L), N.LIME[::-1], 5, cv2.LINE_AA)
            cv2.addWeighted(ov, a, fr, 1 - a, 0, fr)
        if te >= 15.0:
            blit(fr, spr("l7b", lambda: N.label("небәрі", 46)), W / 2, 805, 1, a * clamp((te - 15) / .15))
        if te >= 15.5:
            p = eexpo((te - 15.5) / .7); p = 1 if p > .96 else p
            v = int(round(8000 * p / 100) * 100); txt = f"{v:,}".replace(",", " ") + " ₸"
            blit(fr, spr(("w7", txt), lambda: N.wallet_card("барлығы", "KZT", txt, cross=False)), W / 2,
                 1075 + 50 * (1 - eo((te - 15.5) / .45)), 1, a * clamp((te - 15.5) / .12))
    # urgency
    # urgency: thin lime timer bar draining while "үлгеріп қалыңыз" is said
    a = fadeio(te, 17.36, 18.30)
    if a:
        k = clamp((te - 17.40) / .9)
        line(fr, (W / 2 - 300, 1180), (W / 2 + 300, 1180), 1.0, 10, .35 * a, (255, 255, 255))
        line(fr, (W / 2 - 300, 1180), (W / 2 + 300 - 600 * k, 1180), 1.0, 10, a)
    # telegram
    a = fadeio(te, 18.37, VOICE_LEN)
    if a: blit(fr, spr("l9", lambda: N.label("барлық фотолар", 52)), W / 2, 520, 1, a)
    a = fadeio(te, 19.83, VOICE_LEN)
    if a: blit(fr, spr("s9", lambda: N.stat_card("Telegram", "· канал", "фото · баға", "telegram")), W / 2,
               720 + 60 * (1 - eo((te - 19.83) / .45)), .96 + .04 * eo((te - 19.83) / .45), a)
    # outro card
    if te >= VOICE_LEN + .05:
        d = te - VOICE_LEN - .05
        blit(fr, spr("oe1", lambda: N.label("оптом · 1 дана", 52)), W / 2, 700, 1, clamp(d / .15))
        blit(fr, spr("oe2", lambda: N.big_text("800 ₸", 240, N.LIME, edge=False)), W / 2, 880, .9 + .1 * back(d / .4), clamp(d / .12))
        blit(fr, spr("oe3", lambda: N.tag("10 дана — 8 000 ₸", size=52)), W / 2, 1090, back((d - .25) / .35), clamp((d - .25) / .12))
        blit(fr, spr("oe4", lambda: N.stat_card("Telegram", "· канал", "фото · баға", "telegram")), W / 2, 1320,
             .96 + .04 * eo((d - .45) / .4), clamp((d - .45) / .15))

# ------------------------------------------------------------------ render
def main(out):
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "15",
                            "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709",
                            "-colorspace", "bt709", out], stdin=subprocess.PIPE)
    yy = np.linspace(0, 1, H)[:, None, None].astype(np.float32)
    vig = (1 - 0.32 * np.clip((yy - .6) / .4, 0, 1)) * (1 - .2 * np.clip((.15 - yy) / .15, 0, 1))
    rd = {}
    for n in range(int(round(TOTAL * FPS))):
        te = n / FPS
        act = [i for i, sh in enumerate(SHOTS)
               if sh["a"] - TRANS.get(sh["a"], ("cut", 0))[1] / 2 <= te < sh["b"] + TRANS.get(sh["b"], ("cut", 0))[1] / 2]
        fs = {}
        for i in act:
            if i not in rd: rd[i] = B.Reader(SHOTS[i]["clip"], B.src_time(SHOTS[i], te - SHOTS[i]["a"]) - .05)
            fs[i] = B.frame_of(SHOTS[i], te, rd[i])
        for i in list(rd):
            if i not in act: rd.pop(i).close()
        if len(act) == 1: fr = fs[act[0]]
        else:
            i, j = act[0], act[1]
            kind, dur = TRANS[SHOTS[i]["b"]]
            fr = B.transition(kind, clamp((te - (SHOTS[i]["b"] - dur / 2)) / dur), fs[i], fs[j])
        fr = fr * vig
        interlude(fr, te)
        motion(fr, te)
        captions(fr, te)
        if te < .5:
            m = eo(te / .5); h2 = int(H / 2 * m); mask = np.zeros((H, 1, 1), np.float32); mask[H // 2 - h2:H // 2 + h2] = 1
            fr = fr * mask
        if te > TOTAL - .35: fr *= clamp((TOTAL - te) / .35)
        enc.stdin.write(np.clip(fr, 0, 255).astype(np.uint8).tobytes())
        if n % 150 == 0: print(f"{te:5.1f}s", flush=True)
    enc.stdin.close(); enc.wait()

if __name__ == "__main__":
    main(sys.argv[1])
