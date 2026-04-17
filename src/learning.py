# src/learning.py - Passive Learning (runs AFTER upload, zero impact on generation time)
import json
from pathlib import Path
import ollama
import datetime

from rich.console import Console
from rich.prompt import Prompt

console = Console()

LOG_FILE = Path("performance_log.json")


def log_upload(title: str, video_id: str, mode: str):
    entry = {
        "timestamp": str(datetime.datetime.now()),
        "title": title,
        "video_id": video_id,
        "mode": mode  # "brainrot", "educational", "tutorial", "viral"
    }
    try:
        data = json.loads(LOG_FILE.read_text()) if LOG_FILE.exists() else []
        if not isinstance(data, list):
            data = []
    except (json.JSONDecodeError, Exception):
        data = []
    data.append(entry)
    LOG_FILE.write_text(json.dumps(data, indent=2))


SUGGESTIONS_FILE = Path("assets/learning_suggestions.txt")


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
        with console.status("[cyan]Analyzing upload history via Ollama…[/cyan]"):
            response = ollama.chat(model="qwen2.5-coder:3b", messages=[{"role": "user", "content": prompt}])
        suggestion = response['message']['content']
        console.print("[bold cyan]🧠 Learning Suggestion:[/bold cyan]")
        console.print(suggestion)
        SUGGESTIONS_FILE.parent.mkdir(exist_ok=True, parents=True)
        SUGGESTIONS_FILE.write_text(suggestion)
        return suggestion
    except Exception as e:
        console.print(f"[red]⚠  Learning error: {e}[/red]")
        return str(e)


def start_learning_mode():
    suggest_improvements()
    console.input("\n  [dim]Press Enter to return…[/dim]")
