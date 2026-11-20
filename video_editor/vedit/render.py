"""Frame renderer: cuts, eased punch-in zooms on the speaker, B-roll, motion graphics, outro.

Reads the graded constant-fps intermediate, writes an H.264 video track (no audio).
All times in the config are SOURCE times; the timeline maps them to the edited cut.
"""
import math
import os
import subprocess

import cv2
import numpy as np

from . import gfx
from .gfx import (Sprite, back_out, badge_circle, blit, caption_card, ease_in_out, ease_out, hex_rgba, icon,
                  pill)


class Reader:
    def __init__(self, path, w, h, fps, start=0.0):
        self.w, self.h = w, h
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{start:.4f}", "-i", path, "-f", "rawvideo",
                                   "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE, bufsize=10 ** 8)
        self.n = int(round(start * fps))
        self.last = None

    def get(self, idx):
        while self.n <= idx:
            buf = self.p.stdout.read(self.w * self.h * 3)
            if len(buf) < self.w * self.h * 3:
                return self.last
            self.last = np.frombuffer(buf, np.uint8).reshape(self.h, self.w, 3)
            self.n += 1
        return self.last

    def close(self):
        self.p.kill()


def transform(frame, sc, fx, fy, W, H, ytarget=0.37):
    if sc <= 1.0005:
        return frame
    cw, ch = W / sc, H / sc
    x0 = min(max(fx - cw / 2, 0), W - cw)
    y0 = min(max(fy - ch * ytarget, 0), H - ch)
    M = np.float32([[sc, 0, -x0 * sc], [0, sc, -y0 * sc]])
    return cv2.warpAffine(frame, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def vignette(W, H, amount=0.22):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * .75)) ** 2 + ((yy - H / 2) / (H * .75)) ** 2)
    return (1 - amount * np.clip(r - 0.35, 0, 1) ** 1.5)[..., None].astype(np.float32)


