"""Prayer-mat sale reel re-cut in the saved NEON LIME style.
Footage/transitions from build.py; overlays = neon captions + neon motion design."""
import math, os, subprocess, sys
import numpy as np, cv2
sys.path.insert(0, "/home/user/Saltow/video_editor")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import premium_reels_jainamaz as B   # footage + transitions of the editorial cut
from vedit import neon as N
from PIL import Image

W, H, FPS, TOTAL = B.W, B.H, B.FPS, B.TOTAL
clamp, eo, eio, eexpo = B.clamp, B.eo, B.eio, B.eexpo
def back(x, k=1.70158):
    x = clamp(x); return 1 + (k + 1) * (x - 1) ** 3 + k * (x - 1) ** 2

# --- the Safi moment: new 4K/120fps product clip, elegant slow motion
B.CLIPFPS["safi_new"] = 120
for sh in B.SHOTS:
    if sh["clip"] == "safi_bottle":
        sh.update(clip="safi_new", s0=0.45, speed=0.75, z=(1.0, 1.08), pan=(0, 0))

# ------------------------------------------------------------------ sprites
class Spr:
    def __init__(self, im):
        a = np.asarray(im.convert("RGBA")).astype(np.float32)
        self.rgb = a[..., :3][..., ::-1].copy(); self.a = a[..., 3:4] / 255.0
        self.h, self.w = a.shape[:2]
_cache = {}
def spr(key, fn):
    if key not in _cache: _cache[key] = Spr(fn())
    return _cache[key]

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

def lime_line(fr, p0, p1, k, th=5, alpha=1.0, color=N.LIME):
    if k <= 0 or alpha <= 0: return
    x = p0[0] + (p1[0] - p0[0]) * k; y = p0[1] + (p1[1] - p0[1]) * k
    ov = fr.copy(); cv2.line(ov, (int(p0[0]), int(p0[1])), (int(x), int(y)), color[::-1], th, cv2.LINE_AA)
    cv2.addWeighted(ov, alpha, fr, 1 - alpha, 0, fr)

# ------------------------------------------------------------------ captions (neon karaoke)
WORDS = [("Бізге",0.00),("дүкенге",0.38),("келіп,",0.96),("сіздерде",1.40),("арзан",1.78),("жайнамаздар",2.10),
 ("бар",2.84),("ма?",3.02),("—",3.30),("деп",3.34),("сұрайтындар",3.56),("өте",4.06),("көп.",4.38),
 ("Қараңыздар,",4.86),("қандай",5.70),("жайнамаздарды",6.44),("акцияға",7.26),("бердік!",7.88),
 ("Қазір",8.44),("бізге",9.04),("Safi",9.72),("өнімдері",10.12),("келе",10.70),("жатыр,",10.90),
 ("барынша",11.42),("орын",11.96),("босату",12.22),("керек.",12.74),
 ("Бірақ",13.06),("жайнамаздардың",13.42),("барлығы",14.48),("4 500-ден,",15.06),("3 500-ден",16.36),
 ("сатылған,",17.56),("сапасы",18.08),("өте",18.94),("күшті",19.26),("жайнамаздар.",19.72),
 ("Қазір",21.92),("барлығы",22.76),("1 800",23.40),("теңге.",24.18),
 ("10",24.70),("дана",25.64),("алсаңыз,",25.92),("18 000-ға",26.56),("аласыз,",27.26),
 ("өзіңіз",28.52),("қалаған",29.22),("бағаға",29.54),("сата",29.92),("бере",30.18),("аласыз.",30.44),
 ("Барлығы",31.08),("түрік",31.66),("өнімі,",31.95),("қараңызшы,",32.28),("әдемі",33.08),("түрлері",33.50),("бар!",33.82),
 ("Барлығының",34.69),("суретін",35.22),("алғыңыз",35.74),("келсе,",37.12),("Telegram-ға",37.46),
 ("салатын",38.08),("боламыз.",38.52)]
WORDS = [(w, t) for w, t in WORDS if w != "—"]
KEY = {"арзан", "көп.", "акцияға", "Safi", "орын", "босату", "күшті", "1 800", "18 000-ға", "түрік", "әдемі", "Telegram-ға"}

def pages():
    out, cur = [], []
    for i, (w, t) in enumerate(WORDS):
        txt = " ".join(x[0] for x in cur + [(w, t)])
        if cur and (len(cur) >= 3 or len(txt) > 22 or cur[-1][0][-1] in ".?!,"):
            out.append(cur); cur = []
        cur.append((w, t))
    if cur: out.append(cur)
    res = []
    for j, p in enumerate(out):
        start = p[0][1]
        nxt = out[j + 1][0][1] if j + 1 < len(out) else TOTAL - 1.4
        end = min(nxt, p[-1][1] + 1.2)
        res.append((start, end, p))
    return res
