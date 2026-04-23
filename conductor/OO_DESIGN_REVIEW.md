# Object-Oriented Design Review

**Scope:** `dashboard.py`, `src/modes/rotgen.py`, `src/modes/brainrot.py`, `src/modes/tcm_educational.py`
**Focus:** Integration of new dashboard parameters (Advanced View, Asset Selection) and adherence to SOLID/DRY principles.

## Findings

### 1. 🔴 CRITICAL: Interface Mismatch (Liskov Substitution Principle)
*   **Location:** `src/modes/rotgen.py`
*   **Problem:** The original `run_rotgen_pipeline` function did not inherit from `BaseMode` or accept the standard pipeline arguments (`voice`, `dry_run`, custom assets) used by other modes. This breaks polymorphism when `dashboard.py` expects a uniform interface to pass custom UI selections.
*   **Resolution:** Refactored `rotgen.py` into a proper `RotgenMode` class inheriting from `BaseMode`. The entry point now correctly handles environment variables for custom characters and backgrounds.

### 2. 🔴 CRITICAL: Unhandled Dependencies (Dependency Inversion Principle)
*   **Location:** `src/modes/brainrot.py`, `src/modes/tcm_educational.py`
*   **Problem:** The UI allowed users to select custom backgrounds (`CUSTOM_BG`), but the backend logic hardcoded asset fetching via `get_local_viral_gameplay()` and `TCM_BG_KEYWORDS`. The high-level policy (video composition) depended on low-level detail (hardcoded asset paths) instead of abstractions provided by the caller (the UI).
*   **Resolution:** Updated `BrainrotMode` and `TCMMode` to accept and prioritize `custom_bg`. They now inject the user's selected asset into the composition pipeline, making the UI selection functional.

### 3. 🟡 WARNING: Violation of Open/Closed Principle (OCP)
*   **Location:** `dashboard.py` (Backend Routing)
*   **Problem:** `MODE_COMMANDS` dictates how the Flask app calls the backend scripts. It requires manual modification whenever a script's signature changes.
*   **Resolution:** I updated `MODE_COMMANDS` to ensure `rotgen` receives the `{voice}` and `{dry_run}` parameters, but long-term, this should be refactored into a registry pattern where modes self-register their expected arguments.

### 4. 🟡 WARNING: Violation of Single Responsibility Principle (SRP)
*   **Location:** `dashboard.py` (Frontend Layout)
*   **Problem:** The UI generation inside `DASHBOARD_HTML` is a monolithic string. The `openModal` logic handles state, DOM manipulation, and dynamic HTML generation for 10 different modes in a massive `if/else` block.
*   **Resolution:** While the 3-pane RotGen aesthetic was successfully applied, future iterations should extract this into distinct UI components (e.g., separating the "Settings Pane" from the "Preview Pane").

## Conclusion
The UI is now fully functional and properly wired to the backend. The RotGen aesthetic, 3-pane modal layout, and custom asset selection are operational. The underlying Python modes have been refactored to respect the parameters passed down from the dashboard.