class Renderer:
    def __init__(self, cfg, timeline, tracks, graded, W, H, fps, broll_files):
        self.cfg, self.tl, self.tracks = cfg, timeline, tracks
        self.graded, self.W, self.H, self.fps = graded, W, H, fps
        z = cfg.get("zoom", {})
        self.punch = z.get("punch", 1.2)
        self.drift = z.get("drift", 0.03)
        self.emph = [timeline.e(t) for t in z.get("emphasis", [])]
        n = len(timeline.segs)
        self.seg_scale = [1.0 if i % 2 == 0 else self.punch for i in range(n)]
        self.seg_scale[-1] = 1.0
        self.broll = [dict(b, a=timeline.e(b["start"]), b=timeline.e(b["end"]), path=broll_files[i])
                      for i, b in enumerate(cfg.get("broll", []))]
        self.gfx = [dict(g, a=timeline.e(g["start"]), b=timeline.e(g["end"])) for g in cfg.get("graphics", [])]
        self.flash = [timeline.e(t) for t in cfg.get("flash_at", [])]
        o = cfg.get("outro")
        self.outro = (timeline.total - o.get("duration", 1.4), timeline.total) if o else None
        self.vig = vignette(W, H, cfg.get("grade", {}).get("vignette", 0.22))
        self.spr = {}

    # ---------- framing ----------
    def framing(self, te):
        ts, i = self.tl.s(te)
        seg_start = self.tl.offs[i]
        seg_len = self.tl.segs[i][1] - self.tl.segs[i][0]
        tgt = self.seg_scale[i]
        prev = self.seg_scale[i - 1] if i > 0 else tgt
        k = ease_out((te - seg_start) / 0.45) if i > 0 else 1.0
        sc = prev + (tgt - prev) * (0.55 + 0.45 * k)          # eased glide into the new framing
        p = ease_in_out((te - seg_start) / max(seg_len, 0.5))
        sc *= 1.0 + (self.drift * p if i % 2 == 0 else -self.drift * 0.66 * p)   # slow push / pull
        for t0 in self.emph:                                    # emphasis push-in on key lines
            d = te - t0
            if 0 <= d < 2.6:
                sc *= 1.0 + 0.07 * (ease_in_out(d / 0.6) if d < 0.6 else
                                    (1 - ease_in_out((d - 1.9) / 0.7) if d > 1.9 else 1))
        fx, fy = self.tracks.at(ts)
        return ts, max(sc, 1.0), fx, fy

    def sp(self, key, fn):
        if key not in self.spr:
            self.spr[key] = Sprite(fn())
        return self.spr[key]

    # ---------- graphics ----------
    def draw_graphics(self, fr, te):
        W = self.W
        for b in self.broll:
            if b.get("label") and b["a"] <= te < b["b"]:
                d, r = te - b["a"], b["b"] - te
                s = self.sp("bl" + b["label"], lambda: pill(b["label"], b.get("icon"), fs=44))
                blit(fr, s, W / 2 + (1 - ease_out(d / 0.5)) * -700, self.H * 0.615, 1.0, min(1, r / 0.25))
        for g in self.gfx:
            if not (g["a"] <= te < g["b"]):
                continue
            d, r = te - g["a"], g["b"] - te
            out = min(1, r / 0.3)
            y = g.get("y", 330)
            key = repr(sorted((k, str(v)) for k, v in g.items()))
            col = hex_rgba(g.get("color", "#14B8A0"))
            t = g["type"]
            if t == "card":
                s = self.sp(key, lambda: caption_card(g["lines"], fs=g.get("size", 52)))
                blit(fr, s, W / 2, y - 40 * (1 - ease_out(d / .5)), 0.9 + 0.1 * back_out(d / .5), min(1, d / .25) * out)
            elif t == "badge":
                s = self.sp(key, lambda: badge_circle(g["big"], g.get("small", ""), col))
                blit(fr, s, W / 2, y, back_out(d / .45), min(1, d / .15) * out)
                if g.get("caption"):
                    s2 = self.sp(key + "c", lambda: pill(g["caption"], None, fs=38))
                    blit(fr, s2, W / 2 + (1 - ease_out((d - .25) / .45)) * 900, y + 230, 1, (d > .25) * out)
            elif t == "pill":
                s = self.sp(key, lambda: pill(g["text"], g.get("icon"), fs=g.get("size", 46), icbg=col))
                blit(fr, s, W / 2, y, back_out(d / .4), min(1, d / .12) * out)
            elif t == "list":
                if g.get("title"):
                    s = self.sp(key + "t", lambda: pill(g["title"], g.get("icon", "star"), fs=40, icbg=col))
                    blit(fr, s, W / 2, y, back_out(d / .4), min(1, d / .15) * out)
                for j, item in enumerate(g["items"]):
                    t_item, name = item[0], item[1]
                    ic = item[2] if len(item) > 2 else "check"          # e.g. "cross" for "not available"
                    dd = te - (self.tl.e(t_item) - 0.05)
                    if dd < 0:
                        continue
                    icol = hex_rgba("#EF4444" if ic == "cross" else "#22C55E")
                    s = self.sp(key + name, lambda: pill(name, ic, fs=34, icbg=icol))
                    x = W / 2 + (-235 if j % 2 == 0 else 235)
                    yy = y + 130 + (j // 2) * 108
                    blit(fr, s, x, yy + 30 * (1 - ease_out(dd / .35)), back_out(dd / .35), min(1, dd / .12) * out)
            elif t == "progress":
                al = min(1, d / .2) * out
                s = self.sp(key, lambda: pill(g["text"], None, fs=44))
                blit(fr, s, W / 2, y - 30 * (1 - ease_out(d / .4)), 1, al)
                bw, bh, by = 700, 26, int(y + 110)
                x0 = int(W / 2 - bw / 2)
                p = ease_in_out((d - .4) / max(.5, (g["b"] - g["a"]) - 1.5))
                bk = fr.copy()
                cv2.rectangle(bk, (x0 - 40, by - 34), (x0 + bw + 40, by + bh + 34), (22, 18, 18), -1, cv2.LINE_AA)
                cv2.addWeighted(bk, 0.62 * al, fr, 1 - 0.62 * al, 0, fr)
                ov = fr.copy()
                cv2.rectangle(ov, (x0, by), (x0 + bw, by + bh), (40, 30, 25), -1, cv2.LINE_AA)
                cv2.rectangle(ov, (x0, by), (x0 + int(bw * p), by + bh), (74, 213, 255), -1, cv2.LINE_AA)
                cv2.addWeighted(ov, 0.92 * al, fr, 1 - 0.92 * al, 0, fr)

    def draw_outro(self, fr, te):
        o = self.cfg["outro"]
        a, b = self.outro
        d, r = te - a, b - te
        k = ease_in_out(d / .6)
        fr[:] = cv2.GaussianBlur(fr, (0, 0), 1 + 18 * k) * (1 - 0.45 * k)
        s1 = self.sp("o1", lambda: caption_card(o.get("lines", ["SAFI"]), fs=52))
        blit(fr, s1, self.W / 2, self.H * .42, 0.9 + .1 * back_out(d / .5), min(1, d / .3))
        if o.get("pill"):
            s2 = self.sp("o2", lambda: pill(o["pill"], o.get("icon", "heart"), fs=48, icbg=hex_rgba("#EF4444")))
            blit(fr, s2, self.W / 2, self.H * .42 + 200, back_out((d - .35) / .45), 1 if d > .35 else 0)
        if r < 0.4:
            fr *= max(0, r / 0.4)

    # ---------- main loop ----------
    def run(self, out_path, t_start=0.0, t_len=None, log=print):
        W, H, fps = self.W, self.H, self.fps
        n_total = int(round(self.tl.total * fps))
        i0 = int(t_start * fps)
        n_end = n_total if t_len is None else min(n_total, i0 + int(t_len * fps))
        enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                                "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                                "-crf", "15", "-pix_fmt", "yuv420p", "-color_primaries", "bt709",
                                "-color_trc", "bt709", "-colorspace", "bt709", out_path], stdin=subprocess.PIPE)
        ts0, _ = self.tl.s(i0 / fps)
        main = Reader(self.graded, W, H, fps, max(0, ts0 - 0.1))
        br = {}
        for n in range(i0, n_end):
            te = n / fps
            ts, sc, fx, fy = self.framing(te)
            idx = int(round(ts * fps))
            if idx < main.n - 1:
                main.close()
                main = Reader(self.graded, W, H, fps, ts)
            fr = transform(main.get(idx), sc, fx, fy, W, H).astype(np.float32)
            for j, b in enumerate(self.broll):
                if b["a"] <= te < b["b"]:
                    if j not in br:
                        br[j] = Reader(b["path"], W, H, fps, 0.0)
                    d, r = te - b["a"], b["b"] - te
                    bf = br[j].get(int((b.get("offset", 0) + d) * fps))
                    if bf is None:
                        continue
                    z = 1.08 - 0.08 * ease_out(d / 0.5) + 0.04 * ease_in_out(d / (b["b"] - b["a"]))
                    bf = transform(bf, z, W / 2, H / 2, W, H, 0.5).astype(np.float32)
                    mix = min(ease_out(d / 0.18), ease_out(r / 0.18))
                    fr = fr * (1 - mix) + bf * mix
                elif te >= b["b"] and j in br:
                    br.pop(j).close()
            for ft in self.flash:
                d = te - ft
                if -0.05 <= d < 0.18:
                    fl = 0.45 * (1 - abs(d - 0.02) / 0.16)
                    if fl > 0:
                        fr = fr * (1 - fl) + 255 * fl
            fr *= self.vig
            self.draw_graphics(fr, te)
            if self.outro and te >= self.outro[0]:
                self.draw_outro(fr, te)
            if te < 0.25:
                fr *= ease_out(te / 0.25)
            enc.stdin.write(np.clip(fr, 0, 255).astype(np.uint8).tobytes())
            if n % (fps * 5) == 0:
                log(f"  render {te:5.1f}s / {self.tl.total:.1f}s")
        enc.stdin.close()
        enc.wait()
        main.close()
        for r in br.values():
            r.close()
