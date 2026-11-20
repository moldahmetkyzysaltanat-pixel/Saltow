#!/usr/bin/env python3
"""PRO VIDEO EDITOR - automatic interview edit with Kazakh subtitles.

  python edit.py analyze  INPUT.MOV -p project/          # grade, transcribe, find pauses and faces
  python edit.py translate -p project/ [--context "..."]  # English -> Kazakh with the Claude API (optional)
  python edit.py render   -p project/ -c config.json      # cut, zoom, B-roll, graphics, music, subtitles, export
  python edit.py auto     INPUT.MOV -p project/ -c config.json   # all three in one go

The original file is never modified; everything is written inside the project folder.
"""
import argparse
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vedit import gfx, media, subtitles, timeline, transcribe  # noqa: E402


def log(*a):
    print(*a, flush=True)


def load_cfg(path):
    if not path:
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def P(project, *names):
    return os.path.join(project, *names)


# ---------------------------------------------------------------- analyze
def analyze(args):
    cfg = load_cfg(args.config)
    pj = args.project
    os.makedirs(P(pj, "out"), exist_ok=True)
    info = media.probe(args.input)
    out_cfg = cfg.get("output", {})
    portrait = info["height"] >= info["width"]
    W = out_cfg.get("width", 1080 if portrait else 1920)
    H = out_cfg.get("height", 1920 if portrait else 1080)
    fps = out_cfg.get("fps") or media.nice_fps(info["fps"])
    meta = {"input": os.path.abspath(args.input), "info": info, "W": W, "H": H, "fps": fps}
    json.dump(meta, open(P(pj, "source.json"), "w"), indent=1)
    log(f"source: {info['width']}x{info['height']} {info['fps']:.2f} fps, {info['duration']:.1f}s, "
        f"transfer={info['transfer'] or 'sdr'} -> working {W}x{H} @ {fps} fps")

    log("1/5 colour grade (HDR->SDR tonemap if needed)...")
    media.make_graded(args.input, P(pj, "graded.mp4"), info, W, H, fps, cfg.get("grade", {}))
    log("2/5 audio: extract + clean voice...")
    media.extract_audio(args.input, P(pj, "audio16k.wav"), 16000)
    media.extract_audio(args.input, P(pj, "voice_clean.wav"), 48000, media.VOICE_CHAIN)
    log("3/5 transcribe (faster-whisper large-v3, first run downloads ~3 GB)...")
    tr = transcribe.transcribe(P(pj, "audio16k.wav"), P(pj, "transcript.json"),
                               model=args.whisper_model, language=args.language, prompt=args.prompt)
    log("4/5 pauses...")
    sil = timeline.detect_silences(P(pj, "audio16k.wav"), cfg.get("cuts", {}).get("threshold_db", -30))
    json.dump(sil, open(P(pj, "silences.json"), "w"))
    log("5/5 faces...")
    from vedit import faces
    faces.detect(P(pj, "graded.mp4"), P(pj, "faces.json"), W, H)

    subs_path = P(pj, "subtitles.json")
    if not os.path.exists(subs_path):
        ph = transcribe.phrases(tr)
        json.dump([dict(p, kk="") for p in ph], open(subs_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log("\nTranscript (source times - use these in config.json):")
    for s in tr["segments"]:
        log(f"  [{s['start']:6.2f} - {s['end']:6.2f}] {s['text']}")
    log(f"\nNext: fill the \"kk\" fields in {subs_path} (or run `translate`), then `render`.")


# ---------------------------------------------------------------- translate
def do_translate(args):
    from vedit import translate
    pj = args.project
    subs = json.load(open(P(pj, "subtitles.json"), encoding="utf-8"))
    log(f"translating {len(subs)} phrases with {translate.MODEL}...")
    res = translate.translate(subs, args.context or "")
    json.dump(res, open(P(pj, "subtitles.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for r in res:
        log(f"  {r['start']:6.2f}  {r['en']}\n          -> {r['kk']}")
    log("Check the Kazakh text in subtitles.json, then run `render`.")


# ---------------------------------------------------------------- render
def prep_broll(cfg, meta, pj):
    """Grade + crop + scale every B-roll clip to the working format (cached)."""
    files = []
    os.makedirs(P(pj, "broll"), exist_ok=True)
    for i, b in enumerate(cfg.get("broll", [])):
        src = b["file"]
        if not os.path.isabs(src):
            src = os.path.join(os.path.dirname(os.path.abspath(cfg["_path"])), src)
        dst = P(pj, "broll", f"b{i:02d}.mp4")
        stamp = json.dumps([src, b.get("crop"), b.get("source_start", 0), meta["W"], meta["H"], meta["fps"]])
        cached = os.path.exists(dst) and os.path.exists(dst + ".key") and open(dst + ".key").read() == stamp
        if not cached:
            info = media.probe(src)
            vf = media.grade_filter(info, cfg.get("grade", {}))
            pre = f"crop={b['crop']}," if b.get("crop") else ""
            dur = (b["end"] - b["start"]) + b.get("offset", 0) + 0.5
            media.run(["ffmpeg", "-v", "error", "-y", "-ss", str(b.get("source_start", 0)), "-t", f"{dur:.2f}",
                       "-i", src, "-an", "-vf",
                       f"{pre}{vf},scale={meta['W']}:{meta['H']}:force_original_aspect_ratio=increase:flags=lanczos,"
                       f"crop={meta['W']}:{meta['H']},fps={meta['fps']}",
                       "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", dst])
            open(dst + ".key", "w").write(stamp)
        files.append(dst)
    return files


def render(args):
    import numpy as np  # noqa: F401
    from vedit import audio, faces
    from vedit.render import Renderer

    cfg = load_cfg(args.config)
    cfg["_path"] = args.config or os.path.join(args.project, "config.json")
    pj = args.project
    meta = json.load(open(P(pj, "source.json")))
    W, H, fps, dur = meta["W"], meta["H"], meta["fps"], meta["info"]["duration"]
    gf = cfg.get("graphics_font", {})
    gfx.set_fonts(gf.get("bold"), gf.get("black"))

    # cuts -> timeline (the outro continues the last shot when footage exists)
    c = cfg.get("cuts", {})
    sil = json.load(open(P(pj, "silences.json")))
    end_at = c.get("end_at") or dur
    keep = timeline.keep_segments(sil, dur, end_at, c.get("min_pause", 0.45), extra_cuts=c.get("remove", []))
    voice_end = keep[-1][1]
    if cfg.get("outro"):
        keep[-1][1] = min(dur - 0.05, keep[-1][1] + cfg["outro"].get("duration", 1.4))
    tl = timeline.Timeline(keep)
    json.dump(keep, open(P(pj, "keep.json"), "w"))
    log(f"{len(keep)} segments, {dur:.1f}s -> {tl.total:.1f}s")

    tracks = faces.FaceTracks(json.load(open(P(pj, "faces.json"))), W, H, fps, dur, cfg.get("speakers"))
    broll_files = prep_broll(cfg, meta, pj)
    r = Renderer(cfg, tl, tracks, P(pj, "graded.mp4"), W, H, fps, broll_files)

    log("render video...")
    vtrack = P(pj, "video_track.mp4")
    r.run(vtrack, args.preview_start or 0.0, args.preview, log)

    log("audio mix...")
    cfg.setdefault("audio", {}).setdefault("voice_end", voice_end)
    audio.build_mix(P(pj, "voice_clean.wav"), tl, r, cfg, pj)
    media.run(["ffmpeg", "-v", "error", "-y", "-i", P(pj, "voice_edit.wav"), "-i", P(pj, "music.wav"),
               "-i", P(pj, "sfx.wav"), "-filter_complex",
               "[0]loudnorm=I=-16:TP=-2:LRA=9[v];[v][1][2]amix=inputs=3:normalize=0,alimiter=limit=0.89:level=false[m]",
               "-map", "[m]", "-ar", "48000", "-ac", "2", P(pj, "mix.wav")])

    log("subtitles...")
    subs = json.load(open(P(pj, "subtitles.json"), encoding="utf-8"))
    n = subtitles.build(subs, tl, cfg.get("subtitles"), W, H, P(pj, "subs.ass"), P(pj, "out", "subtitles_kk.srt"))
    log(f"  {n} subtitles")

    log("export...")
    name = cfg.get("output", {}).get("name", "final")
    fonts_dir = (cfg.get("subtitles") or {}).get("fonts_dir") or "/usr/share/fonts"
    ass = P(pj, "subs.ass").replace("\\", "/").replace(":", "\\:")
    fd = fonts_dir.replace("\\", "/").replace(":", "\\:")
    a_off = ["-ss", str(args.preview_start)] if args.preview_start else []
    final = P(pj, "out", f"{name}.mp4")
    media.run(["ffmpeg", "-v", "error", "-y", "-i", vtrack] + a_off + ["-i", P(pj, "mix.wav"), "-filter_complex",
               f"[0:v]setpts=PTS+{args.preview_start or 0}/TB,ass='{ass}':fontsdir='{fd}',setpts=PTS-STARTPTS[v];"
               "[1:a]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]",
               "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "slow", "-crf", "17",
               "-profile:v", "high", "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709",
               "-colorspace", "bt709", "-r", str(fps), "-c:a", "aac", "-b:a", "320k", "-ac", "2",
               "-movflags", "+faststart", "-shortest", final])
    log(f"done: {final}")
    if fps > 60 and not args.preview:
        phone = P(pj, "out", f"{name}_phone_60fps.mp4")
        media.run(["ffmpeg", "-v", "error", "-y", "-i", final, "-vf", "fps=60", "-c:v", "libx264", "-preset", "slow",
                   "-crf", "21", "-maxrate", "6M", "-bufsize", "12M", "-profile:v", "high", "-level", "4.2",
                   "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", phone])
        log(f"phone version: {phone}")
    if cfg.get("_path") and os.path.exists(cfg["_path"]):
        shutil.copy(cfg["_path"], P(pj, "out", "config_used.json"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("analyze", "translate", "render", "auto"):
        s = sub.add_parser(name)
        if name in ("analyze", "auto"):
            s.add_argument("input")
            s.add_argument("--whisper-model", default="large-v3")
            s.add_argument("--language", default=None, help="force speech language, e.g. en")
            s.add_argument("--prompt", default=None, help="names/terms to help the transcriber")
        s.add_argument("-p", "--project", required=True)
        s.add_argument("-c", "--config", default=None)
        if name in ("translate", "auto"):
            s.add_argument("--context", default="", help="one line about the video for the translator")
        if name in ("render", "auto"):
            s.add_argument("--preview", type=float, default=None, help="render only N seconds")
            s.add_argument("--preview-start", type=float, default=None, help="edited-time start for --preview")
    args = ap.parse_args()
    if args.cmd == "analyze":
        analyze(args)
    elif args.cmd == "translate":
        do_translate(args)
    elif args.cmd == "render":
        render(args)
    else:
        analyze(args)
        do_translate(args)
        render(args)


if __name__ == "__main__":
    main()
