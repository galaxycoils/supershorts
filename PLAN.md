# Plan: Architecture Remediation and Refactoring

This plan outlines the steps to address the critical and warning findings identified during the architecture review.

## 1. Phase 1: Immediate Safety & Polish [T1]
- **Objective**: Fix runtime risks and improve documentation.
- **Tasks**:
    - Fix `AttributeError` in `src/engine/video_engine.py` (API-003).
    - Add type hints to public interfaces (API-001).
    - Rename internal functions re-exported for public use (API-004).

## 2. Phase 2: Structural Abstraction [T2]
- **Objective**: Invert dependencies and decouple modes from infrastructure details.
- **Tasks**:
    - Define abstract interfaces/protocols for `LLMService`, `TTSService`, and `VideoUploader` in `src/core/interfaces/`.
    - Refactor `src/infrastructure/` modules to implement these interfaces.
    - Update `src/modes/` to use dependency injection for infrastructure services.

## 3. Phase 3: Pipeline Consolidation [T2]
- **Objective**: Eliminate code duplication across content generation modes.
- **Tasks**:
    - Create `BaseMode` or `VideoProductionPipeline` in `src/core/`.
    - Extract shared orchestration logic (topic -> script -> TTS -> render -> compose -> upload).
    - Refactor individual modes (`brainrot`, `tcm`, `tutorial`, etc.) to subclass `BaseMode`.

## 4. Phase 4: Testability & Mocking [T2]
- **Objective**: Enable full unit testing by wrapping side-effect-heavy I/O.
- **Tasks**:
    - Implement gateway adapters for `subprocess` and `selenium`.
    - Add unit tests for `BaseMode` and `VideoEngine` using mocks for infrastructure.

## 5. Completion Criteria
- Zero critical architecture findings remain.
- Code duplication across modes reduced by >50%.
- Unit test suite covers orchestration logic without requiring external APIs or environment setup.
