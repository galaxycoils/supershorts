import pytest
from unittest.mock import patch, MagicMock, call, ANY
from pathlib import Path
import tempfile
import shutil
from src.core.config import VideoOptions
from src.core.interfaces import ILLMService, ITTSService, IVideoUploader, IVideoEngine
from src.modes.tutorial import (
    TutorialMode, generate_tutorial_content, start_tutorial_generation,
    _enforce_slide_content
)


@pytest.fixture
def mock_llm():
    return MagicMock(spec=ILLMService)


@pytest.fixture
def mock_tts():
    return MagicMock(spec=ITTSService)


@pytest.fixture
def mock_uploader():
    return MagicMock(spec=IVideoUploader)


@pytest.fixture
def mock_video_engine():
    return MagicMock(spec=IVideoEngine)


@pytest.fixture
def temp_dir():
    """Create temp directory for test output."""
    tmpdir = tempfile.mkdtemp()
    yield Path(tmpdir)
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def tutorial_mode(mock_llm, mock_tts, mock_uploader, mock_video_engine, temp_dir):
    """Create TutorialMode instance with mocks."""
    with patch("src.modes.tutorial.OUTPUT_DIR", temp_dir):
        mode = TutorialMode(
            llm_service=mock_llm,
            tts_service=mock_tts,
            uploader_service=mock_uploader,
            video_engine=mock_video_engine,
            dry_run=False,
            voice="en-US"
        )
    return mode


@pytest.fixture
def tutorial_mode_dry_run(mock_llm, mock_tts, mock_uploader, mock_video_engine, temp_dir):
    """Create TutorialMode instance in dry_run mode."""
    with patch("src.modes.tutorial.OUTPUT_DIR", temp_dir):
        mode = TutorialMode(
            llm_service=mock_llm,
            tts_service=mock_tts,
            uploader_service=mock_uploader,
            video_engine=mock_video_engine,
            dry_run=True,
            voice="en-US"
        )
    return mode


class TestTutorialModeInit:
    """Test TutorialMode initialization."""

    def test_init_with_all_services(self, mock_llm, mock_tts, mock_uploader, mock_video_engine):
        """Initialize with all services."""
        mode = TutorialMode(mock_llm, mock_tts, mock_uploader, mock_video_engine)
        assert mode.llm is mock_llm
        assert mode.tts is mock_tts
        assert mode.uploader is mock_uploader
        assert mode.video_engine is mock_video_engine
        assert mode.dry_run is False

    def test_init_dry_run_mode(self, mock_llm, mock_tts, mock_uploader, mock_video_engine):
        """Initialize in dry_run mode."""
        mode = TutorialMode(
            mock_llm, mock_tts, mock_uploader, mock_video_engine,
            dry_run=True, voice="en-GB"
        )
        assert mode.dry_run is True
        assert mode.voice == "en-GB"


class TestGetPendingTopics:
    """Test topic selection."""

    def test_get_pending_topics_returns_one(self, tutorial_mode):
        """get_pending_topics returns exactly one random topic."""
        with patch("random.sample") as mock_sample:
            mock_sample.return_value = ["Machine Learning"]
            topics = tutorial_mode.get_pending_topics()
            assert len(topics) == 1
            assert topics[0]["title"] == "Machine Learning"

    def test_get_pending_topics_format(self, tutorial_mode):
        """Topics are dicts with 'title' key."""
        topics = tutorial_mode.get_pending_topics()
        assert isinstance(topics, list)
        assert all("title" in t for t in topics)


class TestMarkComplete:
    """Test completion marking."""

    def test_mark_complete_dry_run(self, tutorial_mode_dry_run):
        """Dry run doesn't call log_upload."""
        topic = {"title": "Test Topic"}
        tutorial_mode_dry_run.mark_complete(topic, "video_123")
        # Should not raise

    def test_mark_complete_logs_upload(self, tutorial_mode):
        """mark_complete calls log_upload when not dry_run."""
        with patch("src.core.learning.log_upload") as mock_log:
            topic = {"title": "Test Topic"}
            tutorial_mode.mark_complete(topic, "video_123")
            mock_log.assert_called_once_with("Test Topic", "video_123", "tutorial")

    def test_mark_complete_skips_upload_if_no_id(self, tutorial_mode):
        """mark_complete skips log_upload if video_id is None."""
        with patch("src.core.learning.log_upload") as mock_log:
            topic = {"title": "Test Topic"}
            tutorial_mode.mark_complete(topic, None)
            mock_log.assert_not_called()


