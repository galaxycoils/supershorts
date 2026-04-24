# SuperShorts Implementation Plan (RotGen V2 Aesthetic)

## Objective
Implement UI/UX refinements based on `DESIGN.md` (RotGen V2 Aesthetic).

## Execution Sequence

### Phase 1: Foundation & Variables
- [ ] Task 1.1: Define CSS Variables in `static/css/style.css` for palette (primary-bg, surface-bg, accent-gradient, etc.).
- [ ] Task 1.2: Implement Typography Rules (Inter & Fira Code) in global styles.
- [ ] Task 1.3: Set Base Elevation Levels (z-index and shadows).

### Phase 2: Component Refinement
- [ ] Task 2.1: Style Buttons with 12px radius, transition, and accent-gradient glow.
- [ ] Task 2.2: Implement Card containers with 16px radius and Level 2 elevation.
- [ ] Task 2.3: Update Inputs/Selects with focus accent-glow.
- [ ] Task 2.4: Create Status Badge components with background opacity.

### Phase 3: Layout & Structure
- [ ] Task 3.1: Enforce Sidebar fixed width (260px) and active states.
- [ ] Task 3.2: Implement Responsive CSS Grid for main content.
- [ ] Task 3.3: Refactor advanced production modals to Three-Pane Layout.
- [ ] Task 3.4: Apply 8px spacing unit across all components.

### Phase 4: Responsive Behavior
- [ ] Task 4.1: Implement Tablet view (768px - 1024px) with collapsed sidebar.
- [ ] Task 4.2: Implement Mobile view (<768px) with hidden sidebar and hamburger menu.

## Verification Checklist
- [ ] Command: `node --check static/js/main.js` (Verify JS integrity)
- [ ] Manual: Inspect `/static/css/style.css` for CSS variable coverage.
- [ ] Visual: Capture screenshots at 1440px, 1024px, and 480px viewports.

## Exit Criteria
- All CSS variables from `DESIGN.md` defined.
- 100% of components match border-radius and shadow specs.
- Layout remains functional across all three target breakpoints.
