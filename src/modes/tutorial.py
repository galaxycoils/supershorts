import json
import random
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from tqdm import tqdm

from src.core.config import TUTORIAL_TOPICS, YOUR_NAME, OUTPUT_DIR, OLLAMA_MODEL, OLLAMA_TIMEOUT, VideoOptions
from src.core.interfaces import ILLMService, ITTSService, IVideoUploader, IVideoEngine
from src.core.base_mode import BaseMode
from src.utils.text import clamp_words

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
    def __init__(self, llm_service: ILLMService, tts_service: ITTSService, 
                 uploader_service: IVideoUploader, video_engine: IVideoEngine,
                 dry_run: bool = False, voice: Optional[str] = None):
        super().__init__(llm_service, tts_service, uploader_service, video_engine)
        self.dry_run = dry_run
        self.voice = voice

    def get_pending_topics(self) -> List[Dict[str, Any]]:
        # For tutorial, we mostly pick from TUTORIAL_TOPICS randomly if not provided
        return [{"title": t} for t in random.sample(TUTORIAL_TOPICS, 1)]

    def mark_complete(self, topic: Dict[str, Any], video_id: Optional[str]):
        if self.dry_run:
            print(f"DEBUG: Dry run complete for {topic['title']}")
            return
        if video_id:
            from src.core.learning import log_upload
            log_upload(topic["title"], video_id, "tutorial")

    def generate_script(self, topic: Dict[str, Any]) -> Dict[str, Any]:
        if self.dry_run:
            return {
                "long_slides": [{"title": topic["title"], "content": "Dry run content."}],
                "short_highlight": f"{topic['title']} dry run highlight.",
                "hashtags": "#DryRun",
                "title": topic["title"]
            }

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
        if result and result.get("long_slides"):
            result["long_slides"] = _enforce_slide_content(result["long_slides"], min_words=120)
            result["title"] = topic["title"]
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
            "title": topic["title"]
        }
        return fallback

    def generate_assets(self, content: Dict[str, Any], uid: str) -> Dict[str, List[Path]]:
        long_slides = content.get("long_slides", [])
        slide_audio_paths = []
        for i, slide in enumerate(long_slides):
            txt = f"{slide.get('title', '')}. {slide.get('content', '')}"
            a_path = self.output_dir / f"{uid}_long_audio_{i}.mp3"
            if self.dry_run:
                a_path.touch()
                slide_audio_paths.append(a_path)
            else:
                slide_audio_paths.append(self.tts.text_to_speech(txt, a_path, voice=self.voice))

        slide_dir = self.output_dir / f"{uid}_slides"
        slide_paths = []
        for i, slide in enumerate(long_slides):
            if self.dry_run:
                path = slide_dir / f"slide_{i+1}.png"
                slide_dir.mkdir(exist_ok=True, parents=True)
                path.touch()
            else:
                path = self.video_engine.generate_visuals(slide_dir, 'long', slide, slide_number=i+1, total_slides=len(long_slides))
            slide_paths.append(Path(path))
            
        return {"images": slide_paths, "audio": slide_audio_paths}

    def compose(self, content: Dict[str, Any], assets: Dict[str, List[Path]], output_path: str) -> str:
        if self.dry_run:
            Path(output_path).touch()
            return output_path
        long_script = ' '.join(f"{s.get('title', '')}. {s.get('content', '')}" for s in content.get("long_slides", []))
        self.video_engine.compose_video(assets["images"], assets["audio"], output_path, VideoOptions(
            video_type='long', lesson_title=content.get("title", "Tutorial"), is_tutorial=True, script=long_script
        ))
        return output_path

    def upload(self, content: Dict[str, Any], video_path: str) -> Optional[str]:
        if self.dry_run:
            return "DRY_RUN_ID"
        topic = content.get("title", "Tutorial")
        hashtags = content.get("hashtags", "#Tutorial #Learn #Tech")
        desc = f"New deep dive tutorial: {topic}\n\n{hashtags}\n\nProduced by SuperShorts"
        return self.uploader.upload(Path(video_path), topic, desc, ["tutorial", "ai"])

    def run_tutorial_pipeline(self, topic_str: str):
        """Custom pipeline for tutorial as it produces two videos."""
        content = self.generate_script({"title": topic_str})
        uid = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 1. Long form video
        assets = self.generate_assets(content, uid)
        long_video_path = self.output_dir / f"tutorial_long_{uid}.mp4"
        self.compose(content, assets, str(long_video_path))
        long_id = self.upload(content, str(long_video_path))
        
        # 2. Short highlight video
        short_text = content.get("short_highlight", "")
        short_audio_path = self.output_dir / f"{uid}_short.mp3"
        if self.dry_run:
            short_audio_path.touch()
        else:
            short_audio_path = self.tts.text_to_speech(short_text, short_audio_path, voice=self.voice)
            
        short_slide_dir = self.output_dir / f"{uid}_short_slides"
        if self.dry_run:
            short_slide_dir.mkdir(exist_ok=True, parents=True)
            short_slide = short_slide_dir / "slide_1.png"
            short_slide.touch()
        else:
            short_slide = Path(self.video_engine.generate_visuals(short_slide_dir, 'short',
                                                {"title": topic_str, "content": short_text},
                                                slide_number=1, total_slides=1))
        
        short_video_path = self.output_dir / f"tutorial_short_{uid}.mp4"
        if self.dry_run:
            short_video_path.touch()
        else:
            self.video_engine.compose_video([short_slide], [short_audio_path], str(short_video_path),
                          VideoOptions(video_type='short', lesson_title=topic_str, script=short_text))

        short_id = self.upload({"title": f"{topic_str} #Shorts", "hashtags": content.get("hashtags"), "short_form_highlight": short_text}, str(short_video_path))

        if long_id:
            self.mark_complete({"title": topic_str}, long_id)
        if short_id:
            from src.core.learning import log_upload
            log_upload(topic_str, short_id, "tutorial_short")

def generate_tutorial_content(topic: str, llm_service: Optional[ILLMService] = None) -> Dict[str, Any]:
    """Legacy wrapper for tutorial content generation."""
    llm = llm_service or OllamaLLMService()
    mode = TutorialMode(llm, None, None, None)
    return mode.generate_script({"title": topic})

def start_tutorial_generation(llm_service=None, tts_service=None, uploader_service=None, video_engine=None, dry_run=False, voice=None, topic=None):
    # If running from dashboard, we might not want interactive input
    import os
    topic_str = topic or os.environ.get("TUTORIAL_TOPIC")
    if not topic_str:
        try:
            raw = input("Enter tutorial topic (or press Enter to auto-pick): ").strip()
            topic_str = raw if raw else random.choice(TUTORIAL_TOPICS)
        except EOFError:
            topic_str = random.choice(TUTORIAL_TOPICS)

    mode = TutorialMode(llm_service, tts_service, uploader_service, video_engine, dry_run=dry_run, voice=voice)
    mode.run_tutorial_pipeline(topic_str)
