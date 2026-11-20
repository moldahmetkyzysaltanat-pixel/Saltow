"""Voice cut + music bed (your file or a generated one) + SFX + ducking -> stereo mix."""
import wave

import numpy as np

SR = 48000


def read_wav(p):
    w = wave.open(p)
    x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    if w.getnchannels() > 1:
        x = x.reshape(-1, w.getnchannels()).mean(1)
    return x


def write_wav(p, x):
    x = np.clip(x, -1, 1)
    if x.ndim == 1:
        x = x[:, None]
    w = wave.open(p, "wb")
    w.setnchannels(x.shape[1]); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((x * 32767).astype(np.int16).tobytes()); w.close()


def cut_voice(voice_full, timeline, voice_end=None):
    N = int(round(timeline.total * SR))
    out = np.zeros(N, np.float32)
    fade = int(0.008 * SR)
    for k, ((a, b), o) in enumerate(zip(timeline.segs, timeline.offs)):
        seg = voice_full[int(a * SR):int(b * SR)].copy()
        if voice_end and b > voice_end:        # silence the tail under the outro
            cut = max(0, int((voice_end - a) * SR))
            seg[cut:] = 0
            f = min(cut, int(.15 * SR))
            if f:
                seg[cut - f:cut] *= np.linspace(1, 0, f)
        if len(seg) > 2 * fade:
            seg[:fade] *= np.linspace(0, 1, fade)
            seg[-fade:] *= np.linspace(1, 0, fade)
        i0 = int(round(o * SR)); n = min(len(seg), N - i0)
        out[i0:i0 + n] += seg[:n]
    return out


def synth_music(N, seed=7, bpm=100):
    """Original light corporate bed (I-V-vi-IV), so there is no licensing question."""
    rng = np.random.default_rng(seed)
    beat = 60 / bpm
    note = lambda m: 440 * 2 ** ((m - 69) / 12)
    prog = [[48, 55, 60, 64, 67], [43, 55, 59, 62, 67], [45, 57, 60, 64, 69], [41, 53, 57, 60, 65]]
    total = N / SR
    music = np.zeros(N, np.float32)

    def env(n, a=.6, r=.9):
        e = np.ones(n, np.float32)
        na, nr = min(int(a * SR), n // 2), min(int(r * SR), n // 2)
        e[:na] = np.linspace(0, 1, na); e[n - nr:] *= np.linspace(1, 0, nr)
        return e

    pos, ci = 0.0, 0
    while pos < total:
        ch = prog[ci % 4]
        n0 = int(pos * SR); n = min(int((8 * beat + .8) * SR), N - n0)
        tt = np.arange(n) / SR
        pad = np.zeros(n, np.float32)
        for m in ch:
            f = note(m + 12)
            for det in (-0.12, 0.12):
                ph = rng.uniform(0, 6.28)
                pad += np.sin(2 * np.pi * f * (1 + det / 100) * tt + ph) * .5 + .12 * np.sin(2 * np.pi * 2 * f * tt + ph)
        music[n0:n0 + n] += pad * env(n) * 0.022
        arp = [ch[2] + 24, ch[3] + 24, ch[4] + 24, ch[3] + 24]
        for k in range(16):
            m0 = int((pos + k * beat / 2) * SR); ln = min(int(.5 * SR), N - m0)
            if ln <= 0:
                break
            tk = np.arange(ln) / SR; f = note(arp[k % 4])
            music[m0:m0 + ln] += (np.sin(2 * np.pi * f * tk) + .3 * np.sin(4 * np.pi * f * tk)) * np.exp(-tk * 9) * .03
        for k in range(8):
            m0 = int((pos + k * beat) * SR); ln = min(int(beat * SR), N - m0)
            if ln <= 0:
                break
            tk = np.arange(ln) / SR
            music[m0:m0 + ln] += np.sin(2 * np.pi * note(ch[0]) * tk) * np.exp(-tk * 3) * .06
        pos += 8 * beat; ci += 1
    for k in range(int(total / beat) + 1):
        m0 = int(k * beat * SR); ln = min(int(.3 * SR), N - m0)
        if ln <= 0:
            break
        tk = np.arange(ln) / SR
        music[m0:m0 + ln] += np.sin(2 * np.pi * (50 + 90 * np.exp(-tk * 35)) * tk) * np.exp(-tk * 12) * .10
        h0 = int((k * beat + beat / 2) * SR); hl = min(int(.06 * SR), N - h0)
        if hl > 0:
            hn = np.diff(rng.standard_normal(hl).astype(np.float32), prepend=0)
            music[h0:h0 + hl] += hn * np.exp(-np.arange(hl) / SR * 60) * .012
    return music


def load_music(path, N):
    import subprocess
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True).stdout
    m = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    if len(m) == 0:
        raise SystemExit(f"cannot read music file {path}")
    reps = int(np.ceil(N / len(m)))
    return np.tile(m, reps)[:N]


