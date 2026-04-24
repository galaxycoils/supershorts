import json
import random
import datetime
from pathlib import Path
from tqdm import tqdm

from src.core.config import (
    CONTENT_PACKAGE_TOPICS, YOUR_NAME, OUTPUT_DIR, VIRAL_GAMEPLAY_PATH, VideoOptions
)
from src.core.interfaces import IVideoEngine, ILLMService, ITTSService, IVideoUploader
from src.utils.text import strip_emojis, enforce_script_length, clamp_words

def generate_youtube_content_package(llm_service=None, tts_service=None, uploader_service=None, video_engine=None, dry_run=False, voice=None) -> None:
    """Expert YouTube Content Strategist — auto-picks topic, generates script + video + upload."""
    if not all([llm_service, tts_service, uploader_service, video_engine]):
        raise ValueError("All services (llm, tts, uploader, engine) must be provided to generate_youtube_content_package")

    print("\n  📦 YouTube Content Strategist Activated\n")

    # Handle non-interactive mode (Dashboard)
    import os
    raw = os.environ.get("PACKAGE_TOPIC", "")
    if not raw:
        try:
            raw = input("  Seed category (or Enter to auto-pick): ").strip()
        except EOFError:
            raw = ""
            
    topic = raw if raw else random.choice(CONTENT_PACKAGE_TOPICS)
    if not raw:
        print(f"  Auto-picked: {topic}")

    if dry_run:
        result = {
            "selected_title": f"{topic} DRY RUN",
            "full_script": "This is a dry run script. It should be long enough but it is just a test.",
            "pexels_keywords": "test dryrun",
            "description": "Dry run description",
            "hashtags": "#DryRun"
        }
    else:
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

        print("  Calling LLM for content package...")
        result = llm_service.generate(prompt, json_mode=True)

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
    script     = enforce_script_length(script)
    desc       = result.get("description", "") + "\n\n" + result.get("hashtags", "")
    pexels_kw  = result.get("pexels_keywords", "technology abstract")

    timestamp    = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = f"pkg_{timestamp}"

    audio_path = OUTPUT_DIR / f"{unique_id}_audio.mp3"
    if dry_run:
        audio_path.touch()
    else:
        audio_path = tts_service.text_to_speech(script, audio_path, voice=voice)

    slide_dir  = OUTPUT_DIR / f"{unique_id}_slides"
    if dry_run:
        slide_dir.mkdir(exist_ok=True, parents=True)
        slide_path = slide_dir / "slide_1.png"
        slide_path.touch()
    else:
        slide_path = video_engine.generate_visuals(
            slide_dir, "long",
            slide_content={"title": title, "content": script[:600]},
            slide_number=1, total_slides=1,
        )

    video_path = OUTPUT_DIR / f"{unique_id}_video.mp4"
    if dry_run:
        video_path.touch()
    else:
        video_engine.compose_video([slide_path], [audio_path], video_path, VideoOptions(video_type="long", lesson_title=title, script=script))

    if dry_run:
        video_id = "DRY_RUN_ID"
    else:
        tags     = ",".join(dict.fromkeys((pexels_kw + ",YouTube,education").split(",")[:10]))
        print(f"  Uploading → {title[:60]}...")
        video_id = uploader_service.upload(video_path, title, desc, tags.split(","))

    if video_id:
        from src.core.learning import log_upload
        log_upload(title, video_id, "content_package")


def start_viral_gameplay_mode(llm_service=None, tts_service=None, uploader_service=None, video_engine=None, dry_run=False, voice=None):
    """Educational videos with FORCED viral gameplay backgrounds."""
    from src.core.learning import log_upload
    from src.generator import generate_lesson_content

    if not all([llm_service, tts_service, uploader_service, video_engine]):
        raise ValueError("All services (llm, tts, uploader, engine) must be provided to start_viral_gameplay_mode")

    clips = list(VIRAL_GAMEPLAY_PATH.glob("*.mp4"))
    if not clips:
        print(f"\n⚠️ No gameplay clips found in {VIRAL_GAMEPLAY_PATH}/")

    # Handle non-interactive mode (Dashboard)
    import os
    topic = os.environ.get("VIRAL_TOPIC", "")
    if not topic:
        try:
            topic = input("Enter topic for viral gameplay video: ").strip()
        except EOFError:
            topic = ""
            
    if not topic:
        topic = "Future of AI Agents"
        print(f"  Using: {topic}")

    content = generate_lesson_content(topic, llm_service=llm_service)
    unique_id = f"viral_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

    slides_data = content.get('long_form_slides', [])[:5]
    if not slides_data:
        print("❌ No content generated.")
        return

    slide_audio_paths = []
    for i, slide in enumerate(tqdm(slides_data, desc="  TTS (viral)")):
        txt = f"{slide.get('title', '')}. {slide.get('content', '')}"
        audio_path = OUTPUT_DIR / f"{unique_id}_audio_{i}.mp3"
        if dry_run:
            audio_path.touch()
            slide_audio_paths.append(audio_path)
        else:
            slide_audio_paths.append(tts_service.text_to_speech(txt, audio_path, voice=voice))

    slide_dir = OUTPUT_DIR / f"{unique_id}_slides"
    slide_paths = []
    for i, slide in enumerate(tqdm(slides_data, desc="  Slides (viral)")):
        if dry_run:
            slide_dir.mkdir(exist_ok=True, parents=True)
            path = slide_dir / f"slide_{i+1}.png"
            path.touch()
        else:
            path = video_engine.generate_visuals(slide_dir, 'short', slide, slide_number=i+1, total_slides=len(slides_data))
        slide_paths.append(path)

    video_path = OUTPUT_DIR / f"{unique_id}.mp4"
    if dry_run:
        video_path.touch()
        video_id = "DRY_RUN_ID"
    else:
        viral_script = ' '.join(f"{s.get('title', '')}. {s.get('content', '')}" for s in slides_data)
        viral_script = clamp_words(viral_script, min_w=99, max_w=127)
        video_engine.compose_video(slide_paths, slide_audio_paths, video_path, 
                      VideoOptions(video_type='short', lesson_title=topic, force_viral_bg=True, script=viral_script))

        thumb_path = Path(video_engine.generate_visuals(OUTPUT_DIR, 'short', is_thumbnail=True, thumbnail_title=topic))

        hashtags = content.get("hashtags", "#AI #Shorts #Viral")
        desc = f"{topic}\n\n{hashtags}\n\nProduced by SuperShorts"
        video_id = uploader_service.upload(video_path, f"{topic[:80]} #Shorts", desc, ["AI", "Shorts", "Viral"], thumb_path)
    
    if video_id:
        log_upload(topic, video_id, "viral_gameplay")
    print(f"✅ Viral gameplay video done: {topic}")
