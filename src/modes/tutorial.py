import json
import random
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from tqdm import tqdm

from src.core.config import TUTORIAL_TOPICS, YOUR_NAME, OUTPUT_DIR, OLLAMA_MODEL, OLLAMA_TIMEOUT, VideoOptions
from src.core.interfaces import ILLMService, ITTSService, IVideoUploader
from src.core.base_mode import BaseMode
from src.infrastructure.llm import OllamaLLMService
from src.infrastructure.tts import StandardTTSService, text_to_speech
from src.infrastructure.browser_uploader import YouTubeBrowserUploader
from src.engine.video_engine import generate_visuals, compose_video
from src.utils.text import clamp_words
from src.utils.json import safe_json_parse

_SLIDE_PAD = (
    " This concept is foundational — understanding it deeply will directly affect "
    "the quality of your AI projects. Let's break it down further with a real-world "
    "analogy. Think of it like building a house: you need solid foundations before "
    "you add walls and a roof. The same applies here."
)

def _enforce_slide_content(slides: list, min_words: int = 120) -> list:
    padded = []
    for s in slides:
        content = s.get("content", s.get("title", ""))
        while len(content.split()) < min_words:
            content += _SLIDE_PAD
        words = content.split()
        if len(words) > 200:
            content = " ".join(words[:200])
        padded.append({**s, "content": content.strip()})
    return padded

class TutorialMode(BaseMode):
    def get_pending_topics(self) -> List[Dict[str, Any]]:
        # For tutorial, we mostly pick from TUTORIAL_TOPICS randomly if not provided
        return [{"title": t} for t in random.sample(TUTORIAL_TOPICS, 1)]

    def mark_complete(self, topic: Dict[str, Any], video_id: Optional[str]):
        if video_id:
            from src.core.learning import log_upload
            log_upload(topic["title"], video_id, "tutorial")

    def generate_script(self, topic: Dict[str, Any]) -> Dict[str, Any]:
        print(f"📚 Generating ~10-minute tutorial for: {topic['title']}")
        prompt = f"""You are creating a 10-minute YouTube tutorial on: {topic['title']}
Return ONLY valid JSON:
{{
  "long_slides": [
    {{"title": "slide title here", "content": "detailed explanation..."}}
  ],
  "short_highlight": "spoken script with hook and CTA",
  "hashtags": "#Tutorial #AI #Dev"
}}"""
        result = self.llm.generate(prompt, json_mode=True)
        if result.get("long_slides"):
            result["long_slides"] = _enforce_slide_content(result["long_slides"], min_words=120)
            return result

        fallback = {
            "long_slides": _enforce_slide_content([
                {"title": f"Introduction to {topic['title']}", "content": f"{topic['title']} is a practical concept that helps developers build better systems with clearer reasoning and fewer avoidable mistakes."},
                {"title": "Core Idea", "content": f"The core idea behind {topic['title']} is understanding the tradeoffs, the common patterns, and the places where beginners usually get stuck."},
                {"title": "Real-World Use", "content": f"In real projects, {topic['title']} matters because teams need solutions that are understandable, maintainable, and effective under production constraints."},
                {"title": "Common Mistakes", "content": f"The biggest mistake is copying patterns without understanding the underlying principles. Good engineers adapt ideas to the context they are working in."},
                {"title": "Practical Workflow", "content": f"A practical workflow is to start with the simplest version, test it, measure it, and refine it only when the real constraints justify more complexity."},
            ], min_words=120),
            "short_highlight": f"{topic['title']} becomes much easier when you focus on the fundamentals first, then apply them to real code step by step.",
            "hashtags": "#Tutorial #AI #Dev #LearnToCode",
        }
        return fallback

    def generate_assets(self, content: Dict[str, Any], uid: str) -> Dict[str, List[Path]]:
        # This mode is unique as it creates TWO videos. 
        # For simplicity in BaseMode, we focus on the LONG video as the primary asset.
        long_slides = content.get("long_slides", [])
        slide_audio_paths = []
        for i, slide in enumerate(long_slides):
            txt = f"{slide.get('title', '')}. {slide.get('content', '')}"
            a_path = self.output_dir / f"{uid}_long_audio_{i}.mp3"
            slide_audio_paths.append(self.tts.text_to_speech(txt, a_path))

        slide_dir = self.output_dir / f"{uid}_slides"
        slide_paths = []
        for i, slide in enumerate(long_slides):
            path = generate_visuals(slide_dir, 'long', slide, slide_number=i+1, total_slides=len(long_slides))
            slide_paths.append(Path(path))
            
        return {"images": slide_paths, "audio": slide_audio_paths}

    def compose(self, content: Dict[str, Any], assets: Dict[str, List[Path]], output_path: str) -> str:
        long_script = ' '.join(f"{s.get('title', '')}. {s.get('content', '')}" for s in content.get("long_slides", []))
        compose_video(assets["images"], assets["audio"], output_path, VideoOptions(
            video_type='long', lesson_title=content.get("title", "Tutorial"), is_tutorial=True, script=long_script
        ))
        return output_path

    def upload(self, content: Dict[str, Any], video_path: str) -> Optional[str]:
        topic = content.get("title", "Tutorial")
        hashtags = content.get("hashtags", "#Tutorial #Learn #Tech")
        desc = f"New deep dive tutorial: {topic}\n\n{hashtags}\n\nProduced by SuperShorts"
        return self.uploader.upload(Path(video_path), topic, desc, ["tutorial", "ai"])

