import pytest
from unittest.mock import MagicMock, patch
from src.generator import generate_brainrot_topics, generate_brainrot_script, render_brainrot_slide, create_brainrot_video
from pathlib import Path
from PIL import Image

def test_generate_brainrot_topics_schema(mock_llm):
    mock_llm.generate.return_value = {
        "topics": [
            {"title": "AI Secret", "hook": "Shocking!", "angle": "The hidden truth"}
        ]
    }
    result = generate_brainrot_topics(count=1, llm_service=mock_llm)
    assert len(result) == 1
    assert "title" in result[0]
    assert "hook" in result[0]
    assert "angle" in result[0]

def test_generate_brainrot_script_enforcement(mock_llm):
    # Mock a very long script to test clamping
    long_script = "word " * 200
    mock_llm.generate.return_value = {
        "slides": [{"text": "hook", "duration_hint": "short"}],
        "full_script": long_script,
        "title": "Title",
        "hashtags": "#AI"
    }
    topic = {"title": "Test", "hook": "Hook", "angle": "Angle"}
    result = generate_brainrot_script(topic, llm_service=mock_llm)
    word_count = len(result['full_script'].split())
    # clamp_words uses max_w=127 by default
    assert word_count <= 127
    assert word_count >= 99

def test_render_brainrot_slide_output(tmp_path):
    # Test if image is created and has correct dimensions
    output_dir = tmp_path / "brainrot_test"
    text = "Hello Brainrot World"
    path_str = render_brainrot_slide(output_dir, text, 1, 1)
    path = Path(path_str)
    assert path.exists()
    with Image.open(path) as img:
        assert img.size == (1080, 1920)

@patch('src.infrastructure.video_engine_impl.StandardVideoEngine.compose_brainrot_video')
def test_create_brainrot_video_logic(mock_compose):
    mock_compose.return_value = "out.mp4"
    create_brainrot_video(["slide1.png"], ["audio1.wav"], "out.mp4", "Title")
    assert mock_compose.called
