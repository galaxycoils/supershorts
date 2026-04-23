import abc
import json
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from tqdm import tqdm

from src.core.config import OUTPUT_DIR, VideoOptions
from src.core.interfaces import ILLMService, ITTSService, IVideoUploader
from src.infrastructure.llm import OllamaLLMService
from src.infrastructure.tts import StandardTTSService
from src.infrastructure.browser_uploader import YouTubeBrowserUploader
from src.engine.video_engine import generate_visuals, compose_video

class BaseMode(abc.ABC):
    """
    Abstract base class for all content generation modes.
    Implements the Template Method pattern for the video production pipeline.
    """
    def __init__(self, 
                 llm_service: Optional[ILLMService] = None, 
                 tts_service: Optional[ITTSService] = None, 
                 uploader_service: Optional[IVideoUploader] = None):
        self.llm = llm_service or OllamaLLMService()
        self.tts = tts_service or StandardTTSService()
        self.uploader = uploader_service or YouTubeBrowserUploader()
        self.output_dir = OUTPUT_DIR

    @abc.abstractmethod
    def get_pending_topics(self) -> List[Dict[str, Any]]:
        """Retrieve topics that need processing."""
        pass

    @abc.abstractmethod
    def mark_complete(self, topic: Dict[str, Any], video_id: Optional[str]):
        """Mark a topic as successfully processed."""
        pass

    @abc.abstractmethod
    def generate_script(self, topic: Dict[str, Any]) -> Dict[str, Any]:
        """Generate script content for the topic."""
        pass

    def produce_video(self, topic: Dict[str, Any], count: int, total: int) -> Optional[str]:
        """Produce a single video for a topic (The Template Method)."""
        uid = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        print(f"\n▶️  [{count}/{total}] Topic: '{topic.get('title', 'Unknown')}'")
        
        try:
            # 1. Script Generation
            content = self.generate_script(topic)
            
            # 2. Asset Generation (Visuals & Audio)
            # This part is still mostly mode-specific in how slides are structured,
            # but we can provide a default implementation for standard slides.
            assets = self.generate_assets(content, uid)
            
            # 3. Video Composition
            video_path = self.output_dir / f"video_{uid}.mp4"
            final_path = self.compose(content, assets, str(video_path))
            
            # 4. Upload
            video_id = self.upload(content, final_path)
            
            # 5. Finalize
            self.mark_complete(topic, video_id)
            return video_id

        except Exception as e:
            print(f"❌ Failed to produce video for '{topic.get('title')}': {e}")
            import traceback
            traceback.print_exc()
            return None

    def run_pipeline(self, max_videos: int = 3):
        """Execute the full pipeline for a batch of topics."""
        self.output_dir.mkdir(exist_ok=True, parents=True)
        pending = self.get_pending_topics()
        
        if not pending:
            print("📋 No pending topics found.")
            return

        batch = pending[:max_videos]
        processed = 0
        
        for i, topic in enumerate(batch):
            if self.produce_video(topic, i + 1, len(batch)):
                processed += 1
                
        print(f"✅ Pipeline finished. Processed {processed} video(s).")

    @abc.abstractmethod
    def generate_assets(self, content: Dict[str, Any], uid: str) -> Dict[str, List[Path]]:
        """Mode-specific asset generation (slides, audio)."""
        pass

    @abc.abstractmethod
    def compose(self, content: Dict[str, Any], assets: Dict[str, List[Path]], output_path: str) -> str:
        """Mode-specific video composition."""
        pass

    @abc.abstractmethod
    def upload(self, content: Dict[str, Any], video_path: str) -> Optional[str]:
        """Mode-specific upload logic (tags, descriptions)."""
        pass
