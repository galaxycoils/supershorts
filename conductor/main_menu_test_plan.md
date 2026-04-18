# Plan: Main Menu & Workflow Testing and Fixes

## Objective
Ensure every option in the `main.py` menu and the `run_workflow.py` engine works correctly after the massive architectural refactor. Fix any routing, import, or execution errors and verify with automated tests.

## Key Files & Context
- `main.py`: The interactive entry point.
- `run_workflow.py`: The batch execution engine.
- `src/generator.py`: The compatibility bridge.
- `src/core/learning.py`: Missing re-exports (e.g., `start_learning_mode`).
- `tests/test_main_menu.py` (To be created).

## Implementation Steps
1. **Fix Known Static Errors**: Update `main.py` and `src/generator.py` to ensure missing imports like `start_learning_mode` (Option 5) and `cleanup_after_upload` are correctly mapped and re-exported.
2. **Automated Menu Testing**: Create a new test file (`tests/test_main_menu.py`) that uses `unittest.mock` to simulate a user selecting options 1 through 12. This will verify that the menu correctly routes to the new modular entry points without throwing `NameError` or `ImportError`.
3. **Automated Workflow Testing**: Create tests for `run_workflow.py` to ensure batch processing (e.g., `run_brainrot`, `run_tcm`) works.
4. **Run, Fix, and Verify**: Use `pytest` to run these tests. If any option crashes or fails to route, fix the broken code and re-run the tests until we achieve a 100% pass rate.

## Verification
- Run `pytest tests/test_main_menu.py` and `pytest tests/test_workflow.py` (if created) to verify all options are correctly routed and executed without syntax or import errors.
