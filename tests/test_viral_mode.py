"""Tests for viral.py — dry-run behavior and DRY_RUN_ID elimination."""
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def _make_services():
    llm = MagicMock()
    llm.generate.return_value = {
        "selected_title": "Test Title",
        "full_script": "A" * 600,
        "pexels_keywords": "test",
        "description": "desc",
        "hashtags": "#Test",
    }
    tts = MagicMock()
    tts.text_to_speech.side_effect = lambda text, path, **kw: path
    uploader = MagicMock()
    uploader.upload.return_value = "real_video_id"
    engine = MagicMock()
    engine.generate_visuals.return_value = "/tmp/slide.png"
    engine.compose_video.return_value = "/tmp/video.mp4"
    return llm, tts, uploader, engine


class TestGenerateYoutubeContentPackageDryRun:
    def test_dry_run_returns_none_video_id(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PACKAGE_TOPIC", "AI Tools")
        monkeypatch.setenv("OUTPUT_DIR", str(tmp_path))
        from src.core import config
        monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path)

        from src.modes.viral import generate_youtube_content_package
        import src.modes.viral as viral_mod
        monkeypatch.setattr(viral_mod, "OUTPUT_DIR", tmp_path)

        llm, tts, uploader, engine = _make_services()
        with patch("src.core.learning.log_upload") as mock_log:
            generate_youtube_content_package(
                llm_service=llm, tts_service=tts,
                uploader_service=uploader, video_engine=engine,
                dry_run=True,
            )
            # uploader must NOT be called on dry run
            uploader.upload.assert_not_called()
            # log_upload must NOT be called with a fake/None id
            mock_log.assert_not_called()

    def test_live_run_calls_uploader_and_logs(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PACKAGE_TOPIC", "Machine Learning")
        import src.modes.viral as viral_mod
        monkeypatch.setattr(viral_mod, "OUTPUT_DIR", tmp_path)

        llm, tts, uploader, engine = _make_services()
        with patch("src.core.learning.log_upload") as mock_log:
            from src.modes.viral import generate_youtube_content_package
            generate_youtube_content_package(
                llm_service=llm, tts_service=tts,
                uploader_service=uploader, video_engine=engine,
                dry_run=False,
            )
            uploader.upload.assert_called_once()
            mock_log.assert_called_once()
            args = mock_log.call_args[0]
            assert args[1] == "real_video_id"


class TestStartViralGameplayModeDryRun:
    def test_dry_run_no_upload_no_log(self, tmp_path, monkeypatch):
        monkeypatch.setenv("VIRAL_TOPIC", "Python Tips")
        import src.modes.viral as viral_mod
        monkeypatch.setattr(viral_mod, "OUTPUT_DIR", tmp_path)
        monkeypatch.setattr(viral_mod, "VIRAL_GAMEPLAY_PATH", tmp_path)

        llm, tts, uploader, engine = _make_services()

        lesson_content = {
            "long_form_slides": [{"title": "T", "content": "C"}] * 3,
            "short_form_highlight": "Tip!",
            "hashtags": "#AI",
        }
        with patch("src.generator.generate_lesson_content", return_value=lesson_content), \
             patch("src.core.learning.log_upload") as mock_log:
            from src.modes.viral import start_viral_gameplay_mode
            start_viral_gameplay_mode(
                llm_service=llm, tts_service=tts,
                uploader_service=uploader, video_engine=engine,
                dry_run=True,
            )
            uploader.upload.assert_not_called()
            mock_log.assert_not_called()
