import pytest
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path
from PIL import Image
import src.infrastructure.video as video

def test_get_local_background_empty_folder():
    with patch("src.infrastructure.video.BACKGROUNDS_PATH") as mock_path:
        mock_path.exists.return_value = False
        img = video.get_local_background("test", "short")
        assert img.size == video.SHORT_VIDEO_SIZE
        assert img.mode == 'RGBA'

def test_get_local_background_no_images():
    with patch("src.infrastructure.video.BACKGROUNDS_PATH") as mock_path:
        mock_path.exists.return_value = True
        # First call glob("*.*") returns something to pass the first check
        # Then images = list(jpg) + list(png) + list(jpeg) is empty
        mock_path.glob.side_effect = [[MagicMock()], [], [], []]
        img = video.get_local_background("test", "long")
        assert img.size == video.LONG_VIDEO_SIZE

def test_get_local_viral_gameplay_no_path():
    with patch("src.infrastructure.video.VIRAL_GAMEPLAY_PATH") as mock_path:
        mock_path.exists.return_value = False
        result = video.get_local_viral_gameplay()
        assert result is None

def test_get_local_viral_gameplay_no_clips():
    with patch("src.infrastructure.video.VIRAL_GAMEPLAY_PATH") as mock_path:
        mock_path.exists.return_value = True
        # mock_path / "cleaned_bg.mp4"
        mock_file = MagicMock(spec=Path)
        mock_file.exists.return_value = False
        mock_path.__truediv__.return_value = mock_file

        mock_path.glob.return_value = []
        result = video.get_local_viral_gameplay()
        assert result is None

@patch("requests.get")
def test_get_relevant_pexels_video_error(mock_get):
    mock_get.side_effect = Exception("Network error")
    result = video.get_relevant_pexels_video("nature", "long")
    assert result is None

@patch("requests.get")
def test_get_relevant_pexels_video_no_hd_fallback(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "videos": [
            {
                "id": 789,
                "video_files": [
                    {"quality": "sd", "link": "http://sd_link.mp4"}
                ]
            }
        ]
    }
    mock_get.return_value = mock_response
    
    with patch("src.infrastructure.video.PEXELS_CACHE_DIR") as mock_cache:
        mock_cache.exists.return_value = True
        mock_file = MagicMock(spec=Path)
        mock_file.exists.return_value = True
        mock_file.__str__.return_value = "789.mp4"
        mock_cache.__truediv__.return_value = mock_file
        
        result = video.get_relevant_pexels_video("nature", "long")
        assert result == "789.mp4"


def test_get_local_background_with_match():
    mock_img_path = MagicMock(spec=Path)
    mock_img_path.name = "ai_bg.png"
    mock_img_path.suffix = ".png"
    mock_img_path.__str__.return_value = "ai_bg.png"
    
    with patch("src.infrastructure.video.BACKGROUNDS_PATH") as mock_path, \
         patch("PIL.Image.open") as mock_open_img:
        
        mock_path.exists.return_value = True
        # First call is len(list(BACKGROUNDS_PATH.glob("*.*")))
        # Then images = list(glob(*.jpg)) + list(glob(*.png)) + list(glob(*.jpeg))
        mock_path.glob.side_effect = [
            [mock_img_path], # glob("*.*")
            [],              # glob("*.jpg")
            [mock_img_path], # glob("*.png")
            []               # glob("*.jpeg")
        ]
        
        mock_img = MagicMock(spec=Image.Image)
        mock_img.convert.return_value = mock_img
        mock_img.resize.return_value = mock_img
        mock_open_img.return_value = mock_img
        
        img = video.get_local_background("AI learning", "short")
        assert img is not None
        mock_open_img.assert_called_once_with(mock_img_path)

def test_get_local_gameplay_clips_exist():
    mock_clip = MagicMock(spec=Path)
    mock_clip.__str__.return_value = "gameplay.mp4"
    with patch("src.infrastructure.video.GAMEPLAY_PATH") as mock_path:
        mock_path.glob.return_value = [mock_clip]
        result = video.get_local_gameplay("short")
        assert result == "gameplay.mp4"

