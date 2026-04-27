import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from src.infrastructure.instagram_uploader import InstagramUploader, upload_to_instagram_browser

@pytest.fixture
def mock_browser_adapter():
    adapter = MagicMock()
    # Mock push_task to execute the task immediately for testing
    def side_effect(task_fn):
        task_fn()
    adapter.push_task.side_effect = side_effect
    return adapter

@patch("src.infrastructure.instagram_uploader.upload_to_instagram_browser")
def test_instagram_uploader_upload(mock_upload_fn, mock_browser_adapter):
    uploader = InstagramUploader(browser_adapter=mock_browser_adapter)
    mock_upload_fn.return_value = "test_id"
    
    video_path = Path("test.mp4")
    result = uploader.upload(video_path, "Title", "Desc", ["tag1", "tag2"])
    
    assert result == "test_id"
    mock_upload_fn.assert_called_once()
    # Check if caption was formatted correctly
    args, kwargs = mock_upload_fn.call_args
    assert "Title" in kwargs["caption"]
    assert "Desc" in kwargs["caption"]
    assert "#tag1" in kwargs["caption"]
    assert "#tag2" in kwargs["caption"]

@patch("src.infrastructure.instagram_uploader.get_browser")
@patch("time.sleep") # Speed up tests
def test_upload_to_instagram_browser_success(mock_sleep, mock_get_browser):
    mock_driver = MagicMock()
    mock_get_browser.return_value = mock_driver
    mock_driver.current_url = "https://www.instagram.com/"
    
    # Mock WebDriverWait and EC
    with patch("src.infrastructure.instagram_uploader.WebDriverWait") as mock_wait:
        mock_wait_instance = mock_wait.return_value
        # Mock elements
        mock_create_btn = MagicMock()
        mock_file_input = MagicMock()
        mock_next_btn = MagicMock()
        mock_caption_input = MagicMock()
        mock_share_btn = MagicMock()
        mock_success_msg = MagicMock()
        
        mock_wait_instance.until.side_effect = [
            mock_create_btn, # create_btn
            mock_file_input, # file_input
            mock_next_btn,   # next_btn (crop)
            mock_next_btn,   # next_btn (edit)
            mock_caption_input, # caption_input
            mock_share_btn,  # share_btn
            mock_success_msg # success_msg
        ]
        
        result = upload_to_instagram_browser("test.mp4", "Test Caption")
        
        assert result is not None
        assert "instagram_success" in result
        mock_driver.get.assert_called_with("https://www.instagram.com/")
        mock_file_input.send_keys.assert_called()
        mock_caption_input.send_keys.assert_called_with("Test Caption")
        mock_driver.quit.assert_called_once()

@patch("src.infrastructure.instagram_uploader.get_browser")
def test_upload_to_instagram_browser_not_logged_in(mock_get_browser):
    mock_driver = MagicMock()
    mock_get_browser.return_value = mock_driver
    mock_driver.current_url = "https://www.instagram.com/accounts/login/"
    
    result = upload_to_instagram_browser("test.mp4", "Test Caption")
    
    assert result is None
    mock_driver.quit.assert_called_once()
