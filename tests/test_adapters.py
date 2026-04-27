import pytest
from unittest.mock import patch, MagicMock, call
import subprocess
import queue
import threading
from src.infrastructure.adapters.system_adapter import SystemAdapter
from src.infrastructure.adapters.browser_adapter import BrowserAdapter


class TestSystemAdapter:
    """Test system command execution adapter."""

    def test_run_command_basic(self):
        """Execute basic system command."""
        adapter = SystemAdapter()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["echo", "test"], returncode=0, stdout=b"test", stderr=b""
            )
            result = adapter.run_command(["echo", "test"])
            assert result.returncode == 0
            mock_run.assert_called_once()

    def test_run_command_with_check_true(self):
        """Test check=True parameter."""
        adapter = SystemAdapter()
        with patch("subprocess.run") as mock_run:
            adapter.run_command(["cmd"], check=True)
            mock_run.assert_called_once()
            assert mock_run.call_args[1]["check"] is True

    def test_run_command_with_capture_output(self):
        """Test capture_output parameter."""
        adapter = SystemAdapter()
        with patch("subprocess.run") as mock_run:
            adapter.run_command(["cmd"], capture_output=True)
            mock_run.assert_called_once()
            assert mock_run.call_args[1]["capture_output"] is True

    def test_run_command_with_kwargs(self):
        """Test passing additional kwargs."""
        adapter = SystemAdapter()
        with patch("subprocess.run") as mock_run:
            adapter.run_command(["cmd"], timeout=30, cwd="/tmp")
            mock_run.assert_called_once()
            assert "timeout" in mock_run.call_args[1]
            assert "cwd" in mock_run.call_args[1]

    def test_run_ffmpeg_basic(self):
        """Test ffmpeg command construction."""
        adapter = SystemAdapter()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["ffmpeg"], returncode=0
            )
            adapter.run_ffmpeg(
                input_args=["-i", "input.mp4"],
                output_args=["output.mp4"]
            )
            # Verify ffmpeg was called with correct structure
            args = mock_run.call_args[0][0]
            assert args[0] == "ffmpeg"
            assert "-y" in args
            assert "-loglevel" in args
            assert "input.mp4" in args
            assert "output.mp4" in args

    def test_run_ffmpeg_with_loglevel(self):
        """Test ffmpeg with custom loglevel."""
        adapter = SystemAdapter()
        with patch("subprocess.run") as mock_run:
            adapter.run_ffmpeg(
                input_args=["-i", "in.mp4"],
                output_args=["out.mp4"],
                loglevel="verbose"
            )
            args = mock_run.call_args[0][0]
            assert "verbose" in args

    def test_run_ffmpeg_complex_args(self):
        """Test ffmpeg with complex argument lists."""
        adapter = SystemAdapter()
        with patch("subprocess.run") as mock_run:
            input_args = ["-i", "input.mp4", "-filter:v", "scale=1920:1080"]
            output_args = ["-c:v", "libx264", "output.mp4"]
            adapter.run_ffmpeg(input_args=input_args, output_args=output_args)
            args = mock_run.call_args[0][0]
            assert all(arg in args for arg in input_args)
            assert all(arg in args for arg in output_args)


