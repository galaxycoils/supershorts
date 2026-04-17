# src/generator.py - FULLY UPDATED FOR NEW FEATURES
import os
import re
import json
import random
import requests
import numpy as np
from io import BytesIO
import ollama
from PIL import Image, ImageDraw, ImageFont, ImageFilter
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

from moviepy.editor import AudioFileClip, ImageClip, VideoFileClip, CompositeVideoClip, CompositeAudioClip, concatenate_videoclips, vfx
from moviepy.config import change_settings
from pathlib import Path
from pydub import AudioSegment
from tqdm import tqdm
import pyttsx3
import time
import datetime

# --- Configuration ---
ASSETS_PATH = Path("assets")
FONT_FILE = ASSETS_PATH / "fonts/arial.ttf"
BACKGROUND_MUSIC_PATH = ASSETS_PATH / "music/bg_music.mp3"
BACKGROUNDS_PATH = ASSETS_PATH / "backgrounds"
GAMEPLAY_PATH = ASSETS_PATH / "gameplay"
VIRAL_GAMEPLAY_PATH = ASSETS_PATH / "viral_gameplay"   # ← NEW FOLDER: Subway Surfers etc.
FALLBACK_THUMBNAIL_FONT = ImageFont.load_default()
YOUR_NAME = "Chaitanya"
PEXELS_API_KEY = "jsVc9Hd2JnpHjPeY5347XU9UHDkz75QLtFkGKmxMS4o44GlG4mHo1jAz"
PEXELS_CACHE_DIR = ASSETS_PATH / "pexels"
OUTPUT_DIR = Path("output")
PEXELS_CACHE_DIR.mkdir(exist_ok=True, parents=True)
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
GAMEPLAY_PATH.mkdir(exist_ok=True, parents=True)
VIRAL_GAMEPLAY_PATH.mkdir(exist_ok=True, parents=True)

if os.name == 'posix':
    change_settings({"IMAGEMAGICK_BINARY": "/opt/homebrew/bin/convert"})


def get_encoder_kwargs() -> dict:
    """Pick the fastest encoder available for this host.

    Apple Silicon gets hardware-accelerated h264_videotoolbox (~3-5x faster
    than libx264 ultrafast). Everything else falls back to libx264 ultrafast
    with all but one core available. On low-memory hosts (M1 8 GB etc.) we
    drop the bitrate and cap threads so videotoolbox's ring buffer doesn't
    blow past 4 GB while MoviePy still holds its input clips in RAM.
    """
    import platform
    from src.hardware import encoder_bitrate, is_low_mem
    cores = os.cpu_count() or 4
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        threads = min(4, cores) if is_low_mem() else cores
        return dict(
            codec="h264_videotoolbox",
            audio_codec="aac",
            audio_bitrate="192k",
            ffmpeg_params=["-b:v", encoder_bitrate()],
            threads=threads,
            logger="bar",
        )
    threads = min(4, cores) if is_low_mem() else max(1, cores - 1)
    return dict(
        codec="libx264",
        audio_codec="aac",
        audio_bitrate="192k",
        preset="ultrafast",
        threads=threads,
        logger="bar",
    )

def get_local_background(lesson_title: str, video_type: str) -> Image.Image:
    """Fixed for modern Pillow (no more ANTIALIAS error)."""
    if not BACKGROUNDS_PATH.exists() or len(list(BACKGROUNDS_PATH.glob("*.*"))) < 1:
        print("⚠️ Backgrounds folder is low/empty")
        w, h = (1920, 1080) if video_type == 'long' else (1080, 1920)
        return Image.new('RGBA', (w, h), color=(12, 17, 29))
    
    images = list(BACKGROUNDS_PATH.glob("*.jpg")) + list(BACKGROUNDS_PATH.glob("*.png")) + list(BACKGROUNDS_PATH.glob("*.jpeg"))
    if not images:
        w, h = (1920, 1080) if video_type == 'long' else (1080, 1920)
        return Image.new('RGBA', (w, h), color=(12, 17, 29))
    
    keywords = ["ai", "neural", "tech", "code", "abstract", "future", "data", "brain", "learning"]
    title_lower = lesson_title.lower()
    scored = [(sum(1 for kw in keywords if kw in title_lower or kw in img.name.lower()), img) for img in images]
    scored.sort(reverse=True, key=lambda x: x[0])
    chosen = scored[0][1] if scored[0][0] > 0 else random.choice(images)
    
    print(f"🎨 Using local background: {chosen.name}")
    img = Image.open(chosen).convert("RGBA")
    
    # Modern Pillow resizing (no ANTIALIAS)
    width, height = (1920, 1080) if video_type == 'long' else (1080, 1920)
    img = img.resize((width, height), Image.Resampling.LANCZOS)
    return img

def get_local_gameplay(video_type: str) -> str:
    clips = list(GAMEPLAY_PATH.glob("*.mp4"))
    if clips:
        return str(random.choice(clips))
    return None

