# src/modes/studio_ideas.py
# YouTube Studio Idea Generator — real YT suggestions + thumbnails + Ollama dialogue
# Auto-produces short-form video + uploads for every idea found. Zero interactive prompts
# after the first-time API key setup.

import json
import re
import time
import datetime
import concurrent.futures
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional
from tqdm import tqdm

from src.core.config import (
    OUTPUT_DIR,
    PROJECT_ROOT,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT,
    YOUR_NAME,
    VideoOptions
)
from src.core.interfaces import ILLMService, ITTSService, IVideoUploader, IVideoEngine
from src.core.base_mode import BaseMode
from src.utils.text import strip_emojis, clamp_words

LOG_FILE    = PROJECT_ROOT / "performance_log.json"
IDEAS_FILE  = PROJECT_ROOT / "youtube_studio_ideas.json"
CONFIG_FILE = PROJECT_ROOT / "config.json"


# ─────────────────────────── helpers ────────────────────────────

def load_performance_data():
    try:
        return json.loads(LOG_FILE.read_text()) if LOG_FILE.exists() else []
    except Exception:
        return []


def get_trending_context():
    return (
        "Trending: DeepSeek-V3, Qwen-2.5-Max, Agentic Workflows, "
        "local RAG, AI video generation, coding agents, GPT-5 rumours, "
        "open-source LLMs, Claude 3.5, Gemini Ultra, AI coding tools."
    )


def get_yt_api_key() -> str | None:
    """Read YouTube Data API key from config.json; prompt + save if missing."""
    try:
        cfg = json.loads(CONFIG_FILE.read_text()) if CONFIG_FILE.exists() else {}
        if cfg.get("youtube_api_key"):
            return cfg["youtube_api_key"]
    except Exception:
        cfg = {}

    print("\n  YouTube Data API key needed for real Studio suggestions.")
    print("  Get free key: https://console.cloud.google.com/apis/library/youtube.googleapis.com")
    try:
        key = input("  Paste API key (Enter to skip → Ollama-only mode): ").strip()
    except EOFError:
        key = ""
        
    if key:
        cfg["youtube_api_key"] = key
        CONFIG_FILE.write_text(json.dumps(cfg, indent=2))
        print("  Key saved to config.json")
    return key or None


# ─────────────────── YouTube Data API v3 ────────────────────────

def fetch_yt_suggestions(query: str = "AI tutorial 2025",
                          max_results: int = 5,
                          api_key: str = None) -> list:
    if not api_key:
        return []
    url = (
        "https://www.googleapis.com/youtube/v3/search"
        f"?part=snippet&q={requests.utils.quote(query)}"
        f"&type=video&order=viewCount&maxResults={max_results}&key={api_key}"
    )
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if "error" in data:
            print(f"  YT API error: {data['error'].get('message','unknown')}")
            return []
        results = []
        for item in data.get("items", []):
            snippet  = item.get("snippet", {})
            video_id = item.get("id", {}).get("videoId", "")
            thumbs   = snippet.get("thumbnails", {})
            thumb_url = (
                thumbs.get("maxres", thumbs.get("high", thumbs.get("medium", {}))).get("url", "")
            )
            results.append({
                "video_id":      video_id,
                "title":         snippet.get("title", ""),
                "description":   snippet.get("description", ""),
                "channel":       snippet.get("channelTitle", ""),
                "thumbnail_url": thumb_url,
                "yt_link":       f"https://youtube.com/watch?v={video_id}",
            })
        return results
    except Exception as e:
        print(f"  YT fetch failed: {e}")
        return []


def download_yt_thumbnail(video_data: dict) -> str | None:
    url      = video_data.get("thumbnail_url", "")
    video_id = video_data.get("video_id", "unknown")
    if not url:
        return None
    out_dir = PROJECT_ROOT / "output" / "thumbnails"
    out_dir.mkdir(exist_ok=True, parents=True)
    dest = out_dir / f"yt_{video_id}.jpg"
    if dest.exists():
        return str(dest)
    try:
        r = requests.get(url, timeout=10)
        dest.write_bytes(r.content)
        print(f"  Thumbnail: {dest.name}")
        return str(dest)
    except Exception as e:
        print(f"  Thumbnail download failed: {e}")
        return None