# ---------------- SFX (synthesized) ----------------
_rng = np.random.default_rng(11)


def whoosh(dur=.45):
    n = int(dur * SR); x = _rng.standard_normal(n).astype(np.float32); tt = np.arange(n) / SR
    cut = 300 + 5000 * np.sin(np.pi * tt / dur) ** 2
    al = 1 - np.exp(-2 * np.pi * cut / SR)
    y = np.zeros(n, np.float32); acc = 0.0
    for i in range(n):
        acc += al[i] * (x[i] - acc); y[i] = acc
    y *= np.sin(np.pi * tt / dur) ** 1.5
    return y / (np.max(np.abs(y)) + 1e-9) * .35


def pop():
    n = int(.12 * SR); tt = np.arange(n) / SR
    return (np.sin(2 * np.pi * (900 - 500 * tt / .12) * tt) * np.exp(-tt * 45) * .35).astype(np.float32)


def impact():
    n = int(.9 * SR); tt = np.arange(n) / SR
    body = np.sin(2 * np.pi * (45 + 70 * np.exp(-tt * 20)) * tt) * np.exp(-tt * 5)
    return ((body + _rng.standard_normal(n) * np.exp(-tt * 30) * .25) * .45).astype(np.float32)


def ding():
    n = int(.8 * SR); tt = np.arange(n) / SR
    return ((np.sin(2 * np.pi * 1318 * tt) + .5 * np.sin(2 * np.pi * 1975 * tt)) * np.exp(-tt * 6) * .12).astype(np.float32)


def build_sfx(N, renderer):
    sfx = np.zeros(N, np.float32)

    def put(x, at, g=1.0):
        i0 = int(max(0, at) * SR); n = min(len(x), N - i0)
        if n > 0:
            sfx[i0:i0 + n] += x[:n] * g

    W1, W2 = whoosh(), whoosh(.35)
    for b in renderer.broll:
        put(W1, b["a"] - .2, .9); put(W2, b["b"] - .15, .5)
    for t in renderer.flash:
        put(whoosh(.6), t - .3, 1.0)
    for g in renderer.gfx:
        snd = g.get("sfx") or {"badge": "impact", "progress": "pop", "list": "pop"}.get(g["type"], "pop")
        put({"impact": impact(), "pop": pop(), "ding": ding(), "whoosh": W1}[snd], g["a"], .9)
        if g["type"] == "badge":
            put(pop(), g["a"] + .25, .8)
        if g["type"] == "list":
            for t_item, _ in g["items"]:
                put(pop(), renderer.tl.e(t_item) - .05, .8)
        if g["type"] == "progress":
            put(ding(), g["b"] - 1.2, 1.0)
    if renderer.outro:
        put(impact(), renderer.outro[0], .8); put(ding(), renderer.outro[0] + .35, 1.0)
    return sfx


def duck(voice, music, depth_db=-11):
    win = int(.03 * SR)
    pw = np.convolve(voice ** 2, np.ones(win) / win, "same")
    act = (10 * np.log10(pw + 1e-10) > -38).astype(np.float32)
    ctl = act[::48]; sm = np.zeros_like(ctl); g = 0.0
    for i, x in enumerate(ctl):          # attack 60 ms, release 500 ms
        k = 1 - np.exp(-1 / (60 if x > g else 500)); g += k * (x - g); sm[i] = g
    d = np.interp(np.arange(len(music)), np.arange(len(sm)) * 48, sm)
    return music * 10 ** ((depth_db * d) / 20)


def build_mix(voice_full_wav, timeline, renderer, cfg, work):
    acfg = cfg.get("audio", {})
    voice = cut_voice(read_wav(voice_full_wav), timeline, acfg.get("voice_end"))
    N = len(voice)
    mcfg = acfg.get("music", {})
    music = load_music(mcfg["file"], N) if mcfg.get("file") else synth_music(N)
    music[:SR] *= np.linspace(0, 1, SR)
    music[-2 * SR:] *= np.linspace(1, 0, 2 * SR)
    rms = np.sqrt(np.mean(music ** 2)) + 1e-9
    music *= 10 ** (mcfg.get("level_db", -18) / 20) / rms        # bed level before ducking
    music = duck(voice, music, mcfg.get("duck_db", -11))
    sfx = build_sfx(N, renderer) * 10 ** (acfg.get("sfx_db", -2) / 20) if acfg.get("sfx", True) else np.zeros(N)
    write_wav(f"{work}/voice_edit.wav", voice)
    write_wav(f"{work}/music.wav", music)
    write_wav(f"{work}/sfx.wav", sfx)