def get_local_viral_gameplay() -> str | None:
    """NEW: Picks high-motion Subway Surfers / Minecraft style clips"""
    if not VIRAL_GAMEPLAY_PATH.exists():
        return None
    clips = list(VIRAL_GAMEPLAY_PATH.glob("*.mp4"))
    if not clips:
        return None
    chosen = random.choice(clips)
    print(f"🔥 Viral Gameplay background: {chosen.name}")
    return str(chosen)

def get_relevant_pexels_video(query: str, video_type: str) -> str:
    # clean query — guard empty string
    parts = query.split()
    if not parts:
        return None
    query = parts[0]
    headers = {"Authorization": PEXELS_API_KEY}
    orientation = "landscape" if video_type == 'long' else "portrait"
    url = f"https://api.pexels.com/videos/search?query={query}&per_page=5&orientation={orientation}"
    try:
        res = requests.get(url, headers=headers, timeout=15)
        data = res.json()
        if data.get("videos"):
            video_url = None
            for v in data["videos"]:
                for f in v.get("video_files", []):
                    if f.get("quality") == "hd":
                        video_url = f["link"]
                        break
                if video_url:
                    video_id = v["id"]
                    break
            
            if not video_url:
                video_url = data["videos"][0]["video_files"][0]["link"]
                video_id = data["videos"][0]["id"]
            
            video_path = PEXELS_CACHE_DIR / f"{video_id}.mp4"
            if not video_path.exists():
                print(f"⬇️ Downloading Pexels video for '{query}'...")
                r = requests.get(video_url, stream=True, timeout=30)
                with open(video_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        if chunk: f.write(chunk)
            return str(video_path)
    except Exception as e:
        print(f"⚠️ Pexels error: {e}")
    return None

def ollama_generate(prompt: str, json_mode: bool = True) -> dict:
    model = "qwen2.5-coder:3b"
    full_prompt = prompt
    if json_mode:
        full_prompt += "\n\nRespond with ONLY valid JSON. No explanations, no markdown, no extra text."
    response = ollama.chat(
        model=model,
        messages=[{'role': 'user', 'content': full_prompt}],
        options={
            'temperature': 0.6,
            'num_ctx': 4096,
            'num_gpu': 1,
            'num_thread': 8,
            'repeat_penalty': 1.1
        }
    )
    text = response['message']['content'].strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1]

    def _safe_json(s: str) -> dict:
        """Parse JSON tolerantly: strip trailing commas, control chars, BOM."""
        s = s.strip().lstrip('\ufeff')
        # Remove trailing commas before ] or } — common Ollama output issue
        s = re.sub(r',\s*([}\]])', r'\1', s)
        # Strip control chars except tab/newline
        s = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', s)
        return json.loads(s)

    try:
        return _safe_json(text)
    except Exception:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return _safe_json(match.group(0))
            except Exception:
                pass
        return {}

_EMOJI_RE = re.compile(
    "[\U0001F600-\U0001F64F"   # emoticons
    "\U0001F300-\U0001F5FF"   # symbols & pictographs
    "\U0001F680-\U0001F6FF"   # transport & map
    "\U0001F1E0-\U0001F1FF"   # flags
    "\U00002702-\U000027B0"   # dingbats
    "\U000024C2-\U0001F251"   # enclosed chars
    "\U0001F900-\U0001F9FF"   # supplemental symbols
    "\U0001FA00-\U0001FA6F"   # chess symbols
    "\U0001FA70-\U0001FAFF"   # symbols extended-A
    "\U00002300-\U000023FF"   # misc technical
    "]+",
    flags=re.UNICODE,
)

def strip_emojis(text: str) -> str:
    """Remove emoji and non-ASCII decorative chars before TTS."""
    text = _EMOJI_RE.sub('', text)
    return re.sub(r' {2,}', ' ', text).strip()


def text_to_speech(text: str, output_path: Path) -> Path:
    """Better local TTS using Piper (natural neural voice) with pyttsx3 fallback."""
    text = strip_emojis(text)
    print(f"🗣️ TTS → {Path(output_path).stem} ({len(text)} chars)...")
    wav_path = output_path.with_suffix('.wav')
    try:
        import subprocess
        # Piper command - adjust voice path to your downloaded voice
        voice_path = Path.home() / ".local/share/piper-tts/voices/en-us-lessac-medium.onnx"
        if voice_path.exists():
            cmd = [
                "piper",
                "--model", str(voice_path),
                "--output_file", str(wav_path),
                "--length_scale", "1.0",
                "--sentence_silence", "0.3"
            ]
            result = subprocess.run(cmd, input=text.encode(), capture_output=True, check=True)
            print(f"✅ Piper TTS saved → {wav_path.name}")
            return wav_path
        else:
            raise FileNotFoundError("Piper voice not found")
    except Exception as e:
        print(f"⚠️ Piper failed ({e}), falling back to pyttsx3...")
        mp3_path = output_path.with_suffix('.mp3')
        engine = pyttsx3.init()
        engine.setProperty('rate', 170)
        engine.setProperty('volume', 1.0)
        engine.save_to_file(text, str(mp3_path))
        engine.runAndWait()
        audio = AudioSegment.from_mp3(str(mp3_path))
        audio.export(str(wav_path), format="wav", codec="pcm_s16le")
        if mp3_path.exists():
            mp3_path.unlink()
        print(f"✅ Fallback TTS saved → {wav_path.name}")
        return wav_path

