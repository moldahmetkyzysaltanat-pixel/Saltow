"""Chat-dialogue reel (NEON style): two messages over the prayer-mat stacking clip + end card."""
import math, os, subprocess, sys
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFilter, ImageFont
sys.path.insert(0, "/home/user/Saltow/video_editor")
from vedit import neon as N

P = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H, FPS = 1080, 1920, 30
TOTAL = 13.2
FD = "/home/user/Saltow/video_editor/fonts"
F_SEMI = os.path.join(FD, "Montserrat-SemiBold.ttf"); F_XB = os.path.join(FD, "Montserrat-ExtraBold.ttf")

def clamp(x, a=0., b=1.): return max(a, min(b, x))
def eo(x): x = clamp(x); return 1 - (1 - x) ** 3
def eio(x): x = clamp(x); return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def back(x, k=1.9): x = clamp(x); return 1 + (k + 1) * (x - 1) ** 3 + k * (x - 1) ** 2

MSG1 = "1000тг ғана бар, оған жайнамаз келмейтін шығар?!..."
MSG2 = "@zamzam_muslim_products дүкенінде даже 800тгден жайнамаздар бар досым!"
T_TYPE1, T_MSG1 = 0.35, 1.25
T_TYPE2, T_MSG2 = 4.10, 5.10
T_END = 10.9

