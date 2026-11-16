"""Composite original child footage over poem-matched backgrounds.

Child layer: original pixels untouched (only alpha-blended at mask edges).
Audio: copied bit-for-bit from the source. Resolution/fps: same as source.
Usage: composite.py video.mp4 alpha_dir plan.json out.mp4 [--preview start end]
"""
import sys, json, subprocess, cv2, numpy as np

video, adir, plan_path, out = sys.argv[1:5]
prev = sys.argv[5:] and sys.argv[5] == '--preview'
plan = json.load(open(plan_path))
W, H, FPS = 832, 464, 60000 / 1001
XF = plan.get('crossfade', 0.6)

def load_bg(path, drift):
    im = cv2.imread(path)
    s = max(W * 1.06 / im.shape[1], H * 1.06 / im.shape[0])  # 6% headroom for slow drift
    im = cv2.resize(im, (int(im.shape[1] * s + .5), int(im.shape[0] * s + .5)), interpolation=cv2.INTER_AREA)
    if plan.get('dof', 0):
        im = cv2.GaussianBlur(im, (0, 0), plan['dof'])  # shallow depth of field on the background only
    return im.astype(np.float32), drift

scenes = [dict(sc, img=load_bg(sc['image'], sc.get('drift', [1, 0]))) for sc in plan['scenes']]

def bg_at(t):
    def frame(sc):
        im, (dx, dy) = sc['img']
        u = (t - sc['start']) / max(sc['end'] - sc['start'], 1e-3)
        u = min(max(u, 0), 1)
        ox = (im.shape[1] - W) / 2 + dx * (u - .5) * (im.shape[1] - W) * .9
        oy = (im.shape[0] - H) * sc.get('anchor_y', .5) + dy * (u - .5) * (im.shape[0] - H) * .9
        M = np.float32([[1, 0, -ox], [0, 1, -oy]])
        return cv2.warpAffine(im, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    for i, sc in enumerate(scenes):
        if t < sc['end'] or i == len(scenes) - 1:
            cur = frame(sc)
            if i > 0 and t < sc['start'] + XF / 2 and t >= sc['start'] - XF / 2:
                k = (t - (sc['start'] - XF / 2)) / XF
                k = k * k * (3 - 2 * k)  # smoothstep crossfade
                return frame(scenes[i - 1]) * (1 - k) + cur * k
            if i + 1 < len(scenes) and t >= sc['end'] - XF / 2:
                nx = scenes[i + 1]
                k = (t - (sc['end'] - XF / 2)) / XF
                k = k * k * (3 - 2 * k)
                return cur * (1 - k) + frame(nx) * k
            return cur

def read_alpha(i, n):
    # light temporal smoothing (1-2-1) to remove mask flicker; clamp to existing frames
    a = [cv2.imread(f"{adir}/{min(max(j, 0), n - 1):05d}.png", 0).astype(np.float32) / 255 for j in (i - 1, i, i + 1)]
    al = (a[0] + 2 * a[1] + a[2]) / 4
    al = np.clip((al - 0.04) / 0.92, 0, 1)  # trim faint halo / fill near-opaque interior
    return al

def decontaminate(img, a):
    # replace colour of semi-transparent edge pixels with nearby solid-foreground colour
    # (removes green-curtain spill on hair/ear edges); opaque pixels keep original values
    f = img * a[..., None]
    num = cv2.GaussianBlur(f, (0, 0), 2.5); den = cv2.GaussianBlur(a, (0, 0), 2.5)[..., None]
    est = num / np.maximum(den, 1e-3)
    edge = ((a > 0.02) & (a < 0.98))[..., None]
    return np.where(edge, est, img)

def contact_shadow(a):
    # soft ellipse shadow under the feet, derived from the mask's lowest rows
    ys, xs = np.where(a > 0.5)
    sh = np.zeros((H, W), np.float32)
    if len(ys):
        y0 = ys.max(); feet = xs[ys > y0 - 12]
        cx, rx = int(feet.mean()), max(int((feet.max() - feet.min()) * .9), 20)
        cv2.ellipse(sh, (cx, min(y0, H - 3)), (rx, 9), 0, 0, 360, 1, -1)
        sh = cv2.GaussianBlur(sh, (0, 0), 7)
    return sh * plan.get('shadow', 0.35)

n = int(subprocess.check_output(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v', '-show_entries',
                                 'stream=nb_read_frames', '-of', 'csv=p=0', video]).strip())
f0, f1 = (int(float(sys.argv[6]) * FPS), int(float(sys.argv[7]) * FPS)) if prev else (0, n)
dec = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', video, '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'], stdout=subprocess.PIPE)
enc_cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', '60000/1001', '-i', '-']
if prev:
    enc_cmd += ['-c:v', 'libx264', '-crf', '18', '-preset', 'fast', '-pix_fmt', 'yuv420p', out]
else:
    enc_cmd += ['-i', video, '-map', '0:v', '-map', '1:a', '-c:a', 'copy', '-c:v', 'libx264', '-crf', '14',
                '-preset', 'slow', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out]
enc = subprocess.Popen(enc_cmd, stdin=subprocess.PIPE)
for i in range(n):
    buf = dec.stdout.read(W * H * 3)
    if len(buf) < W * H * 3: break
    if i < f0: continue
    if i >= f1: break
    img = np.frombuffer(buf, np.uint8).reshape(H, W, 3).astype(np.float32)
    a = read_alpha(i, n)
    fg = decontaminate(img, a)
    bg = bg_at(i / FPS) * (1 - contact_shadow(a))[..., None]
    o = fg * a[..., None] + bg * (1 - a[..., None])
    enc.stdin.write(np.clip(o + .5, 0, 255).astype(np.uint8).tobytes())
    if i % 300 == 0: print('frame', i, flush=True)
enc.stdin.close(); enc.wait(); dec.kill()
print('DONE', out)
