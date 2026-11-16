import sys, json
from faster_whisper import WhisperModel
src, out = sys.argv[1], sys.argv[2]
m = WhisperModel("large-v3", device="cpu", compute_type="int8", cpu_threads=4)
import wave, numpy as np
wf = wave.open(src); audio = np.frombuffer(wf.readframes(wf.getnframes()), np.int16).astype(np.float32)/32768
segs, info = m.transcribe(audio, language="kk", word_timestamps=True, beam_size=5, vad_filter=False)
res = []
for s in segs:
    res.append({"start": s.start, "end": s.end, "text": s.text.strip(),
                "words": [{"w": w.word.strip(), "s": round(w.start, 2), "e": round(w.end, 2), "p": round(w.probability, 2)} for w in s.words]})
    print(f"[{s.start:6.2f}-{s.end:6.2f}] {s.text}", flush=True)
json.dump(res, open(out, "w"), ensure_ascii=False, indent=1)
