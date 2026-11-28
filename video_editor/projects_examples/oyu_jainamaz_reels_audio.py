import sys, numpy as np
sys.path.insert(0, "/home/user/Saltow/video_editor")
from vedit import audio as A
SR = A.SR
import subprocess
# clarity: remove boom/mud that makes the voice sound "under the nose", add presence + air (no cuts)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", "voice_raw.wav", "-af",
    "highpass=f=100,lowshelf=f=250:g=-5,equalizer=f=500:t=q:w=1.4:g=-2.5,equalizer=f=1200:t=q:w=1.2:g=-1,"
    "equalizer=f=3000:t=q:w=0.9:g=5,highshelf=f=6000:g=4,acompressor=threshold=-24dB:ratio=2.5:attack=5:release=150:makeup=2",
    "-ar", str(SR), "-ac", "1", "voice_clear.wav"], check=True)
v = A.read_wav("voice_clear.wav")                   # full voiceover, no cuts
N = len(v)
m = A.synth_music(N, seed=21, bpm=96)
m[:SR] *= np.linspace(0, 1, SR); m[-int(1.2 * SR):] *= np.linspace(1, 0, int(1.2 * SR))
m *= 10 ** (-38 / 20) / (np.sqrt(np.mean(m ** 2)) + 1e-9)   # quiet bed
m = A.duck(v, m, -16)
sfx = np.zeros(N, np.float32)
def put(x, t, g):
    i = int(max(0, t) * SR); n = min(len(x), N - i)
    if n > 0: sfx[i:i + n] += x[:n] * g
for t in (5.50, 9.80, 13.20, 18.30, 21.10): put(A.whoosh(.4), t - .2, .25)
for t in (0.25, 3.36, 6.82, 9.22, 10.6, 14.64, 16.24, 17.62, 18.88): put(A.pop(), t, .2)

for t in np.arange(9.84, 10.45, .06): put(A.pop()[:int(.03 * SR)], t, .08)
for t in np.arange(19.88, 20.4, .06): put(A.pop()[:int(.03 * SR)], t, .08)
put(A.ding(), 10.5, .3); put(A.ding(), 20.5, .3); put(A.impact(), 21.1, .35)
A.write_wav("voice.wav", v); A.write_wav("music.wav", m); A.write_wav("sfx.wav", sfx)
print("len", N / SR)
