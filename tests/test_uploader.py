import pytest
import os
from unittest.mock import MagicMock, patch
from src.infrastructure.browser_uploader import _find_firefox_profile, _extract_video_id

def test_find_firefox_profile_env():
    with patch.dict(os.environ, {"FIREFOX_PROFILE_PATH": "/tmp/fake_profile"}):
        with patch('os.path.isdir', return_value=True):
            assert _find_firefox_profile() == "/tmp/fake_profile"

def test_extract_video_id_url():
    driver = MagicMock()
    driver.current_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert _extract_video_id(driver) == "dQw4w9WgXcQ"

def test_extract_video_id_elements():
    driver = MagicMock()
    driver.current_url = "https://studio.youtube.com/video/123"
    mock_el = MagicMock()
    mock_el.get_attribute.return_value = "https://youtu.be/dQw4w9WgXcQ"
    driver.find_elements.return_value = [mock_el]
    assert _extract_video_id(driver) == "dQw4w9WgXcQ"

@patch('src.infrastructure.browser_uploader.webdriver.Firefox')
@patch('webdriver_manager.firefox.GeckoDriverManager.install')
def test_get_browser_mock(mock_install, mock_firefox):
    from src.infrastructure.browser_uploader import get_browser
    mock_install.return_value = "/tmp/geckodriver"
    get_browser()
    assert mock_firefox.called
