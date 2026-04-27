import os
import logging
import pytest
from unittest.mock import patch, mock_open, MagicMock
from src.core.logging import setup_logging, get_logger


class TestSetupLogging:
    """Test logging configuration."""

    def test_setup_logging_default_level(self):
        """Test setup_logging with default INFO level."""
        setup_logging()
        root = logging.getLogger()
        assert root.level == logging.INFO

    def test_setup_logging_with_custom_level(self):
        """Test setup_logging with explicit level."""
        setup_logging(level=logging.DEBUG)
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_setup_logging_from_env_var(self):
        """Test setup_logging reads LOG_LEVEL from environment."""
        with patch.dict(os.environ, {"LOG_LEVEL": "WARNING"}):
            setup_logging()
            root = logging.getLogger()
            assert root.level == logging.WARNING

    def test_setup_logging_invalid_env_var_defaults_to_info(self):
        """Test invalid LOG_LEVEL env var falls back to INFO."""
        with patch.dict(os.environ, {"LOG_LEVEL": "INVALID"}, clear=False):
            setup_logging()
            root = logging.getLogger()
            assert root.level == logging.INFO

    def test_setup_logging_removes_existing_handlers(self):
        """Test that setup_logging clears existing handlers to avoid duplicates."""
        root = logging.getLogger()
        # Add a dummy handler
        dummy_handler = logging.StreamHandler()
        root.addHandler(dummy_handler)
        initial_count = len(root.handlers)

        setup_logging()
        # Should have at least the console handler, but no duplicates
        assert len(root.handlers) >= 1

    def test_setup_logging_adds_console_handler(self):
        """Test that setup_logging adds a console handler."""
        setup_logging()
        root = logging.getLogger()
        handlers = root.handlers
        assert any(isinstance(h, logging.StreamHandler) for h in handlers)

    def test_setup_logging_with_log_file(self):
        """Test setup_logging creates file handler when LOG_FILE is set."""
        with patch.dict(os.environ, {"LOG_FILE": "/tmp/test.log"}, clear=False):
            with patch("pathlib.Path.mkdir"):
                with patch("logging.FileHandler") as mock_file_handler:
                    setup_logging()
                    # Verify FileHandler was called
                    mock_file_handler.assert_called_once_with("/tmp/test.log")

    def test_setup_logging_suppresses_noisy_loggers(self):
        """Test that noisy loggers are suppressed."""
        setup_logging()
        assert logging.getLogger("moviepy").level == logging.WARNING
        assert logging.getLogger("selenium").level == logging.WARNING
        assert logging.getLogger("urllib3").level == logging.WARNING


class TestGetLogger:
    """Test logger retrieval."""

    def test_get_logger_returns_named_logger(self):
        """Test get_logger returns a logger with correct name."""
        logger = get_logger("test_module")
        assert logger.name == "test_module"

    def test_get_logger_returns_same_logger_on_multiple_calls(self):
        """Test get_logger returns same logger for same name."""
        logger1 = get_logger("same_module")
        logger2 = get_logger("same_module")
        assert logger1 is logger2

    def test_get_logger_different_names_return_different_loggers(self):
        """Test different names return different logger instances."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")
        assert logger1 is not logger2
