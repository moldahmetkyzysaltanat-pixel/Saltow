import sys, numpy as np
sys.path.insert(0, "/home/user/Saltow/video_editor")
from vedit import audio as A
SR = A.SR; N = int(13.2 * SR)
m = A.synth_music(N, seed=33, bpm=112)
m[:int(.4 * SR)] *= np.linspace(0, 1, int(.4 * SR)); m[-int(1.0 * SR):] *= np.linspace(1, 0, int(1.0 * SR))
m *= 10 ** (-20 / 20) / (np.sqrt(np.mean(m ** 2)) + 1e-9)
sfx = np.zeros(N, np.float32)
def put(x, t, g):
    i = int(max(0, t) * SR); n = min(len(x), N - i)
    if n > 0: sfx[i:i + n] += x[:n] * g
def msg_sound():          # two-note "message received"
    tt = np.arange(int(.32 * SR)) / SR
    a = np.sin(2 * np.pi * 1175 * tt) * np.exp(-tt * 18); b = np.sin(2 * np.pi * 1568 * tt) * np.exp(-tt * 14)
    out = np.zeros(int(.42 * SR), np.float32); out[:len(a)] += a * .35; out[int(.09 * SR):int(.09 * SR) + len(b)] += b[:len(out) - int(.09 * SR)] * .35
    return out
def key_tap():
    n = int(.03 * SR); x = np.random.default_rng(1).standard_normal(n).astype(np.float32)
    return np.diff(x, prepend=0) * np.exp(-np.arange(n) / SR * 160) * .15
for t0, t1 in ((0.35, 1.2), (4.1, 5.05)):
    for t in np.arange(t0, t1, .11): put(key_tap(), t + np.random.default_rng(int(t * 100)).uniform(0, .04), 1.0)
put(msg_sound(), 1.25, 1.0); put(msg_sound(), 5.10, 1.0)
put(A.whoosh(.4), 7.1, .5); put(A.pop(), 7.3, .5); put(A.pop(), 7.5, .35)
put(A.whoosh(.5), 10.7, .5); put(A.impact(), 10.9, .5); put(A.ding(), 11.35, .45)
A.write_wav("music.wav", m); A.write_wav("sfx.wav", sfx)
