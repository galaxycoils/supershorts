import pytest
from unittest.mock import MagicMock
from src.core.interfaces import ILLMService, ITTSService, IVideoUploader, IVideoEngine

@pytest.fixture
def mock_llm():
    llm = MagicMock(spec=ILLMService)
    llm.generate.return_value = {}
    return llm

@pytest.fixture
def mock_tts():
    return MagicMock(spec=ITTSService)

@pytest.fixture
def mock_uploader():
    return MagicMock(spec=IVideoUploader)

@pytest.fixture
def mock_engine():
    engine = MagicMock(spec=IVideoEngine)
    # Common engine return values
    engine.generate_visuals.return_value = "fake_image.png"
    engine.compose_video.return_value = "fake_video.mp4"
    return engine