PAGES = pages()

def word_img(text, lime):
    from PIL import ImageDraw
    f = N.font(N.BLACK, 78)
    t = text.upper()
    bb = f.getbbox(t)
    im = Image.new("RGBA", (bb[2] - bb[0] + 40, 120), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((20 - bb[0], 18), t, font=f, fill=N.LIME if lime else N.WHITE,
                            stroke_width=4, stroke_fill=(16, 16, 16))
    im = N.shadow(N.pad(im, 20), 10, 170, (0, 5))
    return N.glow(im, radius=12, strength=0.4) if lime else im

def draw_captions(fr, te, y=1470):
    for (a, b, p) in PAGES:
        if not (a <= te < b + .12): continue
        out = 1 - eio((te - b) / .12) if te > b else 1
        imgs = []
        for w, t in p:
            active = t <= te < (p[p.index((w, t)) + 1][1] if p.index((w, t)) + 1 < len(p) else b)
            lime = active or w in KEY
            imgs.append(spr(("cap", w, lime), lambda w=w, lime=lime: word_img(w, lime)))
        # two lines max
        lines, cur, wsum = [], [], 0
        for i, s in enumerate(imgs):
            if cur and wsum + s.w - 40 > 960:
                lines.append(cur); cur, wsum = [], 0
            cur.append(i); wsum += s.w - 40
        lines.append(cur)
        yy = y - (len(lines) - 1) * 50
        for ln in lines:
            tot = sum(imgs[i].w - 40 for i in ln) + 16 * (len(ln) - 1)
            x = W / 2 - tot / 2
            for i in ln:
                d = te - p[i][1]
                if d >= 0:
                    s = imgs[i]
                    sc = 1.0 + 0.08 * (1 - eo(d / .18)) if d < .18 else 1.0
                    blit(fr, s, x + (s.w - 40) / 2, yy + 8 * (1 - eo(d / .15)), sc, clamp(d / .08) * out)
                x += imgs[i].w - 40 + 16
            yy += 100

# ------------------------------------------------------------------ motion design
def fadeio(te, a, b, fin=.15, fout=.25):
    if te < a or te > b + fout: return 0
    return clamp((te - a) / fin) * (1 - eio((te - b) / fout) if te > b else 1)

INTERLUDES = [(24.62, 27.94), (39.25, TOTAL)]

def interlude(fr, te):
    for a, b in INTERLUDES:
        if a - .2 <= te < b + .2:
            k = min(eio((te - a + .2) / .35), eio((b + .2 - te) / .35)) if b < TOTAL else eio((te - a + .2) / .35)
            fr[:] = fr * (1 - k) + N.interlude_bg(W, H, te) * k

def money_strike(fr, txt, cx, cy, k, alpha):
    s = spr(("old", txt), lambda: N.big_text(txt, 74, (225, 225, 225), edge=True))
    blit(fr, s, cx, cy, 1, alpha)
    lime_line(fr, (cx - s.w / 2 + 50, cy + 5), (cx + s.w / 2 - 50, cy - 8), k, 7, alpha, N.RED)

def motion(fr, te):
    # 1 · "арзан жайнамаздар бар ма?" — framed headline
    a = fadeio(te, 1.78, 3.30)
    if a: blit(fr, spr("h1", lambda: N.headline("арзан", label="сіздерде", accent="?", size=150)),
               W / 2, 800, .85 + .15 * back((te - 1.78) / .38), a)
    # 2 · "сұрайтындар өте көп"
    a = fadeio(te, 3.40, 4.84)
    if a: blit(fr, spr("l2", lambda: N.label("сұрайтындар")), W / 2, 760, 1, a)
    a = fadeio(te, 4.06, 4.84)
    if a: blit(fr, spr("t2", lambda: N.tag("ӨТЕ КӨП", size=72)), W / 2, 880, back((te - 4.06) / .35), a)
    # 3 · "акцияға бердік"
    a = fadeio(te, 4.90, 8.36)
    if a: blit(fr, spr("l3", lambda: N.label("қараңыздар")), W / 2, 640, 1, a)
    a = fadeio(te, 7.26, 8.36)
    if a: blit(fr, spr("h3", lambda: N.headline("акция", frame=True, size=150)), W / 2, 800, .85 + .15 * back((te - 7.26) / .38), a)
    # 4 · Safi
    a = fadeio(te, 9.72, 11.20)
    if a: blit(fr, spr("h4", lambda: N.headline("SAFI", label="жаңа өнімдер", size=170)), W / 2, 700, .85 + .15 * back((te - 9.72) / .38), a)
    a = fadeio(te, 10.12, 11.20)
    if a: blit(fr, spr("t4", lambda: N.tag("келе жатыр", size=52)), W / 2, 900, back((te - 10.12) / .35), a)
    # 5 · "орын босату керек"
    a = fadeio(te, 11.96, 13.02)
    if a: blit(fr, spr("h5", lambda: N.headline("орын", label="барынша", size=150)), W / 2, 760, .85 + .15 * back((te - 11.96) / .38), a)
    a = fadeio(te, 12.22, 13.02)
    if a: blit(fr, spr("t5", lambda: N.tag("босату керек", size=56)), W / 2, 960, back((te - 12.22) / .35), a)
    # 6 · old prices card
    a = fadeio(te, 14.40, 18.02)
    if a:
        blit(fr, spr("l6", lambda: N.label("бұрынғы баға")), W / 2, 520, 1, a)
        blit(fr, spr("s6", lambda: N.stat_card("Жайнамаз", "· бұрын", "4 500 ₸", "play")), W / 2,
             700 + 60 * (1 - eo((te - 14.4) / .45)), 1, a)
    a = fadeio(te, 16.36, 18.02)
    if a: blit(fr, spr("s6b", lambda: N.stat_card("Жайнамаз", "· бұрын", "3 500 ₸", "play")), W / 2,
               960 + 60 * (1 - eo((te - 16.36) / .45)), 1, a)
    # 7 · quality checklist
    a = fadeio(te, 18.08, 20.48)
    if a:
        blit(fr, spr("cf7", lambda: N.checklist_frame(2)), W / 2, 820, .9 + .1 * back((te - 18.08) / .35), a)
        blit(fr, spr("ct7", lambda: N.tag("сапасы", size=38)), W / 2 - 200, 690, back((te - 18.08) / .35), a)
        for j, (t0, txt) in enumerate(((18.94, "өте күшті"), (19.72, "жайнамаздар"))):
            d = te - t0
            if d >= 0:
                blit(fr, spr(("r7", txt), lambda txt=txt: N.check_row(txt, True)), W / 2 + (1 - eo(d / .3)) * -60,
                     760 + j * 104, 1, clamp(d / .12) * a)
    # 8 · HERO price (soft dark band so lime reads on white mats)
    a = fadeio(te, 21.95, 24.62)
    if a:
        yy = np.arange(H, dtype=np.float32)[:, None, None]
        band = np.exp(-((yy - 760) / 330) ** 4) * 0.62 * a
        fr *= 1 - band
        blit(fr, spr("l8", lambda: N.label("қазір барлығы")), W / 2, 520, 1, a)
        k = clamp((te - 22.3) / .3)
        money_strike(fr, "4 500 ₸", W / 2 - 200, 650, eo((te - 22.6) / .3), a * k)
        money_strike(fr, "3 500 ₸", W / 2 + 200, 650, eo((te - 22.75) / .3), a * k)
        if te >= 23.30:
            p = eexpo((te - 23.30) / .7); p = 1 if p > .96 else p
            v = int(round((4500 + (1800 - 4500) * p) / 50) * 50)
            txt = f"{v:,}".replace(",", " ") + " ₸"
            blit(fr, spr(("cnt", txt), lambda: N.big_text(txt, 210, N.LIME, edge=False)), W / 2, 880,
                 .9 + .1 * back((te - 23.3) / .4), a * clamp((te - 23.3) / .12))
        a2 = fadeio(te, 24.18, 24.62)
        if a2: blit(fr, spr("t8", lambda: N.tag("АКЦИЯ", size=56)), W / 2, 1090, back((te - 24.18) / .3), a2)
    # 9 · interlude: 10 pcs -> 18 000 ₸
    a = fadeio(te, 24.75, 27.94)
    if a:
        blit(fr, spr("l9", lambda: N.label("көтерме баға")), W / 2, 330, 1, a)
        blit(fr, spr("s9", lambda: N.stat_card("Жайнамаз", "· 1 800 ₸", "10 дана", "play")), W / 2,
             520 + 60 * (1 - eo((te - 24.75) / .45)), 1, a)
        d = te - 25.9
        if d > 0:
            L = 150; k = eo(d / .4); ov = fr.copy()
            cv2.line(ov, (W // 2, 680), (W // 2, int(680 + L * k)), N.LIME[::-1], 5, cv2.LINE_AA)
            if k > .8:
                cv2.line(ov, (W // 2 - 20, 680 + L - 22), (W // 2, 680 + L), N.LIME[::-1], 5, cv2.LINE_AA)
                cv2.line(ov, (W // 2 + 20, 680 + L - 22), (W // 2, 680 + L), N.LIME[::-1], 5, cv2.LINE_AA)
            cv2.addWeighted(ov, a, fr, 1 - a, 0, fr)
        if te >= 26.50:
            blit(fr, spr("w9", lambda: N.wallet_card("барлығы", "KZT", "18 000 ₸", cross=False)), W / 2,
                 1040 + 60 * (1 - eo((te - 26.5) / .45)), .96 + .04 * eo((te - 26.5) / .45), a * clamp((te - 26.5) / .15))
    # 10 · resell at your price
    a = fadeio(te, 28.52, 31.04)
    if a: blit(fr, spr("l10", lambda: N.label("өзіңіз қалаған бағаға")), W / 2, 700, 1, a)
    a = fadeio(te, 29.92, 31.04)
    if a: blit(fr, spr("h10", lambda: N.headline("сата бересіз", size=118)), W / 2, 860, .85 + .15 * back((te - 29.92) / .38), a)
    # 11 · Turkish + beautiful
    a = fadeio(te, 31.66, 34.0)
    if a: blit(fr, spr("t11", lambda: N.tag("ТҮРІК ӨНІМІ", size=66)), W / 2, 760, back((te - 31.66) / .35), a)
    a = fadeio(te, 33.08, 34.0)
    if a: blit(fr, spr("r11", lambda: N.check_row("әдемі түрлер", True)), W / 2 + (1 - eo((te - 33.08) / .3)) * -60, 900, 1, a)
    # 12 · Telegram
    a = fadeio(te, 35.0, 39.25)
    if a: blit(fr, spr("l12", lambda: N.label("барлығының суреті")), W / 2, 640, 1, a)
    a = fadeio(te, 37.40, 39.25)
    if a: blit(fr, spr("s12", lambda: N.stat_card("Telegram", "· канал", "барлық суреттер", "telegram")), W / 2,
               840 + 60 * (1 - eo((te - 37.4) / .45)), .96 + .04 * eo((te - 37.4) / .45), a)
    # 13 · end card (on interlude)
    if te >= 39.30:
        d = te - 39.30
        blit(fr, spr("le", lambda: N.label("барлық жайнамаздар")), W / 2, 680, 1, clamp(d / .15))
        blit(fr, spr("he", lambda: N.big_text("1 800 ₸", 220, N.LIME, edge=False)), W / 2, 860, .9 + .1 * back(d / .4), clamp(d / .12))
        blit(fr, spr("te", lambda: N.tag("10 дана — 18 000 ₸", size=50)), W / 2, 1060, back((d - .3) / .35), clamp((d - .3) / .12))

# ------------------------------------------------------------------ render
def main(out):
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "15",
                            "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709",
                            "-colorspace", "bt709", out], stdin=subprocess.PIPE)
    readers = {}
    n0, n1 = 0, int(round(TOTAL * FPS))
    if len(sys.argv) > 3: n0, n1 = int(float(sys.argv[2]) * FPS), int(float(sys.argv[3]) * FPS)
    vig = B.TOPG * (1 - 0.30 * np.clip((np.linspace(0, 1, H)[:, None, None] - 0.62) / 0.38, 0, 1))
    for n in range(n0, n1):
        te = n / FPS
        active = [i for i, sh in enumerate(B.SHOTS)
                  if sh["a"] - B.TRANS.get(sh["a"], ("cut", 0))[1] / 2 <= te < sh["b"] + B.TRANS.get(sh["b"], ("cut", 0))[1] / 2]
        frames = {}
        for i in active:
            if i not in readers:
                readers[i] = B.Reader(B.SHOTS[i]["clip"], B.src_time(B.SHOTS[i], te - B.SHOTS[i]["a"]) - 0.05)
            frames[i] = B.frame_of(B.SHOTS[i], te, readers[i])
        for i in list(readers):
            if i not in active: readers.pop(i).close()
        if len(active) == 1:
            fr = frames[active[0]]
        else:
            i, j = active[0], active[1]
            kind, dur = B.TRANS[B.SHOTS[i]["b"]]
            fr = B.transition(kind, clamp((te - (B.SHOTS[i]["b"] - dur / 2)) / dur), frames[i], frames[j])
        fr = fr * vig
        interlude(fr, te)
        motion(fr, te)
        draw_captions(fr, te)
        if te < 0.3: fr *= eo(te / 0.3)
        if te > TOTAL - 0.35: fr *= clamp((TOTAL - te) / 0.35)
        enc.stdin.write(np.clip(fr, 0, 255).astype(np.uint8).tobytes())
        if n % 150 == 0: print(f"{te:5.1f}s", flush=True)
    enc.stdin.close(); enc.wait()

if __name__ == "__main__":
    main(sys.argv[1])
