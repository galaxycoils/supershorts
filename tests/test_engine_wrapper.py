import pytest
from unittest.mock import patch, MagicMock, call
from pathlib import Path
from src.core.config import VideoOptions
from src.engine.video_engine import generate_visuals, compose_video


class TestEngineWrapperGenerateVisuals:
    """Test generate_visuals wrapper delegation."""

    def test_generate_visuals_delegates_to_engine(self):
        """generate_visuals delegates to _engine.generate_visuals."""
        with patch("src.engine.video_engine._engine") as mock_engine:
            mock_engine.generate_visuals.return_value = "/path/to/output.png"

            result = generate_visuals(
                output_dir="/tmp",
                video_type="brainrot",
                slide_content={"text": "Hello"},
                slide_number=1,
                total_slides=5
            )

            mock_engine.generate_visuals.assert_called_once()
            assert result == "/path/to/output.png"

    def test_generate_visuals_passes_all_arguments(self):
        """Verify all arguments are passed to engine."""
        with patch("src.engine.video_engine._engine") as mock_engine:
            mock_engine.generate_visuals.return_value = "result.png"

            slide_content = {"title": "Test", "description": "Desc"}
            generate_visuals(
                output_dir="/tmp",
                video_type="tutorial",
                slide_content=slide_content,
                slide_number=2,
                total_slides=10,
                is_thumbnail=True,
                thumbnail_title="My Title"
            )

            call_kwargs = mock_engine.generate_visuals.call_args[1]
            assert call_kwargs["output_dir"] == "/tmp"
            assert call_kwargs["video_type"] == "tutorial"
            assert call_kwargs["slide_content"] == slide_content
            assert call_kwargs["slide_number"] == 2
            assert call_kwargs["total_slides"] == 10
            assert call_kwargs["is_thumbnail"] is True
            assert call_kwargs["thumbnail_title"] == "My Title"

    def test_generate_visuals_with_none_slide_content(self):
        """Handle None slide_content."""
        with patch("src.engine.video_engine._engine") as mock_engine:
            mock_engine.generate_visuals.return_value = "result.png"

            result = generate_visuals(
                output_dir="/tmp",
                video_type="brainrot",
                slide_content=None
            )

            assert result == "result.png"
            call_kwargs = mock_engine.generate_visuals.call_args[1]
            assert call_kwargs["slide_content"] is None

    def test_generate_visuals_with_path_objects(self):
        """Handle pathlib.Path objects."""
        with patch("src.engine.video_engine._engine") as mock_engine:
            mock_engine.generate_visuals.return_value = "result.png"

            output_path = Path("/tmp/output")
            generate_visuals(
                output_dir=output_path,
                video_type="brainrot"
            )

            call_kwargs = mock_engine.generate_visuals.call_args[1]
            assert call_kwargs["output_dir"] == output_path

    def test_generate_visuals_default_parameters(self):
        """Test default parameter values."""
        with patch("src.engine.video_engine._engine") as mock_engine:
            mock_engine.generate_visuals.return_value = "result.png"

            generate_visuals(
                output_dir="/tmp",
                video_type="brainrot"
            )

            call_kwargs = mock_engine.generate_visuals.call_args[1]
            assert call_kwargs["slide_number"] == 1
            assert call_kwargs["total_slides"] == 1
            assert call_kwargs["is_thumbnail"] is False
            assert call_kwargs["thumbnail_title"] == ""


class TestEngineWrapperComposeVideo:
    """Test compose_video wrapper delegation."""

    def test_compose_video_delegates_to_engine(self):
        """compose_video delegates to _engine.compose_video."""
        with patch("src.engine.video_engine._engine") as mock_engine:
            mock_engine.compose_video.return_value = "/path/to/final.mp4"

            options = VideoOptions(video_type="long", lesson_title="Test")
            result = compose_video(
                slide_paths=["/tmp/slide1.png"],
                audio_paths=["/tmp/audio1.mp3"],
                output_path="/tmp/output.mp4",
                options=options
            )

            mock_engine.compose_video.assert_called_once()
            assert result == "/path/to/final.mp4"

    def test_compose_video_passes_all_arguments(self):
        """Verify all arguments are passed to engine."""
        with patch("src.engine.video_engine._engine") as mock_engine:
            mock_engine.compose_video.return_value = "final.mp4"

            slide_paths = ["/tmp/slide1.png", "/tmp/slide2.png"]
            audio_paths = ["/tmp/audio1.mp3", "/tmp/audio2.mp3"]
            output_path = "/tmp/output.mp4"
            options = VideoOptions(video_type="long", lesson_title="Test")

            compose_video(
                slide_paths=slide_paths,
                audio_paths=audio_paths,
                output_path=output_path,
                options=options
            )

            mock_engine.compose_video.assert_called_once()

    def test_compose_video_with_path_objects(self):
        """Handle pathlib.Path objects."""
        with patch("src.engine.video_engine._engine") as mock_engine:
            slide_paths = [Path("/tmp/slide1.png")]
            audio_paths = [Path("/tmp/audio1.mp3")]
            output_path = Path("/tmp/output.mp4")
            options = VideoOptions(video_type="long", lesson_title="Test")

            compose_video(
                slide_paths=slide_paths,
                audio_paths=audio_paths,
                output_path=output_path,
                options=options
            )

            mock_engine.compose_video.assert_called_once()

    def test_compose_video_with_empty_lists(self):
        """Handle empty slide/audio lists."""
        with patch("src.engine.video_engine._engine") as mock_engine:
            options = VideoOptions(video_type="long", lesson_title="Test")
            compose_video(
                slide_paths=[],
                audio_paths=[],
                output_path="/tmp/output.mp4",
                options=options
            )

            mock_engine.compose_video.assert_called_once()

    def test_compose_video_with_multiple_files(self):
        """Handle multiple files."""
        with patch("src.engine.video_engine._engine") as mock_engine:
            slide_paths = [f"/tmp/slide{i}.png" for i in range(10)]
            audio_paths = [f"/tmp/audio{i}.mp3" for i in range(10)]
            options = VideoOptions(video_type="long", lesson_title="Test")

            compose_video(
                slide_paths=slide_paths,
                audio_paths=audio_paths,
                output_path="/tmp/output.mp4",
                options=options
            )

            mock_engine.compose_video.assert_called_once()