class TestGenerateScript:
    """Test script generation."""

    def test_generate_script_dry_run(self, tutorial_mode_dry_run):
        """Dry run returns canned script."""
        topic = {"title": "Python Basics"}
        result = tutorial_mode_dry_run.generate_script(topic)
        assert "long_slides" in result
        assert result["title"] == "Python Basics"
        assert "Dry run" in result["long_slides"][0]["content"]

    def test_generate_script_calls_llm(self, tutorial_mode):
        """Real mode calls LLM."""
        tutorial_mode.llm.generate.return_value = {
            "long_slides": [
                {"title": "Intro", "content": "This is a test " * 20}
            ],
            "short_highlight": "Hook and CTA",
            "hashtags": "#Learning"
        }
        topic = {"title": "Python"}
        result = tutorial_mode.generate_script(topic)
        assert result["title"] == "Python"
        tutorial_mode.llm.generate.assert_called_once()

    def test_generate_script_enforces_slide_content(self, tutorial_mode):
        """Script enforces slide content word counts."""
        tutorial_mode.llm.generate.return_value = {
            "long_slides": [
                {"title": "Short", "content": "Too short"}  # 2 words
            ],
            "short_highlight": "Hook",
            "hashtags": "#Tag"
        }
        topic = {"title": "Python"}
        result = tutorial_mode.generate_script(topic)
        # _enforce_slide_content should pad to 120+ words
        slide_words = len(result["long_slides"][0]["content"].split())
        assert slide_words >= 120

    def test_generate_script_fallback_on_llm_failure(self, tutorial_mode):
        """Falls back when LLM returns empty."""
        tutorial_mode.llm.generate.return_value = None
        topic = {"title": "Python"}
        result = tutorial_mode.generate_script(topic)
        assert "long_slides" in result
        assert len(result["long_slides"]) > 0


class TestGenerateAssets:
    """Test asset generation."""

    def test_generate_assets_dry_run(self, tutorial_mode_dry_run):
        """Dry run creates touch files."""
        content = {
            "long_slides": [
                {"title": "Slide 1", "content": "Content 1" * 20}
            ]
        }
        uid = "test_uid"
        result = tutorial_mode_dry_run.generate_assets(content, uid)
        assert "images" in result
        assert "audio" in result
        assert len(result["images"]) > 0
        assert len(result["audio"]) > 0

    def test_generate_assets_calls_tts(self, tutorial_mode):
        """Real mode calls TTS for audio."""
        tutorial_mode.tts.text_to_speech.return_value = "/path/to/audio.mp3"
        tutorial_mode.video_engine.generate_visuals.return_value = "/path/to/slide.png"

        content = {
            "long_slides": [
                {"title": "Slide 1", "content": "Content 1" * 20},
                {"title": "Slide 2", "content": "Content 2" * 20}
            ]
        }
        uid = "test_uid"
        result = tutorial_mode.generate_assets(content, uid)

        assert result["audio"]
        assert tutorial_mode.tts.text_to_speech.call_count == 2

    def test_generate_assets_calls_video_engine(self, tutorial_mode):
        """Real mode calls video_engine for visuals."""
        tutorial_mode.tts.text_to_speech.return_value = "/path/audio.mp3"
        tutorial_mode.video_engine.generate_visuals.return_value = "/path/slide.png"

        content = {
            "long_slides": [
                {"title": "Intro", "content": "Content" * 20}
            ]
        }
        uid = "test_uid"
        tutorial_mode.generate_assets(content, uid)

        tutorial_mode.video_engine.generate_visuals.assert_called_once()
        # Check positional args since they're not passed as kwargs
        call_args = tutorial_mode.video_engine.generate_visuals.call_args
        # Video type is the second positional arg (after output_dir)
        assert call_args[0][1] == "long"


class TestCompose:
    """Test video composition."""

    def test_compose_dry_run(self, tutorial_mode_dry_run):
        """Dry run touches output file."""
        content = {"long_slides": [], "title": "Test"}
        assets = {"images": [Path("/tmp/slide.png")], "audio": [Path("/tmp/audio.mp3")]}
        output = str(tutorial_mode_dry_run.output_dir / "output.mp4")

        result = tutorial_mode_dry_run.compose(content, assets, output)

        assert Path(output).exists()

    def test_compose_calls_video_engine(self, tutorial_mode):
        """Real mode calls video_engine.compose_video."""
        content = {
            "long_slides": [
                {"title": "Slide", "content": "Content"}
            ],
            "title": "Lesson Title"
        }
        assets = {
            "images": [Path("/tmp/slide.png")],
            "audio": [Path("/tmp/audio.mp3")]
        }
        output = "/tmp/output.mp4"

        tutorial_mode.compose(content, assets, output)

        tutorial_mode.video_engine.compose_video.assert_called_once()
        # Check fourth positional arg which is options
        call_args = tutorial_mode.video_engine.compose_video.call_args
        options = call_args[0][3]
        assert options.video_type == "long"
        assert options.is_tutorial is True


