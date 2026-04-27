# src/clipper_mode.py - Automatic Video Clipper (Vizard AI Replica)
# Wraps the kirat11X clipper pipeline.
# Setup: copy all .py files from kirat11X repo into src/clipper/
import subprocess
import sys
import datetime
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from src.core.config import PROJECT_ROOT
from src.core.interfaces import IVideoEngine, ILLMService, ITTSService, IVideoUploader
from src.core.base_mode import BaseMode

console = Console()

CLIPPER_DIR   = PROJECT_ROOT / "src" / "clipper"
WORKSPACE     = PROJECT_ROOT / "outputs" / "clipper"
PIPELINE_FILE = CLIPPER_DIR / "run_pipeline.py"


def _check_setup() -> bool:
    """Verify clipper pipeline files exist."""
    if not PIPELINE_FILE.exists():
        console.print(Panel(
            "[red]src/clipper/run_pipeline.py not found.[/red]\n\n"
            "Setup:\n"
            "  1. Clone/download kirat11X clipper repo\n"
            "  2. Copy all [bold].py[/bold] files into [cyan]src/clipper/[/cyan]\n"
            "  3. [cyan]touch src/clipper/__init__.py[/cyan]",
            title="[yellow]⚠  Clipper Not Configured[/yellow]",
            border_style="yellow",
        ))
        return False
    return True


def _run_builtin_fallback(input_path: Path, workspace: Path, video_engine: IVideoEngine) -> Path:
    """Create a single vertical short from the first 30 seconds of a local video."""
    output_dir = workspace / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{input_path.stem}_short_01.mp4"

    if not video_engine:
        raise ValueError("Video engine required for fallback clipper")
        
    video_engine.extract_short(input_path, output_path, duration=30)
    return output_path


def _verify_clipper_dependencies() -> bool:
    """Verify that required heavy libraries are installed for Clipper mode."""
    heavy_deps = ["faster_whisper", "torch", "sentence_transformers", "cv2", "mediapipe"]
    missing = []
    for dep in heavy_deps:
        try:
            if dep == "cv2":
                import cv2
            else:
                __import__(dep)
        except ImportError:
            missing.append(dep)
    
    if missing:
        console.print(Panel(
            f"[red]Missing heavy dependencies for Clipper mode:[/red]\n"
            f"[yellow]{', '.join(missing)}[/yellow]\n\n"
            "Please run: [cyan]pip install -r requirements.txt[/cyan]",
            title="[yellow]⚠  Dependency Error[/yellow]",
            border_style="red",
        ))
        return False
    return True

