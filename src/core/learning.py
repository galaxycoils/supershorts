# src/learning.py - Passive Learning (runs AFTER upload, zero impact on generation time)
import json
from pathlib import Path
import datetime

from rich.console import Console
from rich.prompt import Prompt

console = Console()

from src.core.config import PROJECT_ROOT, OLLAMA_MODEL, OLLAMA_TIMEOUT
from src.infrastructure.llm import get_llm_service
import concurrent.futures

LOG_FILE = PROJECT_ROOT / "performance_log.json"
_FAKE_IDS = {"BROWSER_UPLOAD_SUCCESS", "MOCK_VIDEO_ID", "UPLOAD_ATTEMPTED", "BROWSER_UPLOAD_FAILED", "DRY_RUN", "DRY_RUN_ID"}


def log_upload(title: str, video_id: str, mode: str):
    if not video_id or video_id in _FAKE_IDS:
        print(f"⚠️ Skipping log_upload: invalid video_id '{video_id}'")
        return
    try:
        data = json.loads(LOG_FILE.read_text()) if LOG_FILE.exists() else []
        if not isinstance(data, list):
            data = []
    except (json.JSONDecodeError, Exception):
        data = []
    if any(e.get("video_id") == video_id for e in data):
        print(f"⚠️ Skipping duplicate log entry for video_id '{video_id}'")
        return
    entry = {
        "timestamp": str(datetime.datetime.now()),
        "title": title,
        "video_id": video_id,
        "mode": mode  # "brainrot", "educational", "tutorial", "viral"
    }
    data.append(entry)
    LOG_FILE.write_text(json.dumps(data, indent=2))


SUGGESTIONS_FILE = PROJECT_ROOT / "assets" / "learning_suggestions.txt"


def suggest_improvements():
    try:
        raw = json.loads(LOG_FILE.read_text()) if LOG_FILE.exists() else []
    except (json.JSONDecodeError, Exception):
        raw = []
    if len(raw) < 3:
        console.print("[yellow]⚠  Not enough data yet (need at least 3 uploads).[/yellow]")
        return "Not enough data yet (need at least 3 uploads)."
    data = raw[-10:]
    prompt = (
        f"Analyze these uploads: {json.dumps(data)}\n"
        f"Suggest 3 concrete improvements for future videos (titles, backgrounds, hooks, length). Be very brief."
    )
    try:
        with console.status("[cyan]Analyzing upload history via AI…[/cyan]"):
            llm = get_llm_service()
            # Use raw string generation (not JSON mode) for suggestions
            suggestion = llm.generate(prompt, json_mode=False)
            if isinstance(suggestion, dict):
                # Fallback if provider returns object instead of string in non-json mode
                suggestion = json.dumps(suggestion)
                
        console.print("[bold cyan]🧠 Learning Suggestion:[/bold cyan]")
        console.print(suggestion)
        SUGGESTIONS_FILE.parent.mkdir(exist_ok=True, parents=True)
        SUGGESTIONS_FILE.write_text(suggestion)
        return suggestion
    except Exception as e:
        console.print(f"[red]⚠  Learning error: {type(e).__name__}: {e}[/red]")
        return str(e)


def start_learning_mode():
    suggest_improvements()
    console.input("\n  [dim]Press Enter to return…[/dim]")
