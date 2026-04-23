# Rotgen Clone & Core Systems Overhaul Plan

## 1. UI & Functional Parity (Rotgen Clone)
- **Model Selection:** The dashboard already queries `localhost:11434/api/tags` for installed Ollama models. We will ensure the "LLM Model Override" dropdown in the advanced settings dynamically populates these models perfectly.
- **Voice Expansion:** Expand `PIPER_VOICES` significantly to match the variety seen in Rotgen (e.g., Adam, Arnold, Antoni equivalents). We will add a utility script to auto-download missing Piper `.onnx` models from HuggingFace to ensure they work out-of-the-box.
- **Gallery Redesign:** Completely overhaul the "Recent Productions" (Gallery) section to feature a modern, grid-based masonry or clean list layout with thumbnails, status badges, and quick-action buttons (Play, Delete, Open), mirroring a premium SaaS dashboard.

## 2. Production & Upload Pipeline Verification
- Deploy `qa-tester` and `debugger` agents to rigorously test the end-to-end pipeline (Brainrot, TCM, RotGen).
- Ensure `browser_uploader` or API uploaders handle authentication robustly. If credentials (e.g., `client_secrets.json`) are missing, the UI will clearly indicate this state rather than crashing silently.

## 3. Automation & Permissions
- Update `.gemini/GEMINI.md` or `.claude.json` to configure auto-approval thresholds, honoring your request to "do the tasks without asking for approval".
- Integrate `context7-cli` to fetch and synchronize relevant Claude skills for extended capabilities.

## 4. Documentation & Release
- Rewrite `README.md` completely. Add detailed sections: Architecture, Setup (Ollama, Piper), Modes (Brainrot, TCM), and UI screenshots placeholders.
- Automate a GitHub release using `gh release create` and attach the generated binaries/source code.

## 5. Multi-Agent Orchestration
- We will execute parallel reviews using `performance-reviewer`, `ui-design-system`, `code-review`, `quality-reviewer`, and `critic` to ensure the resulting codebase is bulletproof and optimized.
- Apply `caveman-compress` to compress internal logs and memory files for efficiency.
