"""Tests for src/utils/json.py — safe_json_parse."""
import pytest
from src.utils.json import safe_json_parse


class TestSafeJsonParse:
    def test_plain_json_object(self):
        assert safe_json_parse('{"a": 1}') == {"a": 1}

    def test_plain_json_array(self):
        assert safe_json_parse('[1, 2, 3]') == [1, 2, 3]

    def test_strips_bom(self):
        assert safe_json_parse('\ufeff{"x": true}') == {"x": True}

    def test_strips_trailing_comma_in_object(self):
        assert safe_json_parse('{"a": 1,}') == {"a": 1}

    def test_strips_trailing_comma_in_array(self):
        assert safe_json_parse('[1, 2,]') == [1, 2]

    def test_strips_control_characters(self):
        assert safe_json_parse('{"a": "\x00b"}') == {"a": "b"}

    def test_strips_leading_whitespace(self):
        assert safe_json_parse('   {"z": null}') == {"z": None}

    def test_nested_structure(self):
        data = '{"videos": [{"title": "Test", "script": "Hello world"}]}'
        result = safe_json_parse(data)
        assert result["videos"][0]["title"] == "Test"

    def test_json_embedded_in_fluff_fallback(self):
        """Raw LLM output may have text before/after the JSON."""
        text = 'Here is the JSON: {"answer": 42} done.'
        assert safe_json_parse(text) == {"answer": 42}

    def test_array_embedded_in_fluff_fallback(self):
        text = 'Result: [{"a": 1}] end.'
        assert safe_json_parse(text) == [{"a": 1}]

    def test_raises_on_invalid_json(self):
        with pytest.raises(Exception):
            safe_json_parse("not json at all")

    def test_raises_when_fallback_also_fails(self):
        with pytest.raises(Exception):
            safe_json_parse("{broken [json")
