# Implementation Plan: Option 2 (Stateless + Queue)

## Background & Motivation
Race conditions corrupt videos (shared frame array). Firefox profile locks fail parallel uploads. Need stateless video rendering + sequential queue for uploads.

## Scope & Impact
Files affected:
- `src/utils/captions.py` (remove cache)
- `src/infrastructure/browser_uploader.py` (refactor upload call)
- `src/infrastructure/adapters/browser_adapter.py` (add thread queue)

## Proposed Solution
- **Stateless Captions:** Remove `frame_cache` dict. Call `render_subtitle_frame` directly in `make_frame`. No shared mutable state.
- **Upload Queue:** `BrowserAdapter` runs background `threading.Thread` with `queue.Queue`. Uploads put onto queue. Thread executes one by one, bypassing Firefox profile lock issues.

## Alternatives Considered
- Option 1 (Deep copy + lock) - Rejected.
- Option 3 (API only) - Rejected (API quota limits).

## Phased Implementation Plan
1. **Fix Captions:** Open `src/utils/captions.py`. Delete `frame_cache` initialization. Update `make_frame` to generate `render_subtitle_frame(entry["text"], W)[:, :, :3]` on the fly.
2. **Build Queue:** Update `BrowserAdapter` (or create if missing) to spawn a daemon thread. Add `queue.Queue` for tasks.
3. **Refactor Uploader:** Update `YouTubeBrowserUploader.upload` in `src/infrastructure/browser_uploader.py` to push tasks to `self.browser.queue` instead of synchronous `upload_to_youtube_browser`.
4. **Worker Logic:** Worker thread pops task, calls `upload_to_youtube_browser`, and logs success/failure.

## Verification
- `pytest tests/test_render_race.py tests/test_shared_empty_frame.py` (Passes clean).
- `pytest tests/test_uploader.py tests/test_uploader_resilience.py`.

## Migration & Rollback
- Git revert changes if queue deadlocks or hangs.