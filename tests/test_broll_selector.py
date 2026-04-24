"""Tests for AIBRollSelector — TDD first."""
import pytest
from unittest.mock import MagicMock, patch, call
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_llm(queries=None, raises=False):
    """Return a mock ILLMService."""
    svc = MagicMock()
    if raises:
        svc.generate.side_effect = Exception("LLM exploded")
    else:
        svc.generate.return_value = {"queries": queries or ["bitcoin crash", "stock market", "crypto trading"]}
    return svc


# ---------------------------------------------------------------------------
# Import under test (deferred so failures are clear)
# ---------------------------------------------------------------------------

from src.infrastructure.broll_selector import AIBRollSelector


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

class TestAIBRollSelectorCandidateGeneration:
    """LLM is asked for 3 candidate queries."""

    def test_calls_llm_with_topic(self):
        llm = _make_llm()
        selector = AIBRollSelector(llm)
        with patch("src.infrastructure.broll_selector.get_relevant_pexels_video", return_value="/tmp/vid.mp4"):
            selector.select("bitcoin price crash", "short")
        llm.generate.assert_called_once()
        prompt_arg = llm.generate.call_args[0][0]
        assert "bitcoin price crash" in prompt_arg

    def test_prompt_requests_json_queries(self):
        llm = _make_llm()
        selector = AIBRollSelector(llm)
        with patch("src.infrastructure.broll_selector.get_relevant_pexels_video", return_value="/tmp/vid.mp4"):
            selector.select("AI regulation", "long")
        prompt = llm.generate.call_args[0][0]
        assert "queries" in prompt.lower() or "JSON" in prompt

    def test_json_mode_enabled(self):
        llm = _make_llm()
        selector = AIBRollSelector(llm)
        with patch("src.infrastructure.broll_selector.get_relevant_pexels_video", return_value="/tmp/vid.mp4"):
            selector.select("topic", "short")
        _, kwargs = llm.generate.call_args
        assert kwargs.get("json_mode", True) is True


class TestAIBRollSelectorPexelsIntegration:
    """Tries each LLM query against Pexels, returns first hit."""

    def test_returns_first_successful_pexels_result(self):
        llm = _make_llm(["q1", "q2", "q3"])
        selector = AIBRollSelector(llm)
        with patch("src.infrastructure.broll_selector.get_relevant_pexels_video") as mock_pexels:
            mock_pexels.side_effect = [None, "/tmp/q2.mp4", "/tmp/q3.mp4"]
            result = selector.select("some topic", "short")
        assert result == "/tmp/q2.mp4"
        assert mock_pexels.call_count == 2  # stopped after first hit

    def test_passes_video_type_to_pexels(self):
        llm = _make_llm(["landscape scenery"])
        selector = AIBRollSelector(llm)
        with patch("src.infrastructure.broll_selector.get_relevant_pexels_video") as mock_pexels:
            mock_pexels.return_value = "/tmp/vid.mp4"
            selector.select("nature documentary", "long")
        mock_pexels.assert_called_once_with("landscape scenery", "long")

    def test_returns_none_when_all_queries_fail(self):
        llm = _make_llm(["q1", "q2", "q3"])
        selector = AIBRollSelector(llm)
        with patch("src.infrastructure.broll_selector.get_relevant_pexels_video", return_value=None):
            result = selector.select("topic", "short")
        assert result is None


