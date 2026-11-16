# Extract per-frame alpha (RMBG-1.4) for every original frame; saves 8-bit PNG masks.
import sys, os, subprocess, cv2, numpy as np, onnxruntime as ort
video, model, outdir = sys.argv[1:4]
os.makedirs(outdir, exist_ok=True)
w, h = 832, 464
so = ort.SessionOptions(); so.intra_op_num_threads = 4
s = ort.InferenceSession(model, so, providers=['CPUExecutionProvider'])
inp = s.get_inputs()[0].name
p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', video, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
i = 0
while True:
    buf = p.stdout.read(w * h * 3)
    if len(buf) < w * h * 3: break
    path = f"{outdir}/{i:05d}.png"
    if not os.path.exists(path):
        img = np.frombuffer(buf, np.uint8).reshape(h, w, 3)
        x = (cv2.resize(img, (1024, 1024)).astype(np.float32) / 255. - 0.5).transpose(2, 0, 1)[None]
        y = s.run(None, {inp: x})[0][0, 0]
        a = cv2.resize(y, (w, h), interpolation=cv2.INTER_LINEAR)
        cv2.imwrite(path, (np.clip(a, 0, 1) * 255).astype(np.uint8))
    i += 1
    if i % 100 == 0: print(i, flush=True)
print("DONE", i, flush=True)
