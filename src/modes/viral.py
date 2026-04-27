import json
import random
import datetime
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from tqdm import tqdm

from src.core.config import (
    CONTENT_PACKAGE_TOPICS, YOUR_NAME, OUTPUT_DIR, VIRAL_GAMEPLAY_PATH, VideoOptions
)
from src.core.interfaces import IVideoEngine, ILLMService, ITTSService, IVideoUploader
from src.utils.text import strip_emojis, enforce_script_length, clamp_words
from src.core.base_mode import BaseMode

class ViralGameplayMode(BaseMode):
    """Educational videos with FORCED viral gameplay backgrounds."""
    def __init__(self, llm_service, tts_service, uploader_service, video_engine, dry_run=False, voice=None):
        super().__init__(llm_service, tts_service, uploader_service, video_engine)
        self.dry_run = dry_run
        self.voice = voice

    def get_pending_topics(self) -> List[Dict[str, Any]]:
        topic = self.get_topic_input("VIRAL_TOPIC", "Enter topic for viral gameplay video: ", "Future of AI Agents")
        return [{"title": topic}]

    def mark_complete(self, topic: Dict[str, Any], video_id: Optional[str]):
        if video_id and not self.dry_run:
            from src.core.learning import log_upload
            log_upload(topic["title"], video_id, "viral_gameplay")
        print(f"✅ Viral gameplay video done: {topic['title']}")

    def generate_script(self, topic: Dict[str, Any]) -> Dict[str, Any]:
        from src.generator import generate_lesson_content
        content = generate_lesson_content(topic["title"], llm_service=self.llm)
        content["title"] = topic["title"]
        return content

    def generate_assets(self, content: Dict[str, Any], uid: str) -> Dict[str, List[Path]]:
        slides_data = content.get('long_form_slides', [])[:5]
        if not slides_data:
            raise ValueError("No content generated.")

        slide_audio_paths = []
        for i, slide in enumerate(tqdm(slides_data, desc="  TTS (viral)")):
            txt = f"{slide.get('title', '')}. {slide.get('content', '')}"
            audio_path = self.output_dir / f"{uid}_audio_{i}.mp3"
            if self.dry_run:
                audio_path.touch()
            else:
                audio_path = self.tts.text_to_speech(txt, audio_path, voice=self.voice)
            slide_audio_paths.append(audio_path)

        slide_dir = self.output_dir / f"{uid}_slides"
        slide_paths = []
        for i, slide in enumerate(tqdm(slides_data, desc="  Slides (viral)")):
            if self.dry_run:
                slide_dir.mkdir(exist_ok=True, parents=True)
                path = slide_dir / f"slide_{i+1}.png"
                path.touch()
            else:
                path = self.video_engine.generate_visuals(slide_dir, 'short', slide, slide_number=i+1, total_slides=len(slides_data))
            slide_paths.append(Path(path))

        viral_script = ' '.join(f"{s.get('title', '')}. {s.get('content', '')}" for s in slides_data)
        viral_script = clamp_words(viral_script, min_w=99, max_w=127)
        
        return {
            "images": slide_paths,
            "audio": slide_audio_paths,
            "script": [viral_script]
        }

    def compose(self, content: Dict[str, Any], assets: Dict[str, List[Path]], output_path: str) -> str:
        if self.dry_run:
            Path(output_path).touch()
            return output_path
        
        topic = content.get("title", "Viral")
        self.video_engine.compose_video(
            assets["images"], 
            assets["audio"], 
            output_path, 
            VideoOptions(video_type='short', lesson_title=topic, force_viral_bg=True, script=assets["script"][0])
        )
        return output_path

    def upload(self, content: Dict[str, Any], video_path: str) -> Optional[str]:
        if self.dry_run:
            return "DRY_RUN_ID"
        
        topic = content.get("title", "Viral")
        thumb_path = Path(self.video_engine.generate_visuals(self.output_dir, 'short', is_thumbnail=True, thumbnail_title=topic))
        hashtags = content.get("hashtags", "#AI #Shorts #Viral")
        desc = f"{topic}\n\n{hashtags}\n\nProduced by SuperShorts"
        return self.uploader.upload(Path(video_path), f"{topic[:80]} #Shorts", desc, ["AI", "Shorts", "Viral"], thumb_path)

