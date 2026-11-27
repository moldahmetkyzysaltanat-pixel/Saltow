# PRO VIDEO EDITOR: интервью видеосын автоматты монтаждау

Бір команда түпнұсқа видеодан Reels/TikTok стиліндегі дайын роликті шығарады. Ол мыналарды жасайды:

- паузаларды кеседі;
- дыбысты тазалайды;
- HDR видеоны қалыпты түске келтіреді (color grade);
- сөйлеушінің бетіне қарай плавный zoom жасайды;
- қазақша субтитр қосады (сөз-сөзімен жарықтандырылады);
- B-roll, motion graphics, SFX және фондық музыка (ducking-пен) қосады;
- H.264/AAC форматында экспорттайды.

Түпнұсқа файл ешқашан өзгертілмейді.

## Орнату

```bash
# 1) ffmpeg (libass, zscale қолдауымен)
#    macOS:  brew install ffmpeg
#    Ubuntu: sudo apt install ffmpeg
#    Windows: https://www.gyan.dev/ffmpeg/builds/ ("full" build)
# 2) Python 3.10+
pip install -r requirements.txt
```

Whisper large-v3 моделі бірінші іске қосқанда жүктеледі (~3 GB). Әлсіз компьютерге `--whisper-model medium` жеткілікті.

## Қолдану: 3 қадам

```bash
# 1. Талдау: түсті түзету, транскрипция, паузалар, беттер
python edit.py analyze IMG_2318.MOV -p projects/safi -c config.json --language en

# 2. Қазақшаға аудару (Claude API, ANTHROPIC_API_KEY керек). Қаламасаңыз,
#    projects/safi/subtitles.json ішіндегі "kk" өрістерін қолмен толтырыңыз.
python edit.py translate -p projects/safi --context "Safi брендімен көрмедегі сұхбат"

# 3. Монтаж және экспорт
python edit.py render -p projects/safi -c config.json
#    тек 5 секундтық алдын ала көру:
python edit.py render -p projects/safi -c config.json --preview 5 --preview-start 10
```

Дайын файлдар `projects/safi/out/` қалтасына түседі:

- `final.mp4`;
- `subtitles_kk.srt`;
- `final_phone_60fps.mp4` (түпнұсқа 60 fps-тен жоғары болса).

`analyze` қадамы транскриптіні уақыт белгілерімен бірге шығарады. Сол уақыттарды (секунд, **түпнұсқа видео бойынша**) `config.json`-ға жазасыз.

## config.json: негізгі баптаулар

Толық мысал: `config.example.json`.

| Бөлім | Не береді |
|---|---|
| `cuts` | `min_pause`: осыдан ұзын паузалар қысқарады. `remove`: толық алып тасталатын бөліктер `[[басы, соңы]]`. `end_at`: қай секундта бітеді |
| `speakers` | Кімнің қай уақытта сөйлейтіні (`left`/`right`), zoom сол адамға қарай орталықтанады |
| `zoom` | `punch`: 1.2x. `emphasis`: маңызды сөздердің уақыты (жеңіл push-in) |
| `subtitles` | Субтитр стилі (төменде) |
| `broll` | `file`, `start`, `end`, `source_start`, `crop` (`w:h:x:y`), `label`, `icon` |
| `graphics` | `card`, `pill`, `badge`, `list`, `progress` түрлері, әрқайсысының `start`/`end`/`y` мәндері бар |
| `outro` | Соңғы карточка мәтіні |
| `audio.music` | `file`: өз музыкаңыз (mp3/wav). `null` болса, авторлық құқығы жоқ музыка генерацияланады. `level_db`, `duck_db` |
| `grade` | `contrast`, `saturation`, `gamma`, `warmth`, `vignette` |
| `graphics_font` | Графикаға арналған шрифт файлдары: `{"bold": "fonts/Montserrat-ExtraBold.ttf"}` |

Иконкалар: `check`, `cross`, `leaf`, `flask`, `pin`, `star`, `heart`, `arrow`.

### Субтитрді референс стильге келтіру

```jsonc
"subtitles": {
  "mode": "karaoke",            // "karaoke": сөз-сөзімен (Reels стилі), "phrase": тұтас фраза
  "font": "Montserrat ExtraBold",
  "fonts_dir": "fonts",         // .ttf/.otf файлдары жатқан қалта
  "size": 76,
  "uppercase": true,
  "color": "#FFFFFF",           // негізгі түс
  "highlight": "#FFD84A",       // айтылып жатқан сөз және *кілт сөздер*
  "outline": 7, "outline_color": "#000000", "shadow": 2,
  "position_y": 0.73,           // экран биіктігінің үлесі (0 = жоғары, 1 = төмен)
  "max_chars_per_line": 16,
  "words_per_page": 3,
  "pop": true
}
```

Шрифтте қазақ әріптері (Ә Ғ Қ Ң Ө Ұ Ү Һ І) болуы керек. Inter шрифтінде олар бар, бұл тексерілген. Басқа шрифтті (мысалы, Google Fonts-тағы Montserrat не Rubik) алдымен қысқа `--preview` арқылы тексеріңіз: әріп жоқ болса, оның орнына бос шаршы шығады.

`subtitles.json` ішінде сөзді `*жұлдызшамен*` қоршасаңыз, ол highlight түсімен шығады.

## Сақталған стильдер

Толығы `STYLE_GUIDE.md` файлында.

- **NEON LIME** (референс Reels): `config.neon.example.json` + `"subtitles": {"preset": "neon_lime"}`
- **PREMIUM EDITORIAL** (екі шрифт, обводкасыз): `"subtitles": {"preset": "premium_editorial"}`, мысал скрипт: `projects_examples/premium_reels_jainamaz.py`

## Модульдер

| Файл | Міндеті |
|---|---|
| `vedit/media.py` | ffprobe, HDR (HLG/PQ) → SDR tonemap, color grade, аудио |
| `vedit/transcribe.py` | faster-whisper, сөз деңгейіндегі уақыт белгілері |
| `vedit/timeline.py` | Паузаларды табу, түпнұсқа уақыт пен монтаж уақыты арасындағы сәйкестік |
| `vedit/faces.py` | Бет трекингі (OpenCV) |
| `vedit/render.py` | Zoom, B-roll, графика, outro |
| `vedit/gfx.py` | Графика спрайттары мен easing |
| `vedit/neon.py` | NEON LIME стилінің компоненттері (карточкалар, headline, tag, tree, interlude) |
| `vedit/subtitles.py` | ASS/SRT, karaoke және phrase стильдері |
| `vedit/audio.py` | Дауысты кесу, музыка, SFX, ducking |
| `vedit/translate.py` | Claude API (`claude-opus-5-5`) арқылы ағылшыннан қазақшаға аудару |

## Ескертулер

- `--prompt` транскрипцияға атауларды үйретеді, бірақ кейде сол мәтін транскриптіге «кіріп кетеді». Нәтижені міндетті түрде тексеріңіз.
- Аударманы әрдайым қолмен қарап шығыңыз, әсіресе есімдер мен компания атауларын.
- 120 fps 4K видео ұзақ өңделеді (90 секундтық ролик үшін шамамен 15–20 минут).
