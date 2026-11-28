"""Kazakh-ornament prayer mats reel. Full voiceover (22.61 s), 9 clips, NEON minimal motion,
two-font captions (no stroke, no box), growth rules: hook at 0 s, CTA at the end, safe zones."""
import os, subprocess, sys
import numpy as np, cv2
sys.path.insert(0, "/tmp/claude-0/-home-user-Saltow/ff4d6f8e-eeda-5c24-9b8f-32a0a8602af8/scratchpad/p7/work")
import build7c as M                      # helpers: word/captions renderer, blit, spr, fadeio, ln, back, VR
B, N = M.B, M.N
P = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B.G = os.path.join(P, "g")
B.CLIPFPS.update({f"f{i}": 60 for i in range(1, 10)})
W, H, FPS = 1080, 1920, 30
TOTAL = 22.61
clamp, eo, eio, eexpo, back = B.clamp, B.eo, B.eio, B.eexpo, M.back
blit, spr, fadeio, ln, T = M.blit, M.spr, M.fadeio, M.ln, M.T
WHITE, CREAM, LIME = M.WHITE, M.CREAM, N.LIME

# ("v", clip, a, b, s0, speed, z0, z1)
SHOTS = [
    ("v", "f2", 0.00, 2.00, 0.6, 1.0, 1.00, 1.06),   # MEDIUM: whole black mat (symmetrical) — hook
    ("v", "f1", 2.00, 3.90, 0.4, 1.0, 1.04, 1.10),   # DETAIL: brown ornament corner  "осындай әдемі"
    ("v", "f4", 3.90, 5.50, 0.6, 1.0, 1.06, 1.12),   # CLOSE: grey ornament  "сапалы жайнамаздарымыз бар"
    ("v", "f9", 5.50, 7.70, 0.4, 1.0, 1.02, 1.08),   # MEDIUM: reveal olive mat  "4 500-ден сатқан"
    ("v", "f8", 7.70, 9.80, 0.7, 1.0, 1.08, 1.02),   # MEDIUM: black mat  "қазір жеңілдікпен"
    ("v", "f5", 9.80, 11.80, 0.2, 1.0, 1.04, 1.10),  # CLOSE: maroon ornament  "2 500 теңге ғана"
    ("v", "f7", 11.80, 13.20, 0.0, 0.62, 1.04, 1.10),# DETAIL: ornament edge (slow-mo) — breath
    ("v", "f6", 13.20, 15.60, 0.3, 1.0, 1.04, 1.10), # DETAIL: folded edge + fringe  "іздеп кеткен жандар"
    ("v", "f3", 15.60, 18.30, 0.0, 0.95, 1.00, 1.06),# MEDIUM: whole mat  "таптырмас мүмкіндік"
    ("v", "f1", 18.30, TOTAL, 3.6, 1.0, 1.02, 1.08), # DETAIL brown (under the 10-pcs offer + end card)
]
TRANS = {5.50: ("dissolve", .30), 9.80: ("zoom", .30), 13.20: ("dissolve", .35), 18.30: ("slide_up", .32)}

