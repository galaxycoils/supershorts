import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from src.modes.brainrot import BrainrotMode
from src.modes.rotgen import RotgenMode
from src.modes.tcm_educational import TCMMode

def test_brainrot_mode_parameters():
    mock_llm = MagicMock()
    mock_tts = MagicMock()
    mock_uploader = MagicMock()
    mock_engine = MagicMock()
    
    mode = BrainrotMode(
        llm_service=mock_llm,
        tts_service=mock_tts,
        uploader_service=mock_uploader,
        video_engine=mock_engine,
        voice="test_voice",
        custom_bg="test_bg.mp4"
    )
    
    assert mode.voice == "test_voice"
    assert mode.custom_bg == "test_bg.mp4"
    
    # Test generate_assets uses the voice
    with patch('src.modes.brainrot.strip_emojis', side_effect=lambda x: x):
        content = {"slides": [{"text": "Hello"}]}
        # Mocking Path objects and touch()
        with patch('src.modes.brainrot.Path.touch'):
            mode.generate_assets(content, "123")
            mock_tts.text_to_speech.assert_called_once()
            args, kwargs = mock_tts.text_to_speech.call_args
            assert kwargs.get('voice') == "test_voice"

def test_rotgen_mode_parameters():
    mock_llm = MagicMock()
    mock_tts = MagicMock()
    mock_uploader = MagicMock()
    mock_engine = MagicMock()
    
    mode = RotgenMode(
        llm_service=mock_llm,
        tts_service=mock_tts,
        uploader_service=mock_uploader,
        video_engine=mock_engine,
        voice="test_voice",
        custom_bg="test_bg.mp4",
        custom_char="test_char.png"
    )
    
    assert mode.voice == "test_voice"
    assert mode.custom_bg == "test_bg.mp4"
    assert mode.custom_char == "test_char.png"
    
    # Test generate_assets uses the voice
    with patch('src.modes.rotgen.strip_emojis', side_effect=lambda x: x):
        content = {"script": "Hello follow for more AI facts"}
        mode.generate_assets(content, "123")
        mock_tts.text_to_speech.assert_called_once()
        args, kwargs = mock_tts.text_to_speech.call_args
        assert kwargs.get('voice') == "test_voice"

def test_tcm_mode_parameters():
    mock_llm = MagicMock()
    mock_tts = MagicMock()
    mock_uploader = MagicMock()
    mock_engine = MagicMock()
    
    mode = TCMMode(
        llm_service=mock_llm,
        tts_service=mock_tts,
        uploader_service=mock_uploader,
        video_engine=mock_engine,
        voice="test_voice",
        custom_bg="test_bg.mp4"
    )
    
    assert mode.voice == "test_voice"
    assert mode.custom_bg == "test_bg.mp4"
    
    # Test generate_assets uses the voice
    content = {"short_form_highlight": "Hello", "title": "TCM"}
    # Mocking generate_visuals on the engine service
    mode.generate_assets(content, "123")
    mock_tts.text_to_speech.assert_called_once()
    args, kwargs = mock_tts.text_to_speech.call_args
    assert kwargs.get('voice') == "test_voice"

def test_tcm_mode_custom_bg_propagation():
    mock_llm = MagicMock()
    mock_tts = MagicMock()
    mock_uploader = MagicMock()
    mock_engine = MagicMock()
    
    mode = TCMMode(
        llm_service=mock_llm,
        tts_service=mock_tts,
        uploader_service=mock_uploader,
        video_engine=mock_engine,
        custom_bg="test_bg.mp4"
    )
    
    content = {"title": "TCM"}
    assets = {"images": [Path("img.png")], "audio": [Path("aud.mp3")], "script": ["hello"]}
    
    with patch('src.modes.tcm_educational.Path.exists', return_value=True):
        mode.compose(content, assets, "out.mp4")
        mock_engine.compose_video.assert_called_once()
        args, kwargs = mock_engine.compose_video.call_args
        # VideoOptions is args[3]
        options = args[3]
        assert options.custom_bg == "test_bg.mp4"
