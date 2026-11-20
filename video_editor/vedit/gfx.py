"""Motion-graphics sprites (PIL) + animation helpers."""
import math, numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Fonts for graphics; override with set_fonts() from the config ("graphics_font").
FB = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
FK = "/usr/share/fonts/opentype/inter/Inter-Black.otf"


def set_fonts(bold=None, black=None):
    global FB, FK
    FB = bold or FB
    FK = black or bold or FK


def font(p, s): return ImageFont.truetype(p, s)


def hex_rgba(h, a=255):
    h = h.lstrip("#"); return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)

WHITE = (255, 255, 255, 255); INK = (18, 22, 30, 255)
TEAL = (16, 185, 160, 255); YEL = (255, 213, 74, 255); RED = (239, 68, 68, 255)
GREEN = (34, 197, 94, 255); BLUE = (37, 99, 235, 255)

def ease_out(x): x = min(max(x, 0), 1); return 1 - (1 - x) ** 3
def ease_in_out(x): x = min(max(x, 0), 1); return 4*x**3 if x < .5 else 1 - (-2*x + 2)**3 / 2
def back_out(x, k=1.70158):
    x = min(max(x, 0), 1); return 1 + (k + 1) * (x - 1) ** 3 + k * (x - 1) ** 2

def shadowed(img, rad=18, off=(0, 10), alpha=110):
    pad = rad * 3
    W, H = img.size
    out = Image.new("RGBA", (W + pad*2, H + pad*2), (0, 0, 0, 0))
    a = img.split()[3].point(lambda v: v * alpha // 255)
    sh = Image.new("RGBA", img.size, (0, 0, 0, 255)); sh.putalpha(a)
    out.paste(sh, (pad + off[0], pad + off[1]), sh)
    out = out.filter(ImageFilter.GaussianBlur(rad))
    out.alpha_composite(img, (pad, pad))
    return out

# ---------------- icons ----------------
def icon(kind, size, color=WHITE):
    s = size * 4
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    lw = int(s * 0.11)
    if kind == "check":
        d.line([(s*.2, s*.53), (s*.42, s*.74), (s*.82, s*.28)], fill=color, width=lw, joint="curve")
    elif kind == "cross":
        d.line([(s*.25, s*.25), (s*.75, s*.75)], fill=color, width=lw)
        d.line([(s*.75, s*.25), (s*.25, s*.75)], fill=color, width=lw)
    elif kind == "leaf":
        d.ellipse([s*.18, s*.12, s*.82, s*.88], fill=color)
        im = im.rotate(-40, resample=Image.BICUBIC); d = ImageDraw.Draw(im)
        d.line([(s*.25, s*.8), (s*.7, s*.3)], fill=(0, 0, 0, 0), width=int(s*.05))
    elif kind == "flask":
        d.rectangle([s*.40, s*.08, s*.60, s*.40], fill=color)
        d.polygon([(s*.40, s*.38), (s*.60, s*.38), (s*.88, s*.88), (s*.12, s*.88)], fill=color)
        d.rectangle([s*.32, s*.06, s*.68, s*.13], fill=color)
    elif kind == "pin":
        d.ellipse([s*.2, s*.06, s*.8, s*.66], fill=color)
        d.polygon([(s*.24, s*.46), (s*.76, s*.46), (s*.5, s*.95)], fill=color)
        d.ellipse([s*.38, s*.24, s*.62, s*.48], fill=(0, 0, 0, 0))
    elif kind == "star":
        pts = []
        for i in range(10):
            r = s*.46 if i % 2 == 0 else s*.2
            a = -math.pi/2 + i*math.pi/5
            pts.append((s/2 + r*math.cos(a), s*.53 + r*math.sin(a)))
        d.polygon(pts, fill=color)
    elif kind == "heart":
        d.ellipse([s*.08, s*.15, s*.52, s*.58], fill=color)
        d.ellipse([s*.48, s*.15, s*.92, s*.58], fill=color)
        d.polygon([(s*.11, s*.45), (s*.89, s*.45), (s*.5, s*.9)], fill=color)
    elif kind == "arrow":
        d.line([(s*.12, s*.5), (s*.78, s*.5)], fill=color, width=lw)
        d.polygon([(s*.62, s*.26), (s*.95, s*.5), (s*.62, s*.74)], fill=color)
    return im.resize((size, size), Image.LANCZOS)

# ---------------- sprite builders ----------------
def pill(text, ic=None, bg=WHITE, fg=INK, icbg=TEAL, fs=46):
    f = font(FB, fs)
    tw = int(f.getlength(text)); th = fs
    h = int(fs * 2.0); icw = h if ic else 0
    w = tw + int(fs * 1.3) + icw
    im = Image.new("RGBA", (w, h)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=h // 2, fill=bg)
    x0 = int(fs * .65)
    if ic:
        d.ellipse([6, 6, h - 6, h - 6], fill=icbg)
        ii = icon(ic, int(h * .5)); im.alpha_composite(ii, (int(h*.25), int(h*.25)))
        x0 = h + int(fs * .3)
    d.text((x0, h / 2), text, font=f, fill=fg, anchor="lm")
    return shadowed(im)

def badge_circle(big, small, color, ring=YEL, d=300, bigfs=150):
    im = Image.new("RGBA", (d, d)); dr = ImageDraw.Draw(im)
    dr.ellipse([0, 0, d-1, d-1], fill=ring)
    dr.ellipse([14, 14, d-15, d-15], fill=color)
    dr.text((d/2, d*.47), big, font=font(FK, bigfs), fill=WHITE, anchor="mm")
    if small: dr.text((d/2, d*.77), small, font=font(FB, 30), fill=WHITE, anchor="mm")
    return shadowed(im)

def caption_card(lines, fs=44, bg=(18, 22, 30, 230), fg=WHITE):
    f = font(FB, fs)
    w = max(int(f.getlength(l)) for l in lines) + 70
    h = int(len(lines) * fs * 1.3) + 46
    im = Image.new("RGBA", (w, h)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w-1, h-1], radius=26, fill=bg)
    for i, l in enumerate(lines):
        d.text((w/2, 23 + fs*1.3*i + fs*.65), l, font=f, fill=fg if i == 0 else YEL, anchor="mm")
    return shadowed(im)

class Sprite:
    def __init__(self, img):
        a = np.asarray(img).astype(np.float32)
        self.rgb = a[..., :3][..., ::-1].copy()  # to BGR
        self.a = a[..., 3:4] / 255.0
        self.h, self.w = a.shape[:2]

def blit(frame, spr, cx, cy, scale=1.0, alpha=1.0):
    """composite sprite centered at (cx,cy) onto BGR float frame"""
    if alpha <= 0.003 or scale <= 0.01: return
    rgb, a = spr.rgb, spr.a
    if abs(scale - 1) > 1e-3:
        w = max(1, int(spr.w * scale)); h = max(1, int(spr.h * scale))
        rgb = cv2.resize(rgb, (w, h), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
        a = cv2.resize(a[..., 0], (w, h), interpolation=cv2.INTER_LINEAR)[..., None]
    h, w = a.shape[:2]
    x0 = int(round(cx - w / 2)); y0 = int(round(cy - h / 2))
    fx0, fy0 = max(0, x0), max(0, y0); fx1 = min(frame.shape[1], x0 + w); fy1 = min(frame.shape[0], y0 + h)
    if fx1 <= fx0 or fy1 <= fy0: return
    sa = a[fy0-y0:fy1-y0, fx0-x0:fx1-x0] * alpha
    frame[fy0:fy1, fx0:fx1] = frame[fy0:fy1, fx0:fx1] * (1 - sa) + rgb[fy0-y0:fy1-y0, fx0-x0:fx1-x0] * sa