def generate_curriculum(previous_titles=None):
    print("📋 Generating new curriculum with local Ollama...")
    try:
        history = ""
        if previous_titles:
            formatted = "\n".join([f"{i+1}. {t}" for i, t in enumerate(previous_titles)])
            history = f"The following lessons have already been created:\n{formatted}\n\nPlease continue from where this series left off.\n"
        prompt = f"""
        You are an expert AI educator. Generate a curriculum for a YouTube series called 'AI for Developers by {YOUR_NAME}'.
        {history}
        The style must be: 'Assume the viewer is a beginner or non-technical person starting their journey into AI as a developer.
        Use simple real-world analogies, relatable examples, and then connect to technical concepts.'

        Make sure to include TRENDING and LATEST topics in AI (like multi-agent systems, local LLMs, deepseek, qwen, etc.).

        The curriculum must guide a developer from absolute beginner to advanced AI, covering foundations like Generative AI, LLMs, Vector Databases, and Agentic AI.
        Then continue into deep AI topics like Reinforcement Learning, Transformers internals, multi-agent systems, tool use, LangGraph, AI architecture, and more.

        Respond with ONLY a valid JSON object. The object must contain a key "lessons" which is a list of 20 lesson objects.
        Each lesson object must have these keys: "chapter", "part", "title", "status" (defaulted to "pending"), and "youtube_id" (defaulted to null).
        """
        return ollama_generate(prompt, json_mode=True)
    except Exception as e:
        print(f"❌ Curriculum generation failed: {e}")
        raise

def get_learning_context() -> str:
    from src.learning import get_learning_context as _impl
    return _impl()

def generate_lesson_content(lesson_title):
    print(f"📝 Generating content for lesson: '{lesson_title}'...")
    try:
        learning_context = get_learning_context()
        prompt = f"""
        You are creating a lesson for the 'AI for Developers by {YOUR_NAME}' series. The topic is '{lesson_title}'.
        The style is: Assume the viewer is a beginner developer or non-tech person who wants to learn AI from scratch.
        Use analogies and clear, simple language. Each concept must be explained from a developer's perspective, assuming no prior AI or ML knowledge.
        {learning_context}
        Generate a JSON response with three keys:
        1. "long_form_slides": A list of 7 to 8 slide objects for a longer, more detailed main video. Each object needs a "title" and "content" key.
        2. "short_form_highlight": A single, punchy, 1-2 sentence summary for a YouTube Short.
        3. "hashtags": A string of 5-7 relevant, space-separated hashtags for this lesson (e.g., "#GenerativeAI #LLM #Developer","#NeuralNetworks #BeginnerAI #AIforDevelopers").

        Return only valid JSON.
        """
        return ollama_generate(prompt, json_mode=True)
    except Exception as e:
        print(f"❌ Lesson content failed: {e}")
        raise

def draw_wrapped_text(draw, text, font, content_box, fill="white", center=True, dry_run=False):
    """Render word-wrapped text within a bounding box. Returns False if text doesn't fit."""
    box_left, box_top, box_right, box_bottom = content_box
    pad = 20
    max_width = (box_right - box_left) - (pad * 2)
    available_height = (box_bottom - box_top) - (pad * 2)
    line_spacing = int(font.size * 1.4)

    # Word wrap with character-level fallback for long words
    lines = []
    for paragraph in text.split('\n'):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        line = ""
        for word in words:
            test_line = (line + " " + word).strip()
            if draw.textlength(test_line, font=font) <= max_width:
                line = test_line
            else:
                if line:
                    lines.append(line)
                # Check if single word exceeds max_width — break with hyphen
                if draw.textlength(word, font=font) > max_width:
                    chunk = ""
                    for ch in word:
                        if draw.textlength(chunk + ch + "-", font=font) > max_width:
                            lines.append(chunk + "-")
                            chunk = ch
                        else:
                            chunk += ch
                    line = chunk
                else:
                    line = word
        if line:
            lines.append(line)

    total_height = len(lines) * line_spacing
    if total_height > available_height:
        return False

    if dry_run:
        return True

    y = box_top + pad
    for line_text in lines:
        if center:
            tw = draw.textlength(line_text, font=font)
            x = box_left + (box_right - box_left - tw) / 2
        else:
            x = box_left + pad
        draw.text((x, y), line_text, fill=fill, font=font)
        y += line_spacing
    return True


