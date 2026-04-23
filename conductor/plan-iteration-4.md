# Plan: Deep UI & Pipeline Fixes

## 1. Plan Review & Missing Elements
The current implementation of the dashboard looks modern but lacks functional depth for several requested features:
- **Character Icons:** `static/js/main.js` references placeholder images (e.g., `peter.png`) instead of scraped/generated icons. We need to implement a fallback or download actual icons.
- **Tone Selector:** The "Funny" option in the UI is not wired to any JavaScript state or backend prompt modifier.
- **Auto-Generate:** The "Auto-generate from viral trends" toggle exists in HTML but lacks backend trend-fetching logic.
- **LLM Temperature:** Missing descriptive tooltips explaining what Temperature 0.0 vs 1.0 means for creativity.
- **RAM Stats:** `dashboard.py` doesn't fetch RAM; the UI shows `-- GB`. We need to add `psutil` or `os` calls.
- **Model Selection:** `/api/models` fetches tags but doesn't highlight recommended models (e.g., `qwen2.5-coder` for scripts, `llama3.2` for general reasoning).
- **TCM Mode:** Fails due to potentially missing `VideoOptions` arguments or script format.
- **Background Videos:** Fallbacks in `video_engine.py` either fail silently or return dark backgrounds if Pexels API fails.

## 2. Multi-Agent Execution Strategy (Parallel & Sequential)
Running 10 agents strictly in parallel will cause Git conflicts. I will orchestrate them:
- **Phase 1 (Diagnosis):** `codebase_investigator`, `debugger`, `critic`.
- **Phase 2 (Implementation):** `build-fixer`, `ui-ux-pro-max`, `code-simplifier`.
- **Phase 3 (Validation):** `code-reviewer`, `test-engineer`, `qa-tester`.

## 3. Visual Review HTML
I have generated the `visual-explainer-extension` plan review. Since I am in Plan Mode, I cannot write `.html` files outside of `conductor/`. The HTML review is included below as a code block.

Once you approve this plan, I will exit Plan Mode and execute the fixes.