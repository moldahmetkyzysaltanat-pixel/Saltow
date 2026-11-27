# Project memory: video editing for Instagram Reels / TikTok

The user writes in Kazakh. Answer in Kazakh.

## Always apply (the user does not repeat these each time)

Every video is edited to **grow reach and followers** on Instagram Reels and TikTok.
Follow `video_editor/REELS_GROWTH.md` on every edit, without being asked:

1. **Hook in 0–1.5 s:** open on the strongest shot, with hook text on screen within the first 0.3 s.
   No slow intro, logo or black frame.
2. **Retention:** a visual change (cut, punch-in, graphic, text) every 1.5–3 s,
   and a pattern interrupt every 4–6 s. Never let a static shot run for more than about 3 s.
3. **Subtitles on every video** (most viewers watch muted), inside the platform safe zone.
4. **Safe zone 1080×1920:** keep all text and graphics clear of the top 220 px, the bottom 400 px
   and the right 150 px (like / comment / share buttons).
5. **Value early:** the benefit, price or result appears in the first third of the video.
6. **CTA at the end, 1–1.5 s:** follow / subscribe, «сақтап қой» (save), «досыңа жібер» (send to a friend),
   or a question for the comments. Use `neon.follow_cta()`.
7. **Loop:** make the last frame flow back into the first, so the video replays.
8. **Length:** 15–35 s is best. Never shorten speech (the user's rule), but do remove pauses and fillers.
9. **Audio:** final −14 LUFS, voice clear, music at least 18–20 dB below the voice.
   Recommend that the user add a trending track inside Instagram/TikTok at low volume.
10. **With every video, also deliver:** a Kazakh caption with a hook first line and a CTA, 5–8 hashtags,
    and a suggested cover frame (time code).

## Saved styles

- **NEON LIME** (the user's favourite): `video_editor/vedit/neon.py`, `video_editor/STYLE_GUIDE.md`
- **PREMIUM EDITORIAL** (two fonts, no outline): `video_editor/projects_examples/premium_reels_jainamaz.py`
- The user's standing rules from earlier edits:
  - never cut the start or end of the voiceover;
  - cut only «ыыы / эээ» fillers;
  - subtitles without outline when the brief asks for it;
  - natural colour;
  - music must not cover the voice.

## Pipeline

- Code: `video_editor/` (README in Kazakh).
- Examples of finished edits: `video_editor/projects_examples/`.
- Fonts with Kazakh letters: `video_editor/fonts/` (Montserrat, Cormorant Garamond). Manrope lacks Kazakh letters.
- Drive links: download through `drive.usercontent.google.com` with `confirm=t&uuid=…`.
  Files that require sign-in must be shared as «Anyone with the link».
- Phone-friendly export: 1080×1920, 30 fps, H.264 High L4.2, AAC, under 60 MB.
