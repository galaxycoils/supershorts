"""src/modes/brainrot.py - Brain Rot / High-Engagement Viral Shorts Generator"""
import gc
import json
import random
import datetime
from functools import lru_cache
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from moviepy.editor import (
    AudioFileClip, ImageClip, VideoFileClip,
    CompositeVideoClip, CompositeAudioClip,
    concatenate_videoclips, vfx
)
from tqdm import tqdm

from src.core.config import (
    FONT_FILE, ASSETS_PATH, YOUR_NAME, BACKGROUNDS_PATH,
    GAMEPLAY_PATH, BACKGROUND_MUSIC_PATH, PEXELS_CACHE_DIR, PROJECT_ROOT,
    OLLAMA_MODEL, OLLAMA_TIMEOUT, VideoOptions
)
from src.core.interfaces import ILLMService, ITTSService, IVideoUploader
from src.core.base_mode import BaseMode
from src.infrastructure.llm import OllamaLLMService, ollama_generate
from src.infrastructure.tts import StandardTTSService, text_to_speech
from src.infrastructure.browser_uploader import YouTubeBrowserUploader
from src.infrastructure.video import get_local_gameplay, get_local_viral_gameplay, get_relevant_pexels_video, get_local_background
from src.engine.video_engine import auto_scale_text, draw_wrapped_text
from src.utils.text import strip_emojis, clamp_words
from src.utils.json import safe_json_parse
from src.utils.cleanup import safe_close

BRAINROT_PLAN_FILE = PROJECT_ROOT / "brainrot_plan.json"
OUTPUT_DIR = PROJECT_ROOT / "output"

BRAINROT_PALETTES = [
    {"bg": (20, 20, 20),    "text": "white",   "accent": (255, 30, 80),   "bar": (255, 30, 80)},
    {"bg": (10, 10, 40),    "text": "white",   "accent": (0, 200, 255),   "bar": (0, 180, 220)},
    {"bg": (30, 0, 50),     "text": "white",   "accent": (180, 0, 255),   "bar": (140, 0, 200)},
    {"bg": (40, 20, 0),     "text": "white",   "accent": (255, 150, 0),   "bar": (200, 100, 0)},
    {"bg": (0, 35, 20),     "text": "white",   "accent": (0, 220, 100),   "bar": (0, 180, 80)},
]

@lru_cache(maxsize=4)
def get_gradient_overlay(width, height, palette_bg):
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for y in range(height):
        alpha = int(200 * (y / height)) 
        draw.line([(0, y), (width, y)], fill=(palette_bg[0], palette_bg[1], palette_bg[2], alpha))
    return overlay

