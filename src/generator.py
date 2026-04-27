# src/generator.py - Compatibility Bridge & Orchestration
"""
This module serves as a backward-compatible bridge for the legacy main.py and run_workflow.py.
It re-exports symbols from the new modular structure. 
Internal modules should NOT import from this file to avoid circular dependencies.
"""

from typing import Optional, List, Dict, Any, Union
from pathlib import Path

from src.core.config import (
    PROJECT_ROOT, ASSETS_PATH, OUTPUT_DIR, BACKGROUNDS_PATH,
    GAMEPLAY_PATH, VIRAL_GAMEPLAY_PATH, FONT_FILE,
    BACKGROUND_MUSIC_PATH, PEXELS_CACHE_DIR, PEXELS_API_KEY,
    OLLAMA_MODEL, OLLAMA_TIMEOUT, YOUR_NAME, VideoOptions
)

# --- Infrastructure Re-exports ---
from src.infrastructure.llm import ollama_generate, safe_json_parse, get_llm_service
from src.infrastructure.video import (
    get_local_background, get_local_gameplay, 
    get_local_viral_gameplay, get_relevant_pexels_video
)
from src.infrastructure.tts import text_to_speech
from src.infrastructure.browser_uploader import upload_to_youtube_browser
from src.infrastructure.uploader import upload_to_youtube

# --- Engine Re-exports ---
from src.core.interfaces import IVideoEngine, ILLMService
from src.infrastructure.video_engine_impl import (
    StandardVideoEngine, auto_scale_text, draw_wrapped_text
)
from src.engine.video_engine import (
    generate_visuals, compose_video
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
from src.modes.tutorial import start_tutorial_generation
from src.modes.viral import generate_youtube_content_package, start_viral_gameplay_mode
from src.modes.brainrot import run_brainrot_pipeline
from src.modes.tcm_educational import run_tcm_mode, generate_tcm_curriculum
from src.modes.rotgen import run_rotgen_pipeline
from src.modes.studio_ideas import start_idea_generator
from src.modes.clipper import run_video_clipper
from src.core.learning import start_learning_mode

# Legacy Wrappers for testing
def generate_brainrot_topics(count: int = 10, previous_topics: Optional[List[str]] = None, llm_service: Optional[ILLMService] = None) -> List[dict]:
    """Bridge for backward compatibility."""
    llm = llm_service or get_llm_service()
    prompt = f"Generate {count} topic ideas for viral AI shorts."
    result = llm.generate(prompt, json_mode=True)
    return result.get("topics", [])

def generate_brainrot_script(topic: Dict[str, Any], llm_service: Optional[ILLMService] = None) -> Dict[str, Any]:
    from src.modes.brainrot import BrainrotMode
    mode = BrainrotMode(llm_service or get_llm_service(), None, None, None)
    return mode.generate_script(topic)

def render_brainrot_slide(output_dir: Path, text: str, index: int, total: int, video_engine: Optional[IVideoEngine] = None) -> str:
    from src.infrastructure.video_engine_impl import StandardVideoEngine
    engine = video_engine or StandardVideoEngine()
    return engine.generate_brainrot_slide(output_dir, text, index, total)

def create_brainrot_video(image_paths: List[str], audio_paths: List[str], output_path: str, title: str, video_engine: Optional[IVideoEngine] = None) -> str:
    from src.infrastructure.video_engine_impl import StandardVideoEngine
    engine = video_engine or StandardVideoEngine()
    assets = {"images": [Path(p) for p in image_paths], "audio": [Path(p) for p in audio_paths]}
    options = VideoOptions(lesson_title=title, video_type="short")
    return engine.compose_brainrot_video(assets["images"], assets["audio"], output_path, options)

def generate_tutorial_content(topic, llm_service=None):
    from src.modes.tutorial import TutorialMode
    mode = TutorialMode(llm_service or get_llm_service(), None, None, None)
    return mode.generate_script({"title": topic})

def generate_ideas(count=5, llm_service=None):
    from src.modes.studio_ideas import generate_studio_ideas
    return generate_studio_ideas(count, llm_service=llm_service or get_llm_service())

# --- Core Logic Re-exports ---
from src.core.learning import log_upload, suggest_improvements

# --- High-level Orchestration / Legacy Support ---

def generate_lesson_content(lesson_title, series_name=None, style_description=None, llm_service: Optional[ILLMService] = None):
    """Bridge to LLM service with default style logic."""
    llm = llm_service or get_llm_service()
    
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
            "content": f"A common mistake is using {lesson_title} without understanding the tradeoffs. Good engineers adapt ideas to the context they are working in.",
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
    result = llm.generate(prompt, json_mode=True)
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

def generate_curriculum(focus: str = "AI for Developers", extra: str = "", llm_service: Optional[ILLMService] = None) -> dict:
    """Legacy bridge for curriculum generation."""
    llm = llm_service or get_llm_service()
    prompt = f"Create a 10-lesson curriculum about {focus}. Extra info: {extra}"
    result = llm.generate(prompt, json_mode=True)
    if result and result.get("lessons"):
        return result
    return {
        "curriculum_title": f"{focus} Essentials",
        "lessons": [
            {"chapter": i + 1, "part": 1, "title": f"{focus} Lesson {i + 1}", "status": "pending", "youtube_id": None}
            for i in range(10)
        ],
    }