def auto_scale_text(draw, text, font_path, initial_size, content_box, fill="white", min_size=20):
    """Progressively shrink font until text fits the content_box. Returns font size used."""
    size = initial_size
    while size >= min_size:
        try:
            font = ImageFont.truetype(font_path, size)
        except IOError:
            font = FALLBACK_THUMBNAIL_FONT
        if draw_wrapped_text(draw, text, font, content_box, fill=fill, dry_run=True):
            draw_wrapped_text(draw, text, font, content_box, fill=fill)
            return size
        size -= 3

    # At min_size, render with truncation
    font = ImageFont.truetype(font_path, min_size) if FONT_FILE.exists() else FALLBACK_THUMBNAIL_FONT
    box_left, box_top, box_right, box_bottom = content_box
    max_width = (box_right - box_left) - 40
    available_height = (box_bottom - box_top) - 40
    line_spacing = int(min_size * 1.4)
    max_lines = max(1, int(available_height / line_spacing))

    lines = []
    for paragraph in text.split('\n'):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        line = ""
        for word in words:
            test_line = (line + " " + word).strip()
            if draw.textlength(test_line, font=font) <= max_width:
                line = test_line
            else:
                if line:
                    lines.append(line)
                line = word
            if len(lines) >= max_lines:
                break
        if line and len(lines) < max_lines:
            lines.append(line)
        if len(lines) >= max_lines:
            break

    if len(lines) == max_lines:
        lines[-1] = lines[-1][:max(0, len(lines[-1]) - 3)] + "..."

    y = box_top + 20
    for line_text in lines:
        tw = draw.textlength(line_text, font=font)
        x = box_left + ((box_right - box_left) - tw) / 2
        draw.text((x, y), line_text, fill=fill, font=font)
        y += line_spacing
    return min_size

