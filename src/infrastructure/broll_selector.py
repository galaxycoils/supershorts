"""AI-driven B-Roll selector.

Uses an ILLMService to generate contextually relevant Pexels search queries
from slide content / topic strings, then fetches the first successful result.
"""
from typing import Optional
from src.core.interfaces import ILLMService
from src.infrastructure.video import get_relevant_pexels_video


class AIBRollSelector:
    """Generate candidate Pexels queries via LLM and return first video hit."""

    def __init__(self, llm: ILLMService) -> None:
        self._llm = llm

    def select(self, topic: str, video_type: str) -> Optional[str]:
        """Return a cached local video path for the best-matching b-roll, or None."""
        try:
            prompt = (
                f'Given topic: {topic}, return JSON: {{"queries": ["q1", "q2", "q3"]}}'
            )
            result = self._llm.generate(prompt, json_mode=True)

            if not isinstance(result, dict):
                return None

            candidates = result.get("queries", [])
            if not candidates:
                return None

            for query in candidates:
                if not isinstance(query, str):
                    continue
                path = get_relevant_pexels_video(query, video_type)
                if path:
                    return path

        except Exception as exc:
            print(f"AIBRollSelector: error generating b-roll queries — {exc}")

        return None
