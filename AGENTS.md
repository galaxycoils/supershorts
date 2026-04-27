# SuperShorts — Codex / Agent CLI Context

### MANDATORY PROTOCOL: Universal State Handoff
Read `/Users/cmd/Documents/Obsidian Vault/SuperShorts/STATE_HANDOFF.md` IMMEDIATELY upon starting session. This is your "Second Brain".
1. **Sync**: Pick up context from Gemini/Claude.
2. **Learn**: Log bugs, patterns, and decisions during work.
3. **Handover**: Update status/next actions before closing.

### PROTOCOL 1: Universal Skill Library
Master logic resides in `/Users/cmd/Documents/Obsidian Vault/SuperShorts/Skills/`.
1. **Lookup**: Check Obsidian for specialized skill workflows before acting.
2. **Execute**: Adhere to "Core Rules" in the skill note.
3. **Evolve**: Log new patterns/fixes to "Evolved Learnings" to improve future agent performance.
- **Metaswarm Development**: Follow the full development pipeline (Research → Plan → Design Review → Implementation → Verification).
- **TDD Requirement**: Write tests before implementation. 100% coverage is mandatory as defined in `.coverage-thresholds.json`.

## What This Is
Fully local AI video pipeline. Given a topic, it generates a YouTube Short end-to-end:
script (Ollama LLM) → voiceover (Piper TTS) → slides (PIL) → video composition (MoviePy) → upload (Selenium).
No cloud APIs required. Pexels video cache covers backgrounds even without an API key.

## How to Run
```bash
cd /Users/cmd/money-printer-v2
source venv/bin/activate
python dashboard.py            # starts Flask on :5000
```

## Project Layout
```
dashboard.py                   Flask app + job runner + API
src/
  core/
    config.py                  Constants, paths, VideoOptions
    base_mode.py               Abstract BaseMode (Template Method)
    interfaces.py              ILLMService, ITTSService, IVideoUploader
  infrastructure/
    llm.py                     Ollama wrapper — NEVER raises, returns {} on fail
    tts.py                     Piper TTS
    video.py                   Background resolution (pexels fallback)
    browser_uploader.py        Selenium YouTube upload
  engine/
    video_engine.py            compose_video(), generate_visuals()
  modes/
    tcm_educational.py         TCM curriculum (headless env-var mode)
    brainrot.py
    rotgen.py
    clipper.py
static/js/main.js              Frontend state machine
templates/index.html           Dashboard HTML
scripts/generate_avatars.py    PIL avatar generator tool
assets/
  pexels/                      41 cached background videos (primary fallback)
  gameplay/                    Empty — use pexels/ fallback
  backgrounds/                 Static image backgrounds
  music/                       Background music tracks
```

## Critical Patterns

### LLM Output Validation (always do this)
```python
result = llm.generate(prompt, json_mode=True)
# result may be {} — never raises
lessons = result.get("lessons") if isinstance(result, dict) else None
if not lessons:
    return fallback
```

### Pending Topic Filter
```python
# Correct — rejects both legacy statuses
pending = [l for l in plan["lessons"] if l.get("status") not in ("complete", "published")]
```

### Background Video Fallback
```python
# get_local_gameplay() checks:
# 1. assets/gameplay/*.mp4
# 2. assets/pexels/*.mp4 (cache fallback)
```

## API Endpoints
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/run/{mode}` | POST | Launch production job |
| `/api/stream/{job_id}` | GET | SSE job output stream |
| `/api/models` | GET | List Ollama models + recommendations |
| `/api/health` | GET | Ollama status + RAM + uptime |
| `/api/gallery` | GET | List output/*.mp4 files |
| `/api/assets` | GET | List backgrounds, characters, music |
| `/api/stats` | GET | Upload counts by mode |

## Dashboard Run Payload (POST /api/run/tcm)
```json
{
  "count": 3,
  "voice": "en_US-ryan-high",
  "llm_model": "llama3",
  "temperature": 0.7,
  "dry_run": "n",
  "tcm_topic": "1",
  "tcm_extra": "focus on sleep"
}
```
Dashboard sets env vars: `TCM_TOPIC`, `TCM_EXTRA`, `TCM_COUNT`, `TCM_USE_EXISTING=n`.

## Code Style
- Python 3.10+, type hints preferred
- No comments unless WHY is non-obvious
- Interfaces in `src/core/interfaces.py` — prefer injecting mocks in tests
- PIL uses `Image.Resampling.LANCZOS` (not deprecated `ANTIALIAS`)
- All paths as `pathlib.Path`

## Testing Snippets
```bash
# TCM pipeline smoke test
python3 -c "
from src.modes.tcm_educational import TCMMode, generate_tcm_curriculum
class FakeLLM:
    def generate(self, p, json_mode=True): return {}
plan = generate_tcm_curriculum('TCM', '', llm_service=FakeLLM())
assert plan['lessons'][0]['status'] == 'pending'
print('OK')
"

# Background video
python3 -c "from src.infrastructure.video import get_local_gameplay; r=get_local_gameplay('short'); assert r; print('BG:', r)"

# JS syntax
node --check static/js/main.js && echo OK
```
