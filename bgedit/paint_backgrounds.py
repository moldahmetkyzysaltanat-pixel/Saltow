"""Procedurally paint six 1920x1080 backgrounds that follow the poem's scenes."""
import sys, os, numpy as np, cv2
W, H = 1920, 1080
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
rng = np.random.default_rng(7)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)

def noise(scale, oct=5, seed=0):
    r = np.random.default_rng(seed); acc = np.zeros((H, W), np.float32); amp = 1; tot = 0
    for o in range(oct):
        s = max(int(scale / 2 ** o), 2)
        g = r.random((H // s + 2, W // s + 2)).astype(np.float32)
        acc += amp * cv2.resize(g, (W + 2 * s, H + 2 * s), interpolation=cv2.INTER_CUBIC)[s:s + H, s:s + W]
        tot += amp; amp *= .5
    return acc / tot

def C(hexs):  # '#rrggbb' -> BGR float
    h = hexs.lstrip('#'); return np.array([int(h[4:6], 16), int(h[2:4], 16), int(h[0:2], 16)], np.float32)

def vgrad(top, bot, y0=0, y1=H):
    t = np.clip((yy - y0) / max(y1 - y0, 1), 0, 1)[..., None]
    return C(top) * (1 - t) + C(bot) * t

def ridge(base, amp, scale, seed, rough=4):
    x = np.arange(W, dtype=np.float32)
    r = np.random.default_rng(seed); y = np.zeros(W, np.float32); a = amp
    for o in range(rough):
        n = max(int(W / (scale / 2 ** o)), 2); pts = r.random(n + 3)
        y += a * cv2.resize(pts[None].astype(np.float32), (W, 1), interpolation=cv2.INTER_CUBIC)[0]; a *= .45
    return base - y

def fill_below(img, line, color, feather=1.5):
    m = (yy >= line[None, :]).astype(np.float32)
    m = cv2.GaussianBlur(m, (0, 0), feather)[..., None]
    col = color if np.ndim(color) == 3 else np.broadcast_to(color, img.shape)
    return img * (1 - m) + col * m, m[..., 0]

def clouds(img, y0, y1, dens=.55, seed=1, tint='#ffffff'):
    n = noise(420, 6, seed); band = np.clip(1 - np.abs((yy - (y0 + y1) / 2) / ((y1 - y0) / 2)), 0, 1)
    c = np.clip((n - dens) * 3.2, 0, 1) * band
    return img * (1 - c[..., None] * .85) + C(tint) * c[..., None] * .85

def sun(img, cx, cy, r, color='#fff2c0', glow=.55):
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    g = np.exp(-(d / (r * 6)) ** 2) * glow; disk = np.clip((r - d) / 2 + .5, 0, 1)
    img = img + C(color) * g[..., None] * .6
    return img * (1 - disk[..., None]) + C(color) * disk[..., None]

def grass(img, horizon, top, bot, seed=3):
    g = vgrad(top, bot, horizon, H)
    tex = noise(60, 5, seed)[..., None]; streak = noise(8, 2, seed + 1)[..., None]
    g = g * (0.86 + 0.22 * tex) * (0.95 + 0.1 * streak)
    return fill_below(img, np.full(W, horizon, np.float32), g, 1.2)[0]

def haze(img, horizon, color, strength=.35, spread=120):
    t = np.exp(-((yy - horizon) / spread) ** 2)[..., None] * strength
    return img * (1 - t) + C(color) * t

def save(name, img):
    img = img * (1 + (noise(3, 1, 99)[..., None] - .5) * .03)  # fine film grain
    cv2.imwrite(f"{out}/{name}.jpg", np.clip(img, 0, 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 95])

# 1. Кең байтақ дала — wide steppe, high sky
img = vgrad('#3d8fd6', '#cfe6f5', 0, 700)
img = clouds(img, 80, 520, .56, 11)
hz = 700
for base, amp, col, sd in [(hz, 40, '#9fb7c4', 21), (hz + 6, 26, '#a9b98a', 22)]:
    img = fill_below(img, ridge(base, amp, 900, sd), C(col))[0]
img = grass(img, hz + 18, '#c4b56a', '#8a8f3e')
img = haze(img, hz, '#e8eef0', .4, 40)
save('01_steppe', img)

# 2. Асқар тау + бұлақ — snowy Tian Shan peaks above an alpine lake, spruce slopes
img = vgrad('#2f7fd0', '#d6ecf7', 0, 620)
img = clouds(img, 60, 300, .62, 12)
peaks = ridge(520, 330, 700, 31, 5)
img, m = fill_below(img, peaks, vgrad('#8fa2b8', '#5d6f86', 200, 620))
pk = peaks[None, :]; snowline = 300 + 60 * noise(140, 3, 5)
snow = np.clip((snowline - yy) / 14, 0, 1) * m * np.clip((noise(45, 4, 6) - .35) * 4, 0, 1) ** .5
snow = cv2.GaussianBlur(snow, (0, 0), 1.5)
img = img * (1 - snow[..., None]) + C('#f4f7fb') * snow[..., None]
img = haze(img, 560, '#cfe0ea', .35, 70)
img = fill_below(img, ridge(640, 120, 500, 32), vgrad('#2f5a3e', '#1e3b2a', 520, 700) * (0.85 + .3 * noise(12, 3, 6))[..., None])[0]
lake_top = 700
water = vgrad('#3f86a8', '#235f7a', lake_top, 860)
refl = cv2.flip(img, 0)[H - 2 * lake_top:H - 2 * lake_top + H] if False else None
img, wm = fill_below(img, np.full(W, lake_top, np.float32), water * (0.92 + .16 * noise(4, 2, 7))[..., None], 1)
img = grass(img, 860, '#7c9a4a', '#4f6a2c', 8) * (yy[..., None] >= 860) + img * (yy[..., None] < 860)
save('02_mountains_lake', img)

# 3. Көк байрақ желбіре — open sky in flag colours with a golden sun over the steppe
img = vgrad('#00a3dd', '#9fdcf5', 0, 760)
img = sun(img, 1380, 300, 70, '#ffe36e', .9)
ang = np.arctan2(yy - 300, xx - 1380); d = np.sqrt((xx - 1380) ** 2 + (yy - 300) ** 2)
rays = (np.cos(ang * 32) > .55) * np.clip(1 - (d - 90) / 260, 0, 1) * (d > 90)
img = img * (1 - rays[..., None] * .35) + C('#ffe36e') * rays[..., None] * .35
img = clouds(img, 380, 640, .6, 13)
img = fill_below(img, ridge(760, 30, 900, 41), C('#9db48e'))[0]
img = grass(img, 775, '#b8bf5e', '#7f8b35', 9)
img = haze(img, 765, '#e6f3f8', .45, 30)
save('03_sky_sun', img)

# 4. Ана тілі, домбыра, бабалар мұрасы — white yurts on a mountain meadow
img = vgrad('#4a92d4', '#e2eff6', 0, 640)
img = clouds(img, 80, 380, .58, 14)
img = fill_below(img, ridge(560, 220, 800, 51), vgrad('#97a8bd', '#6f8098', 300, 640))[0]
img = haze(img, 600, '#d9e6ee', .4, 60)
img = fill_below(img, ridge(660, 60, 600, 52), C('#6f8f4b'))[0]
img = grass(img, 690, '#8daa52', '#5a7a2e', 10)
for cx, base, r in [(330, 760, 120), (1560, 740, 95), (1760, 770, 70)]:
    wall_h = int(r * .75)
    body = (np.abs(xx - cx) <= r) & (yy <= base) & (yy >= base - wall_h)
    dome = ((xx - cx) / r) ** 2 + ((yy - (base - wall_h)) / (r * .55)) ** 2 <= 1
    dome &= yy <= base - wall_h
    shade = np.clip(.75 + .35 * (cx - xx) / r, .6, 1.05)[..., None]
    y_m = (body | dome).astype(np.float32); y_m = cv2.GaussianBlur(y_m, (0, 0), 1.2)[..., None]
    img = img * (1 - y_m) + C('#f3efe6') * shade * y_m
    band = ((np.abs(yy - (base - wall_h * .55)) < 6) & body).astype(np.float32)[..., None]
    img = img * (1 - band) + C('#b0352c') * band
    door = ((np.abs(xx - cx) < r * .18) & (yy > base - wall_h * .75) & (yy <= base)).astype(np.float32)[..., None]
    img = img * (1 - door) + C('#a3462a') * door
    sh = np.exp(-(((xx - cx - r * .3) / (r * 1.3)) ** 2 + ((yy - base - 6) / 10) ** 2))[..., None] * .35
    img = img * (1 - sh)
save('04_yurts', img)

# 5. Қазақстан – алтын ұям — capital skyline with a tall tower crowned by a golden sphere, golden hour
img = vgrad('#3c6fb8', '#f5c983', 0, 760)
img = sun(img, 540, 610, 60, '#ffd98a', .8)
img = clouds(img, 100, 420, .63, 15, '#fbe3c0')
city = np.full(W, 800, np.float32)
r2 = np.random.default_rng(5); x = 0
while x < W:
    w = int(r2.integers(40, 120)); h = int(r2.integers(60, 260))
    if abs(x - 1180) < 140: h = int(r2.integers(40, 110))
    city[x:x + w] = 800 - h; x += w + int(r2.integers(0, 12))
img, cm = fill_below(img, city, vgrad('#7a7f9e', '#4b4f6c', 560, 800), 0.8)
win = ((noise(3, 1, 16) > .9) & (cm > .5) & ((yy.astype(int) // 14) % 2 == 0) & ((xx.astype(int) // 10) % 2 == 0)).astype(np.float32)[..., None] * .6
img = img * (1 - win) + C('#ffd27a') * win
tx, top = 1180, 300
shaft = (np.abs(xx - tx) < 16 + (yy - top) * .02) & (yy > top + 70) & (yy < 800)
img[shaft] = img[shaft] * 0 + C('#e9e4dc') * (0.8 + .3 * (xx[shaft, None] < tx))
sph = (xx - tx) ** 2 + (yy - top) ** 2 <= 62 ** 2
g = np.clip(1.15 - np.sqrt((xx - tx + 20) ** 2 + (yy - top + 20) ** 2) / 90, .55, 1.15)
img[sph] = C('#f2b33a') * g[sph, None]
for k in range(-4, 5):
    t = np.linspace(0, 1, 200); px = tx + k * 9 * (1 - t) + k * 6; py = top + 62 + 20 + t * 0
for k in np.linspace(-1, 1, 9):
    cv2.line(img, (int(tx + k * 18), 800), (int(tx + k * 48), top + 40), C('#d8d2c8').tolist(), 3)
img = haze(img, 800, '#f2c690', .3, 80)
img = fill_below(img, np.full(W, 800, np.float32), vgrad('#8b8a5a', '#5b5c38', 800, H) * (0.9 + .2 * noise(40, 4, 17))[..., None])[0]
save('05_capital', img)

# 6. Елімді мақтан етемін — sunset over the steppe with distant mountains
img = vgrad('#2d3f86', '#f6a65a', 0, 700)
img = img * 1 + (vgrad('#000000', '#40180a', 300, 700)) * 0
img = sun(img, 960, 650, 85, '#ffd27a', 1.0)
img = clouds(img, 120, 460, .6, 18, '#f3b98a')
img = fill_below(img, ridge(690, 160, 700, 61), vgrad('#7a5a8c', '#4a3a66', 500, 700))[0]
img = haze(img, 690, '#f5b07a', .45, 50)
img = grass(img, 720, '#a77a3a', '#5e4422', 19)
save('06_sunset', img)

sheet = [cv2.resize(cv2.imread(f"{out}/{f}"), (640, 360)) for f in sorted(os.listdir(out)) if f.endswith('.jpg')]
cv2.imwrite(f"{out}/sheet.jpg", np.vstack([np.hstack(sheet[i:i + 3]) for i in (0, 3)]))
print('ok')
