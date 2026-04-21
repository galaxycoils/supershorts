import json
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image


class DryRunHarness:
    def __init__(self, root: Path):
        self.root = root
        self.output_dir = root / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.uploads = []
        self.logs = []
        self.compositions = []
        self.tts_calls = []
        self._upload_counter = 0

    def fake_tts(self, text, output_path):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        wav_path = output_path.with_suffix(".wav")
        wav_path.write_bytes(b"RIFFDRYRUNWAVE")
        self.tts_calls.append({"text": text, "path": str(wav_path)})
        return wav_path

    def fake_visuals(self, output_dir, video_type, slide_content=None,
                     slide_number=1, total_slides=1, is_thumbnail=False, thumbnail_title=""):
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        name = "thumbnail.png" if is_thumbnail or thumbnail_title else f"slide_{slide_number:02d}.png"
        path = output_dir / name
        Image.new("RGB", (64, 64), color=(20, 40, 60)).save(path)
        return str(path)

    def fake_compose(self, slide_paths, audio_paths, output_path, *args, **kwargs):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"DRYRUNMP4")
        self.compositions.append({
            "slides": list(map(str, slide_paths)),
            "audio": list(map(str, audio_paths)),
            "output": str(output_path),
            "args": args,
            "kwargs": kwargs,
        })
        return str(output_path)

    def fake_upload(self, video_path, title, description, tags, thumbnail_path=None):
        self._upload_counter += 1
        video_id = f"DRYRUN{self._upload_counter:05d}"
        self.uploads.append({
            "video_path": str(video_path),
            "title": title,
            "description": description,
            "tags": tags,
            "thumbnail_path": None if thumbnail_path is None else str(thumbnail_path),
            "video_id": video_id,
        })
        return video_id

    def fake_log_upload(self, title, video_id, mode):
        self.logs.append({"title": title, "video_id": video_id, "mode": mode})

    def fake_sleep(self, *_args, **_kwargs):
        return None

    def fake_render_slide(self, output_dir, *_args, slide_index=1, **_kwargs):
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"slide_{slide_index:02d}.png"
        Image.new("RGB", (64, 64), color=(80, 30, 20)).save(path)
        return str(path)

    def fake_create_video(self, _slide_paths, _audio_paths, output_path, *_args, **_kwargs):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"DRYRUNVIDEO")
        self.compositions.append({"output": str(output_path), "type": "brainrot"})

    def fake_subprocess_run(self, cmd, cwd=None, **_kwargs):
        cmd = list(cmd)
        workspace = Path(cmd[cmd.index("--workspace") + 1])
        output_dir = workspace / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "clip_01.mp4").write_bytes(b"DRYRUNCLIP")
        return SimpleNamespace(stdout="dry-run clipper ok", stderr="", returncode=0)


class FakeAudioClip:
    def __init__(self, *_args, duration=1.5, **_kwargs):
        self.duration = duration

    def close(self):
        return None


class FakeClip:
    def close(self):
        return None


def _lesson_content(title: str) -> dict:
    return {
        "long_form_slides": [
            {"title": f"{title} Intro", "content": "Dry run slide content one."},
            {"title": f"{title} Detail", "content": "Dry run slide content two."},
        ],
        "short_form_highlight": f"Dry run highlight for {title}",
        "hashtags": "#DryRun #AI #Shorts",
    }


def _lesson_content_with_kwargs(title: str, **_kwargs) -> dict:
    return _lesson_content(title)


@pytest.fixture
def harness(tmp_path, monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda *_args, **_kwargs: None)
    return DryRunHarness(tmp_path)


