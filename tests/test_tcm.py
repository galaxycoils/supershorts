import pytest
from unittest.mock import MagicMock, patch
from src.core.config import VideoOptions
from src.generator import generate_tcm_curriculum, clamp_words, compose_video

def test_clamp_words_tcm():
    text = "Short text"
    clamped = clamp_words(text, min_w=10, max_w=20)
    assert len(clamped.split()) >= 10
    assert len(clamped.split()) <= 20

@patch('ollama.chat')
def test_generate_tcm_curriculum_mock(mock_ollama):
    mock_ollama.return_value = {
        'message': {
            'content': '{"curriculum_title": "Test TCM", "lessons": [{"chapter": 1, "part": 1, "title": "Lesson 1", "status": "pending", "youtube_id": null}]}'
        }
    }
    result = generate_tcm_curriculum("TCM", "")
    assert result['curriculum_title'] == "Test TCM"
    assert len(result['lessons']) == 1
    assert result['lessons'][0]['title'] == "Lesson 1"

from src.generator import generate_lesson_content, compose_video

@patch('src.infrastructure.llm.ollama_generate')
def test_generate_lesson_content_params(mock_ollama):
    mock_ollama.return_value = {
        "long_form_slides": [],
        "short_form_highlight": "Test highlight",
        "hashtags": "#test"
    }
    # Test with custom series and style
    generate_lesson_content("TCM Topic", series_name="TCM Series", style_description="Custom Style")
    
    # Check if the prompt sent to ollama contains our custom strings
    # We need to access the first argument of the first call
    assert mock_ollama.called
    args, kwargs = mock_ollama.call_args
    prompt = args[0]
    assert "TCM Series" in prompt
    assert "Custom Style" in prompt

@patch('src.infrastructure.video_engine_impl.get_relevant_pexels_video')
@patch('src.infrastructure.video_engine_impl.get_local_gameplay')
@patch('src.infrastructure.video_engine_impl.AudioFileClip')
@patch('src.infrastructure.video_engine_impl.ImageClip')
@patch('src.infrastructure.video_engine_impl.concatenate_videoclips')
@patch('src.infrastructure.video_engine_impl.VideoFileClip')
def test_compose_video_bg_query(mock_video, mock_concat, mock_image, mock_audio, mock_local, mock_pexels):
    # Mock necessary objects for compose_video to run without errors
    mock_pexels.return_value = "fake_bg.mp4"
    
    # Mock audio
    mock_audio_instance = MagicMock()
    mock_audio_instance.duration = 1.0
    mock_audio.return_value = mock_audio_instance
    
    # Mock video (background)
    mock_video_instance = MagicMock()
    mock_video_instance.duration = 10.0
    mock_video_instance.size = (1080, 1920)
    # Ensure method chaining returns the mock instance
    mock_video_instance.fx.return_value = mock_video_instance
    mock_video_instance.subclip.return_value = mock_video_instance
    mock_video_instance.resize.return_value = mock_video_instance
    mock_video_instance.set_position.return_value = mock_video_instance
    mock_video.return_value = mock_video_instance
    
    # Mock image (slide)
    mock_image_instance = MagicMock()
    mock_image_instance.set_duration.return_value = mock_image_instance
    mock_image_instance.fadein.return_value = mock_image_instance
    mock_image_instance.fadeout.return_value = mock_image_instance
    mock_image_instance.set_opacity.return_value = mock_image_instance
    mock_image_instance.set_position.return_value = mock_image_instance
    mock_image_instance.set_audio.return_value = mock_image_instance
    mock_image.return_value = mock_image_instance
    
    # Run compose_video with bg_query
    with patch('src.infrastructure.video_engine_impl.CompositeVideoClip') as mock_composite:
        mock_composite.return_value.duration = 1.0
        mock_composite.return_value.set_audio.return_value = mock_composite.return_value
        compose_video(["img.png"], ["audio.wav"], "out.mp4", VideoOptions(
            video_type="short", lesson_title="Title", bg_query="TCM Herbs"
        ))
    
    # Verify get_relevant_pexels_video was called with bg_query
    mock_pexels.assert_called_with("TCM Herbs", "short")