# ------------------------------------------------------------------ bubble rendering
def wrap(text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if font.getlength(t) <= maxw or not cur: cur = t
        else: lines.append(cur); cur = w
    lines.append(cur); return lines

def bubble(text, mine):
    f = ImageFont.truetype(F_SEMI, 50); fb = ImageFont.truetype(F_XB, 50)
    lines = wrap(text, f, 760)
    lh = 66
    w = int(max(f.getlength(l) for l in lines)) + 76
    h = lh * len(lines) + 56
    pad = 40
    im = Image.new("RGBA", (w + 2 * pad, h + 2 * pad + 20), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    fill = N.LIME + (255,) if mine else (32, 32, 34, 238)
    fg = (14, 14, 14) if mine else (255, 255, 255)
    x0, y0 = pad, pad
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=38, fill=fill)
    # tail
    if mine: d.polygon([(x0 + w - 40, y0 + h - 30), (x0 + w + 18, y0 + h + 14), (x0 + w - 6, y0 + h - 4)], fill=fill)
    else: d.polygon([(x0 + 40, y0 + h - 30), (x0 - 18, y0 + h + 14), (x0 + 6, y0 + h - 4)], fill=fill)
    y = y0 + 28
    for l in lines:
        x = x0 + 38
        for i, word in enumerate(l.split(" ")):
            ff = fb if word.startswith("@") or "800" in word else f
            col = ((20, 70, 10) if mine else N.LIME) if word.startswith("@") else fg
            if word.startswith("@") and mine: col = (0, 0, 0)
            d.text((x, y), word, font=ff, fill=col)
            if word.startswith("@"):          # underline the handle like a link
                d.line([(x, y + 56), (x + ff.getlength(word), y + 56)], fill=col, width=3)
            x += ff.getlength(word + " ")
        y += lh
    # time + ticks
    st = ImageFont.truetype(F_SEMI, 24)
    tc = (40, 60, 20) if mine else (150, 150, 150)
    tx = x0 + w - (78 if mine else 24)
    d.text((tx, y0 + h - 10), "12:48" if mine else "12:47", font=st, fill=tc, anchor="rb")
    if mine:   # double read-tick
        for k in (0, 14):
            bx = x0 + w - 62 + k; by = y0 + h - 22
            d.line([(bx, by), (bx + 7, by + 7), (bx + 20, by - 8)], fill=tc, width=3)
    out = N.shadow(im, 22, 170, (0, 10))
    return out.filter(ImageFilter.SMOOTH) if False else out

def typing(mine):
    im = Image.new("RGBA", (230, 140), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    fill = N.LIME + (255,) if mine else (32, 32, 34, 238)
    d.rounded_rectangle([30, 25, 200, 115], radius=40, fill=fill)
    return im

def header():
    w, h = 980, 150
    im = Image.new("RGBA", (w + 60, h + 60), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([30, 30, 30 + w, 30 + h], radius=40, fill=(20, 20, 22, 235), outline=(70, 70, 70), width=2)
    d.ellipse([60, 55, 160, 155], fill=(70, 120, 200))
    d.text((110, 105), "Д", font=ImageFont.truetype(F_XB, 48), fill=(255, 255, 255), anchor="mm")
    d.ellipse([140, 132, 162, 154], fill=(60, 220, 100), outline=(20, 20, 22), width=4)
    d.text((190, 72), "Досым", font=ImageFont.truetype(F_XB, 44), fill=(255, 255, 255))
    d.text((190, 128), "online", font=ImageFont.truetype(F_SEMI, 30), fill=N.LIME)
    d.text((w - 20, 105), "• • •", font=ImageFont.truetype(F_XB, 34), fill=(160, 160, 160), anchor="rm")
    return N.shadow(im, 20, 160, (0, 8))

def ig_card():
    f1 = ImageFont.truetype(F_SEMI, 34); f2 = ImageFont.truetype(F_XB, 50)
    handle = "@zamzam_muslim_products"
    w = int(200 + f2.getlength(handle) + 50); h = 220
    im = Image.new("RGBA", (w + 80, h + 80), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([40, 40, 40 + w, 40 + h], radius=34, fill=(24, 24, 24, 245), outline=(68, 68, 68), width=2)
    im.alpha_composite(N._instagram(130), (70, 85))
    d.text((230, 88), "Instagram", font=f1, fill=(200, 200, 200))
    d.text((230 + f1.getlength("Instagram ") + 6, 92), "· дүкен", font=ImageFont.truetype(F_SEMI, 30), fill=N.LIME)
    d.text((230, 150), handle, font=f2, fill=(255, 255, 255))
    return N.shadow(im, 24, 160)

class Spr:
    def __init__(self, im):
        a = np.asarray(im.convert("RGBA")).astype(np.float32)
        self.rgb = a[..., :3][..., ::-1].copy(); self.a = a[..., 3:4] / 255.0; self.h, self.w = a.shape[:2]
_c = {}
def spr(k, fn):
    if k not in _c: _c[k] = Spr(fn())
    return _c[k]
def blit_at(fr, s, x0, y0, scale=1.0, alpha=1.0, ox=0.0, oy=1.0):
    """place sprite with its (ox, oy) relative anchor at (x0, y0); scale around that anchor."""
    if alpha <= .003 or scale <= .02: return
    rgb, a, w, h = s.rgb, s.a, s.w, s.h
    if abs(scale - 1) > 1e-3:
        w, h = max(1, int(s.w * scale)), max(1, int(s.h * scale))
        rgb = cv2.resize(rgb, (w, h)); a = cv2.resize(a[..., 0], (w, h))[..., None]
    x, y = int(round(x0 - ox * w)), int(round(y0 - oy * h))
    fx0, fy0, fx1, fy1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if fx1 <= fx0 or fy1 <= fy0: return
    sa = a[fy0 - y:fy1 - y, fx0 - x:fx1 - x] * alpha
    fr[fy0:fy1, fx0:fx1] = fr[fy0:fy1, fx0:fx1] * (1 - sa) + rgb[fy0 - y:fy1 - y, fx0 - x:fx1 - x] * sa
def blit_c(fr, s, cx, cy, scale=1.0, alpha=1.0): blit_at(fr, s, cx, cy, scale, alpha, .5, .5)

def dots(fr, te, t0, x, y, mine):
    """typing indicator: bubble + 3 bouncing dots."""
    d = te - t0
    s = spr(("typ", mine), lambda: typing(mine))
    sc = .7 + .3 * back(d / .3)
    blit_at(fr, s, x, y, sc, clamp(d / .12), 1.0 if mine else 0.0, 1.0)
    cx0 = x - 115 * sc if mine else x + 115 * sc
    col = (20, 20, 20) if mine else (200, 200, 200)
    for i in range(3):
        ph = math.sin(te * 9 - i * .9)
        cv2.circle(fr, (int(cx0 + (i - 1) * 36 * sc), int(y - 70 * sc - 8 * max(0, ph))), int(11 * sc), col[::-1], -1, cv2.LINE_AA)

def overlay(fr, te):
    # soft top-darkening so the chat reads on the bright shelf
    # header
    if te >= .1:
        d = te - .1
        hd = spr("hdr", header)
        blit_c(fr, hd, W / 2, 190 - 40 * (1 - eo(d / .45)), 1, clamp(d / .25) * (1 - eio((te - T_END) / .35)))
    end_out = 1 - eio((te - T_END) / .35) if te > T_END else 1
    # message 1 (left)
    b1 = spr("b1", lambda: bubble(MSG1, False))
    y1 = 600 if te < T_MSG2 else 600 - 40 * eo((te - T_MSG2) / .4)
    if T_TYPE1 <= te < T_MSG1:
        dots(fr, te, T_TYPE1, 50, y1, False)
    if te >= T_MSG1:
        d = te - T_MSG1
        blit_at(fr, b1, 20, y1 + 30, .6 + .4 * back(d / .35), clamp(d / .1) * end_out, 0.0, 1.0)
    # message 2 (right)
    b2 = spr("b2", lambda: bubble(MSG2, True))
    y2 = 640 + b2.h - 40
    if T_TYPE2 <= te < T_MSG2:
        dots(fr, te, T_TYPE2, W - 50, 860, True)
    if te >= T_MSG2:
        d = te - T_MSG2
        blit_at(fr, b2, W - 20, y2, .6 + .4 * back(d / .35), clamp(d / .1) * end_out, 1.0, 1.0)
    # emphasis: "800 ₸" sticker pops onto the stack after the reply is read
    if 7.3 <= te < T_END + .3:
        d = te - 7.3
        s = spr("p800", lambda: N.big_text("800 ₸", 170, N.LIME, edge=False))
        blit_c(fr, s, W / 2 + 170, 1330, .8 + .2 * back(d / .4), clamp(d / .12) * end_out)
        t = spr("from", lambda: N.tag("-ДЕН БАСТАП", size=40))
        blit_c(fr, t, W / 2 + 170, 1460, back((d - .2) / .35), clamp((d - .2) / .12) * end_out)
    # end card
    if te >= T_END:
        d = te - T_END
        k = eio(d / .45)
        fr[:] = fr * (1 - .62 * k)
        blit_c(fr, spr("e0", lambda: N.label("жайнамаздар", 48)), W / 2, 700, 1, clamp((d - .1) / .2))
        blit_c(fr, spr("e1", lambda: N.big_text("800 ₸", 230, N.LIME, edge=False)), W / 2, 880, .9 + .1 * back(d / .4), clamp(d / .15))
        blit_c(fr, spr("e2", lambda: N.tag("-ДЕН БАСТАП", size=50)), W / 2, 1050, back((d - .2) / .35), clamp((d - .2) / .12))
        blit_c(fr, spr("e3", ig_card), W / 2, 1290,
               .96 + .04 * eo((d - .4) / .4), clamp((d - .4) / .15))

class Reader:
    def __init__(self, path):
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                                  stdout=subprocess.PIPE, bufsize=10 ** 8); self.last = None
    def next(self):
        b = self.p.stdout.read(W * H * 3)
        if len(b) == W * H * 3: self.last = np.frombuffer(b, np.uint8).reshape(H, W, 3)
        return self.last

def main(out):
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "15",
                            "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709",
                            "-colorspace", "bt709", out], stdin=subprocess.PIPE)
    rd = Reader(os.path.join(P, "g", "v.mp4"))
    yy = np.linspace(0, 1, H)[:, None, None].astype(np.float32)
    shade = 1 - .38 * np.clip((.55 - yy) / .55, 0, 1) ** 1.3        # darker top: chat area
    for n in range(int(round(TOTAL * FPS))):
        te = n / FPS
        f = rd.next().astype(np.float32)
        z = 1.0 + .06 * eio(te / TOTAL)
        M = cv2.getRotationMatrix2D((W / 2, H * .7), 0, z)
        fr = cv2.warpAffine(f, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        k = clamp((te - .1) / .5) * (1 - eio((te - T_END) / .35) if te > T_END else 1)
        fr *= 1 - (1 - shade) * k
        overlay(fr, te)
        if te < .25: fr *= eo(te / .25)
        if te > TOTAL - .3: fr *= clamp((TOTAL - te) / .3)
        enc.stdin.write(np.clip(fr, 0, 255).astype(np.uint8).tobytes())
    enc.stdin.close(); enc.wait(); rd.p.kill()

if __name__ == "__main__":
    main(sys.argv[1])
