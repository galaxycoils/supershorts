# src/modes/tcm_educational.py - Traditional Chinese Medicine Educational Mode
import gc
import json
import datetime
import time
import random
from pathlib import Path
from typing import List, Dict, Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich import box

from src.core.config import PROJECT_ROOT, OLLAMA_MODEL, OLLAMA_TIMEOUT, YOUR_NAME, VideoOptions, OUTPUT_DIR
from src.core.interfaces import ILLMService, ITTSService, IVideoUploader
from src.core.base_mode import BaseMode
from src.infrastructure.llm import OllamaLLMService, ollama_generate
from src.infrastructure.tts import StandardTTSService
from src.infrastructure.browser_uploader import YouTubeBrowserUploader
from src.engine.video_engine import generate_visuals, compose_video
from src.utils.text import clamp_words
import src.core.learning as _learning

console = Console()

TCM_PLAN_FILE = PROJECT_ROOT / "tcm_plan.json"

TCM_BG_KEYWORDS = [
    "traditional medicine herbs",
    "acupuncture therapy",
    "Chinese herbal medicine",
    "meditation wellness",
    "herb preparation",
    "holistic healing lotus",
    "tea ceremony zen",
]

TOPIC_CHOICES = {
    "1": "Traditional Chinese Medicine (TCM)",
    "2": "Eastern Medicine",
    "3": "Ayurvedic Medicine",
    "4": "Holistic Wellness",
}

