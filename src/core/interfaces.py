from typing import Protocol, Optional, Union, List, Any, Dict
from pathlib import Path

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

class IVideoEngine(Protocol):
    def generate_visuals(self, output_dir: Union[str, Path], video_type: str, slide_content: Optional[Dict[str, Any]] = None,
                         slide_number: int = 1, total_slides: int = 1, is_thumbnail: bool = False, thumbnail_title: str = "") -> str:
        ...
    
    def compose_video(self, slide_paths: List[Union[str, Path]], audio_paths: List[Union[str, Path]], output_path: Union[str, Path], 
                       options: Any) -> str:
        ...