def render_brainrot_slide(output_dir, text, slide_num, total_slides, palette=None):
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    width, height = 1080, 1920
    if not palette: palette = random.choice(BRAINROT_PALETTES)
    
    img = Image.new('RGB', (width, height), palette["bg"])
    draw = ImageDraw.Draw(img)
    
    # 1. Background image (blurred)
    try:
        bg_files = list(BACKGROUNDS_PATH.glob("*.jpg")) + list(BACKGROUNDS_PATH.glob("*.png"))
        if bg_files:
            bg = Image.open(random.choice(bg_files)).convert('RGB')
            bg = bg.resize((width, height), Image.Resampling.LANCZOS)
            bg = bg.filter(ImageFilter.GaussianBlur(radius=15))
            img.paste(bg, (0, 0))
    except: pass

    # 2. Gradient overlay
    overlay = get_gradient_overlay(width, height, palette["bg"])
    img.paste(overlay, (0, 0), overlay)

    # 3. Text rendering
    try:
        font_main = ImageFont.truetype(str(FONT_FILE), 120)
        font_sub  = ImageFont.truetype(str(FONT_FILE), 60)
    except:
        font_main = font_sub = ImageFont.load_default()

    # Progress bar at top
    bar_w = int((slide_num / total_slides) * (width - 100))
    draw.rectangle([50, 50, 50 + bar_w, 70], fill=palette["bar"])
    
    # Main text centered
    text_box = (100, height//3, width-100, 2*height//3)
    auto_scale_text(draw, text.upper(), str(FONT_FILE), 130, text_box, fill=palette["text"])

    # Branding
    draw.text((width//2, height - 150), f"@{YOUR_NAME.upper()}", fill=palette["accent"], font=font_sub, anchor="mm")

    path = output_dir / f"slide_{slide_num:02d}.png"
    img.convert("RGB").save(path)
    return path

def create_brainrot_video(slide_images, audio_paths, output_path, title, script=None):
    if len(slide_images) != len(audio_paths):
        raise ValueError(f"Slide/audio count mismatch: {len(slide_images)} slides vs {len(audio_paths)} audio")
    clips = []
    audio_clips_to_close = []
    final = None
    bg_clip = None
    bg_music = None

    try:
        for img_p, aud_p in zip(slide_images, audio_paths):
            audio = AudioFileClip(str(aud_p))
            audio_clips_to_close.append(audio)
            
            img_clip = ImageClip(str(img_p)).set_duration(audio.duration).set_audio(audio)
            img_clip = img_clip.fadein(0.3).fadeout(0.3)
            clips.append(img_clip)

        final = concatenate_videoclips(clips, method="compose")
        total_duration = final.duration

        # Layered Background (Gameplay)
        gameplay = get_local_viral_gameplay()
        if gameplay and Path(gameplay).exists():
            bg_clip = VideoFileClip(gameplay).subclip(0, total_duration).resize(height=1920)
            if bg_clip.w > 1080:
                bg_clip = bg_clip.crop(x_center=bg_clip.w/2, width=1080)
            
            # Subtitles only for gameplay-heavy parts
            final = CompositeVideoClip([bg_clip.volumex(0), final.set_position("center").set_opacity(0.85)])
        
        # Background Music
        if BACKGROUND_MUSIC_PATH.exists():
            bg_music = AudioFileClip(str(BACKGROUND_MUSIC_PATH)).volumex(0.15).set_duration(total_duration)
            if final.audio is not None:
                composite_audio = CompositeAudioClip([final.audio.volumex(1.2), bg_music])
                final = final.set_audio(composite_audio)
            else:
                final = final.set_audio(bg_music)

        temp_audio = str(output_path).replace('.mp4', 'TEMP_MPY_wvf_snd.mp4')
        final.write_videofile(
            str(output_path),
            fps=24,
            codec="libx264",
            audio_codec="aac",
            threads=3,
            preset="ultrafast",
            logger='bar',
            temp_audiofile=temp_audio,
        )
    finally:
        safe_close(audio_clips_to_close, final, bg_clip, bg_music)

class BrainrotMode(BaseMode):
    def __init__(self, llm_service=None, tts_service=None, uploader_service=None, dry_run=False, voice=None):
        super().__init__(llm_service, tts_service, uploader_service)
        self.dry_run = dry_run
        self.voice = voice

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
        if self.dry_run:
            print(f"DEBUG: Dry run complete for {topic['title']}")
            return
        if not BRAINROT_PLAN_FILE.exists(): return
        try:
            with open(BRAINROT_PLAN_FILE) as f:
                plan = json.load(f)
            for t in plan.get("topics", []):
                if t["title"] == topic["title"]:
                    t["status"] = "complete"
                    t["youtube_id"] = video_id or "UPLOAD_ATTEMPTED"
                    break
            with open(BRAINROT_PLAN_FILE, 'w') as f:
                json.dump(plan, f, indent=2)
            
            if video_id:
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
        if not result.get("slides") or not result.get("full_script"):
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
        palette = random.choice(BRAINROT_PALETTES)
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
                image_paths.append(render_brainrot_slide(slide_dir, text, idx + 1, len(slides_data), palette=palette))
            
        return {"images": image_paths, "audio": audio_paths}

    def compose(self, content: Dict[str, Any], assets: Dict[str, List[Path]], output_path: str) -> str:
        if self.dry_run:
            Path(output_path).touch()
            return output_path
        create_brainrot_video(assets["images"], assets["audio"], output_path, content["title"], script=content["full_script"])
        return output_path

    def upload(self, content: Dict[str, Any], video_path: str) -> Optional[str]:
        title = content.get("title", "AI Fact")[:100]
        hashtags = content.get("hashtags", "#AI #Shorts #Tech")
        desc = f"{content['full_script']}\n\n{hashtags}\n\nAI for Developers by {YOUR_NAME}"
        tags = ["AI", "Shorts", "Tech", "BrainRot", "AIFacts"]
        return self.uploader.upload(Path(video_path), title, desc, tags)

def generate_brainrot_topics(count: int = 10, previous_topics: Optional[List[str]] = None, llm_service: Optional[ILLMService] = None) -> List[dict]:
    """Bridge for backward compatibility."""
    llm = llm_service or OllamaLLMService(generate_fn=ollama_generate)
    print("🧠 Generating brain rot topics...")
    history = ""
    if previous_topics:
        formatted = "\n".join(f"- {t}" for t in previous_topics)
        history = f"\nAlready created:\n{formatted}\n\nCreate NEW topics, don't repeat.\n"
    prompt = f"You are a viral content strategist. Generate EXACTLY {count} topic ideas. Format JSON: 'topics' (list of 'title', 'hook', 'angle')."
    result = llm.generate(prompt, json_mode=True)
    topics = result.get("topics", [])
    if topics:
        return topics[:count] if count < len(topics) else topics
    if result:
        return []

    fallback_topics = [
        {"title": "Why AI Agents Are Suddenly Everywhere", "hook": "AI agents are exploding right now.", "angle": "What changed and why developers care."},
        {"title": "The Hidden Cost of Bad Prompts", "hook": "Most people are wasting AI with weak prompts.", "angle": "Better prompting changes output quality fast."},
        {"title": "Local LLMs Are Better Than You Think", "hook": "You do not need the cloud for everything.", "angle": "Why local models are becoming practical."},
        {"title": "This AI Workflow Saves Hours", "hook": "One workflow can save your whole week.", "angle": "Automating repeated development tasks."},
        {"title": "Why Developers Need AI Systems Thinking", "hook": "Using AI well is now a systems problem.", "angle": "The shift from toy prompts to real pipelines."},
    ]
    return fallback_topics[:count]

def generate_brainrot_script(topic: dict, llm_service: Optional[ILLMService] = None) -> dict:
    """Bridge for backward compatibility."""
    llm = llm_service or OllamaLLMService(generate_fn=ollama_generate)
    mode = BrainrotMode(llm_service=llm)
    return mode.generate_script(topic)

def run_brainrot_pipeline(shorts_per_run: int = 3, llm_service=None, tts_service=None, uploader_service=None, dry_run=False, voice=None):
    mode = BrainrotMode(
        llm_service or OllamaLLMService(generate_fn=ollama_generate),
        tts_service,
        uploader_service,
        dry_run=dry_run,
        voice=voice
    )
    pending = mode.get_pending_topics()

    if not pending:
        print("📋 No pending topics. Generating new batch...")
        new_topics = generate_brainrot_topics(llm_service=mode.llm)
        plan = {"topics": []}
        for t in new_topics:
            t["status"] = "pending"
            plan["topics"].append(t)
        with open(BRAINROT_PLAN_FILE, 'w') as f:
            json.dump(plan, f, indent=2)
        pending = new_topics

    print(f"🚀 Brain Rot Pipeline: {len(pending)} topics available, producing {shorts_per_run}.")
    for i, topic in enumerate(pending[:shorts_per_run]):
        mode.produce_video(topic, i + 1, shorts_per_run)

    print("✅ Pipeline finished.")
