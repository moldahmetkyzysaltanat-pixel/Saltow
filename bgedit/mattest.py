import sys, time, cv2, numpy as np, onnxruntime as ort
model, size, mean, std, frames, out = sys.argv[1], int(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), sys.argv[5].split(','), sys.argv[6]
s = ort.InferenceSession(model, providers=['CPUExecutionProvider'])
inp = s.get_inputs()[0].name
rows = []
for f in frames:
    img = cv2.imread(f)[:, :, ::-1]
    h, w = img.shape[:2]
    x = cv2.resize(img, (size, size)).astype(np.float32) / 255.
    if mean < 0:  # imagenet
        x = (x - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
    else:
        x = (x - mean) / std
    x = x.transpose(2, 0, 1)[None].astype(np.float32)
    t = time.time(); y = s.run(None, {inp: x})[-1][0, 0]; dt = time.time() - t
    if y.min() < 0 or y.max() > 1: y = 1 / (1 + np.exp(-y))
    a = cv2.resize(y, (w, h))
    print(f, f"{dt:.2f}s", a.min(), a.max())
    chk = np.zeros_like(img); chk[:] = (255, 0, 255)
    comp = (img * a[..., None] + chk * (1 - a[..., None])).astype(np.uint8)
    rows.append(np.hstack([img, comp]))
cv2.imwrite(out, np.vstack(rows)[:, :, ::-1])
