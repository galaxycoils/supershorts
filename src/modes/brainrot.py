"""src/modes/brainrot.py - Brain Rot / High-Engagement Viral Shorts Generator"""
import json
import os
import random
from typing import List, Dict, Any, Optional
from pathlib import Path

from src.core.config import (
    YOUR_NAME, PROJECT_ROOT, VideoOptions
)
from src.core.interfaces import ILLMService, IVideoEngine, ITTSService, IVideoUploader
from src.core.base_mode import BaseMode
from src.utils.text import strip_emojis, clamp_words

BRAINROT_PLAN_FILE = PROJECT_ROOT / "brainrot_plan.json"
OUTPUT_DIR = PROJECT_ROOT / "output"

class BrainrotMode(BaseMode):
    def __init__(self, llm_service, tts_service, uploader_service, video_engine, dry_run=False, voice=None, custom_bg=None):
        super().__init__(llm_service, tts_service, uploader_service, video_engine)
        self.dry_run = dry_run
        self.voice = voice
        self.custom_bg = custom_bg

    def get_pending_topics(self) -> List[Dict[str, Any]]:
        if not BRAINROT_PLAN_FILE.exists():
            return []
        try:
            with open(BRAINROT_PLAN_FILE) as f:
                plan = json.load(f)
                return [t for t in plan.get("topics", []) if t.get("status") == "pending"]
        except Exception:
            return []

    def mark_complete(self, topic: Dict[str, Any], video_id: Optional[str]):
        if not BRAINROT_PLAN_FILE.exists(): return
        try:
            with open(BRAINROT_PLAN_FILE) as f:
                plan = json.load(f)
            for t in plan.get("topics", []):
                if t["title"] == topic["title"]:
                    t["status"] = "complete"
                    t["youtube_id"] = video_id or "DRY_RUN"
                    break
            with open(BRAINROT_PLAN_FILE, 'w') as f:
                json.dump(plan, f, indent=2)
            
            if video_id and not self.dry_run:
                from src.core.learning import log_upload
                log_upload(topic["title"], video_id, "brainrot")
        except Exception as e:
            print(f"⚠️ Error marking complete: {e}")

    def generate_script(self, topic: Dict[str, Any]) -> Dict[str, Any]:
        if self.dry_run:
            return {
                "slides": [{"text": "Dry run hook", "duration_hint": "short"}, {"text": "Dry run angle", "duration_hint": "medium"}, {"text": "AI is changing everything. Ready?", "duration_hint": "short"}, {"text": "Follow for more. 🔥", "duration_hint": "short"}],
                "full_script": "Dry run hook. Dry run angle. AI is changing everything. Follow for more.",
                "title": f"{topic['title']} DRY",
                "hashtags": "#DryRun",
            }
        print(f"📝 Scripting: '{topic['title']}'...")
        prompt = f"""You are writing a viral 30-45 second YouTube Short script about AI.
Topic: {topic['title']}
Hook: {topic['hook']}
Angle: {topic['angle']}
Rules:
- Total script 100-120 words (35-42 seconds)
- 4 slides total: hook, point 1, point 2, CTA
Format JSON: 'slides' (list of 4 with 'text', 'duration_hint'), 'full_script', 'title', 'hashtags'."""
        
        result = self.llm.generate(prompt, json_mode=True)
        if not result or not result.get("slides") or not result.get("full_script"):
            result = {
                "slides": [{"text": topic["hook"], "duration_hint": "short"}, {"text": topic["angle"], "duration_hint": "medium"}, {"text": "AI is changing everything. Ready?", "duration_hint": "short"}, {"text": "Follow for more. 🔥", "duration_hint": "short"}],
                "full_script": f"{topic['hook']} {topic['angle']} AI is changing everything. Follow for more.",
                "title": f"{topic['title']} 🤯",
                "hashtags": "#AI #Shorts #Tech #AIFacts",
            }
        if result.get("full_script"):
            result["full_script"] = clamp_words(result["full_script"], min_w=99, max_w=127)
        return result

    def generate_assets(self, content: Dict[str, Any], uid: str) -> Dict[str, List[Path]]:
        slide_dir = self.output_dir / f"brainrot_{uid}"
        slides_data = content.get("slides", [])
        
        audio_paths = []
        image_paths = []
        
        for idx, slide in enumerate(slides_data):
            text = strip_emojis(slide.get("text", ""))
            a_path = self.output_dir / f"brainrot_s{idx+1}_{uid}.mp3"
            
            if self.dry_run:
                audio_path = Path(f"dry_audio_{idx}_{uid}.wav")
                audio_path.touch()
                audio_paths.append(audio_path)
                image_path = slide_dir / f"dry_slide_{idx}.png"
                slide_dir.mkdir(exist_ok=True, parents=True)
                image_path.touch()
                image_paths.append(image_path)
            else:
                audio_paths.append(self.tts.text_to_speech(text, a_path, voice=self.voice))
                image_paths.append(Path(self.video_engine.generate_brainrot_slide(slide_dir, text, idx + 1, len(slides_data))))
            
        return {"images": image_paths, "audio": audio_paths}

    def compose(self, content: Dict[str, Any], assets: Dict[str, List[Path]], output_path: str) -> str:
        if self.dry_run:
            Path(output_path).touch()
            return output_path
            
        options = VideoOptions(
            video_type="short",
            lesson_title=content.get("title", "Brainrot"),
            custom_bg=self.custom_bg,
            fps=24,
            threads=3
        )
        return self.video_engine.compose_brainrot_video(assets["images"], assets["audio"], output_path, options)

    def upload(self, content: Dict[str, Any], video_path: str) -> Optional[str]:
        title = content.get("title", "AI Fact")[:100]
        hashtags = content.get("hashtags", "#AI #Shorts #Tech")
        desc = f"{content['full_script']}\n\n{hashtags}\n\nAI for Developers by {YOUR_NAME}"
        tags = ["AI", "Shorts", "Tech", "BrainRot", "AIFacts"]
        return self.uploader.upload(Path(video_path), title, desc, tags)