def test_educational_mode_dry_run(tmp_path, monkeypatch, harness):
    import main

    content_plan = tmp_path / "content_plan.json"
    content_plan.write_text(json.dumps({
        "lessons": [
            {"chapter": 1, "part": 1, "title": "Dry Run Lesson", "status": "pending", "youtube_id": None}
        ]
    }, indent=2))

    monkeypatch.setattr(main, "CONTENT_PLAN_FILE", content_plan)
    monkeypatch.setattr(main, "OUTPUT_DIR", harness.output_dir)
    monkeypatch.setattr(main, "generate_lesson_content", _lesson_content)
    monkeypatch.setattr(main, "text_to_speech", harness.fake_tts)
    monkeypatch.setattr(main, "generate_visuals", harness.fake_visuals)
    monkeypatch.setattr(main, "compose_video", harness.fake_compose)
    monkeypatch.setattr(main, "upload_to_youtube", harness.fake_upload)
    monkeypatch.setattr(main, "log_upload", harness.fake_log_upload)

    main.main_flow(lessons_per_run=1)

    updated_plan = json.loads(content_plan.read_text())
    assert updated_plan["lessons"][0]["status"] == "complete"
    assert len(harness.uploads) == 2
    assert len(harness.compositions) == 2


def test_tutorial_mode_dry_run(monkeypatch, harness):
    import src.modes.tutorial as tutorial
    import src.infrastructure.browser_uploader as uploader
    import src.core.learning as learning

    monkeypatch.setattr(tutorial, "OUTPUT_DIR", harness.output_dir)
    monkeypatch.setattr("builtins.input", lambda _prompt="": "")
    monkeypatch.setattr(tutorial, "generate_tutorial_content", lambda _topic: {
        "long_slides": [
            {"title": "Slide 1", "content": "Detailed tutorial dry run content."},
            {"title": "Slide 2", "content": "More detailed tutorial dry run content."},
        ],
        "short_highlight": "Dry run tutorial short highlight",
        "hashtags": "#DryRun #Tutorial",
    })
    monkeypatch.setattr(tutorial, "text_to_speech", harness.fake_tts)
    monkeypatch.setattr(tutorial, "generate_visuals", harness.fake_visuals)
    monkeypatch.setattr(tutorial, "compose_video", harness.fake_compose)
    monkeypatch.setattr(uploader, "upload_to_youtube_browser", harness.fake_upload)
    monkeypatch.setattr(learning, "log_upload", harness.fake_log_upload)

    tutorial.start_tutorial_generation()

    assert len(harness.uploads) == 2
    assert len(harness.compositions) == 2


def test_viral_mode_dry_run(monkeypatch, harness):
    import src.modes.viral as viral
    import src.infrastructure.browser_uploader as uploader
    import src.core.learning as learning
    import src.generator as generator

    monkeypatch.setattr(viral, "OUTPUT_DIR", harness.output_dir)
    monkeypatch.setattr("builtins.input", lambda _prompt="": "")
    monkeypatch.setattr(viral, "ollama_generate", lambda *_args, **_kwargs: {
        "selected_title": "Dry Run Content Package",
        "full_script": "Dry run package script " * 40,
        "pexels_keywords": "ai productivity",
        "description": "Dry run package description",
        "hashtags": "#DryRun #Package",
    })
    monkeypatch.setattr(generator, "generate_lesson_content", _lesson_content_with_kwargs)
    monkeypatch.setattr(viral, "text_to_speech", harness.fake_tts)
    monkeypatch.setattr(viral, "generate_visuals", harness.fake_visuals)
    monkeypatch.setattr(viral, "compose_video", harness.fake_compose)
    monkeypatch.setattr(uploader, "upload_to_youtube_browser", harness.fake_upload)
    monkeypatch.setattr(learning, "log_upload", harness.fake_log_upload)

    viral.generate_youtube_content_package()
    viral.start_viral_gameplay_mode()

    assert len(harness.uploads) == 2
    assert len(harness.compositions) == 2


