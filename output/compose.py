import cv2, numpy as np, os, sys, subprocess, bisect

N = 2555
FPS = 60000 / 1001
W, H = 1920, 1080
S = 2.75           # foreground upscale
CX_REF = 415       # child's x in reference frame
CX_OUT = 670       # where the child stands in the output
Y0 = 44            # reference-frame row mapped to output top

cam = np.load('cam.npy')
keys = sorted(int(f[:5]) for f in os.listdir('mk') if f.endswith('.png'))

# ---------------- scenes ----------------
# (start_sec, image, zoom0, zoom1, (cx0,cy0), (cx1,cy1))
SC = [
    (0.0,  'a4c036', 1.06, 1.16, (0.46, 0.50), (0.52, 0.50)),   # Кең байтақ далам, туған жер
    (3.5,  '09938e', 1.18, 1.08, (0.56, 0.55), (0.50, 0.55)),   # Жүрегім саған байланған
    (6.6,  '0e032d', 1.05, 1.18, (0.50, 0.45), (0.52, 0.42)),   # Асқар тау
    (9.4,  'be5fc1', 1.18, 1.06, (0.50, 0.50), (0.50, 0.48)),   # Бәрінен сенсің жайнаған
    (11.7, '152e38', 1.08, 1.20, (0.48, 0.40), (0.54, 0.36)),   # Көк байрағым желбіре
    (14.2, 'c2714f', 1.30, 1.40, (0.39, 0.50), (0.37, 0.52)),   # Биіктерге самғағын
    (16.0, '568a8b', 1.28, 1.36, (0.39, 0.46), (0.39, 0.42)),   # Тәуелсіз елдің ...
    (18.2, '8a6470', 1.36, 1.26, (0.39, 0.48), (0.40, 0.50)),   # ... ардағым
    (20.6, '5097a8', 1.06, 1.22, (0.52, 0.50), (0.60, 0.46)),   # Ана тілім / Домбырам
    (25.0, '964c24', 1.24, 1.32, (0.40, 0.48), (0.39, 0.46)),   # Бабамнан қалған
    (27.1, '45bdf4', 1.12, 1.26, (0.52, 0.58), (0.58, 0.62)),   # Қорғаймын сені, Отаным
    (29.7, '450c5c', 1.30, 1.38, (0.39, 0.52), (0.38, 0.54)),   # Қазақстан — алтын ұям
    (31.8, '52e3a6', 1.06, 1.16, (0.50, 0.50), (0.50, 0.46)),   # мекенім
    (34.2, '12450c', 1.18, 1.06, (0.50, 0.50), (0.50, 0.46)),   # Бес жасар кішкентай болсам да
    (37.2, '1a5a3c', 1.02, 1.10, (0.50, 0.50), (0.52, 0.48)),   # Елімді мақтан етемін
]
XF = 0.6   # crossfade seconds
DUR = N / FPS


class Scene:
    def __init__(s, i):
        s.t0, name, s.z0, s.z1, s.c0, s.c1 = SC[i]
        s.t1 = SC[i + 1][0] if i + 1 < len(SC) else DUR
        s.ta, s.tb = s.t0 - XF / 2, s.t1 + XF / 2
        im = cv2.imread(f'bg2/{name}.jpg')
        k = 2.6
        im = cv2.resize(im, None, fx=k, fy=k, interpolation=cv2.INTER_LANCZOS4)
        # gentle depth-of-field softness, then a touch of local contrast
        im = cv2.GaussianBlur(im, (0, 0), 2.2)
        s.im = im
        s.h, s.w = im.shape[:2]
        s.wmax = min(s.w, s.h * 16 / 9)
        small = cv2.resize(im, (64, 36), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
        s.mean = small.reshape(-1, 3).mean(0)

    def render(s, t):
        u = np.clip((t - s.ta) / (s.tb - s.ta), 0, 1)
        u = u * u * (3 - 2 * u) * 0.5 + u * 0.5      # soft ease
        z = s.z0 + (s.z1 - s.z0) * u
        ww = s.wmax / z
        hh = ww * 9 / 16
        cx = (s.c0[0] + (s.c1[0] - s.c0[0]) * u) * s.w
        cy = (s.c0[1] + (s.c1[1] - s.c0[1]) * u) * s.h
        cx = np.clip(cx, ww / 2, s.w - ww / 2)
        cy = np.clip(cy, hh / 2, s.h - hh / 2)
        k = W / ww
        M = np.float32([[k, 0, W / 2 - k * cx], [0, k, H / 2 - k * cy]])
        return cv2.warpAffine(s.im, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


scenes = [Scene(i) for i in range(len(SC))]


def background(t):
    act = [s for s in scenes if s.ta <= t < s.tb]
    out = None
    mean = None
    for s in act:
        w = 1.0
        if out is not None:
            w = np.clip((t - s.ta) / XF, 0, 1)
            w = w * w * (3 - 2 * w)
        r = s.render(t).astype(np.float32)
        if out is None:
            out, mean = r, s.mean.copy()
        else:
            out = out * (1 - w) + r * w
            mean = mean * (1 - w) + s.mean * w
    return out, mean


# ---------------- masks ----------------
X0, X1 = 180, 700
dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
gx, gy = np.meshgrid(np.arange(X1 - X0, dtype=np.float32), np.arange(464, dtype=np.float32))
_fr = {}


def frame(f):
    if f not in _fr:
        if len(_fr) > 24:
            for k in sorted(_fr)[:8]:
                del _fr[k]
        _fr[f] = cv2.imread(f'fr/{f:05d}.png')
    return _fr[f]


def kmask(f):
    return cv2.imread(f'mk/{f:05d}.png', 0)[:, X0:X1].astype(np.float32) / 255


def warp_from(key, f):
    g1 = cv2.cvtColor(frame(f)[:, X0:X1], cv2.COLOR_BGR2GRAY)
    g0 = cv2.cvtColor(frame(key)[:, X0:X1], cv2.COLOR_BGR2GRAY)
    fl = dis.calc(g1, g0, None)
    return cv2.remap(kmask(key), gx + fl[..., 0], gy + fl[..., 1], cv2.INTER_LINEAR)


def mask(f):
    i = bisect.bisect_left(keys, f)
    if i < len(keys) and keys[i] == f:
        m = kmask(f)
    else:
        a, b = keys[i - 1], keys[min(i, len(keys) - 1)]
        if b <= f:
            m = warp_from(a, f)
        else:
            wa = (b - f) / (b - a)
            m = warp_from(a, f) * wa + warp_from(b, f) * (1 - wa)
    full = np.zeros((464, 832), np.float32)
    full[:, X0:X1] = m
    full = np.maximum(full, flagmask(frame(f)))
    return full


def flagmask(im):
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, (88, 70, 120), (112, 255, 255))
    m[:, :330] = 0
    m[:, 640:] = 0
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    m = cv2.copyMakeBorder(m, 30, 30, 0, 0, cv2.BORDER_CONSTANT, value=0)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25)))[30:-30]
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    out = np.zeros(m.shape, np.uint8)
    if cs:
        c = max(cs, key=cv2.contourArea)
        if cv2.contourArea(c) > 250:
            cv2.drawContours(out, [c], -1, 255, -1)
    return cv2.GaussianBlur(out.astype(np.float32) / 255, (0, 0), 0.8)


