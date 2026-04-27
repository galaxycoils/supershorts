import pytest
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path
from src.infrastructure.tts import (
    StandardTTSService,
    text_to_speech
)

def test_tts_piper_success():
    mock_system = MagicMock()
    service = StandardTTSService(system_adapter=mock_system)
    
    with patch("piper.voice.PiperVoice.load") as mock_load, \
         patch("src.infrastructure.tts._PIPER_VOICES_DIR") as mock_dir, \
         patch("wave.open", mock_open()):
        
        mock_file = MagicMock()
        mock_file.exists.return_value = True
        mock_dir.__truediv__.return_value = mock_file
        
        result = service.text_to_speech("hello", Path("out.wav"), voice="ryan")
        assert result == Path("out.wav")
        mock_load.assert_called_once()

def test_tts_piper_fallback_on_voice_not_found():
    mock_system = MagicMock()
    service = StandardTTSService(system_adapter=mock_system)
    
    with patch("piper.voice.PiperVoice.load") as mock_load, \
         patch("src.infrastructure.tts._PIPER_VOICES_DIR") as mock_dir, \
         patch("wave.open", mock_open()):
        
        # mock_dir / "wrong-voice.onnx" doesn't exist
        mock_file = MagicMock()
        mock_file.exists.return_value = False
        mock_dir.__truediv__.return_value = mock_file
        
        # requested voice not found, should print warning but keep trying other candidates
        with patch("builtins.print") as mock_print:
            # It will eventually fail all Piper candidates and move to macOS say
            with patch.object(service.system, "run_command") as mock_say:
                service.text_to_speech("hello", Path("out.wav"), voice="wrong-voice")
                mock_print.assert_any_call("⚠️ Requested voice wrong-voice not found, falling back...")

@patch("src.infrastructure.tts.SystemAdapter")
def test_tts_macos_say_fallback(mock_adapter_class):
    mock_system = mock_adapter_class.return_value
    service = StandardTTSService(system_adapter=mock_system)
    
    # Piper fails (e.g. import error or load error)
    with patch("piper.voice.PiperVoice.load", side_effect=Exception("Piper error")):
        # Alex say works
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.unlink") as mock_unlink:
            service.text_to_speech("hello", Path("out.wav"))
            mock_system.run_command.assert_called()
            mock_system.run_ffmpeg.assert_called()

@patch("src.infrastructure.tts.SystemAdapter")
def test_tts_pyttsx3_fallback(mock_adapter_class):
    mock_system = mock_adapter_class.return_value
    service = StandardTTSService(system_adapter=mock_system)
    
    # Piper fails, macOS say fails
    with patch("piper.voice.PiperVoice.load", side_effect=Exception("error")), \
         patch.object(service.system, "run_command", side_effect=Exception("say failed")), \
         patch("pyttsx3.init") as mock_pyttsx3_init:
        
        mock_engine = mock_pyttsx3_init.return_value
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.unlink"):
            service.text_to_speech("hello", Path("out.wav"))
            mock_engine.save_to_file.assert_called()
            mock_engine.runAndWait.assert_called()

def test_tts_all_fail():
    service = StandardTTSService()
    with patch("src.infrastructure.tts.strip_markdown", return_value="hello"), \
         patch("piper.voice.PiperVoice.load", side_effect=Exception("error")), \
         patch.object(service.system, "run_command", side_effect=Exception("error")), \
         patch("pyttsx3.init", side_effect=Exception("all dead")):
        
        with pytest.raises(Exception, match="all dead"):
            service.text_to_speech("hello", Path("out.wav"))

def test_text_to_speech_legacy():
    with patch("src.infrastructure.tts.StandardTTSService") as mock_class:
        mock_svc = mock_class.return_value
        mock_svc.text_to_speech.return_value = Path("out.wav")
        result = text_to_speech("hello", Path("out.wav"))
        assert result == Path("out.wav")
