import pytest
from unittest.mock import MagicMock, patch
from src.generator import generate_brainrot_topics, generate_brainrot_script, render_brainrot_slide, create_brainrot_video
from pathlib import Path
from PIL import Image

@patch('src.modes.brainrot.ollama_generate')
def test_generate_brainrot_topics_schema(mock_ollama):
    mock_ollama.return_value = {
        "topics": [
            {"title": "AI Secret", "hook": "Shocking!", "angle": "The hidden truth"}
        ]
    }
    result = generate_brainrot_topics(count=1)
    assert len(result) == 1
    assert "title" in result[0]
    assert "hook" in result[0]
    assert "angle" in result[0]

@patch('src.modes.brainrot.ollama_generate')
def test_generate_brainrot_script_enforcement(mock_ollama):
    # Mock a very long script to test clamping
    long_script = "word " * 200
    mock_ollama.return_value = {
        "slides": [{"text": "hook", "duration_hint": "short"}],
        "full_script": long_script,
        "title": "Title",
        "hashtags": "#AI"
    }
    topic = {"title": "Test", "hook": "Hook", "angle": "Angle"}
    result = generate_brainrot_script(topic)
    word_count = len(result['full_script'].split())
    # _clamp_words uses max_w=127 by default
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

@patch('src.modes.brainrot.VideoFileClip')
@patch('src.modes.brainrot.AudioFileClip')
@patch('src.modes.brainrot.concatenate_videoclips')
def test_create_brainrot_video_logic(mock_concat, mock_audio, mock_video):
    from src.generator import create_brainrot_video
    mock_audio_instance = MagicMock()
    mock_audio_instance.duration = 1.0
    mock_audio.return_value = mock_audio_instance
    
    mock_video_instance = MagicMock()
    mock_video_instance.duration = 10.0
    mock_video_instance.size = (1080, 1920)
    mock_video_instance.subclip.return_value = mock_video_instance
    mock_video_instance.fx.return_value = mock_video_instance
    mock_video.return_value = mock_video_instance
    
    # ImageClip is also used, patch it where used
    with patch('src.modes.brainrot.ImageClip') as mock_image:
        mock_image_instance = MagicMock()
        mock_image_instance.set_duration.return_value = mock_image_instance
        mock_image_instance.fadein.return_value = mock_image_instance
        mock_image_instance.fadeout.return_value = mock_image_instance
        mock_image_instance.set_opacity.return_value = mock_image_instance
        mock_image_instance.set_position.return_value = mock_image_instance
        mock_image_instance.set_audio.return_value = mock_image_instance
        mock_image.return_value = mock_image_instance
        
        # We need to mock CompositeVideoClip and write_videofile inside the function
        with patch('src.modes.brainrot.CompositeVideoClip') as mock_composite:
            mock_composite.return_value.duration = 1.0
            mock_composite.return_value.set_audio.return_value = mock_composite.return_value
            
            create_brainrot_video(["slide1.png"], ["audio1.wav"], "out.mp4", "Title")
        
    assert mock_concat.called
