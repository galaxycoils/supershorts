import pytest
import json
import os
import datetime
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path
from src.core.learning import (
    log_upload,
    suggest_improvements,
    start_learning_mode
)
import src.core.learning as learning

def test_log_upload_invalid_id():
    with patch("builtins.print") as mock_print:
        log_upload("Title", "DRY_RUN", "viral")
        mock_print.assert_any_call("⚠️ Skipping log_upload: invalid video_id 'DRY_RUN'")

def test_log_upload_success():
    with patch("src.core.learning.LOG_FILE") as mock_file:
        mock_file.exists.return_value = False
        log_upload("Title", "vid123", "viral")
        mock_file.write_text.assert_called_once()
        data = json.loads(mock_file.write_text.call_args[0][0])
        assert data[0]["video_id"] == "vid123"

def test_log_upload_duplicate():
    existing_data = [{"video_id": "vid123"}]
    with patch("src.core.learning.LOG_FILE") as mock_file, \
         patch("builtins.print") as mock_print:
        mock_file.exists.return_value = True
        mock_file.read_text.return_value = json.dumps(existing_data)
        log_upload("Title", "vid123", "viral")
        mock_print.assert_any_call("⚠️ Skipping duplicate log entry for video_id 'vid123'")

def test_log_upload_not_a_list():
    with patch("src.core.learning.LOG_FILE") as mock_file:
        mock_file.exists.return_value = True
        mock_file.read_text.return_value = json.dumps({"not": "a list"})
        log_upload("Title", "vid123", "viral")
        mock_file.write_text.assert_called_once()
        data = json.loads(mock_file.write_text.call_args[0][0])
        assert isinstance(data, list)
        assert len(data) == 1

def test_log_upload_json_error():
    with patch("src.core.learning.LOG_FILE") as mock_file:
        mock_file.exists.return_value = True
        mock_file.read_text.return_value = "invalid-json"
        log_upload("Title", "vid123", "viral")
        mock_file.write_text.assert_called_once()
        data = json.loads(mock_file.write_text.call_args[0][0])
        assert len(data) == 1

def test_log_upload_exception():
    with patch("src.core.learning.LOG_FILE") as mock_file:
        mock_file.exists.return_value = True
        mock_file.read_text.side_effect = Exception("error")
        log_upload("Title", "vid123", "viral")
        mock_file.write_text.assert_called_once()

def test_suggest_improvements_not_enough_data():
    with patch("src.core.learning.LOG_FILE") as mock_file:
        mock_file.exists.return_value = True
        mock_file.read_text.return_value = json.dumps([{"id": 1}])
        result = suggest_improvements()
        assert "Not enough data" in result

def test_suggest_improvements_json_error():
    with patch("src.core.learning.LOG_FILE") as mock_file:
        mock_file.exists.return_value = True
        mock_file.read_text.return_value = "invalid-json"
        result = suggest_improvements()
        assert "Not enough data" in result

@patch("src.core.learning.get_llm_service")
def test_suggest_improvements_success(mock_get_llm):
    mock_llm = mock_get_llm.return_value
    mock_llm.generate.return_value = "Better hooks, shorter titles."
    
    data = [{"video_id": f"v{i}"} for i in range(5)]
    with patch("src.core.learning.LOG_FILE") as mock_log, \
         patch("src.core.learning.SUGGESTIONS_FILE") as mock_sug:
        mock_log.exists.return_value = True
        mock_log.read_text.return_value = json.dumps(data)
        mock_sug.parent.mkdir.return_value = None
        
        result = suggest_improvements()
        assert result == "Better hooks, shorter titles."
        mock_sug.write_text.assert_called_with("Better hooks, shorter titles.")

@patch("src.core.learning.get_llm_service")
def test_suggest_improvements_dict_fallback(mock_get_llm):
    mock_llm = mock_get_llm.return_value
    mock_llm.generate.return_value = {"suggestion": "Use more memes"}
    
    data = [{"video_id": f"v{i}"} for i in range(5)]
    with patch("src.core.learning.LOG_FILE") as mock_log, \
         patch("src.core.learning.SUGGESTIONS_FILE") as mock_sug:
        mock_log.exists.return_value = True
        mock_log.read_text.return_value = json.dumps(data)
        mock_sug.parent.mkdir.return_value = None
        
        result = suggest_improvements()
        assert "Use more memes" in result

@patch("src.core.learning.get_llm_service")
def test_suggest_improvements_error(mock_get_llm):
    mock_get_llm.side_effect = Exception("LLM failure")
    data = [{"video_id": f"v{i}"} for i in range(5)]
    with patch("src.core.learning.LOG_FILE") as mock_log:
        mock_log.exists.return_value = True
        mock_log.read_text.return_value = json.dumps(data)
        result = suggest_improvements()
        assert "LLM failure" in result

@patch("src.core.learning.suggest_improvements")
@patch("rich.console.Console.input", return_value="")
def test_start_learning_mode(mock_input, mock_suggest):
    start_learning_mode()
    mock_suggest.assert_called_once()
