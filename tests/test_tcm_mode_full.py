import pytest
import json
import os
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path
from src.modes.tcm_educational import (
    TCMMode,
    generate_tcm_curriculum,
    run_tcm_mode,
    TCM_PLAN_FILE
)

@pytest.fixture
def mock_services():
    return {
        "llm": MagicMock(),
        "tts": MagicMock(),
        "uploader": MagicMock(),
        "engine": MagicMock()
    }

def test_generate_tcm_curriculum_success(mock_services):
    llm = mock_services["llm"]
    llm.generate.return_value = {
        "curriculum_title": "Test Plan",
        "lessons": [{"chapter": 1, "title": "Lesson 1"}]
    }
    
    result = generate_tcm_curriculum("Focus", "Extra", llm_service=llm)
    assert result["curriculum_title"] == "Test Plan"
    assert result["lessons"][0]["status"] == "pending"

def test_generate_tcm_curriculum_error(mock_services):
    llm = mock_services["llm"]
    llm.generate.side_effect = Exception("LLM error")
    
    result = generate_tcm_curriculum("Focus", "Extra", llm_service=llm)
    assert result["curriculum_title"] == "TCM Essentials"
    assert len(result["lessons"]) == 10

def test_tcm_mode_get_pending_topics():
    plan = {"lessons": [{"title": "L1", "status": "pending"}, {"title": "L2", "status": "complete"}]}
    mode = TCMMode(None, None, None, None, plan=plan)
    pending = mode.get_pending_topics()
    assert len(pending) == 1
    assert pending[0]["title"] == "L1"

def test_tcm_mode_mark_complete():
    plan = {"lessons": [{"title": "L1", "status": "pending"}]}
    mode = TCMMode(None, None, None, None, plan=plan)
    with patch("pathlib.Path.write_text") as mock_write, \
         patch("src.core.learning.log_upload"):
        mode.mark_complete(plan["lessons"][0], "vid123")
        assert plan["lessons"][0]["status"] == "complete"
        mock_write.assert_called_once()

def test_tcm_mode_generate_script_llm_error(mock_services):
    llm = mock_services["llm"]
    llm.generate.return_value = None # Should trigger fallback
    
    mode = TCMMode(llm, None, None, None)
    script = mode.generate_script({"title": "Test"})
    assert "TCM lesson content" in script["long_form_slides"][0]["content"]

def test_tcm_mode_generate_assets(mock_services):
    mode = TCMMode(mock_services["llm"], mock_services["tts"], mock_services["uploader"], mock_services["engine"])
    mode.output_dir = Path("/tmp/tcm")
    
    content = {"title": "Test", "short_form_highlight": "Highlight"}
    assets = mode.generate_assets(content, "uid123")
    
    assert "images" in assets
    assert "audio" in assets
    mock_services["tts"].text_to_speech.assert_called()
    mock_services["engine"].generate_visuals.assert_called()

def test_tcm_mode_compose(mock_services):
    mode = TCMMode(None, None, None, mock_services["engine"], custom_bg="/mock/bg.png")
    assets = {
        "images": [Path("img.png")],
        "audio": [Path("aud.wav")],
        "script": ["script text"]
    }
    with patch("pathlib.Path.exists", return_value=True):
        mode.compose({"title": "Test"}, assets, "out.mp4")
        mock_services["engine"].compose_video.assert_called_once()

def test_tcm_mode_upload(mock_services):
    mode = TCMMode(None, None, mock_services["uploader"], None)
    mode.upload({"title": "Test", "hashtags": "#TCM"}, "out.mp4")
    mock_services["uploader"].upload.assert_called_once()

@patch("src.modes.tcm_educational.Prompt.ask", side_effect=["n", "My Focus", "My Extra", "1"])
@patch("src.modes.tcm_educational.generate_tcm_curriculum")
def test_run_tcm_mode_interactive(mock_gen, mock_prompt, mock_services):
    mock_gen.return_value = {"lessons": []}
    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.read_text", return_value="{}"), \
         patch("pathlib.Path.write_text"):

        run_tcm_mode(
            llm_service=mock_services["llm"],
            tts_service=mock_services["tts"],
            uploader_service=mock_services["uploader"],
            video_engine=mock_services["engine"]
        )
        mock_gen.assert_called()

def test_run_tcm_mode_headless(mock_services):
    with patch("pathlib.Path.exists", return_value=False), \
         patch("pathlib.Path.write_text"), \
         patch("src.modes.tcm_educational.generate_tcm_curriculum") as mock_gen:

        mock_gen.return_value = {"lessons": []}

        run_tcm_mode(
            llm_service=mock_services["llm"],
            tts_service=mock_services["tts"],
            uploader_service=mock_services["uploader"],
            video_engine=mock_services["engine"],
            topic="Headless Topic",
            count="1"
        )
        mock_gen.assert_called()