class ContentPackageMode(BaseMode):
    """Expert YouTube Content Strategist — auto-picks topic, generates script + video + upload."""
    def __init__(self, llm_service, tts_service, uploader_service, video_engine, dry_run=False, voice=None):
        super().__init__(llm_service, tts_service, uploader_service, video_engine)
        self.dry_run = dry_run
        self.voice = voice

    def get_pending_topics(self) -> List[Dict[str, Any]]:
        raw = os.environ.get("PACKAGE_TOPIC", "")
        if not raw:
            try:
                raw = input("  Seed category (or Enter to auto-pick): ").strip()
            except EOFError:
                raw = ""
        topic = raw if raw else random.choice(CONTENT_PACKAGE_TOPICS)
        if not raw:
            print(f"  Auto-picked: {topic}")
        return [{"title": topic}]

    def mark_complete(self, topic: Dict[str, Any], video_id: Optional[str]):
        title = topic.get("generated_title", topic["title"])
        if video_id and not self.dry_run:
            from src.core.learning import log_upload
            log_upload(title, video_id, "content_package")

    def generate_script(self, topic: Dict[str, Any]) -> Dict[str, Any]:
        if self.dry_run:
            topic["generated_title"] = f"{topic['title']} DRY RUN"
            return {
                "selected_title": topic["generated_title"],
                "full_script": "This is a dry run script. It should be long enough but it is just a test.",
                "pexels_keywords": "test dryrun",
                "description": "Dry run description",
                "hashtags": "#DryRun"
            }
        
        prompt = f"""You are an expert YouTube scriptwriter and content strategist.
Create a complete production package for a 5-minute YouTube video.

Topic: {topic['title']}

CRITICAL SCRIPT REQUIREMENTS:
- The "full_script" field MUST be 500+ words of flowing spoken prose
- Write in paragraphs, not bullet points
- No emojis, no markdown
- End with exactly: "Subscribe for more"

Return ONLY valid JSON:
{{
  "selected_title": "Best SEO title under 70 chars",
  "full_script": "MINIMUM 500 WORDS of flowing narration here...",
  "pexels_keywords": "keyword1 keyword2",
  "description": "SEO description",
  "hashtags": "#Tag1 #Tag2"
}}"""
        print("  Calling LLM for content package...")
        result = self.llm.generate(prompt, json_mode=True)
        
        if not result or not result.get("full_script"):
            print("  ⚠️  LLM returned empty — using fallback script.")
            result = {
                "selected_title": topic['title'][:70],
                "full_script": f"{topic['title']}. The science is clear. Subscribe for more.",
                "pexels_keywords": "productivity focus",
                "description": f"{topic['title']}",
                "hashtags": "#Productivity #Science",
            }
        
        topic["generated_title"] = result.get("selected_title", topic["title"])
        return result

    def generate_assets(self, content: Dict[str, Any], uid: str) -> Dict[str, List[Path]]:
        title = strip_emojis(content.get("selected_title", "Package")[:80])
        script = strip_emojis(content.get("full_script", ""))
        script = enforce_script_length(script)
        
        audio_path = self.output_dir / f"{uid}_audio.mp3"
        if self.dry_run:
            audio_path.touch()
        else:
            audio_path = self.tts.text_to_speech(script, audio_path, voice=self.voice)

        slide_dir = self.output_dir / f"{uid}_slides"
        if self.dry_run:
            slide_dir.mkdir(exist_ok=True, parents=True)
            slide_path = slide_dir / "slide_1.png"
            slide_path.touch()
        else:
            slide_path = self.video_engine.generate_visuals(
                slide_dir, "long",
                slide_content={"title": title, "content": script[:600]},
                slide_number=1, total_slides=1,
            )
        
        return {
            "images": [Path(slide_path)],
            "audio": [Path(audio_path)],
            "script": [script],
            "title": [title]
        }

    def compose(self, content: Dict[str, Any], assets: Dict[str, List[Path]], output_path: str) -> str:
        if self.dry_run:
            Path(output_path).touch()
            return output_path
        
        title = assets["title"][0]
        script = assets["script"][0]
        self.video_engine.compose_video(
            assets["images"], 
            assets["audio"], 
            output_path, 
            VideoOptions(video_type="long", lesson_title=title, script=script)
        )
        return output_path

    def upload(self, content: Dict[str, Any], video_path: str) -> Optional[str]:
        if self.dry_run:
            return "DRY_RUN_ID"
        
        title = strip_emojis(content.get("selected_title", "Package")[:80])
        desc = content.get("description", "") + "\n\n" + content.get("hashtags", "")
        pexels_kw = content.get("pexels_keywords", "technology abstract")
        tags = ",".join(dict.fromkeys((pexels_kw + ",YouTube,education").split(",")[:10]))
        
        print(f"  Uploading → {title[:60]}...")
        return self.uploader.upload(Path(video_path), title, desc, tags.split(","))

def generate_youtube_content_package(llm_service=None, tts_service=None, uploader_service=None, video_engine=None, dry_run=False, voice=None) -> None:
    """Expert YouTube Content Strategist — auto-picks topic, generates script + video + upload."""
    if not all([llm_service, tts_service, uploader_service, video_engine]):
        raise ValueError("All services (llm, tts, uploader, engine) must be provided to generate_youtube_content_package")

    print("\n  📦 YouTube Content Strategist Activated\n")
    mode = ContentPackageMode(llm_service, tts_service, uploader_service, video_engine, dry_run=dry_run, voice=voice)
    mode.run_pipeline(max_videos=1)

def start_viral_gameplay_mode(llm_service=None, tts_service=None, uploader_service=None, video_engine=None, dry_run=False, voice=None):
    """Educational videos with FORCED viral gameplay backgrounds."""
    if not all([llm_service, tts_service, uploader_service, video_engine]):
        raise ValueError("All services (llm, tts, uploader, engine) must be provided to start_viral_gameplay_mode")

    clips = list(VIRAL_GAMEPLAY_PATH.glob("*.mp4"))
    if not clips:
        print(f"\n⚠️ No gameplay clips found in {VIRAL_GAMEPLAY_PATH}/")

    mode = ViralGameplayMode(llm_service, tts_service, uploader_service, video_engine, dry_run=dry_run, voice=voice)
    mode.run_pipeline(max_videos=1)
