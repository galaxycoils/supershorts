import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import sys

# We need to mock the entire piper.voice module because StandardTTSService 
# imports it inside the method.
mock_piper = MagicMock()
mock_piper_voice_cls = MagicMock()
mock_piper.PiperVoice = mock_piper_voice_cls

@pytest.fixture(autouse=True)
def setup_piper_mock():
    with patch.dict(sys.modules, {"piper": mock_piper, "piper.voice": mock_piper}):
        yield

@patch("wave.open")
@patch("pathlib.Path.exists")
def test_viral_voice_selection(mock_exists, mock_wave_open):
    from src.infrastructure.tts import StandardTTSService
    service = StandardTTSService()
    output_path = Path("test_output.mp3")
    
    # Mock voice exists
    mock_exists.return_value = True
    
    # Mock Piper synthesis
    mock_voice_instance = MagicMock()
    mock_piper_voice_cls.load.return_value = mock_voice_instance
    
    # Test with different viral voices
    voices = [
        "en_US-ryan-high",
        "en_US-lessac-high",
        "en_US-amy-medium",
        "en_GB-alan-medium",
        "en_US-hfc_female-medium",
        "en_US-joe-medium",
        "en_US-kristin-medium"
    ]
    
    for voice in voices:
        service.text_to_speech("Viral check", output_path, voice=voice)
        # Verify it tried to load the correct .onnx file
        expected_path = Path.home() / f".local/share/piper-tts/voices/{voice}.onnx"
        
        # Check if any call matched the expected path
        found = False
        for call in mock_piper_voice_cls.load.call_args_list:
            if str(call.args[0]) == str(expected_path):
                found = True
                break
        assert found, f"PiperVoice.load not called with {expected_path}"

def test_voice_list_integrity():
    from src.infrastructure.tts import _PIPER_VOICE_NAMES
    
    expected = [
        "en_US-ryan-high",
        "en_US-lessac-high",
        "en_US-amy-medium",
        "en_GB-alan-medium",
        "en_US-hfc_female-medium",
        "en_US-joe-medium",
        "en_US-kristin-medium"
    ]
    for voice in expected:
        assert voice in _PIPER_VOICE_NAMES