class ClipperMode(BaseMode):
    """Automatic Video Clipper Mode."""
    def __init__(self, llm_service, tts_service, uploader_service, video_engine, dry_run=False, voice=None):
        super().__init__(llm_service, tts_service, uploader_service, video_engine)
        self.dry_run = dry_run
        self.voice = voice
        self.workspace = WORKSPACE

    def get_pending_topics(self) -> List[Dict[str, Any]]:
        url = os.environ.get("CLIPPER_URL", "")
        if not url:
            try:
                url = Prompt.ask("  [bold]YouTube URL or local video path[/bold]").strip()
            except EOFError:
                url = ""
        if not url:
            console.print("[yellow]  Cancelled.[/yellow]")
            return []
        return [{"url": url}]

    def mark_complete(self, topic: Dict[str, Any], video_id: Optional[str]):
        # Clipper produces multiple videos, logged in produce_video
        pass

    def generate_script(self, topic: Dict[str, Any]) -> Dict[str, Any]:
        return topic

    def generate_assets(self, content: Dict[str, Any], uid: str) -> Dict[str, List[Path]]:
        url = content.get("url")
        self.workspace.mkdir(parents=True, exist_ok=True)
        output_dir = self.workspace / "outputs"
        
        console.print(f"\n[cyan]🎬 Starting clipper pipeline…[/cyan]")
        console.print(f"[dim]  Input : {url}[/dim]")
        console.print(f"[dim]  Output: {self.workspace}[/dim]\n")

        if _check_setup():
            cmd = [
                sys.executable, "run_pipeline.py",
                "--url", url,
                "--workspace", str(self.workspace.resolve()),
            ]
            with console.status("[cyan]Running clipper pipeline (this may take a while)…[/cyan]"):
                result = subprocess.run(
                    cmd,
                    cwd=CLIPPER_DIR.resolve(),
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=600,
                )
            if result.stdout:
                console.print(result.stdout)
        else:
            local_path = Path(url).expanduser()
            if not local_path.exists():
                console.print("[red]❌ Built-in fallback clipper only supports an existing local video path.[/red]")
                return {"videos": []}
            console.print("[yellow]⚠ External clipper pipeline missing. Using built-in fallback clipper.[/yellow]")
            with console.status("[cyan]Creating fallback vertical short…[/cyan]"):
                _run_builtin_fallback(local_path, self.workspace, self.video_engine)
        
        console.print(f"[green]✅ Clipper finished![/green]")
        console.print(f"[dim]📁 Vertical shorts → {output_dir}/[/dim]")
        
        shorts = list(output_dir.glob("*.mp4"))
        return {"videos": shorts}

    def compose(self, content: Dict[str, Any], assets: Dict[str, List[Path]], output_path: str) -> str:
        return "" # Not used in ClipperMode

    def upload(self, content: Dict[str, Any], video_path: str) -> Optional[str]:
        return None # Not used in ClipperMode

    def produce_video(self, topic: Dict[str, Any], count: int, total: int) -> Optional[str]:
        """Override produce_video to handle multiple clips from one URL."""
        uid = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        
        try:
            content = self.generate_script(topic)
            assets = self.generate_assets(content, uid)
            shorts = assets.get("videos", [])
            
            if not shorts:
                console.print("[yellow]⚠ No short videos found in output directory.[/yellow]")
                return None

            console.print(f"\n[bold cyan]📤 Uploading {len(shorts)} shorts to YouTube…[/bold cyan]")
            last_video_id = None
            for i, video_path in enumerate(shorts):
                title = f"Viral Clip {i+1} from {topic.get('url')[:30]} #Shorts"
                desc = f"Generated by SuperShorts v2.9 AI Clipper. Original source: {topic.get('url')}\n\n#Shorts #Viral #AI"
                tags = ["AI", "Shorts", "Viral", "Clipper"]
                
                console.print(f"  [{i+1}/{len(shorts)}] Uploading: {video_path.name}")
                
                if self.dry_run:
                    video_id = "DRY_RUN_ID"
                else:
                    video_id = self.uploader.upload(video_path, title, desc, tags)

                if video_id:
                    from src.core.learning import log_upload
                    log_upload(title, video_id, "clipper")
                    console.print(f"  [green]✅ Uploaded: {video_id}[/green]")
                    last_video_id = video_id
                    if i < len(shorts) - 1:
                        import time, os
                        cooldown = int(os.environ.get("UPLOAD_COOLDOWN_S", "30"))
                        if cooldown > 0:
                            console.print(f"[yellow]⏳ Waiting {cooldown}s before next upload…[/yellow]")
                            time.sleep(cooldown)
                else:
                    console.print(f"  [yellow]⚠ Upload failed for {video_path.name}[/yellow]")
            
            return last_video_id

        except Exception as e:
            console.print(f"❌ Failed to produce clips for '{topic.get('url')}': {e}")
            import traceback
            traceback.print_exc()
            return None

def run_video_clipper(llm_service=None, tts_service=None, uploader_service=None, video_engine=None, dry_run=False, voice=None):
    """Option 10 — Automatic Video Clipper."""
    console.print()
    console.print(Panel(
        "[bold cyan]Automatic Video Clipper[/bold cyan]\n"
        "Convert long YouTube videos / podcasts into viral vertical Shorts",
        border_style="cyan",
        padding=(0, 2),
    ))
    console.print()

    if not _verify_clipper_dependencies():
        return

    mode = ClipperMode(llm_service, tts_service, uploader_service, video_engine, dry_run=dry_run, voice=voice)
    mode.run_pipeline(max_videos=1)