def generate_tutorial_content(topic: str, llm_service: Optional[ILLMService] = None) -> dict:
    """Bridge for backward compatibility."""
    mode = TutorialMode(llm_service=llm_service)
    return mode.generate_script({"title": topic})

def start_tutorial_generation(llm_service=None, tts_service=None, uploader_service=None):
    raw = input("Enter tutorial topic (or press Enter to auto-pick): ").strip()
    topic_str = raw if raw else random.choice(TUTORIAL_TOPICS)

    content = generate_tutorial_content(topic_str)
    uid = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    out = OUTPUT_DIR
    out.mkdir(exist_ok=True, parents=True)
    _uploader = uploader_service or YouTubeBrowserUploader()
    hashtags = content.get("hashtags", "#Tutorial #Learn #Tech")

    # --- Long form video ---
    long_slides = content.get("long_slides", [])
    long_audio = []
    for i, slide in enumerate(long_slides):
        txt = f"{slide.get('title', '')}. {slide.get('content', '')}"
        long_audio.append(text_to_speech(txt, out / f"{uid}_long_{i}.mp3"))

    slide_dir = out / f"{uid}_slides"
    long_slides_paths = [Path(generate_visuals(slide_dir, 'long', s, slide_number=i+1, total_slides=len(long_slides)))
                         for i, s in enumerate(long_slides)]

    long_video = out / f"tutorial_long_{uid}.mp4"
    long_script = ' '.join(f"{s.get('title', '')}. {s.get('content', '')}" for s in long_slides)
    compose_video(long_slides_paths, long_audio, str(long_video),
                  VideoOptions(video_type='long', lesson_title=topic_str, is_tutorial=True, script=long_script))

    long_id = _uploader.upload(long_video, topic_str,
                               f"New deep dive tutorial: {topic_str}\n\n{hashtags}\n\nProduced by SuperShorts",
                               ["tutorial", "ai"])

    # --- Short highlight video ---
    short_text = content.get("short_highlight", "")
    short_audio = text_to_speech(short_text, out / f"{uid}_short.mp3")
    short_slide_dir = out / f"{uid}_short_slides"
    short_slide = Path(generate_visuals(short_slide_dir, 'short',
                                        {"title": topic_str, "content": short_text},
                                        slide_number=1, total_slides=1))
    short_video = out / f"tutorial_short_{uid}.mp4"
    compose_video([short_slide], [short_audio], str(short_video),
                  VideoOptions(video_type='short', lesson_title=topic_str, script=short_text))

    short_id = _uploader.upload(short_video, f"{topic_str} #Shorts",
                                f"{short_text}\n\n{hashtags}\n\nProduced by SuperShorts",
                                ["tutorial", "ai", "shorts"])

    from src.core.learning import log_upload
    if long_id:
        log_upload(topic_str, long_id, "tutorial")
    if short_id:
        log_upload(topic_str, short_id, "tutorial_short")
