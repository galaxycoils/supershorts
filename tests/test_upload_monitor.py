"""Tests for upload_monitor — TDD first, implementation follows."""
import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch, mock_open, call

import pytest

from src.utils.upload_monitor import UploadMonitor, log_upload_metric
from src.infrastructure.browser_uploader import UploadMetrics


# ---------------------------------------------------------------------------
# UploadMetrics dataclass
# ---------------------------------------------------------------------------

class TestUploadMetrics:
    def test_fields_present(self):
        m = UploadMetrics(attempt=1, duration_seconds=3.14, success=True, error=None, video_id="abc123xyz01")
        assert m.attempt == 1
        assert m.duration_seconds == 3.14
        assert m.success is True
        assert m.error is None
        assert m.video_id == "abc123xyz01"

    def test_failure_state(self):
        m = UploadMetrics(attempt=2, duration_seconds=0.5, success=False, error="TimeoutError", video_id=None)
        assert m.success is False
        assert m.error == "TimeoutError"
        assert m.video_id is None

    def test_is_dataclass_serialisable(self):
        m = UploadMetrics(attempt=1, duration_seconds=1.0, success=True, error=None, video_id="vid0000001")
        d = asdict(m)
        assert set(d.keys()) == {"attempt", "duration_seconds", "success", "error", "video_id"}


# ---------------------------------------------------------------------------
# log_upload_metric — standalone helper
# ---------------------------------------------------------------------------

class TestLogUploadMetric:
    def test_writes_valid_jsonl_line(self, tmp_path):
        log_file = tmp_path / "upload_log.jsonl"
        m = UploadMetrics(attempt=1, duration_seconds=2.5, success=True, error=None, video_id="testvid0001")
        log_upload_metric(m, log_path=log_file)

        lines = log_file.read_text().splitlines()
        assert len(lines) == 1
        obj = json.loads(lines[0])
        assert obj["attempt"] == 1
        assert obj["success"] is True
        assert obj["video_id"] == "testvid0001"
        assert "timestamp" in obj

    def test_appends_multiple_lines(self, tmp_path):
        log_file = tmp_path / "upload_log.jsonl"
        for i in range(3):
            m = UploadMetrics(attempt=i + 1, duration_seconds=float(i), success=True, error=None, video_id=None)
            log_upload_metric(m, log_path=log_file)

        lines = log_file.read_text().splitlines()
        assert len(lines) == 3
        attempts = [json.loads(l)["attempt"] for l in lines]
        assert attempts == [1, 2, 3]

    def test_creates_parent_directories(self, tmp_path):
        nested = tmp_path / "deep" / "nested" / "upload_log.jsonl"
        m = UploadMetrics(attempt=1, duration_seconds=0.1, success=False, error="err", video_id=None)
        log_upload_metric(m, log_path=nested)
        assert nested.exists()

    def test_default_log_path_is_supershorts(self, tmp_path, monkeypatch):
        """Default path resolves under ~/.supershorts/upload_log.jsonl"""
        fake_home = tmp_path
        monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))
        m = UploadMetrics(attempt=1, duration_seconds=0.1, success=True, error=None, video_id=None)
        # Call with no explicit log_path — should not raise
        log_upload_metric(m)
        expected = fake_home / ".supershorts" / "upload_log.jsonl"
        assert expected.exists()

    def test_failure_record_contains_error_field(self, tmp_path):
        log_file = tmp_path / "upload_log.jsonl"
        m = UploadMetrics(attempt=1, duration_seconds=1.0, success=False, error="WebDriverException", video_id=None)
        log_upload_metric(m, log_path=log_file)
        obj = json.loads(log_file.read_text().strip())
        assert obj["error"] == "WebDriverException"
        assert obj["success"] is False


# ---------------------------------------------------------------------------
# UploadMonitor class
# ---------------------------------------------------------------------------

