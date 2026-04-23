# Service Inventory

> Updated after architecture remediation and refactoring.
> Agents MUST read this before adding logic to avoid duplicating utilities.

## Core Architecture

| Component | File | Responsibility | Key Classes/Methods |
|-----------|------|----------------|---------------------|
| Interfaces | `src/core/interfaces.py` | Abstract definitions (Protocols) | `ILLMService`, `ITTSService`, `IVideoUploader` |
| Base Mode | `src/core/base_mode.py` | Pipeline Template Method | `BaseMode.run_pipeline`, `BaseMode.produce_video` |
| Config | `src/core/config.py` | Shared settings & dataclasses | `VideoOptions`, `PROJECT_ROOT`, `OUTPUT_DIR` |

## Services (Infrastructure)

| Service | File | Responsibility | Implementation Class |
|---------|------|---------------|----------------------|
| LLM Service | `src/infrastructure/llm.py` | Ollama JSON generation | `OllamaLLMService` |
| TTS Service | `src/infrastructure/tts.py` | 3-tier speech synthesis | `StandardTTSService` |
| Uploader (API) | `src/infrastructure/uploader.py` | YouTube API uploads | `YouTubeApiUploader` |
| Uploader (Browser) | `src/infrastructure/browser_uploader.py` | Selenium-based uploads | `YouTubeBrowserUploader` |
| Video Utils | `src/infrastructure/video.py` | Pexels/Local assets | `get_relevant_pexels_video`, `get_local_background` |

## Engines

| Engine | File | Responsibility | Key Methods |
|---------|------|---------|---------|
| Video Engine | `src/engine/video_engine.py` | PIL rendering & MoviePy composition | `compose_video`, `generate_visuals` |
| Utils | `src/utils/` | Shared utilities | `cleanup:safe_close`, `text:clamp_words`, `text:strip_markdown` |

## Modes (Strategies)

All modes now subclass `BaseMode` and support dependency injection.

| Mode | File | Strategy | Implementation Class |
|--------|------|---------|-----------------------|
| Brainrot | `src/modes/brainrot.py` | Viral Shorts topics & scripts | `BrainrotMode` |
| TCM | `src/modes/tcm_educational.py` | Educational Eastern Wellness | `TCMMode` |
| Tutorial | `src/modes/tutorial.py` | 10-min Deep Dives + Shorts | `TutorialMode` |

## Established Patterns

- **Dependency Injection**: Use `ILLMService`, `ITTSService`, and `IVideoUploader` in constructors.
- **Template Method**: New modes should override `generate_script`, `generate_assets`, and `compose`.
- **8GB RAM Cleanup**: Use `src.utils.cleanup:safe_close` for all MoviePy clips.
- **Gateway Adapters**: Use `SystemAdapter` and `BrowserAdapter` for I/O to maintain unit-testability.
