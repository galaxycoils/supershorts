# TODO: Architecture Remediation and Refactoring

## Continue

> **Last session:** 0001 - 2026-04-19 - Key Principles
> **Paused at:** 2026-04-27T20:35:02.375Z
>
> Working directory: /Users/cmd/money-printer-v2

---

## Phase 1: Immediate Safety & Polish [backend] [T1]
- [x] Fix critical `AttributeError` in `src/engine/video_engine.py` (API-003)
  - [x] Add `slide_content = slide_content or {}` guard in `generate_visuals`
- [x] Standardize Type Hints for public interfaces (API-001)
  - [x] Add hints to `src/infrastructure/llm.py`
  - [x] Add hints to `src/infrastructure/tts.py`
  - [x] Add hints to `src/engine/video_engine.py`
  - [x] Add hints to `src/infrastructure/uploader.py`
- [x] Clean up Internal/Public function naming (API-004)
  - [x] Rename `src/utils/text.py:_clamp_words` to `clamp_words`
  - [x] Update all references in `src/generator.py` and `src/modes/`
- [x] Group long parameter lists into Dataclasses (API-005)
  - [x] Create `VideoOptions` dataclass in `src/core/config.py`
  - [x] Refactor `compose_video` in `src/engine/video_engine.py` to use `VideoOptions`

## Phase 2: Structural Abstraction [backend] [architecture] [T2]
- [x] Define Service Interfaces in `src/core/interfaces.py` [parallel]
  - [x] Define `ILLMService` (Protocols)
  - [x] Define `ITTSService`
  - [x] Define `IVideoUploader`
- [x] Refactor Infrastructure implementations [parallel]
  - [x] Update `src/infrastructure/llm.py` to implement `ILLMService`
  - [x] Update `src/infrastructure/tts.py` to implement `ITTSService`
  - [x] Standardize uploader signatures in `src/infrastructure/uploader.py` and `src/infrastructure/browser_uploader.py` (API-002)
- [x] Implement Dependency Injection in Modes
  - [x] Update `brainrot.py` to accept injected services
  - [x] Update `tcm_educational.py` to accept injected services

## Phase 3: Pipeline Consolidation [backend] [architecture] [T2]
- [x] Create `src/core/base_mode.py`
  - [x] Implement `BaseMode` abstract class with Template Method pattern (OO-001, OO-002)
  - [x] Implement shared orchestration loop (topic -> script -> TTS -> render -> compose -> upload)
- [x] Refactor individual Modes to subclass `BaseMode`
  - [x] Refactor `BrainrotMode`
  - [x] Refactor `TCMMode`
  - [x] Refactor `TutorialMode`
- [x] Consolidate duplicated utilities (OO-006)
  - [x] Merge `rotgen.py:_enforce_word_count` and `text.py:clamp_words`

## Phase 4: Testability & Mocking [test] [backend] [T2]
- [x] Implement Gateway Adapters for I/O (CA-005)
  - [x] Create `src/infrastructure/adapters/system_adapter.py` for `subprocess`
  - [x] Create `src/infrastructure/adapters/browser_adapter.py` for `selenium`
- [x] Add Unit Test Suite
  - [x] Add tests for `BaseMode` using Mock services
  - [x] Add tests for `VideoEngine` layout logic

## Phase 5: Verification & Cleanup [T1]
- [x] Run full test suite with 100% coverage check
- [x] Verify 8GB RAM safety with `src/utils/cleanup.py`
- [x] Update `SERVICE-INVENTORY.md` to reflect new architecture

---

*Last updated: 2026-04-27T20:35:02.375Z*
