"""ffmpeg helpers: probing, HDR->SDR tonemap + colour grade, constant-fps intermediates."""
import json
import subprocess


def run(cmd, **kw):
    """Run a command, raising with stderr on failure."""
    p = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if p.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(map(str, cmd))}\n{p.stderr[-3000:]}")
    return p


def probe(path):
    out = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path]).stdout
    d = json.loads(out)
    v = next(s for s in d["streams"] if s["codec_type"] == "video")
    a = next((s for s in d["streams"] if s["codec_type"] == "audio"), None)
    num, den = map(int, v.get("avg_frame_rate", "30/1").split("/"))
    fps = num / den if den else 30.0
    rot = 0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(sd["rotation"])
    w, h = int(v["width"]), int(v["height"])
    if abs(rot) in (90, 270):
        w, h = h, w
    return {
        "duration": float(d["format"]["duration"]),
        "width": w, "height": h, "fps": fps,
        "transfer": v.get("color_transfer", ""),
        "has_audio": a is not None,
        "audio_channels": int(a["channels"]) if a else 0,
    }


def nice_fps(fps):
    """Round a measured (often variable) phone frame rate to the nominal one."""
    for f in (24, 25, 30, 48, 50, 60, 120, 240):
        if abs(fps - f) < 0.6:
            return f
    return round(fps)


def grade_filter(info, grade):
    """Filter chain: HDR (HLG/PQ) -> SDR Rec.709 tonemap, then the look from config."""
    parts = []
    if info["transfer"] in ("arib-std-b67", "smpte2084"):
        parts.append(
            f"zscale=tin={info['transfer']}:min=bt2020nc:pin=bt2020:t=linear:npl={grade.get('npl', 100)},"
            "format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,"
            "zscale=t=bt709:m=bt709:r=tv:d=error_diffusion,format=yuv420p")
    else:
        parts.append("format=yuv420p")
    parts.append(f"eq=contrast={grade.get('contrast', 1.07)}:saturation={grade.get('saturation', 1.12)}"
                 f":gamma={grade.get('gamma', 0.98)}")
    warm = grade.get("warmth", 0.02)
    if warm:
        parts.append(f"colorbalance=rs={warm}:bs={-warm}:rm={warm * .75}:bm={-warm * .75}")
    parts.append("curves=master='0/0.02 0.5/0.5 1/0.98'")
    return ",".join(parts)


def make_graded(src, dst, info, width, height, fps, grade, crop=None):
    """Tonemap + grade + scale to the working resolution at constant fps."""
    vf = []
    if crop:
        vf.append(f"crop={crop}")
    vf.append(grade_filter(info, grade))
    vf.append(f"scale={width}:{height}:force_original_aspect_ratio=increase:flags=lanczos,crop={width}:{height}")
    vf.append(f"fps={fps}")
    run(["ffmpeg", "-v", "error", "-y", "-i", src, "-map", "0:v:0", "-an", "-vf", ",".join(vf),
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "13", "-pix_fmt", "yuv420p", dst])


def extract_audio(src, dst, rate=16000, chain=None):
    af = ["pan=mono|c0=0.5*c0+0.5*c1"] if probe(src)["audio_channels"] >= 2 else []
    if chain:
        af.append(chain)
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", src, "-map", "0:a:0"]
    if af:
        cmd += ["-af", ",".join(af)]
    run(cmd + ["-ac", "1", "-ar", str(rate), "-c:a", "pcm_s16le", dst])


VOICE_CHAIN = ("highpass=f=80,afftdn=nr=10:nf=-42:tn=1,"
               "equalizer=f=250:t=q:w=1.2:g=-2,equalizer=f=3200:t=q:w=1.0:g=2.5,highshelf=f=9000:g=1.5,"
               "acompressor=threshold=-22dB:ratio=3:attack=8:release=160:makeup=2")
