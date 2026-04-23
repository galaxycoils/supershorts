# Implementation Plan: Componentized Mobile-Friendly RotGen UI

## 1. Skill Acquisition & Image Analysis
- Run shell commands to import or load the requested Claude skills (`ui-ux-pro-max`, `senior-architect`, `frontend-design`, `senior-backend`, `senior-frontend`, `senior-fullstack`, `data-structure-protocol`, `file-organizer`) into the workspace context.
- Deploy the `vision` agent to deeply analyze the 4 reference images (`/Users/cmd/money-printer-v2/uiexample/*.JPG`). We will extract the exact layout structures, missing options (like voice styles, durations, detailed checkboxes, ratios), and the collapsible sidebar functionality.

## 2. Componentized Refactor (Architecture)
- Extract the 1,500+ line HTML/CSS/JS string from `dashboard.py`.
- Create a new directory structure:
  - `templates/index.html`
  - `static/css/style.css`
  - `static/js/main.js`
- Update `dashboard.py` to use Flask's `render_template` and serve static assets properly, adhering to `senior-architect` and `data-structure-protocol` guidelines.

## 3. UI/UX Enhancements
- Build a responsive, off-canvas collapsible sidebar with a hamburger menu toggle for mobile and tablet devices.
- Inject the precise features, inputs, and modal layout structures discovered by the `vision` agent into the frontend.
- Ensure the RotGen V2 dark mode aesthetic (deep blacks, purple-blue gradients, glassmorphism) is polished and uniform across all screen sizes.

## 4. Multi-Agent Validation
- Deploy parallel subagents (`qa-tester`, `code-review`, `quality-reviewer`, `test-engineer`) to validate the new frontend routing and ensure the backend video production pipeline remains fully functional.
- Use `performance-reviewer` to ensure the split assets are optimized.
- Engage `ui-design-system` and `critic` to cross-reference the final mobile layout against the source images.

## 5. Final Polish
- Compress and organize the session memory and verbose logs using the `caveman:compress` workflow.
- Ensure permissions are properly set and the repository is ready for autonomous deployment.