# ---------------- look ----------------
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
vig = 1 - 0.12 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) ** 1.2
vig = np.clip(vig, 0, 1)[..., None]
rng = np.random.default_rng(7)
lut = np.arange(256, dtype=np.float32) / 255
lut = lut + 0.06 * np.sin(2 * np.pi * (lut - 0.5)) * -1 * 0.5      # gentle S-curve
lut = np.clip(lut, 0, 1)


def compose(f):
    t = (f - 1) / FPS
    bg, mean = background(t)
    fr = frame(f)
    a = mask(f)
    # undo the handheld camera motion, then scale/place the child
    A = cv2.invertAffineTransform(cam[f])
    P = np.float32([[S, 0, CX_OUT - S * CX_REF], [0, S, -S * Y0]])
    M = (np.vstack([P, [0, 0, 1]]) @ np.vstack([A, [0, 0, 1]]))[:2].astype(np.float32)
    fg = cv2.warpAffine(fr, M, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
    al = cv2.warpAffine(a, M, (W, H), flags=cv2.INTER_CUBIC, borderValue=0)
    al = np.clip((al - 0.22) / 0.66, 0, 1)
    al = cv2.GaussianBlur(al, (0, 0), 1.1)
    # mild sharpening of the upscaled original
    fg = np.clip(fg + 0.45 * (fg - cv2.GaussianBlur(fg, (0, 0), 2.0)), 0, 255)
    # lighting integration: tint/exposure towards the scene
    tint = mean / mean.mean()
    lum = float(mean @ np.float32([0.114, 0.587, 0.299]))
    expo = np.clip((lum / 0.5) ** 0.3, 0.74, 1.05)
    kt = 0.16 + 0.2 * np.clip(1 - lum / 0.4, 0, 1)
    fg = fg * ((1 - kt) + kt * tint) * expo
    # light wrap from blurred background on the silhouette edge
    sb = cv2.resize(bg, (W // 8, H // 8), interpolation=cv2.INTER_AREA)
    sb = cv2.resize(cv2.GaussianBlur(sb, (0, 0), 4), (W, H), interpolation=cv2.INTER_LINEAR)
    wrap = (al * (1 - cv2.GaussianBlur(al, (0, 0), 7)))[..., None] * 0.55
    fg = fg + (sb - fg) * wrap
    al3 = al[..., None]
    out = fg * al3 + bg * (1 - al3)
    # grade
    out = lut[np.clip(out, 0, 255).astype(np.uint8)] * 255 * vig
    out += rng.normal(0, 1.6, (H, W, 1)).astype(np.float32)
    k = min(1, t / 0.7, (DUR - t) / 0.9)
    k = max(0.0, k)
    out *= k * k * (3 - 2 * k)
    return np.clip(out, 0, 255).astype(np.uint8)


if __name__ == '__main__':
    if sys.argv[1] == 'test':
        os.makedirs('test', exist_ok=True)
        for f in map(int, sys.argv[2:]):
            cv2.imwrite(f'test/{f:05d}.jpg', compose(f), [cv2.IMWRITE_JPEG_QUALITY, 92])
    else:
        a, b, out = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
        p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}',
                              '-r', '60000/1001', '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '15',
                              '-pix_fmt', 'yuv420p', '-colorspace', 'bt709', '-color_primaries', 'bt709',
                              '-color_trc', 'bt709', out], stdin=subprocess.PIPE)
        for f in range(a, b + 1):
            p.stdin.write(compose(f).tobytes())
            if f % 100 == 0:
                print(f, flush=True)
        p.stdin.close()
        p.wait()