def test_brainrot_mode_dry_run(tmp_path, monkeypatch, harness):
    import src.modes.brainrot as brainrot
    import src.infrastructure.browser_uploader as uploader

    monkeypatch.setattr(brainrot, "OUTPUT_DIR", harness.output_dir)
    monkeypatch.setattr(brainrot, "BRAINROT_PLAN_FILE", tmp_path / "brainrot_plan.json")
    monkeypatch.setattr(brainrot, "generate_brainrot_topics", lambda **_kwargs: [
        {"title": "Dry Run Brainrot", "hook": "Hook", "angle": "Angle"}
    ])
    monkeypatch.setattr(brainrot, "generate_brainrot_script", lambda _topic: {
        "slides": [{"text": "Brain rot one"}, {"text": "Brain rot two"}],
        "full_script": "Dry run brain rot script for testing.",
        "title": "Dry Run Brainrot Title",
        "hashtags": "#DryRun #Brainrot",
    })
    monkeypatch.setattr(brainrot, "text_to_speech", harness.fake_tts)
    monkeypatch.setattr(brainrot, "render_brainrot_slide", harness.fake_render_slide)
    monkeypatch.setattr(brainrot, "create_brainrot_video", harness.fake_create_video)
    monkeypatch.setattr(uploader, "upload_to_youtube_browser", harness.fake_upload)

    brainrot.run_brainrot_pipeline(shorts_per_run=1)

    plan = json.loads(brainrot.BRAINROT_PLAN_FILE.read_text())
    assert plan["topics"][0]["status"] == "complete"
    assert len(harness.uploads) == 1


def test_rotgen_mode_dry_run(tmp_path, monkeypatch, harness):
    import src.modes.rotgen as rotgen
    import src.infrastructure.browser_uploader as uploader
    import src.core.learning as learning

    monkeypatch.setattr(rotgen, "OUTPUT_DIR", harness.output_dir)
    monkeypatch.setattr(rotgen, "ROTGEN_PLAN_FILE", tmp_path / "rotgen_plan.json")
    monkeypatch.setattr(rotgen, "CHARACTERS_PATH", tmp_path / "characters")
    monkeypatch.setattr(rotgen, "VIRAL_TOPICS", ["Dry Run RotGen Topic"])
    monkeypatch.setattr(rotgen, "_build_panel_background", lambda: None)
    monkeypatch.setattr(rotgen, "_load_custom_character", lambda: None)
    monkeypatch.setattr(rotgen, "generate_rotgen_script", lambda _topic=None: {
        "script": "Dry run rotgen script for testing follow for more AI facts",
        "title": "Dry Run RotGen",
        "hashtags": "#DryRun #RotGen",
    })
    monkeypatch.setattr(rotgen, "text_to_speech", harness.fake_tts)
    monkeypatch.setattr(rotgen, "AudioFileClip", FakeAudioClip)
    monkeypatch.setattr(rotgen, "build_character_clip", lambda *_args, **_kwargs: FakeClip())
    monkeypatch.setattr(rotgen, "build_gameplay_clip", lambda *_args, **_kwargs: FakeClip())
    monkeypatch.setattr(rotgen, "compose_rotgen_video", lambda *_args, output_path=None, **_kwargs: harness.fake_compose([], [], output_path or _args[4]))
    monkeypatch.setattr(uploader, "upload_to_youtube_browser", harness.fake_upload)
    monkeypatch.setattr(learning, "log_upload", harness.fake_log_upload)

    rotgen.run_rotgen_pipeline(shorts_per_run=1)

    plan = json.loads(rotgen.ROTGEN_PLAN_FILE.read_text())
    assert len(plan["videos"]) == 1
    assert plan["videos"][0]["status"] == "complete"