M.CAPS[:] = [
    (1.02, 2.58, [[T("Қазақи нақыштағы", 1.02, size=60, w=900)], [T("осындай әдемі", 1.98, "serif", 100, color=CREAM)]]),
    (2.60, 5.02, [[T("сапалы", 3.36, "serif", 104, color=LIME)], [T("жайнамаздарымыз бар.", 3.94, size=58, w=800)]]),
    (5.54, 8.60, [[T("Бұл жайнамаздарды біз", 5.54, size=52, w=800)], [T("4 500 теңгеден", 6.82, size=80, w=900)],
                  [T("сатқан болатынбыз,", 7.76, "serif", 88, color=CREAM)]]),
    (8.62, 11.30, [[T("қазір жеңілдікпен", 8.62, "serif", 92, color=LIME)], [T("2 500 теңге", 9.84, size=92, w=900)],
                   [T("ғана!", 10.84, "serif", 96, color=CREAM)]]),
    (11.50, 12.52, [[T("Қараңыздар,", 11.54, "serif", 100, color=CREAM)], [T("қандай!", 12.14, size=92, w=900)]]),
    (12.56, 16.40, [[T("Бізден", 12.56, size=56, w=800), T("қазақи оюмен", 13.10, size=62, w=900)],
                    [T("жайнамаздарды іздеп кеткен", 14.66, "serif", 80, color=CREAM)],
                    [T("жандар өте көп,", 15.90, size=56, w=800)]]),
    (16.80, 18.86, [[T("сіздерге", 16.82, size=56, w=800)], [T("таптырмас мүмкіндік.", 17.62, "serif", 92, color=LIME)]]),
    (18.88, 21.30, [[T("Он данасын", 18.88, size=62, w=900)], [T("25 000 теңгеге", 19.88, "serif", 96, color=CREAM)],
                    [T("аласыз.", 20.74, size=58, w=800)]]),
]

def motion(fr, te):
    # HOOK (0 s): national ornament + price
    a = fadeio(te, 0.0, 1.95, fin=.08)
    if a:
        blit(fr, spr("h0", lambda: N.label("қазақи ою-өрнек", 50)), W / 2, 460, 1, a)
        blit(fr, spr("h1", lambda: N.headline("жайнамаз", size=140)), W / 2, 630, .9 + .1 * back(te / .35), a)
        blit(fr, spr("h2", lambda: N.tag("2 500 ₸", size=60)), W / 2, 820, back((te - .25) / .35), a * clamp((te - .25) / .12))
    # quality tick
    a = fadeio(te, 3.36, 5.40)
    if a: blit(fr, spr("q", lambda: N.check_row("сапалы · әдемі", True)), W / 2 + (1 - eo((te - 3.36) / .3)) * -60, 520, 1, a)
    # old price card (struck on "жеңілдікпен")
    a = fadeio(te, 6.82, 9.80)
    if a:
        blit(fr, spr("lb", lambda: N.label("бұрынғы баға", 46)), W / 2, 330, 1, a)
        blit(fr, spr("s45", lambda: N.stat_card("Жайнамаз", "· бұрын", "4 500 ₸", "play")), W / 2, 520 + 60 * (1 - eo((te - 6.82) / .45)), 1, a)
        if te >= 9.22:
            ln(fr, (W / 2 - 160, 545), (W / 2 + 260, 530), eo((te - 9.22) / .35), 8, a, (232, 52, 66))
            blit(fr, spr("disc", lambda: N.tag("ЖЕҢІЛДІК", size=50)), W / 2, 720, back((te - 9.22) / .35), a)
    # new price wallet: 4 500 -> 2 500, "1 ДАНА"
    a = fadeio(te, 9.84, 12.90)
    if a:
        blit(fr, spr("lbn", lambda: N.label("қазір", 46)), W / 2, 300, 1, a)
        p = eexpo((te - 9.84) / .7); p = 1 if p > .96 else p
        v = int(round((4500 + (2500 - 4500) * p) / 100) * 100); txt = f"{v:,}".replace(",", " ") + " ₸"
        blit(fr, spr(("w", txt), lambda: N.wallet_card("бар болғаны", "KZT", txt, cross=False)), W / 2,
             560 + 60 * (1 - eo((te - 9.84) / .45)), .96 + .04 * eo((te - 9.84) / .45), a)
        if te >= 10.6: blit(fr, spr("one", lambda: N.tag("1 ДАНА", size=54)), W / 2, 820, back((te - 10.6) / .35), a)
    # demand: "іздеп кеткен жандар өте көп"
    a = fadeio(te, 14.64, 16.70)
    if a:
        blit(fr, spr("dm", lambda: N.headline("сұраныс", label="іздеушілер өте көп", size=130)), W / 2, 600, .85 + .15 * back((te - 14.64) / .38), a)
        if te >= 16.24: blit(fr, spr("up", lambda: N.tag("ӨТЕ КӨП ↑", size=52)), W / 2, 800, back((te - 16.24) / .35), a)
    # "таптырмас мүмкіндік"
    a = fadeio(te, 17.62, 18.80)
    if a: blit(fr, spr("tm", lambda: N.headline("таптырмас", accent="!", size=130)), W / 2, 620, .85 + .15 * back((te - 17.62) / .38), a)
    # 10 pcs = 25 000
    a = fadeio(te, 18.88, 21.10)
    if a:
        blit(fr, spr("s10", lambda: N.stat_card("Жайнамаз", "· 2 500 ₸", "10 дана", "play")), W / 2, 470 + 60 * (1 - eo((te - 18.88) / .45)), 1, a)
        if te >= 19.88:
            p = eexpo((te - 19.88) / .6); p = 1 if p > .96 else p
            v = int(round(25000 * p / 500) * 500); txt = f"{v:,}".replace(",", " ") + " ₸"
            blit(fr, spr(("t", txt), lambda: N.big_text(txt, 150, LIME, edge=False)), W / 2, 760, .9 + .1 * back((te - 19.88) / .4), a * clamp((te - 19.88) / .12))
    # END CARD + follow CTA (growth rule #6)
    if te >= 21.10:
        d = te - 21.10; k = eio(d / .4)
        fr[:] = fr * (1 - k) + N.interlude_bg(W, H, te) * k
        blit(fr, spr("e0", lambda: N.label("қазақи ою-өрнекті жайнамаз", 44)), W / 2, 400, 1, clamp(d / .15))
        blit(fr, spr("e1", lambda: N.big_text("2 500 ₸", 180, LIME, edge=False)), W / 2, 560, .9 + .1 * back(d / .35), clamp(d / .12))
        blit(fr, spr("e2", lambda: N.tag("1 ДАНА", size=50)), W / 2, 715, back((d - .15) / .3), clamp((d - .15) / .1))
        blit(fr, spr("e3", lambda: N.big_text("25 000 ₸", 110, (255, 255, 255), edge=False)), W / 2, 850, 1, clamp((d - .25) / .12))
        blit(fr, spr("e4", lambda: N.tag("10 ДАНА", size=46)), W / 2, 960, back((d - .35) / .3), clamp((d - .35) / .1))
        blit(fr, spr("cta", lambda: N.follow_cta()), W / 2, 1180, .96 + .04 * eo((d - .45) / .35), clamp((d - .45) / .12))

