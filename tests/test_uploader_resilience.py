import pytest
from unittest.mock import MagicMock, patch
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from src.infrastructure.browser_uploader import upload_to_youtube_browser
import time

@patch('src.infrastructure.browser_uploader.get_browser')
@patch('src.infrastructure.browser_uploader.WebDriverWait')
def test_upload_timeout_handling(mock_wait_class, mock_get_browser):
    mock_driver = MagicMock()
    mock_get_browser.return_value = mock_driver
    mock_driver.current_url = "https://studio.youtube.com/upload"
    
    # Simulate a timeout by making wait.until raise a TimeoutException
    mock_wait = MagicMock()
    mock_wait_class.return_value = mock_wait
    from selenium.common.exceptions import TimeoutException
    mock_wait.until.side_effect = TimeoutException("Element not found")
    
    result = upload_to_youtube_browser("video.mp4", "Title", "Desc", "Tags")
    assert result is None
    assert mock_driver.quit.called

@patch('src.infrastructure.browser_uploader.get_browser')
@patch('src.infrastructure.browser_uploader.WebDriverWait')
def test_upload_slow_network_success(mock_wait_class, mock_get_browser):
    mock_driver = MagicMock()
    mock_get_browser.return_value = mock_driver
    mock_driver.current_url = "https://www.youtube.com/watch?v=12345678901"
    
    # Mock successful element interactions
    mock_wait = MagicMock()
    mock_wait_class.return_value = mock_wait
    
    # Mock find_elements to return appropriate mock objects
    mock_textbox = MagicMock()
    mock_driver.find_elements.side_effect = [
        [mock_textbox, mock_textbox], # textboxes
        [MagicMock()],                # next_btns (generic fallback)
        [MagicMock()],                # radios
        [MagicMock()],                # done_btns
        []                            # _extract_video_id link_els
    ]
    
    result = upload_to_youtube_browser("video.mp4", "Title", "Desc", "Tags")
    assert result == "12345678901"
    assert mock_driver.quit.called