def _show_plan_status(plan):
    table = Table(title=f"Plan: {plan.get('curriculum_title', 'Untitled')}", box=box.ROUNDED)
    table.add_column("Ch", justify="right", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Status", justify="center")
    
    for l in plan.get("lessons", []):
        status = "[green]Done[/green]" if l.get("status") == "complete" else "[yellow]Pending[/yellow]"
        table.add_row(str(l.get("chapter", "?")), l.get("title", "Untitled"), status)
    console.print(table)

def generate_tcm_curriculum(focus: str, extra: str, previous_titles=None, llm_service: ILLMService = None) -> dict:
    llm = llm_service or OllamaLLMService(generate_fn=ollama_generate)
    prev = f"\nDo not repeat these titles: {previous_titles}" if previous_titles else ""
    prompt = (
        f"Create a 10-lesson educational video curriculum about: {focus}.\n"
        f"{'Additional focus: ' + extra if extra else ''}{prev}\n\n"
        "Return ONLY valid JSON:\n"
        "{\n"
        '  "curriculum_title": "string",\n'
        '  "lessons": [\n'
        '    {"chapter": 1, "part": 1, "title": "string", "status": "pending", "youtube_id": null}\n'
        '  ]\n'
        "}\n"
        "10 lessons. No markdown, no commentary."
    )
    try:
        return llm.generate(prompt, json_mode=True)
    except Exception as e:
        console.print(f"[yellow]⚠  Curriculum fallback ({e})[/yellow]")
        return {"curriculum_title": "TCM Essentials", "lessons": [{"chapter": i+1, "part": 1, "title": f"TCM Lesson {i+1}", "status": "pending", "youtube_id": None} for i in range(10)]}

class TCMMode(BaseMode):
    def __init__(self, llm_service=None, tts_service=None, uploader_service=None, plan=None, dry_run=False, voice=None):
        super().__init__(llm_service, tts_service, uploader_service)
        self.plan = plan
        self.dry_run = dry_run
        self.voice = voice

    def get_pending_topics(self) -> List[Dict[str, Any]]:
        if not self.plan: return []
        return [l for l in self.plan.get("lessons", []) if l.get("status") == "pending"]

    def mark_complete(self, topic: Dict[str, Any], video_id: Optional[str]):
        if self.dry_run:
            print(f"DEBUG: Dry run complete for {topic['title']}")
            return
        topic["status"] = "complete"
        topic["youtube_id"] = video_id
        TCM_PLAN_FILE.write_text(json.dumps(self.plan, indent=2))
        if video_id:
            _learning.log_upload(topic["title"], video_id, "tcm")

    def generate_script(self, topic: Dict[str, Any]) -> Dict[str, Any]:
        if self.dry_run:
            return {
                "long_form_slides": [{"title": topic["title"], "content": "Dry run content."}],
                "short_form_highlight": f"{topic['title']} dry run highlight.",
                "hashtags": "#DryRun",
                "title": topic["title"]
            }
        series_name = self.plan.get('curriculum_title', 'Traditional Chinese Medicine') if self.plan else 'TCM'
        style_desc = "Assume viewer is interested in Eastern wellness. Use simple analogies."
        
        prompt = f"""You are creating a lesson for '{series_name}'. 
Topic: '{topic["title"]}'
Style: {style_desc}
Generate JSON: long_form_slides (7-8 objs with title/content), short_form_highlight, hashtags."""
        
        result = self.llm.generate(prompt, json_mode=True)
        if not result or not result.get("short_form_highlight"):
            return {
                "long_form_slides": [{"title": topic["title"], "content": "TCM lesson content."}],
                "short_form_highlight": f"{topic['title']} is a key part of TCM wellness.",
                "hashtags": "#TCM #Wellness",
                "title": topic["title"]
            }
        result["title"] = topic["title"]
        return result

    def generate_assets(self, content: Dict[str, Any], uid: str) -> Dict[str, List[Path]]:
        raw_short = content.get("short_form_highlight") or "Educational highlight"
        short_script = clamp_words(raw_short, min_w=99, max_w=127)
        
        if self.dry_run:
            audio_path = Path(f"dry_run_{uid}.wav")
            audio_path.touch()
        else:
            # Piper voice selection
            if self.voice and hasattr(self.tts, 'system'):
                # Hacky way to set voice for standard service if it supports it
                # but better to just pass it if possible.
                # For now we'll just use the default logic but we could enhance ITTSService.
                pass
            audio_path = self.tts.text_to_speech(short_script, self.output_dir / f"tcm_audio_{uid}.mp3", voice=self.voice)

        if self.dry_run:
            slide_path = self.output_dir / f"dry_slide_{uid}.png"
            slide_path.touch()
        else:
            slide_path = generate_visuals(
                output_dir=self.output_dir / f"tcm_slides_{uid}",
                video_type="short",
                slide_content={"title": content.get("title", "TCM"), "content": content.get("short_form_highlight", "")},
                slide_number=1, total_slides=1
            )
        return {"images": [Path(slide_path)], "audio": [audio_path], "script": [short_script]}

    def compose(self, content: Dict[str, Any], assets: Dict[str, List[Path]], output_path: str) -> str:
        if self.dry_run:
            Path(output_path).touch()
            return output_path
        bg_query = random.choice(TCM_BG_KEYWORDS)
        compose_video(assets["images"], assets["audio"], output_path,
                      VideoOptions(video_type="short", lesson_title=content.get("title", "TCM"),
                                   script=assets["script"][0], bg_query=bg_query))
        return output_path

    def upload(self, content: Dict[str, Any], video_path: str) -> Optional[str]:
        if self.dry_run:
            return "DRY_RUN_ID"
        hashtags = content.get("hashtags", "#TCM #Wellness #Health #Shorts")
        desc = f"{content.get('short_form_highlight', '')}\n\n{hashtags}\n\nAI for Developers by {YOUR_NAME}"
        tags = ["TCM", "Traditional Chinese Medicine", "Wellness", "Health", "Eastern Medicine"]
        return self.uploader.upload(Path(video_path), content.get("title", "TCM") + " #Shorts", desc, tags)

def run_tcm_mode(llm_service=None, tts_service=None, uploader_service=None, dry_run=False, voice=None):
    console.print(Panel.fit("🌿 [bold green]SuperShorts TCM Mode[/bold green] 🌿"))
    
    plan = None
    if TCM_PLAN_FILE.exists():
        try:
            plan = json.loads(TCM_PLAN_FILE.read_text())
            _show_plan_status(plan)
            # When called from Dashboard with stdin_input, we might want to skip Prompt.ask
            # but standard implementation uses Prompt.ask. 
            # If stdin_input is provided, Prompt.ask consumes it.
            if Prompt.ask("Use existing plan?", choices=["y", "n"], default="y") == "n":
                plan = None
        except: pass

    if plan is None:
        focus = Prompt.ask("Topic focus", default="Traditional Chinese Medicine")
        extra = Prompt.ask("Extra details", default="")
        llm = llm_service or OllamaLLMService()
        plan = generate_tcm_curriculum(focus, extra, llm_service=llm)
        TCM_PLAN_FILE.write_text(json.dumps(plan, indent=2))

    raw_count = Prompt.ask("How many videos to produce?", default="3")
    mode = TCMMode(llm_service, tts_service, uploader_service, plan, dry_run=dry_run, voice=voice)
    mode.run_pipeline(int(raw_count))
