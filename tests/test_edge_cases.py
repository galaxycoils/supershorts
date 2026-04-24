import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from src.generator import generate_brainrot_topics, generate_brainrot_script, render_brainrot_slide, create_brainrot_video, generate_tcm_curriculum

@patch('src.infrastructure.llm.ollama_generate')
def test_generate_brainrot_topics_invalid_json(mock_ollama):
    # Simulate ollama returning garbage instead of expected dict
    mock_ollama.return_value = {"not_topics": []}
    result = generate_brainrot_topics(count=1)
    assert result == []

@patch('src.generator.ollama_generate')
def test_generate_brainrot_script_missing_keys(mock_ollama):
    # Simulate ollama returning JSON without 'slides'
    mock_ollama.return_value = {"full_script": "Just script, no slides"}
    topic = {"title": "Test", "hook": "Hook", "angle": "Angle"}
    result = generate_brainrot_script(topic)
    # Should use fallback slides
    assert "slides" in result
    assert len(result["slides"]) == 4
    assert result["slides"][0]["text"] == "Hook"

def test_generate_tcm_curriculum_api_error():
    # Simulate API exception via injected ILLMService
    mock_llm = MagicMock()
    mock_llm.generate.side_effect = Exception("Ollama Down")
    result = generate_tcm_curriculum("TCM", "Extra", llm_service=mock_llm)
    # Should use fallback curriculum
    assert result["curriculum_title"] == "TCM Essentials"
    assert len(result["lessons"]) == 10

@patch('src.infrastructure.video_engine_impl.Image.new')
@patch('src.infrastructure.video_engine_impl.ImageDraw.Draw')
def test_render_brainrot_slide_disk_full(mock_draw, mock_image_new, tmp_path):
    # Simulate disk full error during save
    mock_img = MagicMock()
    mock_image_new.return_value = mock_img
    
    # Mock draw.textlength
    mock_draw_instance = MagicMock()
    mock_draw_instance.textlength.return_value = 10
    mock_draw.return_value = mock_draw_instance
    
    # Mock convert("RGB").save(path)
    mock_rgb = MagicMock()
    mock_img.convert.return_value = mock_rgb
    mock_rgb.save.side_effect = OSError(28, "No space left on device")
    
    output_dir = tmp_path / "full_disk_test"
    with pytest.raises(OSError) as excinfo:
        render_brainrot_slide(output_dir, "Some text", 1, 1)
    assert excinfo.value.errno == 28

def test_create_brainrot_video_mismatch():
    # Test count mismatch
    with pytest.raises(ValueError, match="Slide/audio count mismatch"):
        create_brainrot_video(["s1.png"], ["a1.wav", "a2.wav"], "out.mp4", "Title")

@patch('src.infrastructure.video_engine_impl.Image.new')
@patch('src.infrastructure.video_engine_impl.ImageDraw.Draw')
def test_render_brainrot_slide_extreme_text(mock_draw, mock_image_new, tmp_path):
    mock_img = MagicMock()
    mock_image_new.return_value = mock_img
    
    mock_draw_instance = MagicMock()
    # Always return a large text length to force font size reduction
    mock_draw_instance.textlength.return_value = 2000 
    mock_draw.return_value = mock_draw_instance
    
    output_dir = tmp_path / "extreme_text_test"
    # Should complete without error, reaching the minimum font size fallback
    path = render_brainrot_slide(output_dir, "Extremely long text that will not fit even at 24pt", 1, 1)
    
    # Since we mocked Image.new, the file isn't actually saved.
    # Check that convert("RGB").save(...) was called on the mock.
    mock_rgb = mock_img.convert.return_value
    assert mock_rgb.save.called
    save_args, _ = mock_rgb.save.call_args
    assert str(save_args[0]).endswith("slide_01.png")
