import json
import random
import datetime
from pathlib import Path
from tqdm import tqdm

from src.core.config import TUTORIAL_TOPICS, YOUR_NAME, OUTPUT_DIR, OLLAMA_MODEL, OLLAMA_TIMEOUT
from src.infrastructure.llm import ollama_generate
from src.infrastructure.tts import text_to_speech
from src.infrastructure.video import get_local_background, get_local_gameplay, get_relevant_pexels_video
from src.engine.video_engine import generate_visuals, compose_video
from src.utils.text import _clamp_words
from src.utils.json import safe_json_parse

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
    if result.get("long_slides"):
        result["long_slides"] = _enforce_slide_content(result["long_slides"], min_words=120)
    return result

def start_tutorial_generation():
    from src.browser_uploader import upload_to_youtube_browser as upload_to_youtube
    from src.learning import log_upload

    raw = input("Enter tutorial topic (or press Enter to auto-pick): ").strip()
    topic = raw if raw else random.choice(TUTORIAL_TOPICS)
    if not raw:
        print(f"  Auto-picked: {topic}")

    content = generate_tutorial_content(topic)
    
    if not content or not isinstance(content, dict):
        print("❌ Failed to generate tutorial content.")
        return

    unique_id = f"tutorial_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

    print("\n--- Producing Long Tutorial Video ---")
    long_slides = content.get("long_slides", [])
    if not long_slides:
        print("❌ No slides generated.")
        return

    long_slides = _enforce_slide_content(long_slides, min_words=120)

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
    long_script = ' '.join(f"{s.get('title', '')}. {s.get('content', '')}" for s in long_slides)
    compose_video(slide_paths, slide_audio_paths, long_video_path, 'long', topic,
                  is_tutorial=True, script=long_script)

    long_thumb_path = generate_visuals(OUTPUT_DIR, 'long', thumbnail_title=topic)

    print("\n--- Producing Tutorial Short ---")
    short_txt = content.get("short_highlight", f"Check out my new tutorial on {topic}!")
    short_txt = _clamp_words(short_txt, min_w=99, max_w=127)
    short_audio_path = text_to_speech(short_txt, OUTPUT_DIR / f"{unique_id}_short_audio.mp3")

    short_slide_content = {"title": "Tutorial Highlight", "content": short_txt}
    short_slide_path = generate_visuals(OUTPUT_DIR / f"{unique_id}_short_slides", 'short', short_slide_content, slide_number=1, total_slides=1)

    short_video_path = OUTPUT_DIR / f"{unique_id}_short.mp4"
    compose_video([short_slide_path], [short_audio_path], short_video_path, 'short', topic,
                  is_tutorial=True, script=short_txt)
    
    short_thumb_path = generate_visuals(OUTPUT_DIR, 'short', thumbnail_title=f"Tutorial: {topic}")

    print("\n--- Uploading Tutorial ---")
    hashtags = content.get("hashtags", "#Tutorial #Learn #Tech")
    desc = f"New deep dive tutorial: {topic}\n\n{hashtags}\n\nProduced by SuperShorts"
    
    long_video_id = upload_to_youtube(long_video_path, topic, desc, "tutorial,ai," + topic.replace(" ", ","), long_thumb_path)
    
    if long_video_id:
        log_upload(topic, long_video_id, "tutorial")
        print("⏳ Waiting 30 seconds before uploading short...")
        import time; time.sleep(30)
        
        short_title = f"{topic[:80]} #Shorts #Tutorial"
        short_desc = f"{short_txt}\n\nWatch full tutorial: https://youtube.com/watch?v={long_video_id}\n\n{hashtags}"
        short_video_id = upload_to_youtube(short_video_path, short_title, short_desc, "shorts,tutorial", short_thumb_path)
        if short_video_id:
            log_upload(short_title, short_video_id, "tutorial_short")
    else:
        print("⚠️ Long video upload failed. Skipping Short upload.")
