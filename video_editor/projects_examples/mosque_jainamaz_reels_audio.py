import sys, numpy as np
sys.path.insert(0, "/home/user/Saltow/video_editor")
from vedit import audio as A
SR = A.SR
v = A.read_wav("voice_raw.wav")                     # original voiceover, untouched (no cuts)
N = len(v)
m = A.synth_music(N, seed=21, bpm=96)
m[:SR] *= np.linspace(0, 1, SR); m[-int(1.2 * SR):] *= np.linspace(1, 0, int(1.2 * SR))
m *= 10 ** (-27 / 20) / (np.sqrt(np.mean(m ** 2)) + 1e-9)   # quiet bed
m = A.duck(v, m, -14)
sfx = np.zeros(N, np.float32)
def put(x, t, g):
    i = int(max(0, t) * SR); n = min(len(x), N - i)
    if n > 0: sfx[i:i + n] += x[:n] * g
for t in (5.72, 7.84, 10.40, 17.14, 26.44, 29.16): put(A.whoosh(.4), t - .2, .25)
for t in (6.2, 7.9, 10.46, 12.02, 12.68, 13.42, 14.52, 21.1, 24.92): put(A.pop(), t, .2)
for j in range(5): put(A.pop(), 8.0 + j * .16, .12)
for t in np.arange(22.84, 23.45, .06): put(A.pop()[:int(.03 * SR)], t, .08)
put(A.ding(), 23.5, .3); put(A.ding(), 31.3, .3)
A.write_wav("voice.wav", v); A.write_wav("music.wav", m); A.write_wav("sfx.wav", sfx)
print("len", N / SR)
