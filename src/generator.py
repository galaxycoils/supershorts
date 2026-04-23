# src/generator.py - Compatibility Bridge & Orchestration
"""
This module serves as a backward-compatible bridge for the legacy main.py and run_workflow.py.
It re-exports symbols from the new modular structure. 
Internal modules should NOT import from this file to avoid circular dependencies.
"""

# --- Core Re-exports (Config) ---
from src.core.config import (
    PROJECT_ROOT, ASSETS_PATH, OUTPUT_DIR, BACKGROUNDS_PATH,
    GAMEPLAY_PATH, VIRAL_GAMEPLAY_PATH, FONT_FILE,
    BACKGROUND_MUSIC_PATH, PEXELS_CACHE_DIR, PEXELS_API_KEY,
    OLLAMA_MODEL, OLLAMA_TIMEOUT, YOUR_NAME
)

# --- Infrastructure Re-exports ---
from src.infrastructure.llm import ollama_generate, safe_json_parse
from src.infrastructure.video import (
    get_local_background, get_local_gameplay, 
    get_local_viral_gameplay, get_relevant_pexels_video
)
from src.infrastructure.tts import text_to_speech
from src.infrastructure.browser_uploader import upload_to_youtube_browser
from src.infrastructure.uploader import upload_to_youtube

# --- Engine Re-exports ---
from src.engine.video_engine import (
    generate_visuals, compose_video, 
    auto_scale_text, draw_wrapped_text
)
from moviepy.editor import (
    VideoFileClip, AudioFileClip, ImageClip, 
    CompositeVideoClip, CompositeAudioClip,
    concatenate_videoclips, vfx
)

# --- Utils Re-exports ---
from src.utils.text import strip_emojis, strip_markdown, clamp_words, enforce_script_length
from src.utils.cleanup import safe_close

# --- Mode Re-exports (Backward compatibility for main.py / run_workflow.py) ---
from src.modes.tutorial import start_tutorial_generation, generate_tutorial_content
from src.modes.viral import generate_youtube_content_package, start_viral_gameplay_mode
from src.modes.brainrot import run_brainrot_pipeline, generate_brainrot_topics, generate_brainrot_script, render_brainrot_slide, create_brainrot_video
from src.modes.tcm_educational import run_tcm_mode, generate_tcm_curriculum
from src.modes.rotgen import run_rotgen_pipeline
from src.modes.studio_ideas import start_idea_generator
from src.modes.clipper import run_video_clipper
from src.core.learning import start_learning_mode

# --- Core Logic Re-exports ---
from src.core.learning import log_upload, suggest_improvements

# --- High-level Orchestration / Legacy Support ---

def generate_lesson_content(lesson_title, series_name=None, style_description=None):
    """Bridge to LLM service with default style logic."""
    if not series_name:
        series_name = f"AI for Developers by {YOUR_NAME}"
    if not style_description:
        style_description = (
            "Assume the viewer is a beginner developer. "
            "Use analogies and clear, simple language."
        )
    
    prompt = f"""You are creating a lesson for '{series_name}'. 
Topic: '{lesson_title}'
Style: {style_description}
Generate JSON: long_form_slides (7-8 objs with title/content), short_form_highlight, hashtags."""
    fallback_slides = [
        {
            "title": f"What {lesson_title} Means",
            "content": f"{lesson_title} is an important concept for developers. This lesson explains the idea in simple terms, why it matters, and where it shows up in real projects.",
        },
        {
            "title": "Why It Matters",
            "content": f"If you understand {lesson_title}, you can make better technical decisions, debug faster, and build more reliable systems with fewer surprises.",
        },
        {
            "title": "Real-World Example",
            "content": f"In practice, {lesson_title} appears when teams move from simple prototypes to production systems. Clear fundamentals help avoid fragile designs and repeated mistakes.",
        },
        {
            "title": "Common Mistakes",
            "content": f"A common mistake is using {lesson_title} without understanding the tradeoffs. Good engineers compare simplicity, performance, and maintainability before choosing an approach.",
        },
        {
            "title": "How To Apply It",
            "content": f"The best way to use {lesson_title} is to start small, measure results, and improve the implementation step by step instead of overengineering from day one.",
        },
        {
            "title": "Key Takeaway",
            "content": f"The main takeaway is that {lesson_title} is most useful when paired with clear goals, practical constraints, and consistent iteration.",
        },
    ]
    result = ollama_generate(prompt, json_mode=True)
    if result:
        if not result.get("long_form_slides"):
            result["long_form_slides"] = fallback_slides
        
        # Coerce highlight to string if LLM returns a list
        highlight = result.get("short_form_highlight")
        if isinstance(highlight, list):
            result["short_form_highlight"] = " ".join(highlight)
        elif not highlight:
            result["short_form_highlight"] = f"{lesson_title} matters more than most developers think. Learn the basics, avoid common mistakes, and apply it step by step for better results."
        
        if not result.get("hashtags"):
            result["hashtags"] = "#AI #Developer #Programming #Tech"
        return result

    return {
        "long_form_slides": fallback_slides,
        "short_form_highlight": f"{lesson_title} matters more than most developers think. Learn the basics, avoid common mistakes, and apply it step by step for better results.",
        "hashtags": "#AI #Developer #Programming #Tech",
    }

def generate_curriculum(focus: str, extra: str = "") -> dict:
    """Legacy bridge for curriculum generation."""
    prompt = f"Create a 10-lesson curriculum about {focus}. Extra info: {extra}"
    result = ollama_generate(prompt, json_mode=True)
    if result and result.get("lessons"):
        return result
    return {
        "curriculum_title": f"{focus} Essentials",
        "lessons": [
            {"chapter": i + 1, "part": 1, "title": f"{focus} Lesson {i + 1}", "status": "pending", "youtube_id": None}
            for i in range(10)
        ],
    }
