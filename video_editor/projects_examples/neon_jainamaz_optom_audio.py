import sys, subprocess, numpy as np
sys.path.insert(0, "/home/user/Saltow/video_editor")
from vedit import audio as A
SR = A.SR
SEGS = [[0, 2.18], [2.62, 6.52], [7.12, 9.12], [9.42, 10.24], [10.88, 12.57], [13.31, 20.08], [20.87, 25.06]]
TOTAL = sum(b - a for a, b in SEGS) + 1.30
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", "voice_raw.wav", "-af",
  "highpass=f=80,afftdn=nr=8:nf=-45,equalizer=f=250:t=q:w=1.2:g=-1.5,equalizer=f=3500:t=q:w=1:g=2,acompressor=threshold=-20dB:ratio=2.5:attack=8:release=160",
  "-ar", str(SR), "-ac", "1", "voice_clean.wav"], check=True)
v = A.read_wav("voice_clean.wav")
# energy check at every cut point (should be near silence)
for a, b in SEGS:
    for t in (a, b):
        i = int(t * SR); w = v[max(0, i - 480):i + 480]
        print(f"cut@{t:5.2f}  {10*np.log10(np.mean(w**2)+1e-12):6.1f} dB")
N = int(TOTAL * SR); out = np.zeros(N, np.float32); xf = int(.010 * SR); pos = 0
for k, (a, b) in enumerate(SEGS):
    seg = v[int(a * SR):int(b * SR)].copy()
    if k > 0: seg[:xf] *= np.linspace(0, 1, xf)
    if k < len(SEGS) - 1: seg[-xf:] *= np.linspace(1, 0, xf)
    st = pos
    out[st:st + len(seg)] += seg[:N - st]; pos = st + len(seg)
print("voice ends", pos / SR, "total", TOTAL)
m = A.synth_music(N, seed=9, bpm=104)
m[:SR // 2] *= np.linspace(0, 1, SR // 2); m[-int(1.5 * SR):] *= np.linspace(1, 0, int(1.5 * SR))
m *= 10 ** (-19 / 20) / (np.sqrt(np.mean(m ** 2)) + 1e-9)
m = A.duck(out, m, -12)
sfx = np.zeros(N, np.float32)
def put(x, t, g):
    i = int(max(0, t) * SR); n = min(len(x), N - i)
    if n > 0: sfx[i:i + n] += x[:n] * g
for t, k in {2.40: "zoom", 4.00: "whip", 10.30: "zoom", 12.10: "whip", 13.90: "in", 16.90: "out", 18.30: "slide", 21.55: "in"}.items():
    put(A.whoosh(.45 if k != "whip" else .35), t - .22, .5)
for t in (5.95, 6.65, 7.25, 8.10, 8.95): put(A.whoosh(.22), t - .1, .22)      # quick colour cuts
for t in (6.20, 6.70, 7.30, 8.19, 9.02, 11.08, 2.46, 3.74): put(A.pop(), t, .3)
put(A.impact(), .55, .35); put(A.impact(), 12.98, .45); put(A.impact(), 21.6, .45)
for t in np.arange(12.98, 13.55, .06): put(A.pop()[:int(.03 * SR)], t, .12)
for t in np.arange(15.5, 16.15, .06): put(A.pop()[:int(.03 * SR)], t, .12)
put(A.ding(), 13.6, .5); put(A.ding(), 16.2, .5); put(A.ding(), 19.85, .35)
A.write_wav("voice_edit.wav", out); A.write_wav("music.wav", m); A.write_wav("sfx.wav", sfx)
