"""Speech -> words with timestamps (faster-whisper)."""
import json
import os
import wave

import numpy as np


def load_wav(path):
    w = wave.open(path)
    return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768


def transcribe(wav16k, out_json, model="large-v3", language=None, prompt=None):
    # Hugging Face's Xet CDN is often blocked behind proxies; plain HTTP works.
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    from faster_whisper import WhisperModel

    m = WhisperModel(model, device="cpu", compute_type="int8")
    segs, info = m.transcribe(load_wav(wav16k), language=language, initial_prompt=prompt,
                              word_timestamps=True, beam_size=5, condition_on_previous_text=False)
    out = {"language": info.language, "segments": []}
    for s in segs:
        out["segments"].append({
            "start": round(s.start, 3), "end": round(s.end, 3), "text": s.text.strip(),
            "words": [{"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3)} for w in s.words],
        })
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    return out


def phrases(transcript, max_dur=3.4, max_chars=42):
    """Split whisper segments into short subtitle-sized phrases (by words)."""
    res = []
    for seg in transcript["segments"]:
        cur = []
        for w in seg["words"]:
            cur.append(w)
            text = " ".join(x["w"] for x in cur)
            end_sentence = w["w"].endswith((".", "?", "!"))
            if (cur[-1]["e"] - cur[0]["s"] > max_dur or len(text) > max_chars or
                    (end_sentence and len(cur) > 2) or (w["w"].endswith(",") and len(text) > 22)):
                res.append({"start": cur[0]["s"], "end": cur[-1]["e"], "en": text})
                cur = []
        if cur:
            res.append({"start": cur[0]["s"], "end": cur[-1]["e"], "en": " ".join(x["w"] for x in cur)})
    return res
