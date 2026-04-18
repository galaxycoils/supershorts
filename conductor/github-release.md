# Plan: GitHub Update and New Release

## Objective
Commit the recent architectural refactoring and stabilization changes, push them to the GitHub repository, and create a new release.

## Key Files & Context
- All modified files in `src/`, `tests/`, and `.beads/`.
- New files in `src/core/`, `src/engine/`, `src/infrastructure/`, and `src/modes/`.
- `DESIGN.md` and `SERVICE-INVENTORY.md`.

## Implementation Steps
1. **Stage Changes**: Run `git add .` to stage all modifications, deletions, and new files.
2. **Commit**: Run `git commit -m "refactor: modularize architecture, stabilize all video modes, and fix memory leaks"` (following conventional commits and caveman-commit style if applicable).
3. **Push**: Run `git push origin HEAD` to push the changes to the remote repository.
4. **Create Release**: Run `gh release create v3.0.0 --title "v3.0.0 - Modular Architecture & Stabilization" --generate-notes` to tag and publish the new release on GitHub.

## Verification
- Run `git status` to ensure working tree is clean.
- Run `gh release list` to verify the new release is published.