class TestUploadMonitor:
    def test_log_path_default(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
        monitor = UploadMonitor()
        assert monitor.log_path == tmp_path / ".supershorts" / "upload_log.jsonl"

    def test_log_path_custom(self, tmp_path):
        p = tmp_path / "custom.jsonl"
        monitor = UploadMonitor(log_path=p)
        assert monitor.log_path == p

    def test_record_writes_metric(self, tmp_path):
        monitor = UploadMonitor(log_path=tmp_path / "log.jsonl")
        m = UploadMetrics(attempt=1, duration_seconds=5.0, success=True, error=None, video_id="x" * 11)
        monitor.record(m)
        lines = (tmp_path / "log.jsonl").read_text().splitlines()
        assert len(lines) == 1

    def test_record_accumulates_in_memory(self, tmp_path):
        monitor = UploadMonitor(log_path=tmp_path / "log.jsonl")
        for i in range(5):
            m = UploadMetrics(attempt=i + 1, duration_seconds=1.0, success=True, error=None, video_id=None)
            monitor.record(m)
        assert len(monitor.history) == 5

    def test_last_success_returns_none_when_empty(self, tmp_path):
        monitor = UploadMonitor(log_path=tmp_path / "log.jsonl")
        assert monitor.last_success() is None

    def test_last_success_returns_latest(self, tmp_path):
        monitor = UploadMonitor(log_path=tmp_path / "log.jsonl")
        monitor.record(UploadMetrics(attempt=1, duration_seconds=1.0, success=False, error="err", video_id=None))
        monitor.record(UploadMetrics(attempt=2, duration_seconds=2.0, success=True, error=None, video_id="vid00000001"))
        result = monitor.last_success()
        assert result is not None
        assert result.video_id == "vid00000001"

    def test_summary_counts(self, tmp_path):
        monitor = UploadMonitor(log_path=tmp_path / "log.jsonl")
        monitor.record(UploadMetrics(attempt=1, duration_seconds=1.0, success=True, error=None, video_id="a" * 11))
        monitor.record(UploadMetrics(attempt=2, duration_seconds=1.0, success=False, error="x", video_id=None))
        monitor.record(UploadMetrics(attempt=3, duration_seconds=1.0, success=True, error=None, video_id="b" * 11))
        s = monitor.summary()
        assert s["total"] == 3
        assert s["successes"] == 2
        assert s["failures"] == 1


# ---------------------------------------------------------------------------
# upload_with_retry on SeleniumUploader
# ---------------------------------------------------------------------------

class TestUploadWithRetry:
    """Tests for SeleniumUploader.upload_with_retry — mocks the inner upload() call."""

    def _make_uploader(self):
        from src.infrastructure.browser_uploader import SeleniumUploader
        uploader = SeleniumUploader.__new__(SeleniumUploader)
        return uploader

    def test_success_on_first_attempt(self, tmp_path):
        from src.infrastructure.browser_uploader import SeleniumUploader
        uploader = self._make_uploader()
        uploader.monitor = MagicMock()
        uploader.upload = MagicMock(return_value="vid00000001")

        result = uploader.upload_with_retry(
            video_path=Path("/fake/video.mp4"),
            title="T", description="D", tags=["a"],
            max_retries=3,
        )
        assert result == "vid00000001"
        uploader.upload.assert_called_once()
        uploader.monitor.record.assert_called_once()
        metric = uploader.monitor.record.call_args[0][0]
        assert metric.success is True
        assert metric.attempt == 1

    def test_retries_on_failure_then_succeeds(self, tmp_path):
        from src.infrastructure.browser_uploader import SeleniumUploader
        uploader = self._make_uploader()
        uploader.monitor = MagicMock()
        # Fail twice, succeed on third
        uploader.upload = MagicMock(side_effect=[None, None, "vid00000002"])

        with patch("src.infrastructure.browser_uploader.time.sleep"):
            result = uploader.upload_with_retry(
                video_path=Path("/fake/video.mp4"),
                title="T", description="D", tags=[],
                max_retries=3,
            )

        assert result == "vid00000002"
        assert uploader.upload.call_count == 3
        assert uploader.monitor.record.call_count == 3

    def test_exhausts_retries_returns_none(self, tmp_path):
        from src.infrastructure.browser_uploader import SeleniumUploader
        uploader = self._make_uploader()
        uploader.monitor = MagicMock()
        uploader.upload = MagicMock(return_value=None)

        with patch("src.infrastructure.browser_uploader.time.sleep"):
            result = uploader.upload_with_retry(
                video_path=Path("/fake/video.mp4"),
                title="T", description="D", tags=[],
                max_retries=3,
            )

        assert result is None
        assert uploader.upload.call_count == 3
        # All three attempts recorded as failures
        calls = uploader.monitor.record.call_args_list
        assert all(c[0][0].success is False for c in calls)

    def test_exception_in_upload_counts_as_failure(self):
        from src.infrastructure.browser_uploader import SeleniumUploader
        uploader = self._make_uploader()
        uploader.monitor = MagicMock()
        uploader.upload = MagicMock(side_effect=RuntimeError("boom"))

        with patch("src.infrastructure.browser_uploader.time.sleep"):
            result = uploader.upload_with_retry(
                video_path=Path("/fake/video.mp4"),
                title="T", description="D", tags=[],
                max_retries=2,
            )

        assert result is None
        assert uploader.upload.call_count == 2
        calls = uploader.monitor.record.call_args_list
        assert all(c[0][0].success is False for c in calls)
        assert calls[0][0][0].error == "boom"

    def test_duration_seconds_is_positive(self):
        from src.infrastructure.browser_uploader import SeleniumUploader
        uploader = self._make_uploader()
        uploader.monitor = MagicMock()
        uploader.upload = MagicMock(return_value="vid00000003")

        uploader.upload_with_retry(
            video_path=Path("/fake/video.mp4"),
            title="T", description="D", tags=[],
            max_retries=1,
        )

        metric = uploader.monitor.record.call_args[0][0]
        assert metric.duration_seconds >= 0.0

    def test_retry_delay_called_between_attempts(self):
        from src.infrastructure.browser_uploader import SeleniumUploader
        uploader = self._make_uploader()
        uploader.monitor = MagicMock()
        uploader.upload = MagicMock(side_effect=[None, "vid00000004"])

        with patch("src.infrastructure.browser_uploader.time.sleep") as mock_sleep:
            uploader.upload_with_retry(
                video_path=Path("/fake/video.mp4"),
                title="T", description="D", tags=[],
                max_retries=3,
            )

        # One sleep between attempt 1 (fail) and attempt 2 (succeed)
        mock_sleep.assert_called_once()
        assert mock_sleep.call_args[0][0] == 5
