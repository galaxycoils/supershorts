# FILE: src/uploader.py
# This is the new, robust version that handles authentication correctly
# for both local use and GitHub Actions deployment.

import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from pathlib import Path

CLIENT_SECRETS_FILE = Path('client_secrets.json')
CREDENTIALS_FILE = Path('credentials.json')
YOUTUBE_UPLOAD_SCOPE = ["https://www.googleapis.com/auth/youtube.upload"]

def get_authenticated_service():
    credentials = None
    if CREDENTIALS_FILE.exists():
        print("INFO: Found existing credentials file.")
        credentials = Credentials.from_authorized_user_file(str(CREDENTIALS_FILE), YOUTUBE_UPLOAD_SCOPE)
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            print("INFO: Refreshing expired credentials...")
            credentials.refresh(Request())
        else:
            print("INFO: No valid credentials found. Checking for client_secrets.json...")
            if not CLIENT_SECRETS_FILE.exists():
                print(f"WARNING: {CLIENT_SECRETS_FILE} not found. YouTube upload will be skipped.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS_FILE), scopes=YOUTUBE_UPLOAD_SCOPE)
            credentials = flow.run_local_server(port=0)
        with open(CREDENTIALS_FILE, 'w') as f:
            f.write(credentials.to_json())
        print(f"INFO: Credentials saved to {CREDENTIALS_FILE}")
    return build('youtube', 'v3', credentials=credentials)

def upload_to_youtube(video_path, title, description, tags, thumbnail_path=None):
    print(f"Uploading '{video_path}' to YouTube...")
    try:
        youtube = get_authenticated_service()
        if not youtube:
            print("YouTube service not available. Skipping upload.")
            return "MOCK_VIDEO_ID"
        request_body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags.split(','),
                'categoryId': '28'
            },
            'status': {
                'privacyStatus': 'public',
                'selfDeclaredMadeForKids': False
            }
        }
        media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
        request = youtube.videos().insert(
            part=','.join(request_body.keys()),
            body=request_body,
            media_body=media
        )
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"Uploaded {int(status.progress() * 100)}%.")
        video_id = response.get('id')
        print(f"Video uploaded successfully! Video ID: {video_id}")
        if thumbnail_path and os.path.exists(thumbnail_path):
            print(f"Uploading thumbnail '{thumbnail_path}' for video ID: {video_id}...")
            try:
                thumbnail_media = MediaFileUpload(str(thumbnail_path))
                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=thumbnail_media
                ).execute()
                print("Thumbnail uploaded successfully!")
            except Exception as e:
                print(f"ERROR: Failed to upload thumbnail: {e}")
        else:
            print("No thumbnail path provided or thumbnail file does not exist. Skipping thumbnail upload.")
        return video_id
    except Exception as e:
        print(f"ERROR: Failed to upload to YouTube. {e}")
        raise
