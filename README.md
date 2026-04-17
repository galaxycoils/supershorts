# SuperShorts v2.7

**Fully local AI video factory — educational series, viral Shorts, RotGen character mode, TCM content, automated video clipping, and a workflow engine. Zero paid APIs.**

<p align="center">
  <img src="assets/supershorts_poster.png" alt="SuperShorts" width="340"/>
</p>

![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![Ollama](https://img.shields.io/badge/LLM-Ollama%20local-orange)
![MoviePy](https://img.shields.io/badge/video-MoviePy%201.0.3-red)
![Rich](https://img.shields.io/badge/UI-Rich%20TUI-purple)
![License](https://img.shields.io/badge/license-MIT-green)

---

## What It Does

SuperShorts is a fully local, fully automated video production pipeline. Run `python main.py` on any Mac or Linux box and it writes scripts, narrates audio, edits videos, adds subtitles, and uploads to YouTube — entirely on-device with local Ollama LLM and no paid cloud services.

**v2.7 adds:** Rich terminal UI, TCM Educational Mode, Automatic Video Clipper, a JSON-based Workflow Engine with built-in scheduling, and post-upload output cleanup.

---

## Menu — 12 Options

```
  [1]   📚  Educational Videos        Long-form + linked Short (curriculum-based)
  [2]   🧠  Brain Rot Viral Shorts    Sensationalized AI shorts, 30–45 s
  [3]   🎮  Viral Gameplay Mode       Subway Surfers-style background + AI narration
  [4]   🎓  Tutorial Videos           ~10-min deep-dive + linked Short
  [5]   📈  Learning Mode             Self-improvement analysis from past uploads
  [6]   💡  YouTube Studio Ideas      Real YT suggestions, thumbnails & scripts
  [7]   📋  View Content Plan         Browse lessons + brain rot topic tracker
  [8]   🎭  RotGen Character Mode     ByteBot AI character + gameplay + auto-subtitles
  [9]   📦  YouTube Content Package   Expert AI: topic → script → 5-min video → upload
  [10]  ✂️  Automatic Video Clipper   Long YouTube/podcast → viral vertical Shorts
  [11]  🌿  TCM Educational Mode      Traditional Chinese Medicine content series
  [12]  🚪  Exit
```

Live stats bar shows lesson + brain rot progress on every menu render.

---

## New in v2.7

### Rich Terminal UI
All menus, tables, progress output, and prompts now use the `rich` library. Panel headers, aligned tables, `console.status()` spinners during Ollama calls, color-coded success/error/warning output — zero raw ANSI escape codes.

### Workflow Engine (`run_workflow.py`)
JSON-defined automation pipelines with dependency graphs, parallel wave execution, retry logic, and execution summaries.

```bash
python run_workflow.py --list                              # list available workflows
python run_workflow.py --validate workflows/daily.workflow.json
python run_workflow.py workflows/daily.workflow.json       # run it
```

Three pre-built workflows in `workflows/`:
| Workflow | Schedule | Content |
|----------|----------|---------|
| `daily.workflow.json` | 9 AM daily | 2 educational + 3 brainrot (parallelized) |
| `tcm-weekly.workflow.json` | Monday 10 AM | 5 TCM shorts |
| `full-pipeline.workflow.json` | manual | all modes in sequence |

### Post-Upload Output Cleanup
After every successful upload: saves a tiny reference JSON to `output/uploaded/` then deletes the large `.mp4` to free disk. Thumbnail and logs kept.

### Subtitle Overflow Fix
Subtitle fallback renderer now forces a 2-line midpoint split instead of rendering all text on a single unbounded line. Subtitles never bleed past frame edge.

---

## RotGen Character Mode (Option 8)

Animated AI character talking over gameplay, fully auto-pilot.

**Layout (1080×1920):**
```
┌────────────────────────────┐  y=0
│  CHARACTER PANEL  (768px)  │  ByteBot animated avatar, dark gradient
├────────────────────────────┤  y=768
│  GAMEPLAY VIDEO   (992px)  │  subway surfers / minecraft / Pexels auto
├────────────────────────────┤  y=1760
│  SUBTITLE BAR    (160px)   │  current spoken text, 4-word chunks
└────────────────────────────┘  y=1920
```

**ByteBot character (`assets/characters/bytebot.png`):**
- PIL-drawn cartoon AI avatar, cyan glowing eyes, circuit traces, visor + LED dots, ByteBot badge
- 48-frame animation loop (2 s at 24 fps): head bob, mouth pulse, eye blink

**Auto-pilot flow:**
1. Viral AI topic picked from hook pool
2. Ollama generates ≤60-word ByteBot monologue
3. Piper TTS (pyttsx3 fallback)
4. 48 character frames pre-rendered, freed after `gc.collect()`
5. Gameplay: `assets/viral_gameplay/` → `assets/gameplay/` → Pexels
6. Proportional subtitle chunks composited as `ImageClip` layers
7. H.264 ultrafast, 24 fps, AAC 192k, 3 threads
8. Logged to `rotgen_plan.json`

Drop any RGBA PNG into `assets/characters/` to replace ByteBot.

---

## TCM Educational Mode (Option 11)

Generates Traditional Chinese Medicine / Eastern wellness content series via Ollama.

**Setup:**
1. Select topic: TCM (default), Eastern Medicine, Ayurvedic, Holistic, or custom
2. Add optional sub-topics (e.g. "focus on sleep, anxiety")
3. Pick video count (1–10)
4. Ollama auto-generates a 10-lesson curriculum → saved to `tcm_plan.json`
5. Generates short-form videos and uploads; resumes from last saved state on re-run

---

## Automatic Video Clipper (Option 10)

Converts long YouTube videos or podcasts into viral vertical Shorts using the kirat11X clipper pipeline.

**One-time setup:**
```bash
# 1. Clone kirat11X clipper repo
# 2. Copy all .py files into src/clipper/
cp kirat11X-repo/*.py src/clipper/
touch src/clipper/__init__.py
# 3. Install clipper deps (torch, faster-whisper, mediapipe, etc.)
pip install -r requirements.txt
```

Then run option 10, paste a YouTube URL or local video path — vertical Shorts appear in `outputs/clipper/`.

> Option 10 shows a setup panel with full instructions if `src/clipper/run_pipeline.py` is not found.

---

## Features

| Feature | Detail |
|---------|--------|
| **Educational curriculum** | Ollama generates a 20-lesson series; resumes where it left off |
| **Long-form videos** | 1920×1080, 7-8 slides, Pexels background, TTS + music |
| **Brain Rot Shorts** | 1080×1920, stroke text, 5 palettes, vignette, fast pacing |
| **Tutorial mode** | ~10-min deep-dive + linked Short, auto-uploaded pair |
| **Viral Gameplay mode** | Educational content with forced gameplay background |
| **YouTube Studio Ideas** | Real YouTube Data API v3 → real thumbnails + Ollama script |
| **Learning mode** | Ollama analyses upload history, writes improvement suggestions |
| **RotGen Character mode** | Animated character + gameplay + subtitles — see above |
| **YouTube Content Package** | Expert AI strategist: trending topic → 5-min video → upload |
| **TCM Educational Mode** | TCM / Eastern wellness content, Ollama curriculum, batch upload |
| **Automatic Video Clipper** | YouTube → viral vertical Shorts (kirat11X pipeline) |
| **Workflow Engine** | JSON pipelines, dependency graphs, retry, cron-ready |
| **Rich TUI** | Panels, tables, spinners, color-coded output throughout |
| **Output cleanup** | mp4 deleted post-upload; reference JSON saved to output/uploaded/ |
| **Subtitle safe zone** | Auto-scale + 2-line fallback; subtitles never overflow screen |
| **Emoji-safe TTS** | Unicode regex strips all emoji ranges before speech |
| **Pexels caching** | Videos downloaded once, reused across runs |
| **Piper neural TTS** | Natural voice; pyttsx3 fallback if voice model missing |
| **tqdm progress bars** | ETA on every TTS, slide render, and video build loop |

---

## Prerequisites

- **Python 3.12+**
- **Ollama** running with `qwen2.5-coder:3b` pulled (`ollama pull qwen2.5-coder:3b`)
- **Firefox** logged in to YouTube (Selenium drives this profile)
- **Pexels API key** — set `PEXELS_API_KEY` in `src/generator.py`
- *(Optional)* **Piper TTS** at `~/.local/share/piper-tts/voices/en-us-lessac-medium.onnx`
- *(Optional)* Gameplay MP4s in `assets/viral_gameplay/` for offline gameplay backgrounds
- *(Optional)* YouTube Data API key for Option 6 (prompted on first run, saved to `config.json`)
- *(Option 10 only)* kirat11X clipper files in `src/clipper/` + heavy deps (torch, faster-whisper, etc.)

---

## Setup

```bash
git clone https://github.com/galaxycoils/supershorts
cd supershorts
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
ollama serve &
ollama pull qwen2.5-coder:3b
python main.py
```

---

## Project Structure

```
supershorts/
├── main.py                    # Entry point — menu dispatch + lesson pipeline
├── menu.py                    # Rich TUI: panels, tables, stats, content plan
├── run_workflow.py            # Workflow engine: dependency graph, execution, logging
├── workflows/
│   ├── daily.workflow.json    # Daily: 2 edu + 3 brainrot (parallel)
│   ├── tcm-weekly.workflow.json  # Weekly TCM batch (5 shorts)
│   └── full-pipeline.workflow.json  # Full run: all modes
├── src/
│   ├── generator.py           # Core: LLM gen, TTS, PIL slides, MoviePy compose
│   ├── brainrot.py            # Brain Rot: topics, scripts, stroke slides, video
│   ├── rotgen.py              # RotGen: ByteBot animation, subtitles, compose
│   ├── tcm_mode.py            # TCM Educational Mode
│   ├── clipper_mode.py        # Video Clipper wrapper (kirat11X)
│   ├── ideagenerator.py       # YouTube Studio Ideas: YT API v3 + Ollama
│   ├── captions.py            # Universal subtitle overlay (all video modes)
│   ├── learning.py            # Upload logger + Ollama improvement analysis
│   ├── browser_uploader.py    # YouTube upload via Selenium + Firefox
│   └── uploader.py            # YouTube Data API v3 OAuth upload (backup)
├── assets/
│   ├── characters/            # Drop custom PNG here to replace ByteBot
│   │   └── bytebot.png        # Default ByteBot RGBA avatar (400×500)
│   ├── backgrounds/           # Slide background images
│   ├── fonts/arial.ttf        # Font for all text rendering
│   ├── music/bg_music.mp3     # Background music (looped)
│   ├── gameplay/              # Local gameplay clips (optional)
│   ├── viral_gameplay/        # Subway Surfers / Minecraft clips (optional)
│   └── pexels/                # Cached Pexels background videos
├── output/
│   └── uploaded/              # Reference JSONs (post-upload mp4 cleanup)
├── content_plan.json          # Lesson curriculum (auto-generated)
├── brainrot_plan.json         # Brain Rot topic tracker
├── rotgen_plan.json           # RotGen video log
├── tcm_plan.json              # TCM curriculum tracker
├── performance_log.json       # Upload history for Learning mode
└── requirements.txt
```

---

## Pipeline Diagram

```
Ollama (qwen2.5-coder:3b, local)
    │
    ├─ curriculum / lesson content / brainrot scripts / rotgen monologue / TCM topics
    │
    ▼
Piper TTS  (pyttsx3 fallback)
    │
    ├─ narration → .wav per slide / per video
    │
    ▼
PIL (Pillow 12.2+)
    │
    ├─ slide images 1920×1080 or 1080×1920
    ├─ auto_scale_text: shrink font until fits
    ├─ brainrot: stroke text + numpy vignette gradient
    ├─ rotgen: 48-frame character animation at 24fps
    ├─ subtitles: 4-word chunks, 2-line safe fallback (never overflows)
    │
    ▼
MoviePy 1.0.3
    │
    ├─ CompositeVideoClip: background + slide/character + subtitle ImageClips
    ├─ Pexels auto-download + cache
    ├─ H.264 ultrafast, 24fps, AAC 192k, 3 threads
    │
    ▼
Selenium + Firefox  (YouTube upload)
    │
    ▼
Post-upload cleanup
    ├─ Reference JSON → output/uploaded/
    └─ mp4 deleted to free disk
```

---

## Workflow Engine

Define automation pipelines in JSON, run them directly or schedule via cron.

```bash
# Run daily pipeline
python run_workflow.py workflows/daily.workflow.json

# Validate a workflow (checks deps, function registry)
python run_workflow.py --validate workflows/daily.workflow.json

# List all workflows
python run_workflow.py --list
```

**Workflow features:**
- Dependency graph + topological sort → tasks run in correct order
- Parallel wave execution (independent tasks run in same wave)
- Per-task retry with configurable attempts + delay
- Timing and status table printed on completion
- Execution logs saved to `output/workflow_logs/`

**Example: add to system crontab for fully automated daily runs:**
```bash
crontab -e
# Add:
3 9 * * * cd /path/to/supershorts && source venv/bin/activate && python run_workflow.py workflows/daily.workflow.json
```

---

## Configuration

**`src/generator.py` constants:**

| Variable | Default | Description |
|----------|---------|-------------|
| `YOUR_NAME` | `"Chaitanya"` | Creator name in footers, descriptions, branding |
| `PEXELS_API_KEY` | set yours | Pexels API key for background videos |

**YouTube Data API key** (Option 6): prompted on first use, saved to `config.json`.

---

## Requirements

**Core:**
```
ollama  pyttsx3  pydub  moviepy==1.0.3  Pillow>=12.2.0
requests  selenium  webdriver-manager  tqdm  rich
google-api-python-client  google-auth-httplib2  google-auth-oauthlib
```

**Option 10 — Video Clipper (install when needed):**
```
yt-dlp  ffmpeg-python  librosa  soundfile  faster-whisper
torch  sentence-transformers  scikit-learn  opencv-python  mediapipe
numpy  scipy  python-dateutil
```

---

## Notes

- **Ollama must be running** — `ollama serve` before launching
- **All AI is local** — no paid APIs; Pexels is the only external network dependency (cached after first use)
- **Custom RotGen character** — drop any RGBA PNG into `assets/characters/`
- **Output cleanup** — uploaded mp4s are auto-deleted; reference JSONs in `output/uploaded/` track all uploads
- **Memory-safe** — explicit `.close()` + `gc.collect()` after every video; peak RAM ~115MB on M1
- **macOS note** — ImageMagick binary at `/opt/homebrew/bin/convert`; adjust in `generator.py` if needed
- **Upload stability** — `src/browser_uploader.py` uses Firefox Selenium profile; log into YouTube once in Firefox and it works indefinitely

---

## Changelog

### v2.7 — 2026-04-17
- **Rich TUI**: full terminal UI rewrite — Panel headers, rich tables, spinners, color-coded output; removed all raw ANSI escape codes
- **Option 10 — Automatic Video Clipper**: wrapper for kirat11X clipper pipeline; YouTube/local video → viral vertical Shorts; setup panel if pipeline not installed
- **Option 11 — TCM Educational Mode**: Traditional Chinese Medicine content series; 4-topic selector (TCM, Eastern, Ayurvedic, Holistic, custom); Ollama auto-generates 10-lesson curriculum; batch upload with plan resume
- **Workflow Engine** (`run_workflow.py`): JSON-defined pipelines, topological dependency graph, parallel wave execution, retry, execution logs; 3 pre-built workflows
- **Post-upload output cleanup**: mp4 auto-deleted after upload; reference JSON saved to `output/uploaded/`
- **Subtitle overflow fix**: fallback renderer now forces 2-line midpoint split — subtitles never bleed past frame edge
- **Bare exception fix**: `src/browser_uploader.py` replaces bare `except:` with `except Exception:` throughout

### v2.6 — 2026-04-17
- **Interactive batch count**: Options 1, 2, 8 prompt "How many videos?" (1–10) at startup; warns if >5 on 8 GB RAM
- **M1 8 GB RAM**: explicit `VideoFileClip.close()` + `AudioFileClip.close()` + `gc.collect()` after every video
- **PIL cleanup**: `Image.close()` after each slide save
- **Temp audio cleanup**: slide audio WAV/MP3 deleted after video composition
- **Bug fix**: ephemeral `AudioFileClip` leak in duration-sum expressions now properly closed
- **Bug fix**: `build_gameplay_clip` raw `VideoFileClip` closed after resize (rotgen.py)

### v2.5 — 2026-04-17
- Universal subtitles across all video modes via `src/captions.py`
- 35–45 s Shorts enforcement (99–127 words at 170 wpm)
- Natural Piper TTS integration

### v2.2 — 2026-04-16
- **YouTube Content Package** (Option 9): expert AI strategist mode

### v2.0 — 2026-04-16
- **RotGen Character Mode** (Option 8): ByteBot animated avatar + gameplay + live subtitles
- **YouTube Studio Ideas** (Option 6): real YT Data API v3 suggestions
- Brain Rot performance: numpy gradient replaces pixel loop (285× speedup)
- Pillow 12.2 upgrade (patched 4 CVEs)
- tqdm progress bars, emoji-safe TTS, Learning mode

### v1.0 — initial
- Educational curriculum, Brain Rot Shorts, Selenium upload

---

## License

MIT