def generate_visuals(output_dir, video_type, slide_content=None, thumbnail_title=None, slide_number=0, total_slides=0):
    output_dir.mkdir(exist_ok=True, parents=True)
    is_thumbnail = thumbnail_title is not None
    width, height = (1920, 1080) if video_type == 'long' else (1080, 1920)
    title = thumbnail_title if is_thumbnail else slide_content.get("title", "")
    
    if is_thumbnail:
        bg_image = get_local_background(title, video_type)
        bg_image = bg_image.resize((width, height)).filter(ImageFilter.GaussianBlur(5))
        darken_layer = Image.new('RGBA', bg_image.size, (0, 0, 0, 150))
        final_bg = Image.alpha_composite(bg_image, darken_layer).convert("RGB")
        if video_type == 'long':
            w, h = final_bg.size
            if h > w:
                print("Detected vertical thumbnail for long video. Rotating...")
                final_bg = final_bg.transpose(Image.ROTATE_270).resize((1920, 1080))
    else:
        final_bg = Image.new('RGBA', (width, height), (0, 0, 0, 0))

    draw = ImageDraw.Draw(final_bg)
    try:
        title_font = ImageFont.truetype(str(FONT_FILE), 80 if video_type == 'long' else 90)
        content_font = ImageFont.truetype(str(FONT_FILE), 45 if video_type == 'long' else 55)
        footer_font = ImageFont.truetype(str(FONT_FILE), 25 if video_type == 'long' else 35)
    except IOError:
        title_font = content_font = footer_font = FALLBACK_THUMBNAIL_FONT
        
    if not is_thumbnail:
        header_height = int(height * 0.18)
        draw.rectangle([0, 0, width, header_height], fill=(25, 40, 65, 200))
        draw.text((width//2, header_height//2), title, fill="white", font=title_font, anchor="mm")
        content_y = header_height + 80
        draw.rectangle([20, content_y - 40, width - 20, height - 120], fill=(0, 0, 0, 150))
        content_text = slide_content.get("content", "")
        content_box = (40, content_y, width - 40, height - 130)
        auto_scale_text(draw, content_text, str(FONT_FILE), 45 if video_type == 'long' else 55, content_box)
        footer_y = height - 80
        footer_text = f"AI for Developers by {YOUR_NAME} • Slide {slide_number}/{total_slides}"
        draw.text((width//2, footer_y), footer_text, fill="white", font=footer_font, anchor="mm")
    else:
        draw.text((width//2, height//2 - 100), title, fill="white", font=title_font, anchor="mm")
        
    file_prefix = "thumbnail" if is_thumbnail else f"slide_{slide_number:02d}"
    path = output_dir / f"{file_prefix}.png"
    final_bg.save(path)
    return str(path)

def compose_video(slide_paths, audio_paths, output_path, video_type, lesson_title, is_tutorial=False, force_viral_bg=False):
    """OPTIMIZED dynamic video – background loaded ONCE, ultrafast encoding."""
    label = 'Tutorial' if is_tutorial else ('Viral' if force_viral_bg else 'Dynamic')
    print(f"🎥 Creating {label} {video_type} video for: {lesson_title} (OPTIMIZED MODE)")

    STATIC_MODE = False  # Set to True only for super-fast testing

    try:
        if not slide_paths or not audio_paths or len(slide_paths) != len(audio_paths):
            raise ValueError("Slide/audio mismatch")

        # Load background ONCE — viral gameplay only when explicitly requested
        if force_viral_bg:
            bg_path = get_local_viral_gameplay() or get_relevant_pexels_video(lesson_title, video_type)
        else:
            bg_path = get_relevant_pexels_video(lesson_title, video_type)
        if not bg_path:
            bg_path = get_local_gameplay(video_type)

        total_duration = sum(AudioFileClip(str(a)).duration for a in audio_paths) + 0.5 * len(audio_paths)

        if bg_path and not STATIC_MODE:
            print(f"🎮 Using background: {Path(bg_path).name} (loaded once)")
            bg_clip = VideoFileClip(bg_path)
            if bg_clip.duration < total_duration:
                bg_clip = bg_clip.fx(vfx.loop, duration=total_duration)
            else:
                bg_clip = bg_clip.subclip(0, total_duration)
            bg_clip = bg_clip.fx(vfx.colorx, 0.78)
            w, h = bg_clip.size
            zoom = 1.06
            bg_clip = bg_clip.resize(zoom).set_position(lambda t: (0 + (t * 2), 0 + (t * 1.2)))
        else:
            bg_clip = None

        # Build slides
        image_clips = []
        for i, (img_path, audio_path) in enumerate(tqdm(list(zip(slide_paths, audio_paths)),
                                                         desc="  Building slides", unit="slide",
                                                         bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]")):
            audio_clip = AudioFileClip(str(audio_path))
            duration = audio_clip.duration + 0.5
            img_clip = ImageClip(str(img_path)).set_duration(duration).fadein(0.5).fadeout(0.5)

            if bg_clip and not STATIC_MODE:
                final_clip = CompositeVideoClip([
                    bg_clip.set_duration(duration),
                    img_clip.set_opacity(0.93).set_position('center')
                ])
            else:
                final_clip = img_clip

            final_clip = final_clip.set_audio(audio_clip)
            image_clips.append(final_clip)

        final_video = concatenate_videoclips(image_clips, method="compose")

        if BACKGROUND_MUSIC_PATH.exists():
            print("🎵 Adding background music...")
            bg_music = AudioFileClip(str(BACKGROUND_MUSIC_PATH)).volumex(0.15)
            if bg_music.duration < final_video.duration:
                bg_music = bg_music.fx(vfx.loop, duration=final_video.duration)
            else:
                bg_music = bg_music.subclip(0, final_video.duration)
            composite = CompositeAudioClip([final_video.audio.volumex(1.2), bg_music])
            final_video = final_video.set_audio(composite)

        print(f"🎬 Encoding video → {Path(output_path).name}")
        try:
            final_video.write_videofile(
                str(output_path),
                fps=24,
                **get_encoder_kwargs(),
            )
            print(f"✅ Video saved: {Path(output_path).name}")
        finally:
            for c in image_clips:
                try: c.close()
                except Exception: pass
            try: final_video.close()
            except Exception: pass
            if bg_clip is not None:
                try: bg_clip.close()
                except Exception: pass

    except Exception as e:
        print(f"❌ Video creation error: {e}")
        import traceback
        traceback.print_exc()
        raise

# ── Length enforcers ─────────────────────────────────────────────────────────

_SLIDE_PAD = (
    " This concept is foundational — understanding it deeply will directly affect "
    "the quality of your AI projects. Let's break it down further with a real-world "
    "analogy. Think of it like building a house: you need solid foundations before "
    "you add walls and a roof. The same applies here. Developers who skip this step "
    "consistently run into problems later that take hours to debug. Take this seriously "
    "and implement it in your own work as soon as possible."
)

def _enforce_slide_content(slides: list, min_words: int = 120) -> list:
    """Pad each slide's content field to at least min_words so TTS hits ~40 s/slide."""
    padded = []
    for s in slides:
        content = s.get("content", s.get("title", ""))
        while len(content.split()) < min_words:
            content += _SLIDE_PAD
        # hard-trim at 200 words to keep slides scannable on screen
        words = content.split()
        if len(words) > 200:
            content = " ".join(words[:200])
        padded.append({**s, "content": content.strip()})
    return padded


_SCRIPT_PAD = (
    " This is something that affects every single person who wants to perform at a "
    "higher level. The research is consistent and spans multiple decades across different "
    "countries and demographics. Understanding this gives you an edge that most people "
    "never bother to develop. The practical application is simpler than you might think, "
    "and the results show up within days, not months. Start with the smallest possible "
    "version of this habit and build from there. Small consistent actions compound into "
    "dramatic changes over time. That is the core insight that separates the top one "
    "percent from everyone else."
)

def _enforce_script_length(script: str, min_words: int = 900) -> str:
    """Pad script to at least min_words (900 w ≈ 5 min @ 170 wpm)."""
    while len(script.split()) < min_words:
        script += " " + _SCRIPT_PAD
    # trim at 1200 words (~7 min) max
    words = script.split()
    if len(words) > 1200:
        script = " ".join(words[:1200])
    return script.strip()


# ── Tutorial topics — auto-picked when user presses Enter ─────────────────────
TUTORIAL_TOPICS = [
    "Build Your First AI Agent with Python",
    "Local LLMs with Ollama – Complete Beginner Guide",
    "Vector Databases Explained Simply for Developers",
    "LangChain vs LangGraph – Which One Should You Use",
    "Prompt Engineering Masterclass – From Beginner to Pro",
    "Fine-Tuning LLMs on Your Own Data – Step by Step",
    "RAG (Retrieval-Augmented Generation) Explained and Built",
    "How to Run DeepSeek Locally on Any Machine",
    "Building Multi-Agent AI Systems from Scratch",
    "Function Calling and Tool Use in Modern LLMs",
    "Embeddings and Semantic Search – How They Really Work",
    "Build a Fully Local AI Coding Assistant",
    "AI Safety and Alignment – What Every Developer Must Know",
    "Transformer Architecture Explained Without the Math",
    "The Complete Guide to Open-Source AI Models in 2026",
]

# NEW: Tutorial Generation
def generate_tutorial_content(topic: str):
    print(f"📚 Generating ~10-minute tutorial for: {topic}")
    prompt = f"""You are creating a 10-minute YouTube tutorial on: {topic}

Generate exactly 15 slides. CRITICAL: each slide "content" MUST be 3-4 full sentences
(minimum 60 words each). Short content is unacceptable — pad with explanation and examples.

Each slide must include:
- A real-world analogy
- A practical developer tip or code example
- Why this matters

Also write a 60-second Short highlight script (hook first, "Follow for more" at end).

Return ONLY valid JSON:
{{
  "long_slides": [
    {{"title": "slide title here", "content": "minimum 60 words of detailed explanation here..."}}
  ],
  "short_highlight": "60-second spoken script with hook and CTA",
  "hashtags": "#Tutorial #AI #Dev #LearnToCode"
}}"""
    result = ollama_generate(prompt, json_mode=True)
    if not result.get("long_slides"):
        print("⚠️  Ollama returned empty long_slides — retrying once...")
        result = ollama_generate(prompt, json_mode=True)
    # Enforce minimum slide length so TTS hits 40+ seconds per slide
    if result.get("long_slides"):
        result["long_slides"] = _enforce_slide_content(result["long_slides"], min_words=120)
    return result

# NEW: Tutorial Pipeline (long + linked short)
def start_tutorial_generation():
    from src.browser_uploader import upload_to_youtube_browser as upload_to_youtube
    from src.learning import log_upload

    raw = input("Enter tutorial topic (or press Enter to auto-pick): ").strip()
    topic = raw if raw else random.choice(TUTORIAL_TOPICS)
    if not raw:
        print(f"  Auto-picked: {topic}")

    content = generate_tutorial_content(topic)
    
    # If content is string, try to parse it (fallback for direct ollama calls or inconsistencies)
    if isinstance(content, str):
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1]
            content = json.loads(content)
        except:
            import re
            match = re.search(r'\{.*\}', content, re.DOTALL)
            content = json.loads(match.group(0)) if match else {}

    if not content or not isinstance(content, dict):
        print("❌ Failed to generate tutorial content.")
        return

    unique_id = f"tutorial_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

    print("\n--- Producing Long Tutorial Video ---")
    long_slides = content.get("long_slides", [])
    if not long_slides:
        print("❌ No slides generated.")
        return

    # Enforce 120-word minimum per slide regardless of LLM output
    long_slides = _enforce_slide_content(long_slides, min_words=120)
    print(f"  {len(long_slides)} slides enforced to 120w+ each "
          f"(~{len(long_slides)*120//170//60}:{len(long_slides)*120//170%60:02d} min target)")

    slide_audio_paths = []
    for i, slide in enumerate(tqdm(long_slides, desc="  TTS (long)")):
        txt = f"{slide.get('title', '')}. {slide.get('content', '')}"
        audio_path = OUTPUT_DIR / f"{unique_id}_long_audio_{i}.mp3"
        wav_path = text_to_speech(txt, audio_path)
        slide_audio_paths.append(wav_path)

    slide_dir = OUTPUT_DIR / f"{unique_id}_slides"
    slide_paths = []
    for i, slide in enumerate(tqdm(long_slides, desc="  Slides (long)")):
        path = generate_visuals(slide_dir, 'long', slide, slide_number=i+1, total_slides=len(long_slides))
        slide_paths.append(path)

    long_video_path = OUTPUT_DIR / f"{unique_id}_long.mp4"
    compose_video(slide_paths, slide_audio_paths, long_video_path, 'long', topic, is_tutorial=True)
    
    long_thumb_path = generate_visuals(OUTPUT_DIR, 'long', thumbnail_title=topic)

    print("\n--- Producing Tutorial Short ---")
    short_txt = content.get("short_highlight", f"Check out my new tutorial on {topic}!")
    short_audio_path = text_to_speech(short_txt, OUTPUT_DIR / f"{unique_id}_short_audio.mp3")
    
    short_slide_content = {"title": "Tutorial Highlight", "content": short_txt}
    short_slide_path = generate_visuals(OUTPUT_DIR / f"{unique_id}_short_slides", 'short', short_slide_content, slide_number=1, total_slides=1)
    
    short_video_path = OUTPUT_DIR / f"{unique_id}_short.mp4"
    compose_video([short_slide_path], [short_audio_path], short_video_path, 'short', topic, is_tutorial=True)
    
    short_thumb_path = generate_visuals(OUTPUT_DIR, 'short', thumbnail_title=f"Tutorial: {topic}")

    print("\n--- Uploading Tutorial ---")
    hashtags = content.get("hashtags", "#Tutorial #Learn #Tech")
    desc = f"New deep dive tutorial: {topic}\n\n{hashtags}\n\nProduced by SuperShorts"
    
    long_video_id = upload_to_youtube(long_video_path, topic, desc, "tutorial,ai," + topic.replace(" ", ","), long_thumb_path)
    
    if long_video_id:
        log_upload(topic, long_video_id, "tutorial")
        print("⏳ Waiting 30 seconds before uploading short...")
        time.sleep(30)
        
        short_title = f"{topic[:80]} #Shorts #Tutorial"
        short_desc = f"{short_txt}\n\nWatch full tutorial: https://youtube.com/watch?v={long_video_id}\n\n{hashtags}"
        short_video_id = upload_to_youtube(short_video_path, short_title, short_desc, "shorts,tutorial", short_thumb_path)
        if short_video_id:
            log_upload(short_title, short_video_id, "tutorial_short")
    else:
        print("⚠️ Long video upload failed or returned no ID. Skipping Short upload.")


# ── YouTube Content Package ──────────────────────────────────────────────────

CONTENT_PACKAGE_TOPICS = [
    "The Science of Habit Formation",
    "Why Sleep Deprivation Destroys Productivity",
    "How Top Performers Structure Their Day",
    "The Hidden Psychology of Motivation",
    "Why Most People Never Reach Their Goals",
    "The Neuroscience of Deep Work",
    "How to Learn Anything 10x Faster",
    "The Truth About Multitasking",
    "Why Your Environment Controls Your Behaviour",
    "The Simple System That Beats Every To-Do App",
    "What High Achievers Do in the First Hour of Their Day",
    "The Real Reason You Procrastinate (And How to Stop)",
]


def generate_youtube_content_package() -> None:
    """Expert YouTube Content Strategist — auto-picks topic, generates script + video + upload."""
    from src.browser_uploader import upload_to_youtube_browser
    from src.learning import log_upload

    print("\n  📦 YouTube Content Strategist Activated\n")

    raw   = input("  Seed category (or Enter to auto-pick): ").strip()
    topic = raw if raw else random.choice(CONTENT_PACKAGE_TOPICS)
    if not raw:
        print(f"  Auto-picked: {topic}")

    prompt = f"""You are an expert YouTube scriptwriter and content strategist.
Create a complete production package for a 5-minute YouTube video.

Topic: {topic}

CRITICAL SCRIPT REQUIREMENTS — READ CAREFULLY:
- The "full_script" field MUST be 500+ words of flowing spoken prose
- Write in paragraphs, not bullet points — this is narrated speech
- No emojis, no asterisks, no markdown formatting
- Start with a single shocking or curiosity hook sentence
- Use transitions: "But here is the thing...", "What most people miss is...", "Research shows..."
- End with exactly: "Subscribe for more"
- Cover at least 4 distinct sub-points about the topic with explanation and examples

Return ONLY valid JSON:
{{
  "title_options": ["Option A", "Option B", "Option C"],
  "selected_title": "Best SEO title under 70 chars",
  "full_script": "MINIMUM 500 WORDS of flowing narration here. Write multiple paragraphs...",
  "pexels_keywords": "keyword1 keyword2 keyword3",
  "description": "2-3 line SEO description with CTA",
  "hashtags": "#Tag1 #Tag2 #Tag3 #Tag4 #Tag5"
}}"""

    print("  Calling Ollama for content package...")
    result = ollama_generate(prompt, json_mode=True)

    if not result or not result.get("full_script"):
        print("  ⚠️  LLM returned empty — using fallback script.")
        result = {
            "selected_title": topic[:70],
            "full_script": (
                f"{topic}. Most people never think about this deeply enough. "
                "The science is clear — those who master this principle outperform everyone around them. "
                "It starts with one small shift in how you approach each day. "
                "Researchers at leading universities have studied this for decades and the results are consistent. "
                "The people at the top of every field do this differently. "
                "And once you understand why, you cannot unsee it. "
                "Start today, not tomorrow. Subscribe for more."
            ),
            "pexels_keywords": "productivity focus mindset",
            "description": f"{topic}\n\nScience-backed insights every week. Subscribe now.",
            "hashtags": "#Productivity #Science #Psychology #Mindset #Learning",
        }

    title      = strip_emojis(result.get("selected_title", topic)[:80])
    script     = strip_emojis(result.get("full_script", ""))
    # Enforce 5-minute minimum (900 words @ 170 wpm ≈ 5.3 min)
    script     = _enforce_script_length(script, min_words=900)
    desc       = result.get("description", "") + "\n\n" + result.get("hashtags", "")
    pexels_kw  = result.get("pexels_keywords", "technology abstract")

    # Save .md package
    timestamp    = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    package_path = OUTPUT_DIR / f"content_package_{timestamp}.md"
    package_path.write_text(
        f"# YouTube Content Package\n\nGenerated: {datetime.datetime.now():%Y-%m-%d %H:%M}\n\n"
        + json.dumps(result, indent=2),
        encoding="utf-8",
    )
    print(f"  Package saved → {package_path.name}")
    print(f"  Title: {title}")
    print(f"  Script: {len(script.split())} words\n")

    unique_id = f"pkg_{timestamp}"

    # TTS
    audio_path = text_to_speech(script, OUTPUT_DIR / f"{unique_id}_audio.mp3")

    # Visuals — single long-form slide
    slide_dir  = OUTPUT_DIR / f"{unique_id}_slides"
    slide_path = generate_visuals(
        slide_dir, "long",
        slide_content={"title": title, "content": script[:600]},
        slide_number=1, total_slides=1,
    )

    # Compose
    video_path = OUTPUT_DIR / f"{unique_id}_video.mp4"
    print(f"  Composing → {video_path.name}")
    compose_video([slide_path], [audio_path], video_path, "long", title)

    # Upload
    tags     = ",".join(dict.fromkeys((pexels_kw + ",YouTube,education").split(",")[:10]))
    print(f"  Uploading → {title[:60]}...")
    video_id = upload_to_youtube_browser(video_path, title, desc, tags)

    if video_id:
        log_upload(title, video_id, "content_package")
        print(f"  Live: https://youtube.com/watch?v={video_id}")
    else:
        print(f"  Upload failed — video saved locally: {video_path.name}")


def start_viral_gameplay_mode():
    """Educational videos with FORCED viral gameplay backgrounds (Subway Surfers style)."""
    from src.browser_uploader import upload_to_youtube_browser as upload_to_youtube
    from src.learning import log_upload

    clips = list(VIRAL_GAMEPLAY_PATH.glob("*.mp4"))
    if not clips:
        print(f"\n⚠️  No gameplay clips found in {VIRAL_GAMEPLAY_PATH}/")
        print("   Drop Subway Surfers, Minecraft, or satisfying MP4s there and retry.")
        print("   Falling back to Pexels backgrounds...\n")

    topic = input("Enter topic for viral gameplay video (or press Enter for random AI topic): ").strip()
    if not topic:
        topic = random.choice([
            "Why AI Will Replace 90% of Jobs by 2030",
            "This FREE AI Codes Better Than ChatGPT",
            "Nobody Is Talking About This AI Secret",
            "How To Build Your Own GPT in 5 Minutes",
            "The AI Tool That Makes $1000/Day Automatically",
        ])
        print(f"  Using: {topic}")

    content = generate_lesson_content(topic)
    unique_id = f"viral_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Short-form only (portrait) for viral gameplay
    slides_data = content.get('long_form_slides', [])[:5]  # Max 5 slides for shorts
    if not slides_data:
        print("❌ No content generated.")
        return

    slide_audio_paths = []
    for i, slide in enumerate(tqdm(slides_data, desc="  TTS (viral)")):
        txt = f"{slide.get('title', '')}. {slide.get('content', '')}"
        audio_path = OUTPUT_DIR / f"{unique_id}_audio_{i}.mp3"
        slide_audio_paths.append(text_to_speech(txt, audio_path))

    slide_dir = OUTPUT_DIR / f"{unique_id}_slides"
    slide_paths = []
    for i, slide in enumerate(tqdm(slides_data, desc="  Slides (viral)")):
        path = generate_visuals(slide_dir, 'short', slide, slide_number=i+1, total_slides=len(slides_data))
        slide_paths.append(path)

    video_path = OUTPUT_DIR / f"{unique_id}.mp4"
    compose_video(slide_paths, slide_audio_paths, video_path, 'short', topic, force_viral_bg=True)

    thumb_path = generate_visuals(OUTPUT_DIR, 'short', thumbnail_title=topic)

    hashtags = content.get("hashtags", "#AI #Shorts #Viral")
    desc = f"{topic}\n\n{hashtags}\n\nProduced by SuperShorts"
    video_id = upload_to_youtube(video_path, f"{topic[:80]} #Shorts", desc, "AI,Shorts,Viral", thumb_path)
    if video_id:
        log_upload(topic, video_id, "viral_gameplay")
    print(f"✅ Viral gameplay video done: {topic}")
