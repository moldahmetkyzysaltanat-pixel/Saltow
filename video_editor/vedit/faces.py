"""Face tracking (OpenCV Haar) so punch-in zooms stay centred on the speaker."""
import json
import subprocess

import numpy as np


def detect(video, out_json, width, height, samples_per_sec=5):
    import cv2

    cc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    sw, sh = width // 2, height // 2
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", video, "-vf", f"fps={samples_per_sec},scale={sw}:{sh}",
                          "-f", "rawvideo", "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
    out, i = [], 0
    while True:
        buf = p.stdout.read(sw * sh)
        if len(buf) < sw * sh:
            break
        g = np.frombuffer(buf, np.uint8).reshape(sh, sw)
        fs = cc.detectMultiScale(g, 1.1, 6, minSize=(sw // 27, sw // 27))
        out.append({"t": i / samples_per_sec,
                    "faces": [[int(x) * 2, int(y) * 2, int(w) * 2, int(h) * 2] for x, y, w, h in fs]})
        i += 1
    json.dump(out, open(out_json, "w"))
    return out


class FaceTracks:
    """Smoothed face centre per speaker. Speakers are told apart by screen side:
    config "speakers": [{"start": 0, "end": 8.1, "side": "right"}, ...] (source time);
    without it, the biggest face in frame is followed."""

    def __init__(self, faces, width, height, fps, duration, speakers=None):
        self.fps, self.w, self.h = fps, width, height
        self.speakers = speakers or []
        self.tracks = {side: self._track(faces, side, duration) for side in ("left", "right", "any")}

    def _track(self, faces, side, duration):
        ts, xs, ys = [], [], []
        for f in faces:
            c = []
            for x, y, w, h in f["faces"]:
                cx, cy = x + w / 2, y + h / 2
                if w < self.w * 0.08 or cy > self.h * 0.7:   # tiny or low = false positive
                    continue
                if side == "left" and cx > self.w * 0.5:
                    continue
                if side == "right" and cx < self.w * 0.4:
                    continue
                c.append((cx, cy, w))
            if c:
                c.sort(key=lambda v: -v[2])
                ts.append(f["t"]); xs.append(c[0][0]); ys.append(c[0][1])
        tg = np.arange(0, duration + 2, 1 / self.fps)
        if not ts:
            return np.full(len(tg), self.w / 2), np.full(len(tg), self.h * 0.38)
        X, Y = np.interp(tg, ts, xs), np.interp(tg, ts, ys)
        k = max(1, int(self.fps * 1.6))
        ker = np.ones(k) / k
        X = np.convolve(np.pad(X, k, mode="edge"), ker, "same")[k:-k]
        Y = np.convolve(np.pad(Y, k, mode="edge"), ker, "same")[k:-k]
        return X, Y

    def side_at(self, ts):
        for sp in self.speakers:
            if sp["start"] <= ts < sp["end"]:
                return sp.get("side", "any")
        return "any"

    def at(self, ts):
        X, Y = self.tracks[self.side_at(ts)]
        i = min(len(X) - 1, max(0, int(ts * self.fps)))
        return X[i], Y[i]
