"""Tests for clipper.py — dry-run and env-configurable cooldown."""
import os
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import pytest


class TestRunVideoClipperDryRun:
    def test_dry_run_no_upload_no_log(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLIPPER_URL", str(tmp_path / "video.mp4"))
        monkeypatch.setenv("UPLOAD_COOLDOWN_S", "0")

        # Create a fake mp4 in the expected output dir
        output_dir = tmp_path / "outputs"
        output_dir.mkdir()
        fake_mp4 = output_dir / "clip_01.mp4"
        fake_mp4.write_bytes(b"")

        with patch("src.modes.clipper.WORKSPACE", tmp_path), \
             patch("src.modes.clipper._verify_clipper_dependencies", return_value=True), \
             patch("src.modes.clipper._check_setup", return_value=False), \
             patch("src.modes.clipper._run_builtin_fallback"), \
             patch("src.core.learning.log_upload") as mock_log:

            uploader = MagicMock()
            from src.modes.clipper import run_video_clipper
            run_video_clipper(uploader_service=uploader, dry_run=True)

            uploader.upload.assert_not_called()
            mock_log.assert_not_called()

    def test_cooldown_respects_env_zero(self, tmp_path, monkeypatch):
        """UPLOAD_COOLDOWN_S=0 → no sleep between uploads."""
        monkeypatch.setenv("CLIPPER_URL", str(tmp_path / "video.mp4"))
        monkeypatch.setenv("UPLOAD_COOLDOWN_S", "0")

        output_dir = tmp_path / "outputs"
        output_dir.mkdir()
        for i in range(2):
            (output_dir / f"clip_{i}.mp4").write_bytes(b"")

        uploader = MagicMock()
        uploader.upload.return_value = "vid123"

        with patch("src.modes.clipper.WORKSPACE", tmp_path), \
             patch("src.modes.clipper._verify_clipper_dependencies", return_value=True), \
             patch("src.modes.clipper._check_setup", return_value=False), \
             patch("src.modes.clipper._run_builtin_fallback"), \
             patch("src.core.learning.log_upload"), \
             patch("time.sleep") as mock_sleep:

            from src.modes.clipper import run_video_clipper
            run_video_clipper(uploader_service=uploader, dry_run=False)
            mock_sleep.assert_not_called()


class TestBaseModeGetTopicInput:
    def test_env_var_wins_over_prompt(self, monkeypatch):
        monkeypatch.setenv("MY_TOPIC", "from_env")
        from src.core.base_mode import BaseMode
        result = BaseMode.get_topic_input("MY_TOPIC", "Enter topic: ", default="fallback")
        assert result == "from_env"

    def test_default_used_when_env_and_input_empty(self, monkeypatch):
        monkeypatch.delenv("MY_TOPIC", raising=False)
        with patch("builtins.input", return_value=""):
            from src.core.base_mode import BaseMode
            result = BaseMode.get_topic_input("MY_TOPIC", "Enter topic: ", default="fallback")
        assert result == "fallback"

    def test_eoferror_falls_through_to_default(self, monkeypatch):
        monkeypatch.delenv("MY_TOPIC", raising=False)
        with patch("builtins.input", side_effect=EOFError):
            from src.core.base_mode import BaseMode
            result = BaseMode.get_topic_input("MY_TOPIC", "Enter topic: ", default="fallback")
        assert result == "fallback"
