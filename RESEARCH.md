# Research: Architecture Review Scope

## Overview
This research phase maps the `money-printer-v2` project structure to define the scope for a comprehensive architecture review using `arxitect:architecture-review`.

## Project Structure
- **Core**: Configuration and learning logic (`src/core`).
- **Engine**: Video composition using MoviePy (`src/engine/video_engine.py`).
- **Infrastructure**: API wrappers for LLM, TTS, Pexels, and Browser Uploader (`src/infrastructure`).
- **Modes**: Specialized content generation strategies (Brainrot, TCM, Tutorial, Viral, etc. in `src/modes`).
- **Utils**: Captions, cleanup, and helper functions (`src/utils`).

## Architectural Observations
- **Stateless Infrastructure**: The project aims for stateless infrastructure services.
- **Service/Engine/Mode Separation**: There is a clear separation between high-level strategies (Modes), processing logic (Engines), and external interfaces (Infrastructure).
- **Quality Gates**: The project mandates TDD, 8GB RAM safety, and zero paid APIs.

## Review Targets
1. **Dependency Direction**: Verify that `Modes` depend on `Engines`/`Infrastructure` and not vice-versa.
2. **Resource Management**: Evaluate the effectiveness of `cleanup.py` and MoviePy clip handling for 8GB RAM constraints.
3. **API Consistency**: Check if `Infrastructure` services follow a consistent interface pattern.
4. **Modularity**: Assess if new `Modes` can be added without modifying `Engine` or `Infrastructure` core logic.
5. **Data Structure Protocol (DSP)**: Investigate the `.dsp/` directory and how it integrates with the overall architecture.
