# SuperShorts

**Automated AI video factory — creates educational YouTube videos and viral Shorts, 100% locally.**

![Python](https://img.shields.io/badge/python-3.12%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green)

---

## What It Does

SuperShorts is a fully local, zero-API-cost video production pipeline. Point it at a topic and it will:

1. Use a local Ollama LLM to generate a structured lesson curriculum.
2. Convert each lesson into narrated slide-based video (long-form, 1920x1080) and a companion Short (1080x1920).
3. Generate viral "Brain Rot" Shorts — punchy, high-retention content with bold outlined text and attention-grabbing color palettes.
4. Upload everything to YouTube via Selenium driving your existing Firefox profile — no OAuth dance, no API keys.

No OpenAI. No Anthropic. No paid APIs of any kind.

---

## Features

- **Interactive terminal menu** — clean ASCII home screen with four options
- **AI-powered lesson curriculum** — Ollama generates a 20-lesson structured series, picks up where it left off across runs
- **Long-form educational videos** — 1920x1080, ~3-5 minutes, 7-8 content slides per lesson with intro and outro
- **Short-form YouTube Shorts** — 1080x1920, 30-60 seconds, one punchy highlight per lesson
- **Brain Rot Shorts mode** — viral AI content with bold stroke text, vignette overlays, and five attention-grabbing color palettes
- **Auto subtitle fitting** — font size scales down automatically until all text fits; never overflows a slide
- **Automated YouTube upload** — Selenium drives a pre-logged-in Firefox profile; no OAuth setup needed
- **Pexels background videos** — fetched by keyword query and cached locally so they are only downloaded once
- **Piper neural TTS** — natural-sounding voice output; falls back to pyttsx3 if the voice model is not installed
- **Progress output on all operations** — per-step print statements and clear status indicators throughout the pipeline

---

## Prerequisites

- **Python 3.12+**
- **Ollama** installed and running with the `qwen2.5-coder:3b` model pulled
- **Firefox** with a YouTube-logged-in profile (used by the Selenium uploader)
- *(Optional)* **Piper TTS** voice file at `~/.local/share/piper-tts/voices/en-us-lessac-medium.onnx` for natural neural speech
- *(Optional)* Gameplay MP4 files placed in `assets/gameplay/` for Brain Rot background videos

---

## Setup

```bash
git clone https://github.com/galaxycoils/supershorts
cd supershorts
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
ollama pull qwen2.5-coder:3b
```

Make sure Ollama is running before starting the pipeline:

```bash
ollama serve
```

---

## Usage

```bash
python main.py
```

The terminal menu appears:

```
  ____                       ____  _                _
 / ___| _   _ _ __   ___ _ _/ ___|| |__   ___  _ __| |_ ___
 \___ \| | | | '_ \ / _ \ '__\___ \| '_ \ / _ \| '__| __/ __|
  ___) | |_| | |_) |  __/ |   ___) | | | | (_) | |  | |_\__ \
 |____/ \__,_| .__/ \___|_|  |____/|_| |_|\___/|_|   \__|___/
              |_|
                          v1.0  |  Powered by Ollama + MoviePy

=================================================================

  [1]  Start YouTube Video Generation
  [2]  Generate Brain Rot Shorts
  [3]  View Content Plan
  [4]  Exit
```

| Option | Description |
|--------|-------------|
| **[1] Start YouTube Video Generation** | Loads `content_plan.json` (auto-generates if missing), picks the next pending lessons, produces long-form video + companion Short for each, and uploads both to YouTube. |
| **[2] Generate Brain Rot Shorts** | Loads `brainrot_plan.json` (auto-creates if missing), generates viral topic scripts via Ollama, renders bold-styled slides, composes Shorts, and uploads them. |
| **[3] View Content Plan** | Prints a table of all lessons with chapter, part, completion status, and title. |
| **[4] Exit** | Quits the program. |

---

## Project Structure

```
supershorts/
├── main.py                  # Entry point — launches menu; also contains the lesson production pipeline
├── menu.py                  # Interactive terminal menu and banner
├── src/
│   ├── generator.py         # Core engine: Ollama curriculum/content generation, TTS, PIL slide rendering, MoviePy video composition
│   ├── brainrot.py          # Brain Rot viral Shorts pipeline: topic gen, punchy scripting, outlined-text slides, fast video assembly
│   ├── browser_uploader.py  # YouTube upload via Selenium + Firefox browser profile
│   └── uploader.py          # YouTube Data API v3 OAuth upload (backup method)
├── assets/
│   ├── backgrounds/         # Slide background images (JPG/PNG)
│   ├── fonts/               # arial.ttf used for all text rendering
│   ├── music/               # bg_music.mp3 looped under all videos
│   └── gameplay/            # (Optional) MP4 gameplay clips for Brain Rot backgrounds
├── output/                  # All generated files: audio, slides, and final MP4s
├── content_plan.json        # Lesson curriculum with chapter/part/title/status/youtube_id (auto-generated)
└── brainrot_plan.json       # Brain Rot topic tracking with hook/angle/status (auto-created on first run)
```

---

## How It Works

```
Ollama (local LLM — qwen2.5-coder:3b)
    |
    | generates curriculum (content_plan.json)
    | generates lesson slides + short highlight + hashtags
    | generates brain rot topics, hooks, and scripts
    v
Piper TTS  (falls back to pyttsx3)
    |
    | converts narration text to .wav per slide
    v
PIL (Pillow)
    |
    | renders slide images at 1920x1080 (long) or 1080x1920 (short/brain rot)
    | auto-scales font until all text fits the content box
    | brain rot mode: bold stroke text, vignette, accent bar, random color palette
    v
MoviePy
    |
    | loads Pexels background video (cached) or local gameplay clip
    | composites slide images over background with fade in/out
    | mixes narration audio + background music loop
    | encodes to H.264 .mp4 (ultrafast preset, 24fps)
    v
Selenium + Firefox
    |
    | drives pre-logged-in Firefox profile
    | uploads .mp4, title, description, tags to YouTube
    | waits 30 seconds between long-form and Short uploads
```

---

## Configuration

Key constants in `src/generator.py`:

| Variable | Default | Description |
|----------|---------|-------------|
| `YOUR_NAME` | `"Chaitanya"` | Creator name shown in slide footers, video descriptions, and channel branding |
| `PEXELS_API_KEY` | *(set yours)* | Pexels API key for fetching background videos |
| `LESSONS_PER_RUN` | `2` | Number of lessons processed per invocation of option [1] |
| `SHORTS_PER_RUN` | `3` | Number of Brain Rot Shorts produced per invocation of option [2] |

To change the Ollama model, update the `model` variable inside `ollama_generate()` in `src/generator.py`.

---

## Requirements

```
ollama
pyttsx3
pydub
moviepy==1.0.3
Pillow==9.5.0
google-api-python-client
google-auth-httplib2
google-auth-oauthlib
requests
```

Install with:

```bash
pip install -r requirements.txt
```

---

## Notes

- **YouTube upload** uses Selenium to drive your existing Firefox profile. Log in to YouTube in Firefox once; SuperShorts handles the rest — no OAuth credentials or API keys required.
- **Ollama must be running** before starting either pipeline. Launch it with `ollama serve` in a separate terminal.
- **All AI generation is 100% local.** No calls are made to OpenAI, Anthropic, or any other paid AI service.
- **Pexels videos are cached** in `assets/pexels/` by video ID. Repeated runs reuse downloaded files.
- **Generated files accumulate** in `output/`. Audio clips, slide images, and MP4s are not cleaned up automatically — periodically delete stale files to reclaim disk space.
- **macOS note**: the code sets ImageMagick's binary path to `/opt/homebrew/bin/convert`. Adjust in `src/generator.py` if your installation differs.

---

## License

MIT