def test_get_local_gameplay_fallback_to_pexels_cache():
    mock_clip = MagicMock(spec=Path)
    mock_clip.__str__.return_value = "pexels.mp4"
    with patch("src.infrastructure.video.GAMEPLAY_PATH") as mock_gameplay, \
         patch("src.infrastructure.video.PEXELS_CACHE_DIR") as mock_pexels:
        mock_gameplay.glob.return_value = []
        mock_pexels.exists.return_value = True
        mock_pexels.glob.return_value = [mock_clip]
        result = video.get_local_gameplay("short")
        assert result == "pexels.mp4"

def test_get_local_gameplay_none():
    with patch("src.infrastructure.video.GAMEPLAY_PATH") as mock_gameplay, \
         patch("src.infrastructure.video.PEXELS_CACHE_DIR") as mock_pexels:
        mock_gameplay.glob.return_value = []
        mock_pexels.exists.return_value = False
        result = video.get_local_gameplay("short")
        assert result is None

def test_get_local_viral_gameplay_cleaned_bg():
    with patch("src.infrastructure.video.VIRAL_GAMEPLAY_PATH") as mock_path:
        mock_path.exists.return_value = True
        # mock_path / "cleaned_bg.mp4"
        mock_file = MagicMock(spec=Path)
        mock_file.exists.return_value = True
        mock_file.name = "cleaned_bg.mp4"
        mock_file.__str__.return_value = "cleaned_bg.mp4"
        mock_path.__truediv__.return_value = mock_file
        
        result = video.get_local_viral_gameplay()
        assert result == "cleaned_bg.mp4"

def test_get_local_viral_gameplay_random():
    mock_clip = MagicMock(spec=Path)
    mock_clip.name = "subway.mp4"
    mock_clip.__str__.return_value = "subway.mp4"
    with patch("src.infrastructure.video.VIRAL_GAMEPLAY_PATH") as mock_path:
        mock_path.exists.return_value = True
        # mock_path / "cleaned_bg.mp4"
        mock_file = MagicMock(spec=Path)
        mock_file.exists.return_value = False
        mock_path.__truediv__.return_value = mock_file
        
        mock_path.glob.return_value = [mock_clip]
        result = video.get_local_viral_gameplay()
        assert result == "subway.mp4"

def test_get_relevant_pexels_video_empty_query():
    assert video.get_relevant_pexels_video("", "short") is None

@patch("requests.get")
def test_get_relevant_pexels_video_success(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "videos": [
            {
                "id": 123,
                "video_files": [
                    {"quality": "hd", "link": "http://hd_link.mp4"}
                ]
            }
        ]
    }
    mock_get.return_value = mock_response
    
    with patch("src.infrastructure.video.PEXELS_CACHE_DIR") as mock_cache:
        mock_cache.exists.return_value = True
        # mock_cache / "123.mp4"
        mock_file = MagicMock(spec=Path)
        mock_file.exists.return_value = True
        mock_file.__str__.return_value = "123.mp4"
        mock_cache.__truediv__.return_value = mock_file
        
        result = video.get_relevant_pexels_video("nature", "long")
        assert result == "123.mp4"

@patch("requests.get")
def test_get_relevant_pexels_video_download(mock_get):
    mock_search_res = MagicMock()
    mock_search_res.json.return_value = {
        "videos": [{"id": 456, "video_files": [{"quality": "hd", "link": "http://link.mp4"}]}]
    }
    
    mock_download_res = MagicMock()
    mock_download_res.iter_content.return_value = [b"data"]
    
    mock_get.side_effect = [mock_search_res, mock_download_res]
    
    with patch("src.infrastructure.video.PEXELS_CACHE_DIR") as mock_cache:
        mock_file = MagicMock(spec=Path)
        mock_file.exists.return_value = False
        mock_file.__str__.return_value = "456.mp4"
        mock_cache.__truediv__.return_value = mock_file
        
        with patch("builtins.open", mock_open()) as mocked_file:
            result = video.get_relevant_pexels_video("tech", "short")
            assert result == "456.mp4"
            mocked_file.assert_called()
