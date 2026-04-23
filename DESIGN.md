# SuperShorts Design Specification (RotGen V2 Aesthetic)

## 1. Visual Theme & Atmosphere
- **Concept:** Modern, sleek SaaS dashboard optimized for content creators ("Developer Brain Rot" & "Educational Automation" aesthetics).
- **Vibe:** Deep dark mode with neon accents. Feels premium, developer-focused, and highly functional.
- **Inspiration:** RotGen website, blending deep blacks, subtle greys, and vibrant purple-to-blue gradients.

## 2. Color Palette & Roles
| Token | Hex | Usage |
| :--- | :--- | :--- |
| `primary-bg` | `#050505` | Deep black. Application background. |
| `surface-bg` | `#121212` | Dark grey. Card containers, modals, sidebar. |
| `surface-hover` | `#1E1E1E` | Hover state for interactive elements. |
| `accent-gradient` | `linear-gradient(135deg, #8B5CF6, #3B82F6)` | Primary actions, CTA buttons, active tabs. |
| `accent-glow` | `rgba(139, 92, 246, 0.4)` | Box-shadow glows for active elements. |
| `text-main` | `#FFFFFF` | Primary readable text. |
| `text-dim` | `#A1A1AA` | Secondary text, labels, hints. |
| `border-color` | `#27272A` | Subtle dividers and card borders. |
| `success` | `#10B981` | Success states, ok logs. |
| `error` | `#EF4444` | Error states, critical actions. |

## 3. Typography Rules
- **Primary Font:** 'Inter', system-ui, sans-serif.
- **Monospace Font:** 'Fira Code', monospace (for logs, code, IDs).
- **Scale:** 
  - Headings: 14px-18px, bold, tracking-wide.
  - Body: 13px, regular.
  - Small/Labels: 11px, uppercase, tracking-wider.

## 4. Component Stylings
- **Buttons:** 12px border-radius, smooth 0.2s transition. Primary buttons use the `accent-gradient` with a subtle glow on hover. Secondary buttons use `surface-bg` with `border-color`.
- **Cards:** 16px border-radius, `surface-bg` background, 1px solid `border-color`.
- **Inputs/Selects:** `surface-bg` background, `border-color` border, focus state adds `accent-glow` box-shadow.
- **Status Badges:** Small pills with background opacity (10%) and solid text color.

## 5. Layout Principles
- **Sidebar:** Fixed width (260px), full height, distinct active states with gradient text/border.
- **Main Content:** Responsive CSS Grid, centered max-width (1600px), 32px padding.
- **Three-Pane Layout:** For advanced production modals (Script, Settings, Preview).
- **Spacing:** 8px base unit (8, 16, 24, 32, 48).

## 6. Depth & Elevation
- **Level 1 (Base):** `primary-bg`
- **Level 2 (Cards):** `surface-bg` with `0 4px 6px -1px rgba(0,0,0,0.5)`
- **Level 3 (Modals/Popovers):** `surface-bg` with `0 20px 40px -10px rgba(0,0,0,0.8)`, plus backdrop blur.

## 7. Do's and Don'ts
- **Do:** Use gradients sparingly for primary CTAs only.
- **Do:** Maintain high contrast for text (WCAG AA).
- **Don't:** Overclutter the dashboard with borders; use background differences to separate sections.
- **Don't:** Use harsh pure whites or pure blacks for text/cards; use off-whites and off-blacks.

## 8. Responsive Behavior
- **Desktop (>1024px):** Full sidebar, 3-4 column grids.
- **Tablet (768px - 1024px):** Collapsed sidebar, 2 column grids.
- **Mobile (<768px):** Hidden sidebar (hamburger menu), 1 column stack.

## 9. Agent Prompt Guide
- When updating UI elements, strictly adhere to the CSS variables defined in this document.
- Use `var(--accent-gradient)` for any new primary buttons.
- Keep border radii consistent (`--r-lg` for cards, `--r-md` for buttons).