def test_studio_ideas_mode_dry_run(tmp_path, monkeypatch, harness):
    import src.modes.studio_ideas as studio
    import src.infrastructure.browser_uploader as uploader
    import src.core.learning as learning

    monkeypatch.setattr(studio, "OUTPUT_DIR", harness.output_dir)
    monkeypatch.setattr(studio, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(studio, "IDEAS_FILE", tmp_path / "youtube_studio_ideas.json")
    monkeypatch.setattr(studio, "CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(studio, "LOG_FILE", tmp_path / "performance_log.json")
    monkeypatch.setattr(studio, "get_yt_api_key", lambda: None)
    monkeypatch.setattr(studio, "generate_ideas", lambda num_ideas=5: [{
        "title": "Dry Run Idea",
        "hook": "Hook",
        "dialogue": "Dry run studio idea dialogue " * 12,
        "thumbnail_prompt": "dry run thumbnail",
    }])
    monkeypatch.setattr(studio, "text_to_speech", harness.fake_tts)
    monkeypatch.setattr(studio, "generate_visuals", harness.fake_visuals)
    monkeypatch.setattr(studio, "compose_video", harness.fake_compose)
    monkeypatch.setattr(uploader, "upload_to_youtube_browser", harness.fake_upload)
    monkeypatch.setattr(learning, "log_upload", harness.fake_log_upload)

    studio.start_idea_generator()

    assert len(harness.uploads) == 1
    assert len(harness.compositions) == 1


def test_tcm_mode_dry_run(tmp_path, monkeypatch, harness):
    import src.modes.tcm_educational as tcm
    import src.generator as generator
    import src.infrastructure.tts as tts
    import src.engine.video_engine as video_engine
    import src.infrastructure.browser_uploader as uploader
    import src.core.learning as learning

    plan_path = tmp_path / "tcm_plan.json"
    plan_path.write_text(json.dumps({
        "curriculum_title": "Dry Run TCM",
        "lessons": [
            {"chapter": 1, "part": 1, "title": "Dry Run TCM Lesson", "status": "pending", "youtube_id": None}
        ],
    }, indent=2))

    monkeypatch.setattr(tcm, "TCM_PLAN_FILE", plan_path)
    monkeypatch.setattr(tcm, "OUTPUT_DIR", harness.output_dir)
    monkeypatch.setattr(tcm.Prompt, "ask", lambda *args, **kwargs: "y" if "Use it?" in str(args[0]) else "1")
    monkeypatch.setattr(generator, "generate_lesson_content", _lesson_content_with_kwargs)
    monkeypatch.setattr(tts, "text_to_speech", harness.fake_tts)
    monkeypatch.setattr(video_engine, "generate_visuals", harness.fake_visuals)
    monkeypatch.setattr(video_engine, "compose_video", harness.fake_compose)
    monkeypatch.setattr(uploader, "upload_to_youtube_browser", harness.fake_upload)
    monkeypatch.setattr(learning, "log_upload", harness.fake_log_upload)

    tcm.run_tcm_mode()

    updated = json.loads(plan_path.read_text())
    assert updated["lessons"][0]["status"] == "complete"
    assert len(harness.uploads) == 1


def test_clipper_mode_dry_run(tmp_path, monkeypatch, harness):
    import src.modes.clipper as clipper
    import src.infrastructure.browser_uploader as uploader
    import src.core.learning as learning

    monkeypatch.setattr(clipper, "WORKSPACE", tmp_path / "clipper_workspace")
    monkeypatch.setattr(clipper, "_check_setup", lambda: True)
    monkeypatch.setattr(clipper, "_verify_clipper_dependencies", lambda: True)
    monkeypatch.setattr(clipper.Prompt, "ask", lambda *_args, **_kwargs: "https://example.com/video")
    monkeypatch.setattr(clipper.subprocess, "run", harness.fake_subprocess_run)
    monkeypatch.setattr(uploader, "upload_to_youtube_browser", harness.fake_upload)
    monkeypatch.setattr(learning, "log_upload", harness.fake_log_upload)

    clipper.run_video_clipper()

    assert len(harness.uploads) == 1


def test_workflow_runner_dry_run(monkeypatch):
    import run_workflow

    calls = []
    monkeypatch.setattr(run_workflow, "TASK_FNS", {
        "task_a": lambda **_kwargs: calls.append("a") or {"step": "a"},
        "task_b": lambda **_kwargs: calls.append("b") or {"step": "b"},
    })
    workflow = {
        "name": "dry-run-workflow",
        "description": "Dry run workflow harness",
        "tasks": [
            {"id": "a", "name": "Task A", "fn": "task_a"},
            {"id": "b", "name": "Task B", "fn": "task_b", "depends_on": ["a"]},
        ],
    }

    result = run_workflow.WorkflowRunner(workflow).run()

    assert result["status"] == "ok"
    assert calls == ["a", "b"]
