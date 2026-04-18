# Service Inventory

> Updated after architectural split.
> Agents MUST read this before adding logic to avoid duplicating utilities.

## Services

| Service | File | Responsibility | Key Methods |
|---------|------|---------------|-------------|
| LLM Service | `src/infrastructure/llm.py` | Ollama JSON generation | `ollama_generate`, `safe_json_parse` |
| TTS Service | `src/infrastructure/tts.py` | 3-tier speech synthesis | `text_to_speech` |
| Asset Service | `src/infrastructure/video.py` | Pexels/Local background fetching | `get_relevant_pexels_video`, `get_local_background` |

## Engines

| Engine | File | Responsibility | Key Methods |
|---------|------|---------|---------|
| Video Engine | `src/engine/video_engine.py` | PIL rendering & MoviePy composition | `compose_video`, `generate_visuals` |
| Caption Engine | `src/captions.py` | Generator-based subtitle overlay | `add_subtitle_overlay` |

## Modes

| Mode | File | Strategy | Entry Point |
|--------|------|---------|---------|
| Brainrot | `src/brainrot.py` | Viral Shorts topics & scripts | `run_brainrot_pipeline` |
| TCM | `src/tcm_mode.py` | Educational Eastern Wellness | `run_tcm_mode` |
| Tutorial | `src/modes/tutorial.py` | 10-min Deep Dives + Shorts | `start_tutorial_generation` |
| Viral | `src/modes/viral.py` | Forced Gameplay & Packages | `generate_youtube_content_package` |

## Established Patterns

- **8GB RAM Cleanup**: Use `src.utils.cleanup:safe_close` for all MoviePy clips.
- **Stateless Infrastructure**: Infrastructure services should not hold global state.
- **Generator Subtitles**: Use `VideoClip` generator in `captions.py` to avoid memory spikes.