def main(out):
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "15",
                            "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709",
                            "-colorspace", "bt709", out], stdin=subprocess.PIPE)
    yy = np.linspace(0, 1, H)[:, None, None].astype(np.float32)
    grade = (1 - .5 * np.clip((yy - .55) / .30, 0, 1) ** 1.1) * (1 - .15 * np.clip((.12 - yy) / .12, 0, 1))
    rd = {}
    for n in range(int(round(TOTAL * FPS))):
        te = n / FPS
        act = [i for i, sh in enumerate(SHOTS)
               if sh[2] - TRANS.get(sh[2], ("cut", 0))[1] / 2 <= te < sh[3] + TRANS.get(sh[3], ("cut", 0))[1] / 2]
        fs = {}
        for i in act:
            if i not in rd: rd[i] = M.VR(SHOTS[i], te)
            fs[i] = rd[i].frame(te)
        for i in list(rd):
            if i not in act: rd.pop(i).close()
        if len(act) == 1: fr = fs[act[0]]
        else:
            i, j = act[0], act[1]
            kind, dur = TRANS[SHOTS[i][3]]
            fr = B.transition(kind, clamp((te - (SHOTS[i][3] - dur / 2)) / dur), fs[i], fs[j])
        fr = fr * grade
        motion(fr, te)
        M.captions(fr, te)
        if te > TOTAL - .25: fr *= clamp((TOTAL - te) / .25)
        enc.stdin.write(np.clip(fr, 0, 255).astype(np.uint8).tobytes())
    enc.stdin.close(); enc.wait()

if __name__ == "__main__":
    main(sys.argv[1])