class TestUpload:
    """Test video upload."""

    def test_upload_dry_run(self, tutorial_mode_dry_run):
        """Dry run returns DRY_RUN_ID."""
        content = {"title": "Test"}
        result = tutorial_mode_dry_run.upload(content, "/path/to/video.mp4")
        assert result == "DRY_RUN_ID"

    def test_upload_calls_uploader(self, tutorial_mode):
        """Real mode calls uploader.upload."""
        tutorial_mode.uploader.upload.return_value = "video_123"
        content = {
            "title": "Python Basics",
            "hashtags": "#Python #Dev"
        }
        result = tutorial_mode.upload(content, "/path/to/video.mp4")

        tutorial_mode.uploader.upload.assert_called_once()
        assert result == "video_123"


class TestRunTutorialPipeline:
    """Test full pipeline."""

    def test_run_tutorial_pipeline_dry_run(self, tutorial_mode_dry_run):
        """Dry run pipeline completes without calling services."""
        tutorial_mode_dry_run.run_tutorial_pipeline("Python Basics")
        # Should not raise

    def test_run_tutorial_pipeline_calls_all_methods(self, tutorial_mode):
        """Real pipeline calls all steps."""
        tutorial_mode.llm.generate.return_value = {
            "long_slides": [{"title": "Intro", "content": "Content" * 30}],
            "short_highlight": "Hook text here",
            "hashtags": "#Python"
        }
        tutorial_mode.tts.text_to_speech.return_value = Path("/tmp/audio.mp3")
        tutorial_mode.video_engine.generate_visuals.return_value = "/tmp/slide.png"
        tutorial_mode.video_engine.compose_video.return_value = None
        tutorial_mode.uploader.upload.return_value = "vid_123"

        tutorial_mode.run_tutorial_pipeline("Python Basics")

        assert tutorial_mode.llm.generate.called
        assert tutorial_mode.tts.text_to_speech.called
        assert tutorial_mode.video_engine.generate_visuals.called
        assert tutorial_mode.video_engine.compose_video.called


class TestEnforceSlideContent:
    """Test slide content enforcement."""

    def test_enforce_slide_content_pads_short_slides(self):
        """Pad slides with fewer than min_words."""
        slides = [{"title": "Short", "content": "Hi"}]
        result = _enforce_slide_content(slides, min_words=50)
        assert len(result[0]["content"].split()) >= 50

    def test_enforce_slide_content_trims_long_slides(self):
        """Trim slides with more than 200 words."""
        long_content = " ".join(["word"] * 300)
        slides = [{"title": "Long", "content": long_content}]
        result = _enforce_slide_content(slides)
        assert len(result[0]["content"].split()) <= 200

    def test_enforce_slide_content_preserves_title(self):
        """Preserve slide title."""
        slides = [{"title": "MySlide", "content": "Content"}]
        result = _enforce_slide_content(slides)
        assert result[0]["title"] == "MySlide"


class TestGenerateTutorialContent:
    """Test legacy wrapper."""

    def test_generate_tutorial_content(self):
        """Wrapper delegates to TutorialMode.generate_script."""
        mock_llm = MagicMock(spec=ILLMService)
        mock_llm.generate.return_value = {
            "long_slides": [{"title": "Intro", "content": "Content" * 30}],
            "short_highlight": "Hook",
            "hashtags": "#Tag"
        }

        result = generate_tutorial_content("Python", llm_service=mock_llm)

        assert "long_slides" in result
        mock_llm.generate.assert_called_once()


class TestStartTutorialGeneration:
    """Test entry point."""

    def test_start_tutorial_generation_with_topic(self, mock_llm, mock_tts, mock_uploader, mock_video_engine, temp_dir):
        """start_tutorial_generation with explicit topic."""
        mock_llm.generate.return_value = {
            "long_slides": [{"title": "Intro", "content": "Content" * 30}],
            "short_highlight": "Hook",
            "hashtags": "#Tag"
        }
        mock_tts.text_to_speech.return_value = Path("/tmp/audio.mp3")
        mock_video_engine.generate_visuals.return_value = "/tmp/slide.png"

        with patch("src.modes.tutorial.OUTPUT_DIR", temp_dir):
            start_tutorial_generation(
                llm_service=mock_llm,
                tts_service=mock_tts,
                uploader_service=mock_uploader,
                video_engine=mock_video_engine,
                dry_run=True,
                topic="Python"
            )
        # Should not raise
