# SuperShorts — Gemini CLI Context

## Project
AI video factory. Topic → YouTube Short. Fully local (Ollama LLM + Piper TTS + MoviePy).
Repo: https://github.com/galaxycoils/supershorts
Local: /Users/cmd/money-printer-v2
Current version: v3.4.0

## Run
```bash
source venv/bin/activate
python dashboard.py  # http://localhost:5000
```

## Stack
- Python 3.10+ / Flask 3.x
- Ollama (local LLM, default model set via OLLAMA_MODEL env var)
- Piper TTS (local neural voices)
- MoviePy + FFmpeg (video composition)
- PIL/Pillow (slide generation)
- Selenium + Firefox (YouTube auto-upload)

## Key Files
| File | Role |
|------|------|
| `dashboard.py` | Flask app, job runner, `/api/run/{mode}`, SSE streaming |
| `src/core/config.py` | All constants, paths, VideoOptions dataclass |
| `src/core/base_mode.py` | BaseMode: run_pipeline() Template Method |
| `src/infrastructure/llm.py` | Ollama wrapper, safe_json_parse, returns `{}` on failure |
| `src/infrastructure/video.py` | Background resolution (pexels cache fallback) |
| `src/engine/video_engine.py` | compose_video(), generate_visuals() |
| `src/modes/tcm_educational.py` | TCM curriculum pipeline, headless env-var mode |
| `static/js/main.js` | Frontend state machine, modal, SSE consumer |

## Architecture
```
Dashboard POST /api/run/{mode}
  → subprocess with env vars
    → run_*_mode()
      → BaseMode.run_pipeline()
        → generate_script() [Ollama]
        → generate_assets() [PIL + Piper]
        → compose_video() [MoviePy]
        → upload() [Selenium]
```

## Background Video Chain
1. `custom_bg` if set
2. `force_viral_bg` → `assets/viral_gameplay/`
3. Pexels API (needs `PEXELS_API_KEY`)
4. `assets/gameplay/` (often empty)
5. `assets/pexels/` — 41 cached clips ← primary fallback

## LLM Gotcha
`ollama_generate()` NEVER raises. Returns `{}` on all failures.
Always check `result.get("key")` before using LLM output.

## Modes
tcm, brainrot, rotgen, tutorial, viral, clipper, ideas, package, learning

## Characters (voice IDs)
adam=en_US-ryan-high, antoni=en_US-lessac-high, amy=en_US-amy-medium,
arnold=en_GB-alan-medium, rachel=en_US-hfc_female-medium,
joe=en_US-joe-medium, kristin=en_US-kristin-medium

## Env Vars (TCM headless mode)
TCM_TOPIC, TCM_EXTRA, TCM_COUNT, TCM_USE_EXISTING, CUSTOM_BG, CUSTOM_MUSIC,
OLLAMA_MODEL, YOUR_NAME, LLM_TEMPERATURE

## Testing
```bash
python3 -c "from src.modes.tcm_educational import TCMMode; m=TCMMode(plan={'lessons':[{'title':'T','status':'pending'}]}); print(m.get_pending_topics())"
python3 -c "from src.infrastructure.video import get_local_gameplay; print(get_local_gameplay('short'))"
```
