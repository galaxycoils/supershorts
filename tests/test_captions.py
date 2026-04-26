"""Tests for src/utils/captions.py — subtitle chunking and timing."""
import numpy as np
import pytest
from src.utils.captions import chunk_script, assign_timings, render_subtitle_frame


class TestChunkScript:
    def test_basic_chunking(self):
        result = chunk_script("one two three four five six", words_per_chunk=3)
        assert result == ["one two three", "four five six"]

    def test_empty_string(self):
        assert chunk_script("") == []

    def test_whitespace_only(self):
        assert chunk_script("   ") == []

    def test_single_word(self):
        assert chunk_script("hello", words_per_chunk=4) == ["hello"]

    def test_fewer_words_than_chunk_size(self):
        assert chunk_script("only two words", words_per_chunk=10) == ["only two words"]

    def test_extra_whitespace_collapsed(self):
        result = chunk_script("word1  word2   word3", words_per_chunk=2)
        assert result == ["word1 word2", "word3"]

    def test_default_chunk_size(self):
        words = " ".join(["w"] * 8)
        result = chunk_script(words)
        assert all(len(c.split()) <= 4 for c in result)


class TestAssignTimings:
    def test_total_duration_matches(self):
        chunks = ["hello world", "foo bar"]
        timings = assign_timings(chunks, 10.0)
        assert timings[-1]["end"] == pytest.approx(10.0, abs=0.01)

    def test_timings_start_at_zero(self):
        timings = assign_timings(["one two three"], 5.0)
        assert timings[0]["start"] == 0.0

    def test_non_overlapping(self):
        timings = assign_timings(["a b", "c d e", "f"], 9.0)
        for i in range(len(timings) - 1):
            assert timings[i]["end"] == pytest.approx(timings[i + 1]["start"], abs=0.001)

    def test_empty_chunks(self):
        assert assign_timings([], 10.0) == []

    def test_zero_duration(self):
        assert assign_timings(["hello"], 0.0) == []

    def test_proportional_to_word_count(self):
        chunks = ["a", "a b c d"]  # 1 word vs 4 words → 1:4 ratio
        timings = assign_timings(chunks, 10.0)
        assert timings[1]["end"] - timings[1]["start"] > timings[0]["end"] - timings[0]["start"]


class TestRenderSubtitleFrame:
    def test_returns_numpy_array(self):
        frame = render_subtitle_frame("Hello world", 1080)
        assert isinstance(frame, np.ndarray)

    def test_shape_matches_video_width(self):
        from src.utils.captions import SUBTITLE_H
        frame = render_subtitle_frame("Test text", 1080)
        assert frame.shape == (SUBTITLE_H, 1080, 4)

    def test_short_video_width(self):
        frame = render_subtitle_frame("X", 720)
        assert frame.shape[1] == 720

    def test_long_text_does_not_raise(self):
        long_text = "word " * 50
        frame = render_subtitle_frame(long_text.strip(), 1080)
        assert frame is not None

    def test_empty_text_does_not_raise(self):
        frame = render_subtitle_frame("", 1080)
        assert frame is not None
