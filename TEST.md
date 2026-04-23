# TEST: Architecture Remediation and Refactoring

## Test Plan

The following test plan is designed to verify the architectural changes and refactoring performed in the `money-printer-v2` project.

### 1. Unit & Remediation Tests
Verify the new abstract base classes, service interfaces, and mockable adapters.
- **Command:** `./venv/bin/python3 -m pytest tests/test_architecture_remediation.py`
- **Focus:** `BaseMode` orchestration, `StandardTTSService` mockability.

### 2. Mode-Specific Logic Tests
Ensure that the refactored modes still produce correct content and handle data correctly.
- **Command:** `./venv/bin/python3 -m pytest tests/test_brainrot.py tests/test_tcm.py`
- **Focus:** Brainrot script generation, TCM curriculum generation.

### 3. Compatibility Bridge Tests
Verify that the `src/generator.py` bridge still works for legacy callers (main.py, run_workflow.py).
- **Command:** `./venv/bin/python3 -m pytest tests/test_bridge_pipeline_integrity.py`
- **Focus:** Functional parity between old and new internal paths.

### 4. End-to-End Dry Runs
Simulate the full production pipeline without making real external API calls.
- **Command:** `./venv/bin/python3 -m pytest tests/test_content_modes_dry_run.py`
- **Focus:** End-to-end flow from topic to video composition.

### 5. Uploader & Infrastructure Tests
Verify the refactored uploader implementations and their resilience.
- **Command:** `./venv/bin/python3 -m pytest tests/test_uploader.py tests/test_uploader_resilience.py`
- **Focus:** YouTube API and Browser uploader signatures and error handling.

### 6. Comprehensive Suite & Coverage
Run the full test suite and check against the required coverage thresholds.
- **Command:** `./venv/bin/python3 -m pytest --cov=src tests/`
- **Thresholds:** Check against `.coverage-thresholds.json`.

---

## Execution Log

| Test Step | Command | Result | Notes |
|-----------|---------|--------|-------|
| 1. Remediation | `pytest tests/test_architecture_remediation.py` | | |
| 2. Mode Logic | `pytest tests/test_brainrot.py tests/test_tcm.py` | | |
| 3. Bridge Integrity | `pytest tests/test_bridge_pipeline_integrity.py` | | |
| 4. Dry Runs | `pytest tests/test_content_modes_dry_run.py` | | |
| 5. Uploader | `pytest tests/test_uploader.py tests/test_uploader_resilience.py` | | |
| 6. Full Suite | `pytest --cov=src tests/` | | |
