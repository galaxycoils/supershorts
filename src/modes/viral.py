import json
import random
import datetime
from pathlib import Path
from tqdm import tqdm

from src.core.config import (
    CONTENT_PACKAGE_TOPICS, YOUR_NAME, OUTPUT_DIR, VIRAL_GAMEPLAY_PATH,
    OLLAMA_MODEL, OLLAMA_TIMEOUT
)
from src.infrastructure.llm import ollama_generate
from src.infrastructure.tts import text_to_speech
from src.infrastructure.video import get_local_background, get_local_gameplay, get_relevant_pexels_video
from src.engine.video_engine import generate_visuals, compose_video
from src.utils.text import strip_emojis, _enforce_script_length, _clamp_words
from src.utils.json import safe_json_parse

def generate_youtube_content_package() -> None:
    """Expert YouTube Content Strategist — auto-picks topic, generates script + video + upload."""
    from src.infrastructure.browser_uploader import upload_to_youtube_browser
    from src.core.learning import log_upload

    print("\n  📦 YouTube Content Strategist Activated\n")

    raw   = input("  Seed category (or Enter to auto-pick): ").strip()
    topic = raw if raw else random.choice(CONTENT_PACKAGE_TOPICS)
    if not raw:
        print(f"  Auto-picked: {topic}")

    prompt = f"""You are an expert YouTube scriptwriter and content strategist.
Create a complete production package for a 5-minute YouTube video.

Topic: {topic}

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

    print("  Calling Ollama for content package...")
    result = ollama_generate(prompt, json_mode=True)

    if not result or not result.get("full_script"):
        print("  ⚠️  LLM returned empty — using fallback script.")
        result = {
            "selected_title": topic[:70],
            "full_script": f"{topic}. The science is clear. Subscribe for more.",
            "pexels_keywords": "productivity focus",
            "description": f"{topic}",
            "hashtags": "#Productivity #Science",
        }

    title      = strip_emojis(result.get("selected_title", topic)[:80])
    script     = strip_emojis(result.get("full_script", ""))
    script     = _enforce_script_length(script, min_words=1360)
    desc       = result.get("description", "") + "\n\n" + result.get("hashtags", "")
    pexels_kw  = result.get("pexels_keywords", "technology abstract")

    timestamp    = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = f"pkg_{timestamp}"

    audio_path = text_to_speech(script, OUTPUT_DIR / f"{unique_id}_audio.mp3")

    slide_dir  = OUTPUT_DIR / f"{unique_id}_slides"
    slide_path = generate_visuals(
        slide_dir, "long",
        slide_content={"title": title, "content": script[:600]},
        slide_number=1, total_slides=1,
    )

    video_path = OUTPUT_DIR / f"{unique_id}_video.mp4"
    compose_video([slide_path], [audio_path], video_path, "long", title, script=script)

    tags     = ",".join(dict.fromkeys((pexels_kw + ",YouTube,education").split(",")[:10]))
    print(f"  Uploading → {title[:60]}...")
    video_id = upload_to_youtube_browser(video_path, title, desc, tags)

    if video_id:
        log_upload(title, video_id, "content_package")


def start_viral_gameplay_mode():
    """Educational videos with FORCED viral gameplay backgrounds."""
    from src.infrastructure.browser_uploader import upload_to_youtube_browser as upload_to_youtube
    from src.core.learning import log_upload
    from src.generator import generate_lesson_content

    clips = list(VIRAL_GAMEPLAY_PATH.glob("*.mp4"))
    if not clips:
        print(f"\n⚠️ No gameplay clips found in {VIRAL_GAMEPLAY_PATH}/")

    topic = input("Enter topic for viral gameplay video: ").strip()
    if not topic:
        topic = "Future of AI Agents"
        print(f"  Using: {topic}")

    content = generate_lesson_content(topic)
    unique_id = f"viral_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

    slides_data = content.get('long_form_slides', [])[:5]
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
    viral_script = ' '.join(f"{s.get('title', '')}. {s.get('content', '')}" for s in slides_data)
    viral_script = _clamp_words(viral_script, min_w=99, max_w=127)
    compose_video(slide_paths, slide_audio_paths, video_path, 'short', topic,
                  force_viral_bg=True, script=viral_script)

    thumb_path = generate_visuals(OUTPUT_DIR, 'short', thumbnail_title=topic)

    hashtags = content.get("hashtags", "#AI #Shorts #Viral")
    desc = f"{topic}\n\n{hashtags}\n\nProduced by SuperShorts"
    video_id = upload_to_youtube(video_path, f"{topic[:80]} #Shorts", desc, "AI,Shorts,Viral", thumb_path)
    if video_id:
        log_upload(topic, video_id, "viral_gameplay")
    print(f"✅ Viral gameplay video done: {topic}")
