# src/rotgen.py — RotGen Character Mode
# Split-screen brain rot: animated AI character (top) + gameplay (middle) + subtitles (bottom)
# Layout: 1080×1920  │  Character panel 0–768  │  Gameplay 768–1760  │  Subtitle bar 1760–1920

import json
import os
import random
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.core.base_mode import BaseMode
from src.core.config import (
    YOUR_NAME, PROJECT_ROOT, VideoOptions
)
from src.core.interfaces import ILLMService, IVideoEngine, ITTSService, IVideoUploader
from src.utils.text import strip_emojis, clamp_words

# ─────────────────────────── constants ──────────────────────────────────────

ROTGEN_PLAN_FILE   = PROJECT_ROOT / "rotgen_plan.json"
OUTPUT_DIR         = PROJECT_ROOT / "output"

VIRAL_TOPICS = [
    "Why AI Will Replace 90% of Jobs by 2030",
    "This FREE AI Codes Better Than ChatGPT",
    "Nobody Is Talking About This AI Secret",
    "How To Build Your Own AI Agent in 5 Minutes",
    "The AI Tool That Automates Everything",
    "AI Just Beat Every Human At This Task",
    "The Dark Side of AI Nobody Shows You",
    "This AI Model Runs Entirely On Your Phone",
    "Why Big Tech Is Scared Of Open-Source AI",
    "How DeepSeek Destroyed a $600B Company Overnight",
]

# ─────────────────────────── helpers ────────────────────────────────────────

def load_rotgen_plan() -> dict:
    if not ROTGEN_PLAN_FILE.exists():
        return {"videos": []}
    try:
        return json.loads(ROTGEN_PLAN_FILE.read_text())
    except Exception:
        return {"videos": []}


def save_rotgen_plan(plan: dict) -> None:
    ROTGEN_PLAN_FILE.write_text(json.dumps(plan, indent=2))


# ─────────────────────────── script gen ─────────────────────────────────────

# TTS runs at 170 wpm → 35–45 s = 99–127 words target
SCRIPT_MIN_WORDS = 99
SCRIPT_MAX_WORDS = 127


ROTGEN_PAD = (
    " AI is reshaping every single industry on the planet right now at a speed nobody predicted."
    " Companies are being built and destroyed overnight because of this technology."
    " The workers who adapt will thrive. Those who ignore it will fall behind."
    " This is not science fiction. This is happening today, this week, this year."
    " Machine learning models are already writing code, generating art, and diagnosing disease."
    " The next five years will change everything you know about work and business."
    " Early adopters always win. The window to get ahead is closing fast."
    " Stay informed, stay curious, and follow for more AI facts every single day."
)

def _enforce_word_count(text: str) -> str:
    """Trim script to SCRIPT_MAX_WORDS at a sentence boundary. Pad if too short."""
    return clamp_words(text, min_w=SCRIPT_MIN_WORDS, max_w=SCRIPT_MAX_WORDS, pad_text=ROTGEN_PAD)


def generate_rotgen_script(llm_service: ILLMService, topic: str | None = None) -> dict:
    if not topic:
        topic = random.choice(VIRAL_TOPICS)
    print(f"  Topic: {topic}")
    prompt = f"""
You are scripting a 31-40 second YouTube Short for a character called ByteBot.
ByteBot is an enthusiastic AI educator who talks directly to camera.
Topic: {topic}

Rules:
- EXACTLY 90-110 words (this is critical — TTS must hit 31-40 seconds)
- First-person, conversational, energetic
- No emojis (TTS will read them aloud)
- Start with a shocking hook sentence
- End with exactly: "Follow for more AI facts"

Format the JSON with keys: "script", "title", "hashtags"."""
    try:
        result = llm_service.generate(prompt, json_mode=True)
        if result.get("script"):
            result["script"] = _enforce_word_count(result["script"])
            return result
    except Exception as e:
        print(f"  LLM failed ({e}), using fallback script.")
    fallback = (
        f"{topic}. Most people have absolutely no idea this is already happening right now. "
        "AI systems are reshaping every single industry on the planet at a speed nobody predicted. "
        "Companies are being built and destroyed overnight because of this technology. "
        "The workers who adapt will thrive. Those who ignore it will fall behind. "
        "This is not science fiction. This is happening today. "
        "Follow for more AI facts."
    )
    return {
        "script":   _enforce_word_count(fallback),
        "title":    f"{topic[:80]} #Shorts",
        "hashtags": "#AI #Shorts #Tech #AIFacts #ByteBot",
    }