class StudioIdeasMode(BaseMode):
    def __init__(self, llm_service: ILLMService, tts_service: ITTSService, 
                 uploader_service: IVideoUploader, video_engine: IVideoEngine,
                 dry_run: bool = False, voice: Optional[str] = None):
        super().__init__(llm_service, tts_service, uploader_service, video_engine)
        self.dry_run = dry_run
        self.voice = voice

    def get_pending_topics(self) -> List[Dict[str, Any]]:
        # This mode generates its own topics in run_pipeline
        return []

    def mark_complete(self, topic: Dict[str, Any], video_id: Optional[str]):
        if video_id:
            from src.core.learning import log_upload
            if not self.dry_run:
                log_upload(topic["title"], video_id, "studio_idea")
            else:
                print(f"DEBUG: Dry run complete for {topic['title']}")

    def generate_script(self, topic: Dict[str, Any]) -> Dict[str, Any]:
        # If topic is a real YT video, adapt it
        if topic.get("video_id"):
            return self._generate_dialogue_from_yt(topic)
        
        # Otherwise it's just a general idea
        return topic

    def _generate_dialogue_from_yt(self, video_data: dict) -> dict:
        """Ollama generates a 60-90 second Short script from a real YT video."""
        title = video_data.get("title", "")
        desc  = video_data.get("description", "")[:600]
        prompt = f"""You are a YouTube Shorts scriptwriter for the SuperShorts channel.
A trending video exists:
TITLE: {title}
DESCRIPTION: {desc}

Write a punchy 35-45 second Short script on the same topic — punchier and more hooky.
Rules: hook first 2 seconds, plain spoken language, address viewer as "you", end with CTA.
IMPORTANT: dialogue MUST be exactly 99-127 words (35-45 seconds at 170 wpm). NO more, NO less.
Format the JSON with keys: "title", "hook", "dialogue", "thumbnail_prompt"."""
        
        try:
            result = self.llm.generate(prompt, json_mode=True)
            if not result:
                raise ValueError("LLM returned empty result")
        except Exception as e:
            print(f"  Dialogue gen failed ({e}), using fallback.")
            result = {
                "title":            title,
                "hook":             "Nobody is talking about this AI secret...",
                "dialogue":         desc or "This AI technology is changing everything. Here is what you need to know.",
                "thumbnail_prompt": "cinematic neon AI background",
            }
        # Enforce 35-45s duration (99-127 words)
        if result.get("dialogue"):
            result["dialogue"] = clamp_words(result["dialogue"], min_w=99, max_w=127)
        result["yt_thumbnail_url"] = video_data.get("thumbnail_url", "")
        result["yt_video_id"]      = video_data.get("video_id", "")
        result["yt_link"]          = video_data.get("yt_link", "")
        result["source_title"]     = title
        return result

    def generate_ideas(self, num_ideas: int = 5) -> list:
        """Pure LLM idea generation (no YouTube API needed)."""
        data     = load_performance_data()
        trending = get_trending_context()
        past_data = (
            "\n".join(f"- {e.get('title','Untitled')} ({e.get('mode','?')})" for e in data[-10:])
            if data else "No past data. Generate fresh ideas."
        )
        prompt = f"""You are YouTube Studio's AI Idea Generator.
TRENDING: {trending}
PAST PERFORMANCE: {past_data}

Generate {num_ideas} YouTube Short ideas. Each object must have:
- title (clickbait + searchable, include emoji)
- hook (first 2-second sentence)
- dialogue (35-45 second spoken script — exactly 99-127 words, NO more, NO less)
- thumbnail_prompt (visual description)

Format as a JSON array of {num_ideas} objects."""

        print("  Asking LLM for ideas...")
        try:
            ideas = self.llm.generate(prompt, json_mode=True)
            if not ideas:
                raise ValueError("LLM returned empty result")
            if not isinstance(ideas, list):
                ideas = ideas.get("ideas", [ideas]) if isinstance(ideas, dict) else []
            # Enforce 35-45s duration on every idea
            for idea in ideas:
                if isinstance(idea, dict) and idea.get("dialogue"):
                    idea["dialogue"] = clamp_words(idea["dialogue"], min_w=99, max_w=127)
        except Exception as e:
            print(f"  LLM failed ({e}), using fallback ideas.")
            ideas = [
                {
                    "title":            f"🤖 AI Secret #{i+1} Nobody Talks About",
                    "hook":             "Nobody is talking about this...",
                    "dialogue":         (
                        "Here is an AI trick that will change how you work forever. "
                        "Most developers spend hours on tasks that AI can handle in seconds. "
                        "The key is knowing which tool to use and how to prompt it correctly. "
                        "This single technique has saved professionals countless hours every week. "
                        "Start using this today and you will never go back to the old way. "
                        "Subscribe for more AI productivity tips."
                    ),
                    "thumbnail_prompt": "neon circuits dark background",
                }
                for i in range(num_ideas)
            ]
        IDEAS_FILE.write_text(json.dumps(ideas, indent=2))
        return ideas

    def generate_assets(self, content: Dict[str, Any], uid: str) -> Dict[str, List[Path]]:
        title    = strip_emojis(content.get("title", "New Idea"))[:100]
        dialogue = strip_emojis(content.get("dialogue", content.get("script", "")))
        
        # TTS
        audio_path = self.output_dir / f"{uid}_audio.mp3"
        if self.dry_run:
            audio_path.touch()
        else:
            audio_path = self.tts.text_to_speech(dialogue, audio_path, voice=self.voice)

        # Slide visual (dark card with title + hook)
        slide_content = {
            "title":   title,
            "content": content.get("hook", dialogue[:200]),
        }
        slide_dir  = self.output_dir / f"{uid}_slides"
        if self.dry_run:
            slide_dir.mkdir(exist_ok=True, parents=True)
            slide_path = slide_dir / "slide_1.png"
            slide_path.touch()
        else:
            slide_path = self.video_engine.generate_visuals(slide_dir, "short", slide_content,
                                          slide_number=1, total_slides=1)
        
        return {"images": [Path(slide_path)], "audio": [audio_path], "script": [dialogue]}

    def compose(self, content: Dict[str, Any], assets: Dict[str, List[Path]], output_path: str) -> str:
        if self.dry_run:
            Path(output_path).touch()
            return output_path
        title = strip_emojis(content.get("title", "New Idea"))[:100]
        dialogue = assets["script"][0]
        self.video_engine.compose_video(assets["images"], assets["audio"], output_path, 
                                        VideoOptions(video_type="short", lesson_title=title, script=dialogue))
        return output_path

    def upload(self, content: Dict[str, Any], video_path: str) -> Optional[str]:
        title = strip_emojis(content.get("title", "New Idea"))[:100]
        dialogue = content.get("dialogue", "")
        hashtags = "#AI #Shorts #Tech #Viral #AIFacts"
        desc     = f"{dialogue[:500]}\n\n{hashtags}\n\nProduced by SuperShorts"
        short_title = f"{title[:80]} #Shorts"
        
        if self.dry_run:
            # We still call the uploader so tests can track it
            return self.uploader.upload(Path(video_path), short_title, desc, ["AI", "Shorts", "Viral", "Tech", "AIFacts"])
            
        return self.uploader.upload(Path(video_path), short_title, desc, ["AI", "Shorts", "Viral", "Tech", "AIFacts"])

    def run_studio_ideas_pipeline(self):
        print("\n  YouTube Studio Idea Generator — Auto-Pilot Mode\n")
        
        api_key   = get_yt_api_key()
        ideas     = []

        if api_key:
            print("\n  Searching YouTube for trending AI content...")
            yt_videos = fetch_yt_suggestions("AI productivity tutorial 2025",
                                              max_results=5, api_key=api_key)
            if yt_videos:
                print(f"  Found {len(yt_videos)} trending videos — generating adapted scripts...")
                for vid in tqdm(yt_videos, desc="  Adapting", unit="video"):
                    local_thumb = download_yt_thumbnail(vid)
                    idea        = self._generate_dialogue_from_yt(vid)
                    idea["local_thumbnail_path"] = local_thumb
                    ideas.append(idea)
            else:
                print("  No YT results — falling back to LLM ideas.")

        if not ideas:
            ideas = self.generate_ideas(num_ideas=5)

        if not ideas:
            print("  No ideas generated.")
            return

        IDEAS_FILE.write_text(json.dumps(ideas, indent=2))
        print(f"\n  {len(ideas)} ideas ready — producing + uploading all...\n")

        results = []
        for i, idea in enumerate(ideas):
            try:
                uid = f"idea_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{i}"
                assets = self.generate_assets(idea, uid)
                video_path = self.output_dir / f"{uid}.mp4"
                self.compose(idea, assets, str(video_path))
                video_id = self.upload(idea, str(video_path))
                
                if video_id:
                    self.mark_complete(idea, video_id)
                    results.append({"status": "complete", "title": idea.get("title"), "youtube_id": video_id})
                    if i < len(ideas) - 1:
                        print(f"\n  Waiting 30 s before next upload...")
                        time.sleep(30)
                else:
                    results.append({"status": "upload_failed", "title": idea.get("title"), "path": str(video_path)})
            except Exception as e:
                import traceback
                print(f"  Error on idea {i+1}: {e}")
                traceback.print_exc()
                results.append({"status": "error", "error": str(e)})

        done   = sum(1 for r in results if r.get("status") == "complete")
        failed = len(results) - done
        print(f"\n  Studio Ideas done — {done}/{len(ideas)} uploaded"
              + (f", {failed} failed/local" if failed else "") + ".")

def start_idea_generator(llm_service=None, tts_service=None, uploader_service=None, video_engine=None, dry_run=False, voice=None):
    mode = StudioIdeasMode(llm_service, tts_service, uploader_service, video_engine, dry_run=dry_run, voice=voice)
    mode.run_studio_ideas_pipeline()