class TestBrowserAdapter:
    """Test browser automation adapter."""

    def test_browser_adapter_init_no_driver(self):
        """Initialize without driver."""
        adapter = BrowserAdapter()
        assert adapter._driver is None
        assert isinstance(adapter.queue, queue.Queue)

    def test_browser_adapter_init_with_driver(self):
        """Initialize with existing driver."""
        mock_driver = MagicMock()
        adapter = BrowserAdapter(driver=mock_driver)
        assert adapter._driver is mock_driver

    def test_browser_adapter_set_driver(self):
        """Set driver after initialization."""
        adapter = BrowserAdapter()
        mock_driver = MagicMock()
        adapter.set_driver(mock_driver)
        assert adapter._driver is mock_driver

    def test_browser_adapter_driver_property_raises_if_none(self):
        """Accessing driver property raises if not initialized."""
        adapter = BrowserAdapter()
        with pytest.raises(RuntimeError):
            _ = adapter.driver

    def test_browser_adapter_driver_property_returns_driver(self):
        """Driver property returns the driver."""
        mock_driver = MagicMock()
        adapter = BrowserAdapter(driver=mock_driver)
        assert adapter.driver is mock_driver

    def test_browser_adapter_get_url(self):
        """Navigate to URL."""
        mock_driver = MagicMock()
        adapter = BrowserAdapter(driver=mock_driver)
        adapter.get("https://example.com")
        mock_driver.get.assert_called_once_with("https://example.com")

    def test_browser_adapter_find_element(self):
        """Find single element."""
        mock_driver = MagicMock()
        mock_element = MagicMock()
        mock_driver.find_element.return_value = mock_element
        adapter = BrowserAdapter(driver=mock_driver)

        from selenium.webdriver.common.by import By
        result = adapter.find_element(By.ID, "test_id")
        assert result is mock_element
        mock_driver.find_element.assert_called_once()

    def test_browser_adapter_find_elements(self):
        """Find multiple elements."""
        mock_driver = MagicMock()
        mock_elements = [MagicMock(), MagicMock()]
        mock_driver.find_elements.return_value = mock_elements
        adapter = BrowserAdapter(driver=mock_driver)

        from selenium.webdriver.common.by import By
        result = adapter.find_elements(By.TAG_NAME, "button")
        assert result == mock_elements

    def test_browser_adapter_wait_for_element(self):
        """Wait for element to be present."""
        mock_driver = MagicMock()
        mock_element = MagicMock()
        adapter = BrowserAdapter(driver=mock_driver)

        with patch("src.infrastructure.adapters.browser_adapter.WebDriverWait") as mock_wait_class:
            mock_wait_instance = MagicMock()
            mock_wait_class.return_value = mock_wait_instance
            mock_wait_instance.until.return_value = mock_element

            from selenium.webdriver.common.by import By
            result = adapter.wait_for_element(By.ID, "test")
            assert result is mock_element

    def test_browser_adapter_wait_for_all_elements(self):
        """Wait for multiple elements to be present."""
        mock_driver = MagicMock()
        mock_elements = [MagicMock()]
        adapter = BrowserAdapter(driver=mock_driver)

        with patch("src.infrastructure.adapters.browser_adapter.WebDriverWait") as mock_wait_class:
            mock_wait_instance = MagicMock()
            mock_wait_class.return_value = mock_wait_instance
            mock_wait_instance.until.return_value = mock_elements

            from selenium.webdriver.common.by import By
            result = adapter.wait_for_all_elements(By.TAG_NAME, "div")
            assert result == mock_elements

    def test_browser_adapter_wait_for_clickable(self):
        """Wait for element to be clickable."""
        mock_driver = MagicMock()
        mock_element = MagicMock()
        adapter = BrowserAdapter(driver=mock_driver)

        with patch("src.infrastructure.adapters.browser_adapter.WebDriverWait") as mock_wait_class:
            mock_wait_instance = MagicMock()
            mock_wait_class.return_value = mock_wait_instance
            mock_wait_instance.until.return_value = mock_element

            from selenium.webdriver.common.by import By
            result = adapter.wait_for_clickable(By.ID, "button")
            assert result is mock_element

    def test_browser_adapter_execute_script(self):
        """Execute JavaScript."""
        mock_driver = MagicMock()
        mock_driver.execute_script.return_value = "result"
        adapter = BrowserAdapter(driver=mock_driver)

        result = adapter.execute_script("return 1 + 1")
        assert result == "result"
        mock_driver.execute_script.assert_called_once()

    def test_browser_adapter_execute_script_with_args(self):
        """Execute JavaScript with arguments."""
        mock_driver = MagicMock()
        adapter = BrowserAdapter(driver=mock_driver)

        adapter.execute_script("return arguments[0]", "arg1")
        mock_driver.execute_script.assert_called_once_with("return arguments[0]", "arg1")

    def test_browser_adapter_quit(self):
        """Close browser."""
        mock_driver = MagicMock()
        adapter = BrowserAdapter(driver=mock_driver)
        adapter.quit()
        mock_driver.quit.assert_called_once()
        assert adapter._driver is None

    def test_browser_adapter_quit_when_none(self):
        """Quit gracefully when driver is None."""
        adapter = BrowserAdapter()
        adapter.quit()  # Should not raise

    def test_browser_adapter_current_url(self):
        """Get current URL."""
        mock_driver = MagicMock()
        mock_driver.current_url = "https://example.com"
        adapter = BrowserAdapter(driver=mock_driver)

        result = adapter.current_url()
        assert result == "https://example.com"

    def test_browser_adapter_push_task(self):
        """Push task to queue."""
        adapter = BrowserAdapter()
        task_fn = MagicMock()
        adapter.push_task(task_fn)
        # Verify task was queued
        assert not adapter.queue.empty()

    def test_browser_adapter_worker_executes_tasks(self):
        """Worker thread executes queued tasks."""
        adapter = BrowserAdapter()
        task_fn = MagicMock()
        adapter.push_task(task_fn)
        # Wait briefly for worker to process
        adapter.queue.join()
        task_fn.assert_called_once()

    def test_browser_adapter_worker_handles_exceptions(self):
        """Worker swallows task exceptions."""
        adapter = BrowserAdapter()

        def failing_task():
            raise RuntimeError("Task failed")

        adapter.push_task(failing_task)
        adapter.queue.join()  # Should not raise
