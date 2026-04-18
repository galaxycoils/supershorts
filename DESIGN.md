# SuperShorts Design Specification

## Visual Identity
SuperShorts targets "Developer Brain Rot" and "Educational Automation" aesthetics.

### Color Tokens
| Token | Hex | Usage |
| :--- | :--- | :--- |
| `primary-bg` | `#0c111d` | Dark Navy (Main videos) |
| `accent-cyan` | `#00c8ff` | ByteBot / Highlight headers |
| `accent-pink` | `#ff1e50` | Viral Brainrot accents |
| `text-main` | `#ffffff` | Primary readable text |
| `subtitle-bg` | `rgba(0,0,0,0.75)` | Semi-transparent caption bar |

### Layouts
- **Shorts (9:16)**: 1080x1920. Subtitles at `y=1570`.
- **Long (16:9)**: 1920x1080. Subtitles at `y=860`.
- **RotGen**: Character (Top 40%), Gameplay (Middle), Captions (Bottom).

## Service Architecture
- **Infrastructure**: Stateless API wrappers (Ollama, Pexels, Piper).
- **Engine**: PIL/MoviePy composition logic.
- **Modes**: High-level strategy (Brainrot, TCM, Tutorial).

## Quality Gates
- 100% Test Coverage (TDD).
- 8GB RAM Safety (M1/M2).
- Zero paid APIs.
