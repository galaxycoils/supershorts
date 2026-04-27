import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from src.infrastructure.tiktok_uploader import TikTokUploader

def test_tiktok_uploader_init():
    uploader = TikTokUploader(profile_name="test_profile")
    assert uploader.profile_name == "test_profile"

@patch("src.infrastructure.tiktok_uploader.webdriver.Firefox")
@patch("src.infrastructure.tiktok_uploader._build_firefox_service")
@patch("src.infrastructure.tiktok_uploader._find_firefox_profile")
def test_tiktok_upload_success(mock_find_profile, mock_build_service, mock_firefox):
    # Setup mocks
    mock_find_profile.return_value = "/fake/profile"
    mock_driver = MagicMock()
    mock_firefox.return_value = mock_driver
    mock_driver.current_url = "https://www.tiktok.com/upload"
    
    uploader = TikTokUploader()
    video_path = Path("test_video.mp4")
    
    # Mock elements
    mock_file_input = MagicMock()
    mock_caption_el = MagicMock()
    mock_post_btn = MagicMock()
    
    # Mock WebDriverWait
    with patch("src.infrastructure.tiktok_uploader.WebDriverWait") as mock_wait:
        # Sequence of returns for until() calls:
        # 1. iframe check
        # 2. file input
        # 3. caption element
        # 4. post button
        mock_wait.return_value.until.side_effect = [
            MagicMock(), # iframe
            mock_file_input,
            mock_caption_el,
            mock_post_btn
        ]
        
        result = uploader.upload(
            video_path=video_path,
            title="Test Title",
            description="Test Description",
            tags=["tag1", "tag2"]
        )
        
    assert result == "tiktok_upload_success"
    mock_driver.get.assert_called_with("https://www.tiktok.com/upload")
    mock_file_input.send_keys.assert_called()
    mock_driver.execute_script.assert_called()

@patch("src.infrastructure.tiktok_uploader.webdriver.Firefox")
@patch("src.infrastructure.tiktok_uploader._build_firefox_service")
def test_tiktok_upload_not_logged_in(mock_build_service, mock_firefox):
    mock_driver = MagicMock()
    mock_firefox.return_value = mock_driver
    mock_driver.current_url = "https://www.tiktok.com/login"
    
    uploader = TikTokUploader()
    result = uploader.upload(
        video_path=Path("test.mp4"),
        title="T",
        description="D",
        tags=[]
    )
    
    assert result is None

@patch("src.infrastructure.tiktok_uploader.webdriver.Firefox")
@patch("src.infrastructure.tiktok_uploader._build_firefox_service")
def test_tiktok_upload_failure(mock_build_service, mock_firefox):
    mock_driver = MagicMock()
    mock_firefox.return_value = mock_driver
    mock_driver.get.side_effect = Exception("Browser crashed")
    
    uploader = TikTokUploader()
    result = uploader.upload(
        video_path=Path("test.mp4"),
        title="T",
        description="D",
        tags=[]
    )
    
    assert result is None
