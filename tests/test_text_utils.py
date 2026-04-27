import pytest
from src.utils.text import strip_emojis, strip_markdown, clamp_words, enforce_script_length
from src.utils.cleanup import safe_close


class TestStripEmojis:
    """Test emoji removal."""

    def test_strip_emojis_basic(self):
        """Remove simple emojis from text."""
        text = "Hello 😀 World 🌍"
        result = strip_emojis(text)
        assert "😀" not in result
        assert "🌍" not in result
        assert "Hello" in result
        assert "World" in result

    def test_strip_emojis_empty_string(self):
        """Handle empty string."""
        assert strip_emojis("") == ""

    def test_strip_emojis_no_emojis(self):
        """Text with no emojis passes through."""
        text = "Plain text"
        assert strip_emojis(text) == text

    def test_strip_emojis_multiple_spaces(self):
        """Collapse multiple spaces left after emoji removal."""
        text = "Hello 😀 😀 😀 World"
        result = strip_emojis(text)
        assert "  " not in result  # No double spaces

    def test_strip_emojis_only_emojis(self):
        """Text with only emojis becomes empty."""
        text = "😀🌍😀"
        result = strip_emojis(text)
        assert result.strip() == ""


class TestStripMarkdown:
    """Test markdown removal."""

    def test_strip_markdown_bold(self):
        """Remove bold markdown."""
        assert strip_markdown("**bold**") == "bold"

    def test_strip_markdown_italic_asterisk(self):
        """Remove italic markdown with asterisks."""
        assert strip_markdown("*italic*") == "italic"

    def test_strip_markdown_italic_underscore(self):
        """Remove italic markdown with underscores."""
        assert strip_markdown("_italic_") == "italic"

    def test_strip_markdown_bold_underscore(self):
        """Remove bold markdown with underscores."""
        assert strip_markdown("__bold__") == "bold"

    def test_strip_markdown_headers(self):
        """Remove header markers."""
        assert strip_markdown("# Header 1") == "Header 1"
        assert strip_markdown("### Header 3") == "Header 3"

    def test_strip_markdown_links(self):
        """Remove link syntax."""
        result = strip_markdown("[text](url)")
        assert "text" in result
        assert "url" not in result

    def test_strip_markdown_code_blocks(self):
        """Remove code blocks."""
        result = strip_markdown("```\ncode\n```")
        assert "code" not in result

    def test_strip_markdown_inline_code(self):
        """Remove inline code."""
        result = strip_markdown("Use `function()` like this")
        assert "`function()`" not in result
        assert "Use" in result

    def test_strip_markdown_lists(self):
        """Remove list markers."""
        result = strip_markdown("- item 1\n- item 2")
        assert "-" not in result
        assert "item" in result

    def test_strip_markdown_numbered_lists(self):
        """Remove numbered list markers."""
        result = strip_markdown("1. First\n2. Second")
        assert "1." not in result
        assert "First" in result

    def test_strip_markdown_horizontal_rules(self):
        """Remove horizontal rules."""
        result = strip_markdown("text\n---\nmore text")
        assert "---" not in result
        assert "text" in result

    def test_strip_markdown_empty_string(self):
        """Handle empty string."""
        assert strip_markdown("") == ""

    def test_strip_markdown_multiple_spaces(self):
        """Collapse multiple spaces."""
        result = strip_markdown("text   with   spaces")
        assert result == "text with spaces"


class TestClampWords:
    """Test word count clamping."""

    def test_clamp_words_under_minimum(self):
        """Pad text when under minimum word count."""
        short_text = "Hello world"
        result = clamp_words(short_text, min_w=20, max_w=100)
        words = result.split()
        assert len(words) >= 20

    def test_clamp_words_over_maximum(self):
        """Trim text when over maximum word count."""
        long_text = " ".join(["word"] * 200)
        result = clamp_words(long_text, min_w=10, max_w=50)
        words = result.split()
        assert len(words) <= 50

    def test_clamp_words_within_range(self):
        """Leave text alone when within range."""
        text = " ".join(["word"] * 100)
        result = clamp_words(text, min_w=50, max_w=150)
        assert result == text

    def test_clamp_words_custom_padding(self):
        """Use custom padding text."""
        short = "Hi"
        custom_pad = "PADDING"
        result = clamp_words(short, min_w=10, max_w=100, pad_text=custom_pad)
        assert "PADDING" in result

    def test_clamp_words_tries_sentence_boundary(self):
        """Try to trim at sentence boundary in last 30%."""
        text = "One sentence. Another sentence. Final sentence."
        result = clamp_words(text, min_w=1, max_w=5)
        # Should try to end at a period
        assert result.endswith((".", "!") or "?")

    def test_clamp_words_exact_count(self):
        """Clamp to exact word count."""
        text = " ".join(["word"] * 50)
        result = clamp_words(text, min_w=40, max_w=40)
        words = result.split()
        assert len(words) <= 40


class TestEnforceScriptLength:
    """Test script length enforcement."""

    def test_enforce_script_length_under_max(self):
        """Leave short scripts alone."""
        short = " ".join(["word"] * 100)
        result = enforce_script_length(short, max_words=200)
        assert result == short

    def test_enforce_script_length_over_max(self):
        """Trim long scripts."""
        long = " ".join(["word"] * 2000)
        result = enforce_script_length(long, max_words=500)
        words = result.split()
        assert len(words) <= 500

    def test_enforce_script_length_exact_max(self):
        """Trim to exact max."""
        text = " ".join(["word"] * 100)
        result = enforce_script_length(text, max_words=50)
        words = result.split()
        assert len(words) <= 50

    def test_enforce_script_length_empty(self):
        """Handle empty string."""
        assert enforce_script_length("").strip() == ""

    def test_enforce_script_length_whitespace(self):
        """Strip extra whitespace."""
        result = enforce_script_length("word " * 100, max_words=200)
        assert "  " not in result


class TestSafeClose:
    """Test safe resource cleanup."""

    def test_safe_close_object_with_close_method(self):
        """Close object with .close() method."""
        mock_obj = MockCloseable()
        safe_close(mock_obj)
        assert mock_obj.closed

    def test_safe_close_list_of_objects(self):
        """Close multiple objects in a list."""
        objs = [MockCloseable(), MockCloseable()]
        safe_close(objs)
        assert all(obj.closed for obj in objs)

    def test_safe_close_nested_list(self):
        """Close objects in nested lists."""
        nested = [[MockCloseable()], MockCloseable()]
        safe_close(nested)
        assert nested[0][0].closed
        assert nested[1].closed

    def test_safe_close_none_values(self):
        """Skip None values without error."""
        safe_close(None, MockCloseable(), None)

    def test_safe_close_object_without_close(self):
        """Skip objects without .close() method."""
        safe_close("string", 123, {"key": "value"})  # Should not raise

    def test_safe_close_close_raises_exception(self):
        """Swallow exceptions from .close()."""
        mock_obj = MockCloseableError()
        safe_close(mock_obj)  # Should not raise

    def test_safe_close_multiple_args(self):
        """Close multiple separate arguments."""
        obj1 = MockCloseable()
        obj2 = MockCloseable()
        safe_close(obj1, obj2)
        assert obj1.closed and obj2.closed

    def test_safe_close_mixed_types(self):
        """Handle mixed types safely."""
        safe_close(MockCloseable(), [MockCloseable()], None, "string")  # Should not raise


class MockCloseable:
    """Mock object with close() method."""

    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class MockCloseableError:
    """Mock object that raises on close()."""

    def close(self):
        raise RuntimeError("Simulated close error")
