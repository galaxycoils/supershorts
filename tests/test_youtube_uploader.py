import pytest
import os
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path
from src.infrastructure.uploader import (
    get_authenticated_service,
    YouTubeApiUploader,
    upload_to_youtube,
    CLIENT_SECRETS_FILE,
    CREDENTIALS_FILE
)

def test_get_authenticated_service_no_files():
    with patch("src.infrastructure.uploader.CREDENTIALS_FILE") as mock_creds, \
         patch("src.infrastructure.uploader.CLIENT_SECRETS_FILE") as mock_secrets:
        mock_creds.exists.return_value = False
        mock_secrets.exists.return_value = False
        
        result = get_authenticated_service()
        assert result is None

@patch("src.infrastructure.uploader.Credentials")
@patch("src.infrastructure.uploader.build")
def test_get_authenticated_service_valid_creds(mock_build, mock_creds_class):
    with patch("src.infrastructure.uploader.CREDENTIALS_FILE") as mock_creds:
        mock_creds.exists.return_value = True
        mock_creds.__str__.return_value = "creds.json"
        
        mock_creds_instance = MagicMock()
        mock_creds_instance.valid = True
        mock_creds_class.from_authorized_user_file.return_value = mock_creds_instance
        
        get_authenticated_service()
        mock_build.assert_called_once()

@patch("src.infrastructure.uploader.Credentials")
@patch("src.infrastructure.uploader.Request")
@patch("src.infrastructure.uploader.build")
def test_get_authenticated_service_refresh(mock_build, mock_request, mock_creds_class):
    with patch("src.infrastructure.uploader.CREDENTIALS_FILE") as mock_creds:
        mock_creds.exists.return_value = True
        mock_creds.__str__.return_value = "creds.json"
        
        mock_creds_instance = MagicMock()
        mock_creds_instance.valid = False
        mock_creds_instance.expired = True
        mock_creds_instance.refresh_token = "token"
        mock_creds_class.from_authorized_user_file.return_value = mock_creds_instance
        
        with patch("builtins.open", mock_open()):
            get_authenticated_service()
            mock_creds_instance.refresh.assert_called_once()
            mock_build.assert_called_once()

@patch("src.infrastructure.uploader.get_authenticated_service")
def test_youtube_api_uploader_no_service(mock_get_svc):
    mock_get_svc.return_value = None
    uploader = YouTubeApiUploader()
    result = uploader.upload(Path("vid.mp4"), "Title", "Desc", ["tag"])
    assert result is None

@patch("src.infrastructure.uploader.get_authenticated_service")
@patch("src.infrastructure.uploader.MediaFileUpload")
def test_youtube_api_uploader_success(mock_media, mock_get_svc):
    mock_youtube = MagicMock()
    mock_get_svc.return_value = mock_youtube
    
    mock_request = MagicMock()
    mock_request.next_chunk.side_effect = [(MagicMock(progress=lambda: 0.5), None), (None, {"id": "vid123"})]
    mock_youtube.videos().insert.return_value = mock_request
    
    uploader = YouTubeApiUploader()
    result = uploader.upload(Path("vid.mp4"), "Title", "Desc", ["tag"])
    assert result == "vid123"

@patch("src.infrastructure.uploader.get_authenticated_service")
@patch("src.infrastructure.uploader.MediaFileUpload")
@patch("os.path.exists", return_value=True)
def test_youtube_api_uploader_with_thumbnail(mock_exists, mock_media, mock_get_svc):
    mock_youtube = MagicMock()
    mock_get_svc.return_value = mock_youtube
    
    mock_request = MagicMock()
    mock_request.next_chunk.return_value = (None, {"id": "vid123"})
    mock_youtube.videos().insert.return_value = mock_request
    
    uploader = YouTubeApiUploader()
    result = uploader.upload(Path("vid.mp4"), "Title", "Desc", ["tag"], Path("thumb.png"))
    assert result == "vid123"
    mock_youtube.thumbnails().set.assert_called_once()

@patch("src.infrastructure.uploader.InstalledAppFlow")
@patch("src.infrastructure.uploader.build")
def test_get_authenticated_service_new_flow(mock_build, mock_flow_class):
    with patch("src.infrastructure.uploader.CREDENTIALS_FILE") as mock_creds, \
         patch("src.infrastructure.uploader.CLIENT_SECRETS_FILE") as mock_secrets:
        mock_creds.exists.return_value = False
        mock_secrets.exists.return_value = True
        
        mock_flow = mock_flow_class.from_client_secrets_file.return_value
        mock_creds_instance = MagicMock()
        mock_creds_instance.to_json.return_value = "{}"
        mock_flow.run_local_server.return_value = mock_creds_instance
        
        with patch("builtins.open", mock_open()):
            get_authenticated_service()
            mock_flow.run_local_server.assert_called_once()

@patch("src.infrastructure.uploader.get_authenticated_service")
@patch("src.infrastructure.uploader.MediaFileUpload")
@patch("os.path.exists", return_value=True)
def test_youtube_api_uploader_thumbnail_error(mock_exists, mock_media, mock_get_svc):
    mock_youtube = MagicMock()
    mock_get_svc.return_value = mock_youtube
    
    mock_request = MagicMock()
    mock_request.next_chunk.return_value = (None, {"id": "vid123"})
    mock_youtube.videos().insert.return_value = mock_request
    
    # Thumbnail upload fails
    mock_youtube.thumbnails().set.side_effect = Exception("Thumb error")
    
    uploader = YouTubeApiUploader()
    # Should not raise, just print error
    result = uploader.upload(Path("vid.mp4"), "Title", "Desc", ["tag"], Path("thumb.png"))
    assert result == "vid123"

@patch("src.infrastructure.uploader.get_authenticated_service")
def test_youtube_api_uploader_error(mock_get_svc):
    mock_get_svc.side_effect = Exception("API error")
    uploader = YouTubeApiUploader()
    with pytest.raises(Exception, match="API error"):
        uploader.upload(Path("vid.mp4"), "T", "D", [])

@patch("src.infrastructure.uploader.YouTubeApiUploader")
def test_upload_to_youtube_legacy(mock_uploader_class):
    mock_uploader = mock_uploader_class.return_value
    mock_uploader.upload.return_value = "ok"
    
    result = upload_to_youtube(Path("v.mp4"), "T", "D", "tag1, tag2")
    assert result == "ok"
    # Verify comma separation
    args = mock_uploader.upload.call_args[0]
    assert args[3] == ["tag1", "tag2"]