class TestAIBRollSelectorFallbacks:
    """Graceful degradation when LLM fails or returns bad data."""

    def test_returns_none_when_llm_raises(self):
        llm = _make_llm(raises=True)
        selector = AIBRollSelector(llm)
        with patch("src.infrastructure.broll_selector.get_relevant_pexels_video", return_value=None):
            result = selector.select("anything", "short")
        assert result is None

    def test_returns_none_when_llm_returns_empty_dict(self):
        llm = MagicMock()
        llm.generate.return_value = {}
        selector = AIBRollSelector(llm)
        with patch("src.infrastructure.broll_selector.get_relevant_pexels_video", return_value=None):
            result = selector.select("topic", "short")
        assert result is None

    def test_returns_none_when_llm_returns_empty_queries_list(self):
        llm = _make_llm(queries=[])
        selector = AIBRollSelector(llm)
        with patch("src.infrastructure.broll_selector.get_relevant_pexels_video", return_value=None):
            result = selector.select("topic", "short")
        assert result is None

    def test_handles_non_dict_llm_response(self):
        llm = MagicMock()
        llm.generate.return_value = ["q1", "q2"]  # list instead of dict
        selector = AIBRollSelector(llm)
        with patch("src.infrastructure.broll_selector.get_relevant_pexels_video", return_value=None):
            result = selector.select("topic", "short")
        assert result is None

    def test_handles_queries_with_non_string_items(self):
        llm = _make_llm(queries=[None, 42, "valid query"])
        selector = AIBRollSelector(llm)
        with patch("src.infrastructure.broll_selector.get_relevant_pexels_video") as mock_pexels:
            mock_pexels.return_value = "/tmp/vid.mp4"
            result = selector.select("topic", "short")
        # Only "valid query" is a string — should still work
        assert result == "/tmp/vid.mp4"
        mock_pexels.assert_called_once_with("valid query", "short")


class TestVideoEngineIntegration:
    """StandardVideoEngine accepts optional IBRollSelector and uses it."""

    def test_engine_instantiates_without_selector(self):
        from src.infrastructure.video_engine_impl import StandardVideoEngine
        engine = StandardVideoEngine()
        assert engine.broll_selector is None

    def test_engine_accepts_selector(self):
        from src.infrastructure.video_engine_impl import StandardVideoEngine
        selector = MagicMock()
        engine = StandardVideoEngine(broll_selector=selector)
        assert engine.broll_selector is selector

    def test_get_rotgen_gameplay_uses_selector_when_provided(self):
        from src.infrastructure.video_engine_impl import StandardVideoEngine
        selector = MagicMock()
        selector.select.return_value = "/tmp/ai_broll.mp4"
        engine = StandardVideoEngine(broll_selector=selector)

        with patch("src.infrastructure.video_engine_impl.get_local_viral_gameplay", return_value=None), \
             patch("src.infrastructure.video_engine_impl.get_local_gameplay", return_value=None):
            result = engine._get_rotgen_gameplay(topic="machine learning basics")

        selector.select.assert_called_once_with("machine learning basics", "short")
        assert result == "/tmp/ai_broll.mp4"

    def test_get_rotgen_gameplay_falls_back_to_pexels_list_when_no_selector(self):
        from src.infrastructure.video_engine_impl import StandardVideoEngine, ROTGEN_PEXELS_QUERIES
        engine = StandardVideoEngine()

        with patch("src.infrastructure.video_engine_impl.get_local_viral_gameplay", return_value=None), \
             patch("src.infrastructure.video_engine_impl.get_local_gameplay", return_value=None), \
             patch("src.infrastructure.video_engine_impl.get_relevant_pexels_video", return_value="/tmp/fallback.mp4") as mock_pexels:
            result = engine._get_rotgen_gameplay(topic="anything")

        assert result == "/tmp/fallback.mp4"
        # Ensure the call used a query from the predefined list
        used_query = mock_pexels.call_args[0][0]
        assert used_query in ROTGEN_PEXELS_QUERIES

    def test_get_rotgen_gameplay_local_viral_takes_priority(self):
        from src.infrastructure.video_engine_impl import StandardVideoEngine
        selector = MagicMock()
        selector.select.return_value = "/tmp/ai_broll.mp4"
        engine = StandardVideoEngine(broll_selector=selector)

        with patch("src.infrastructure.video_engine_impl.get_local_viral_gameplay", return_value="/local/viral.mp4"):
            result = engine._get_rotgen_gameplay(topic="anything")

        # Local viral clip wins — selector never called
        selector.select.assert_not_called()
        assert result == "/local/viral.mp4"
