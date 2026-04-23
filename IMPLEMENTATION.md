# Implementation Plan: RotGen V2 UI Redesign

## Phase 1: Core Theming & Variables
- Update CSS `:root` variables in `dashboard.py` to match the new `DESIGN.md` (Deep black bg, dark grey surfaces, purple-to-blue gradients).
- Apply 'Inter' font via Google Fonts.
- Update border radii, spacing, and elevation shadows to match the new design specs.

## Phase 2: Layout & Dashboard Redesign
- Redesign the Sidebar to be sleek, with gradient active states.
- Rebuild the KPI cards to look like modern metric cards with trend indicators.
- Refine the Mode Grid (Productions) to have beautiful hover effects and gradient CTAs.
- Update the Gallery and Upload Log tables to use the new aesthetic (status badges, subtle borders).

## Phase 3: Three-Pane Modal / Advanced Settings
- Refactor the production modal (`openModal` function) into a more sophisticated layout.
- Introduce a 3-pane structure (or tabbed structure) if applicable: Script/Prompt input, Settings (Voice, Resolution, Assets), and Preview/Advanced.
- Style the inputs, selects, and toggle switches with the new theme.
- Ensure the Advanced Mode toggle smoothly reveals the power-user settings.

## Phase 4: Validation & Review
- Verify the UI works in both Standard and Advanced modes.
- Execute `metaswarm:design-review-gate` logic to validate the design.
- Test responsive breakpoints.
