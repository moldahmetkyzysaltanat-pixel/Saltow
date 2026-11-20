"""Pause detection and the source <-> edited time mapping."""
import re
import subprocess


def detect_silences(wav, threshold_db=-30, min_len=0.3):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", wav, "-af",
                        f"highpass=f=100,silencedetect=noise={threshold_db}dB:d={min_len}", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    st = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", r)]
    en = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", r)]
    return list(zip(st, en))


def keep_segments(silences, duration, end_at=None, min_pause=0.45, pad_before=0.13, pad_after=0.10,
                  extra_cuts=()):
    """Shorten every pause >= min_pause, leaving a little air so words are never clipped.
    extra_cuts: list of [a, b] source ranges to remove completely (e.g. an off-mic question)."""
    end_at = end_at or duration
    cuts = [(a + pad_before, b - pad_after) for a, b in silences if b - a >= min_pause and b < end_at - 0.2]
    for a, b in extra_cuts:
        cuts = [c for c in cuts if c[1] < a or c[0] > b]
        cuts.append((a, b))
    cuts.sort()
    keep, cur = [], 0.0
    for a, b in cuts:
        if a > cur:
            keep.append([round(cur, 3), round(a, 3)])
        cur = max(cur, b)
    keep.append([round(cur, 3), round(end_at, 3)])
    return [k for k in keep if k[1] - k[0] > 0.05]


class Timeline:
    def __init__(self, segs):
        self.segs = segs
        self.offs, acc = [], 0.0
        for a, b in segs:
            self.offs.append(acc)
            acc += b - a
        self.total = acc

    def e(self, ts):
        """source time -> edited time (a time inside a removed gap snaps to the next kept segment)."""
        for (a, b), o in zip(self.segs, self.offs):
            if ts < a:
                return o
            if ts <= b:
                return o + ts - a
        return self.total

    def s(self, te):
        """edited time -> (source time, segment index)"""
        n = len(self.segs)
        for i, ((a, b), o) in enumerate(zip(self.segs, self.offs)):
            if te < o + (b - a) or i == n - 1:
                return a + (te - o), i
        return self.segs[-1][1], n - 1
