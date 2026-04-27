# Implementation Plan: Multi-LLM Provider & Deployment Hardening

## 1. Multi-LLM Provider Support
Currently, the system is hardcoded to use Ollama via `OllamaLLMService`. We will introduce a provider-agnostic factory and add support for LM Studio (OpenAI-compatible).

### Changes in `src/infrastructure/llm.py`
- Extract common JSON parsing/cleaning logic into a base class or utility.
- Implement `LMStudioLLMService` using `requests` to talk to an OpenAI-compatible endpoint.
- Add `get_llm_service(provider: str, model: str) -> ILLMService` factory function.

### Changes in `src/core/config.py`
- Add `LLM_PROVIDER` (default: 'ollama').
- Add `LMSTUDIO_BASE_URL` (default: 'http://localhost:1234/v1').

### Changes in `dashboard.py`
- Update `/api/run/<mode>` to accept an optional `llm_provider` parameter.
- Pass this parameter to the mode execution logic.
- Update `/api/health` to check LM Studio if it's the configured provider.

### Changes in `static/js/main.js`
- Add a dropdown for "LLM Provider" in the Advanced Settings modal.
- Include the selected provider in the production request payload.

## 2. Deployment Readiness
Prepare the project for a reliable production deployment.

### Dependency Management
- Verify `requirements.txt` captures all necessary libs (especially `psutil` if used for RAM stats).
- Ensure `moviepy` version is pinned for stability.

### Configuration
- Harden `.env.example` with clear instructions for all variables (Pexels, Ollama, LM Studio, YouTube credentials).
- Add a `bootstrap.py` or similar sanity check script to verify all local dependencies (FFmpeg, Piper, Ollama) are reachable.

### Documentation
- Rewrite `README.md` to be a professional product landing page.
- Clear setup guide for both Ollama and LM Studio.
- Document "Characters" and "Modes".

## 3. Verification Plan
- **Unit Tests**: Add tests for `LMStudioLLMService` (using `responses` or similar to mock the API).
- **Integration Tests**: Verify that changing the provider in the dashboard correctly routes the request to the new service.
- **End-to-End**: Run a full production cycle (script -> assets -> composition) using LM Studio.

## 4. Multi-Agent Orchestration
- `senior-architect` (Me): Oversee the refactor and ensure SOLID compliance.
- `python-pro`: Implement the new LLM services and dashboard integration.
- `ui-ux-pro-max`: Polish the dashboard controls for provider switching.
- `qa-tester`: Execute the full verification suite.
