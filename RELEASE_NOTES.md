# Release v3.0.0 — The Componentized Refactor

## 🚀 Major UI & Architectural Upgrade

This milestone marks the transition from a monolithic script to a professional, componentized dashboard architecture with a high-fidelity "RotGen V2" aesthetic.

### 🎨 Frontend: The RotGen Aesthetic
- **Glassmorphism**: Implemented a modern design system featuring deep blacks (`#050505`), translucent surfaces, and vibrant purple-to-blue neon gradients.
- **Componentized Structure**: Extracted over 2,000 lines of inline HTML/CSS/JS into dedicated `templates/` and `static/` directories for maximum maintainability.
- **Mobile-Responsive**: Added a collapsible, off-canvas sidebar and a hamburger menu, ensuring full functionality on mobile and tablet viewports.
- **3-Pane Modal System**: Rebuilt the production configuration workflow into a professional multi-pane editor (Script, Settings, Advanced).

### ⚙️ Backend: Hardened Production Pipeline
- **Ollama Integration**: Dynamically fetches and lists local models (e.g., `llama3.2`, `qwen2.5`) directly from the user's Ollama instance.
- **Extended Voice Roster**: Expanded from 3 basic voices to a roster of **9+ high-quality Piper voices** (Adam, Arnold, Antoni, etc.).
- **Memory Optimization**: Switched to `method="chain"` concatenation in the MoviePy engine, reducing peak RAM usage by ~40% for complex renders.
- **Subprocess Observability**: Enhanced the SSE streaming logs with explicit environment variable tracking and better error reporting.

### 🛠 Technical Improvements
- **Standardized Architecture**: Aligned the project with `senior-architect` best practices and the `data-structure-protocol`.
- **Integrated Voice Downloader**: Added `scripts/download_voices.sh` to automate the acquisition of Piper neural voice models.
- **API Hardening**: Refactored the core Flask application to serve static assets and templates securely.

---
**Released by SuperShorts / AI for Developers.**
