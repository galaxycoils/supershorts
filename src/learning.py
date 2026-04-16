# src/learning.py - Passive Learning (runs AFTER upload, zero impact on generation time)
import json
from pathlib import Path
import ollama
import datetime

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
        return "Not enough data yet (need at least 3 uploads)."
    data = raw[-10:]
    prompt = f"Analyze these uploads: {json.dumps(data)}\nSuggest 3 concrete improvements for future videos (titles, backgrounds, hooks, length). Be very brief."
    try:
        response = ollama.chat(model="qwen2.5-coder:3b", messages=[{"role": "user", "content": prompt}])
        suggestion = response['message']['content']
        print("🧠 Learning Suggestion:\n", suggestion)
        SUGGESTIONS_FILE.parent.mkdir(exist_ok=True, parents=True)
        SUGGESTIONS_FILE.write_text(suggestion)
        return suggestion
    except Exception as e:
        print(f"⚠️ Learning error: {e}")
        return str(e)

def start_learning_mode():
    suggest_improvements()
    input("Press Enter to return...")
