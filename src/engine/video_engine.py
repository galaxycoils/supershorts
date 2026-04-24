from typing import Optional, List, Dict, Any, Union
from pathlib import Path
from src.core.config import VideoOptions
from src.infrastructure.video_engine_impl import (
    StandardVideoEngine, auto_scale_text, draw_wrapped_text
)
from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, concatenate_videoclips
from src.infrastructure.video import get_relevant_pexels_video, get_local_gameplay

# Singleton instance for backward compatibility
_engine = StandardVideoEngine()

def generate_visuals(output_dir: Union[str, Path], video_type: str, slide_content: Optional[Dict[str, Any]] = None,
                    slide_number: int = 1, total_slides: int = 1, is_thumbnail: bool = False, thumbnail_title: str = "") -> str:
    """Legacy wrapper for StandardVideoEngine.generate_visuals."""
    return _engine.generate_visuals(
        output_dir=output_dir,
        video_type=video_type,
        slide_content=slide_content,
        slide_number=slide_number,
        total_slides=total_slides,
        is_thumbnail=is_thumbnail,
        thumbnail_title=thumbnail_title
    )

def compose_video(slide_paths: List[Union[str, Path]], audio_paths: List[Union[str, Path]], output_path: Union[str, Path], 
                  options: VideoOptions) -> str:
    """Legacy wrapper for StandardVideoEngine.compose_video."""
    return _engine.compose_video(
        slide_paths=slide_paths,
        audio_paths=audio_paths,
        output_path=output_path,
        options=options
    )

# Re-export helpers for backward compatibility
__all__ = ['generate_visuals', 'compose_video', 'auto_scale_text', 'draw_wrapped_text']
