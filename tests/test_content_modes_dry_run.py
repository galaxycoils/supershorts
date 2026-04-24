import json
import pytest
from pathlib import Path
from src.core.config import VideoOptions

# Mock helpers
def _lesson_content(title="Lesson"):
    return {
        "long_form_slides": [{"title": title, "content": "Detailed lesson content for dry run."}],
        "short_form_highlight": "Lesson highlight",
        "hashtags": "#DryRun #Lesson"
    }

class DryRunHarness:
    def __init__(self, tmp_path):
        self.output_dir = tmp_path / "output"
        self.output_dir.mkdir()
        self.uploads = []
    
    def get_mock_services(self):
        from unittest.mock import MagicMock
        from src.core.interfaces import ILLMService, ITTSService, IVideoUploader, IVideoEngine
        llm = MagicMock(spec=ILLMService)
        tts = MagicMock(spec=ITTSService)
        uploader = MagicMock(spec=IVideoUploader)
        engine = MagicMock(spec=IVideoEngine)
        
        # Default behavior
        llm.generate.return_value = {}
        tts.text_to_speech.side_effect = lambda t, p, **kw: p
        engine.generate_visuals.side_effect = lambda *args, **kw: str(Path(args[0] if args else kw.get('output_dir')) / "slide.png")
        engine.compose_video.side_effect = lambda *args, **kw: args[2] if len(args) > 2 else kw.get('output_path')
        uploader.upload.side_effect = self.fake_upload
        
        return llm, tts, uploader, engine

    def fake_upload(self, video_path, title, description, tags, thumbnail_path=None, **kwargs):
        self.uploads.append({
            "path": str(video_path),
            "title": title,
            "desc": description,
            "tags": tags,
            "thumbnail": str(thumbnail_path) if thumbnail_path else None
        })
        return "DRY_RUN_ID"

    def fake_log_upload(self, title, video_id, mode):
        self.uploads.append({"title": title, "id": video_id, "mode": mode})

@pytest.fixture
def harness(tmp_path):
    return DryRunHarness(tmp_path)

def test_educational_mode_dry_run(monkeypatch, harness):
    import main
    from src.generator import generate_lesson_content
    
    mock_llm, mock_tts, mock_uploader, mock_engine = harness.get_mock_services()
    
    content_plan = harness.output_dir / "content_plan.json"
    content_plan.write_text(json.dumps({
        "lessons": [{"chapter": 1, "part": 1, "title": "Dry Run Lesson", "status": "pending", "youtube_id": None}]
    }))
    
    monkeypatch.setattr(main, "CONTENT_PLAN_FILE", content_plan)
    monkeypatch.setattr(main, "OUTPUT_DIR", harness.output_dir)
    # Patch the bridge function to return our controlled content
    monkeypatch.setattr("main.generate_lesson_content", lambda *args, **kw: _lesson_content())
    monkeypatch.setattr("main.log_upload", harness.fake_log_upload)
    
    main.main_flow(lessons_per_run=1, llm_service=mock_llm, tts_service=mock_tts, uploader_service=mock_uploader, video_engine=mock_engine)
    
    plan = json.loads(content_plan.read_text())
    assert plan["lessons"][0]["status"] == "complete"

def test_tutorial_mode_dry_run(monkeypatch, harness):
    import src.modes.tutorial as tutorial
    mock_llm, mock_tts, mock_uploader, mock_engine = harness.get_mock_services()
    mock_llm.generate.return_value = {
        "long_slides": [{"title": "Slide 1", "content": "Tutorial content " * 30}],
        "short_highlight": "Highlight",
        "hashtags": "#Tutorial"
    }
    
    monkeypatch.setattr(tutorial, "OUTPUT_DIR", harness.output_dir)
    monkeypatch.setattr("builtins.input", lambda _p="": "")
    monkeypatch.setattr("src.core.learning.log_upload", harness.fake_log_upload)
    
    tutorial.start_tutorial_generation(llm_service=mock_llm, tts_service=mock_tts, uploader_service=mock_uploader, video_engine=mock_engine, dry_run=True)
    assert len(harness.uploads) >= 1

def test_brainrot_mode_dry_run(tmp_path, monkeypatch, harness):
    import src.modes.brainrot as brainrot
    mock_llm, mock_tts, mock_uploader, mock_engine = harness.get_mock_services()
    mock_llm.generate.return_value = {
        "slides": [{"text": "Slide 1"}],
        "full_script": "Script",
        "title": "Title",
        "hashtags": "#Brainrot"
    }
    
    plan_file = tmp_path / "brainrot_plan.json"
    plan_file.write_text(json.dumps({"topics": [{"title": "Topic", "hook": "H", "angle": "A", "status": "pending"}]}))
    
    monkeypatch.setattr(brainrot, "BRAINROT_PLAN_FILE", plan_file)
    monkeypatch.setattr(brainrot, "OUTPUT_DIR", harness.output_dir)
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kw: "")
    monkeypatch.setattr("src.core.learning.log_upload", harness.fake_log_upload)
    
    brainrot.run_brainrot_pipeline(shorts_per_run=1, llm_service=mock_llm, tts_service=mock_tts, uploader_service=mock_uploader, video_engine=mock_engine, dry_run=True)
    
    plan = json.loads(plan_file.read_text())
    assert plan["topics"][0]["status"] == "complete"

def test_rotgen_mode_dry_run(tmp_path, monkeypatch, harness):
    import src.modes.rotgen as rotgen
    mock_llm, mock_tts, mock_uploader, mock_engine = harness.get_mock_services()
    mock_llm.generate.return_value = {"script": "Script follow for more AI facts", "title": "Title", "hashtags": "#Rotgen"}
    
    monkeypatch.setattr(rotgen, "OUTPUT_DIR", harness.output_dir)
    monkeypatch.setattr(rotgen, "ROTGEN_PLAN_FILE", tmp_path / "rotgen_plan.json")
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kw: "")
    monkeypatch.setattr("src.core.learning.log_upload", harness.fake_log_upload)
    
    rotgen.run_rotgen_pipeline(shorts_per_run=1, llm_service=mock_llm, tts_service=mock_tts, uploader_service=mock_uploader, video_engine=mock_engine, dry_run=True)
    assert len(harness.uploads) >= 1

def test_studio_ideas_mode_dry_run(tmp_path, monkeypatch, harness):
    import src.modes.studio_ideas as studio
    mock_llm, mock_tts, mock_uploader, mock_engine = harness.get_mock_services()
    mock_llm.generate.return_value = [{"title": "Idea", "hook": "H", "dialogue": "D " * 20, "thumbnail_prompt": "P"}]
    
    monkeypatch.setattr(studio, "OUTPUT_DIR", harness.output_dir)
    monkeypatch.setattr(studio, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(studio, "IDEAS_FILE", tmp_path / "ideas.json")
    monkeypatch.setattr(studio, "CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(studio, "LOG_FILE", tmp_path / "log.json")
    monkeypatch.setattr(studio, "get_yt_api_key", lambda: "fake")
    monkeypatch.setattr("src.core.learning.log_upload", harness.fake_log_upload)
    
    studio.start_idea_generator(llm_service=mock_llm, tts_service=mock_tts, uploader_service=mock_uploader, video_engine=mock_engine, dry_run=True)
    assert len(harness.uploads) >= 1
