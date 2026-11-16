# Pass 2: re-run RMBG-1.4 on a crop around the child (bbox from pass-1 mask, smoothed over time).
# The child fills the model input ~3-4x larger, so feet, hair and flag edges come out cleaner.
import sys, os, subprocess, cv2, numpy as np, onnxruntime as ort
video, model, a1dir, outdir = sys.argv[1:5]
os.makedirs(outdir, exist_ok=True)
W, H, PAD = 832, 464, 48
so = ort.SessionOptions(); so.intra_op_num_threads = 4
s = ort.InferenceSession(model, so, providers=['CPUExecutionProvider'])
inp = s.get_inputs()[0].name
n = len([f for f in os.listdir(a1dir) if f.endswith('.png')])
boxes = []
for i in range(n):
    ys, xs = np.where(cv2.imread(f"{a1dir}/{i:05d}.png", 0) > 64)
    boxes.append([xs.min(), ys.min(), xs.max(), ys.max()] if len(xs) else boxes[-1] if boxes else [0, 0, W - 1, H - 1])
b = np.array(boxes, np.float32)
# union over a +/-15 frame window so the crop never clips a fast hand or flag movement
k = 15
bb = np.array([[b[max(0, i - k):i + k + 1, 0].min(), b[max(0, i - k):i + k + 1, 1].min(),
                b[max(0, i - k):i + k + 1, 2].max(), b[max(0, i - k):i + k + 1, 3].max()] for i in range(n)])
p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', video, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
for i in range(n):
    img = np.frombuffer(p.stdout.read(W * H * 3), np.uint8).reshape(H, W, 3)
    path = f"{outdir}/{i:05d}.png"
    if os.path.exists(path): continue
    x0, y0 = int(max(bb[i, 0] - PAD, 0)), int(max(bb[i, 1] - PAD, 0))
    x1, y1 = int(min(bb[i, 2] + PAD, W)), int(min(bb[i, 3] + PAD, H))
    crop = img[y0:y1, x0:x1]
    x = (cv2.resize(crop, (1024, 1024), interpolation=cv2.INTER_CUBIC).astype(np.float32) / 255. - 0.5).transpose(2, 0, 1)[None]
    y = s.run(None, {inp: x})[0][0, 0]
    a = np.zeros((H, W), np.float32)
    a[y0:y1, x0:x1] = cv2.resize(y, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA)
    cv2.imwrite(path, (np.clip(a, 0, 1) * 255).astype(np.uint8))
    if i % 100 == 0: print(i, flush=True)
print("DONE", n, flush=True)
