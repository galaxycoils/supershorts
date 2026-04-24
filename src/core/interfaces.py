from typing import Protocol, Optional, Union, List, Any, Dict
from pathlib import Path
from src.core.config import VideoOptions

class ILLMService(Protocol):
    def generate(self, prompt: str, json_mode: bool = True) -> Union[dict, list]:
        """Generate content from LLM."""
        ...

class ITTSService(Protocol):
    def text_to_speech(self, text: str, output_path: Path, voice: Optional[str] = None) -> Path:
        """Convert text to speech audio."""
        ...

class IVideoUploader(Protocol):
    def upload(self, video_path: Path, title: str, description: str, tags: List[str], thumbnail_path: Optional[Path] = None) -> Optional[str]:
        """Upload video to platform and return video ID."""
        ...

class IBRollSelector(Protocol):
    def select(self, topic: str, video_type: str) -> Optional[str]:
        """Return a local video path for b-roll given a topic, or None on failure."""
        ...

class IVideoEngine(Protocol):
    def generate_visuals(self, output_dir: Union[str, Path], video_type: str, slide_content: Optional[Dict[str, Any]] = None,
                         slide_number: int = 1, total_slides: int = 1, is_thumbnail: bool = False, thumbnail_title: str = "") -> str:
        ...
    
    def compose_video(self, slide_paths: List[Union[str, Path]], audio_paths: List[Union[str, Path]], output_path: Union[str, Path], 
                       options: VideoOptions) -> str:
        ...

    def generate_brainrot_slide(self, output_dir: Union[str, Path], text: str, slide_num: int, total_slides: int, palette: Optional[Dict[str, Any]] = None) -> str:
        ...

    def compose_brainrot_video(self, slide_paths: List[Union[str, Path]], audio_paths: List[Union[str, Path]], output_path: Union[str, Path], options: VideoOptions) -> str:
        ...

    def compose_rotgen_video(self, audio_path: Union[str, Path], output_path: Union[str, Path], options: VideoOptions, custom_char_path: Optional[Path] = None) -> str:
        ...

    def extract_short(self, input_path: Union[str, Path], output_path: Union[str, Path], duration: int = 30) -> str:
        """Extract a vertical short from a longer video."""
        ...