class RotgenMode(BaseMode):
    def __init__(self, llm_service, tts_service, uploader_service, video_engine, dry_run=False, voice=None, custom_bg=None, custom_char=None):
        super().__init__(llm_service, tts_service, uploader_service, video_engine)
        self.dry_run = dry_run
        self.voice = voice
        self.custom_bg = custom_bg
        self.custom_char = custom_char

    def get_pending_topics(self) -> List[Dict[str, Any]]:
        plan = load_rotgen_plan()
        done = {v["topic"] for v in plan.get("videos", []) if v.get("status") == "complete"}
        available = [t for t in VIRAL_TOPICS if t not in done] or list(VIRAL_TOPICS)
        return [{"title": t, "topic": t} for t in available]

    def mark_complete(self, topic: Dict[str, Any], video_id: Optional[str]):
        if self.dry_run: return
        plan = load_rotgen_plan()
        entry = topic.copy()
        entry["youtube_id"] = video_id
        entry["status"] = "complete" if video_id else "upload_failed"
        plan["videos"].append(entry)
        save_rotgen_plan(plan)
        if video_id:
            from src.core.learning import log_upload
            log_upload(topic["title"], video_id, "rotgen")

    def generate_script(self, topic: Dict[str, Any]) -> Dict[str, Any]:
        return generate_rotgen_script(self.llm, topic["topic"])

    def generate_assets(self, content: Dict[str, Any], uid: str) -> Dict[str, List[Path]]:
        script_text = strip_emojis(content.get("script", ""))
        audio_path = self.output_dir / f"rotgen_vo_{uid}.mp3"
        
        if self.dry_run:
            audio_path = Path(f"dry_rotgen_{uid}.wav")
            audio_path.touch()
        else:
            audio_path = self.tts.text_to_speech(script_text, audio_path, voice=self.voice)
            
        return {"audio": [audio_path]}

    def compose(self, content: Dict[str, Any], assets: Dict[str, List[Path]], output_path: str) -> str:
        if self.dry_run:
            Path(output_path).touch()
            return output_path
            
        options = VideoOptions(
            video_type="short",
            lesson_title=content.get("title", "Rotgen"),
            custom_bg=self.custom_bg,
            script=content.get("script"),
            fps=24,
            threads=3
        )
        
        custom_char_path = Path(self.custom_char) if self.custom_char else None
        return self.video_engine.compose_rotgen_video(assets["audio"][0], output_path, options, custom_char_path=custom_char_path)

    def upload(self, content: Dict[str, Any], video_path: str) -> Optional[str]:
        title = f"{content.get('title', 'AI Fact')[:80]} #Shorts"
        hashtags = content.get("hashtags", "#AI #Shorts #ByteBot")
        desc = f"{content['script']}\n\n{hashtags}\n\nAI for Developers by {YOUR_NAME}"
        return self.uploader.upload(Path(video_path), title, desc, ["AI","Shorts","BrainRot","ByteBot","AIFacts","Tech"])


def run_rotgen_pipeline(shorts_per_run: int = 3, llm_service=None, tts_service=None, uploader_service=None, video_engine=None, dry_run=False, voice=None, topic=None):
    from rich.prompt import Prompt

    if not all([llm_service, tts_service, uploader_service, video_engine]):
        raise ValueError("All services (llm, tts, uploader, engine) must be provided to run_rotgen_pipeline")

    mode = RotgenMode(
        llm_service,
        tts_service,
        uploader_service,
        video_engine,
        dry_run=dry_run,
        voice=voice,
        custom_bg=os.environ.get("CUSTOM_BG"),
        custom_char=os.environ.get("CUSTOM_CHAR")
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
        pending = [{"title": custom_topic, "topic": custom_topic}]
    else:
        pending = mode.get_pending_topics()

    print(f"🚀 RotGen Pipeline: {len(pending)} topics available, producing {shorts_per_run}.")
    
    for i, topic in enumerate(pending[:shorts_per_run]):
        mode.produce_video(topic, i + 1, shorts_per_run)