def run_brainrot_pipeline(shorts_per_run: int = 3, llm_service=None, tts_service=None, uploader_service=None, video_engine=None, dry_run=False, voice=None, topic=None):
    from rich.prompt import Prompt
    
    if not all([llm_service, tts_service, uploader_service, video_engine]):
        raise ValueError("All services (llm, tts, uploader, engine) must be provided to run_brainrot_pipeline")

    mode = BrainrotMode(
        llm_service,
        tts_service,
        uploader_service,
        video_engine,
        dry_run=dry_run,
        voice=voice,
        custom_bg=os.environ.get("CUSTOM_BG")
    )
    
    # Check for custom topic via argument or stdin (from Dashboard)
    custom_topic = topic
    if not custom_topic:
        try:
            custom_topic = Prompt.ask("Enter custom topic (or leave blank for auto)", default="")
        except EOFError:
            custom_topic = ""
    
    if custom_topic and custom_topic.strip():
        print(f"🎯 Using custom topic: {custom_topic}")
        pending = [{
            "title": custom_topic,
            "hook": f"Did you know about {custom_topic}?",
            "angle": "Explaining the most interesting part of this topic.",
            "status": "pending"
        }]
    else:
        pending = mode.get_pending_topics()
        if not pending:
            print("📋 No pending topics. Using fallback...")
            pending = [
                {"title": "Why AI Agents Are Suddenly Everywhere", "hook": "AI agents are exploding right now.", "angle": "What changed and why developers care."},
                {"title": "The Hidden Cost of Bad Prompts", "hook": "Most people are wasting AI with weak prompts.", "angle": "Better prompting changes output quality fast."},
            ]

    print(f"🚀 Brain Rot Pipeline: {len(pending)} topics available, producing {shorts_per_run}.")
    for i, topic in enumerate(pending[:shorts_per_run]):
        mode.produce_video(topic, i + 1, shorts_per_run)

    print("✅ Pipeline finished.")
