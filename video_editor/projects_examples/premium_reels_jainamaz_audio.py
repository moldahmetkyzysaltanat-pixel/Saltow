import sys, numpy as np
sys.path.insert(0, "/home/user/Saltow/video_editor")
from vedit import audio as A
SR = A.SR; TOTAL = 40.6; N = int(TOTAL * SR)
import subprocess
subprocess.run(["ffmpeg","-v","error","-y","-i","voice_raw.wav","-af",
  "highpass=f=80,afftdn=nr=8:nf=-45,equalizer=f=250:t=q:w=1.2:g=-1.5,equalizer=f=3500:t=q:w=1.0:g=2,acompressor=threshold=-20dB:ratio=2.5:attack=8:release=160",
  "-ar",str(SR),"-ac","1","voice_clean.wav"],check=True)
v = A.read_wav("voice_clean.wav")[:N]; v = np.pad(v, (0, N - len(v)))
f = int(.6 * SR); v[-f:] *= np.linspace(1, 0, f)
m = A.synth_music(N, seed=3, bpm=92)
m[:SR] *= np.linspace(0, 1, SR); m[-2 * SR:] *= np.linspace(1, 0, 2 * SR)
m *= 10 ** (-20 / 20) / (np.sqrt(np.mean(m ** 2)) + 1e-9)
m = A.duck(v, m, -12)
sfx = np.zeros(N, np.float32)
def put(x, t, g):
    i = int(max(0, t) * SR); n = min(len(x), N - i)
    if n > 0: sfx[i:i + n] += x[:n] * g
trans = {2.20: "dissolve", 4.85: "whip", 6.60: "zoom", 8.40: "mask", 11.00: "whip", 13.05: "zoom", 18.05: "slide",
         20.55: "dissolve", 21.95: "zoom", 24.70: "whip", 28.50: "dissolve", 31.08: "zoom", 34.70: "slide", 38.40: "dissolve"}
for t, k in trans.items():
    if k in ("whip", "zoom", "slide"): put(A.whoosh(.4 if k == "whip" else .5), t - .22, .55)
    elif k == "mask": put(A.whoosh(.7), t - .35, .35)
put(A.impact(), 21.95, .55); put(A.impact(), 4.86, .35); put(A.impact(), 39.30, .45)
for t in (4.06, 7.26, 9.72, 11.96, 18.94, 31.66, 37.46): put(A.pop(), t, .25)
# soft ticks while the price counts down / up
for t0, t1 in ((23.30, 24.0), (26.5, 27.2)):
    for t in np.arange(t0, t1, .06): put(A.pop()[: int(.03 * SR)], t, .12)
put(A.ding(), 24.05, .5); put(A.ding(), 27.2, .5)
A.write_wav("voice_edit.wav", v); A.write_wav("music.wav", m); A.write_wav("sfx.wav", sfx)
