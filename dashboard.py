"""
dashboard.py — SuperShorts Production Suite Dashboard  v3.0
Refactored for componentized UI & RotGen V2 Aesthetic
"""
import json
import os
import sys
import uuid
import time
import datetime
import subprocess
import threading
import shutil
import re
import requests as _req
from pathlib import Path
from flask import Flask, Response, jsonify, request, stream_with_context, render_template, send_from_directory

PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

# Use venv python if present (has all deps), else fall back to current interpreter
_VENV_PY = PROJECT_ROOT / "venv" / "bin" / "python3"
PYTHON = str(_VENV_PY) if _VENV_PY.exists() else sys.executable

app   = Flask(__name__, template_folder="templates", static_folder="static")
START = time.time()

# ── job registry ──────────────────────────────────────────────────────────────
JOBS: dict[str, dict] = {}

MODE_COMMANDS = {
    "educational": "from main import main_flow; main_flow(lessons_per_run={count})",
    "brainrot":    "from src.modes.brainrot import run_brainrot_pipeline; run_brainrot_pipeline({count}, dry_run={dry_run}, voice='{voice}')",
    "rotgen":      "from src.modes.rotgen import run_rotgen_pipeline; run_rotgen_pipeline({count}, dry_run={dry_run}, voice='{voice}')",
    "tcm":         "from src.modes.tcm_educational import run_tcm_mode; run_tcm_mode(dry_run={dry_run}, voice='{voice}')",
    "tutorial":    "from src.generator import start_tutorial_generation; start_tutorial_generation()",
    "viral":       "from src.generator import start_viral_gameplay_mode; start_viral_gameplay_mode()",
    "ideas":       "from src.modes.studio_ideas import start_idea_generator; start_idea_generator()",
    "learning":    "from src.core.learning import suggest_improvements; suggest_improvements()",
    "package":     "from src.generator import generate_youtube_content_package; generate_youtube_content_package()",
    "clipper":     "from src.modes.clipper import run_video_clipper; run_video_clipper()",
}

WORKFLOW_COMMANDS = {
    "daily":         [str(PROJECT_ROOT / "run_workflow.py"), str(PROJECT_ROOT / "workflows/daily.workflow.json")],
    "tcm-weekly":    [str(PROJECT_ROOT / "run_workflow.py"), str(PROJECT_ROOT / "workflows/tcm-weekly.workflow.json")],
    "full-pipeline": [str(PROJECT_ROOT / "run_workflow.py"), str(PROJECT_ROOT / "workflows/full-pipeline.workflow.json")],
}

def _dir_mb(path: Path) -> int:
    if not path.exists(): return 0
    return sum(f.stat().st_size for f in path.glob("**/*") if f.is_file()) >> 20

@app.route("/api/stats")
def api_stats():
    stats = {"uploads_total": 0, "mode_breakdown": {}}
    log_path = PROJECT_ROOT / "performance_log.json"
    if log_path.exists():
        try:
            data = json.loads(log_path.read_text())
            stats["uploads_total"] = len(data.get("uploads", []))
            for u in data.get("uploads", []):
                m = u.get("mode", "unknown")
                stats["mode_breakdown"][m] = stats["mode_breakdown"].get(m, 0) + 1
        except: pass
    return jsonify(stats)

@app.route("/api/health")
def api_health():
    import psutil
    ollama_ok = False
    try:
        r = _req.get("http://localhost:11434/api/tags", timeout=1)
        ollama_ok = r.status_code == 200
    except: pass
    ram_gb = psutil.virtual_memory().available >> 30
    return jsonify({"ollama": ollama_ok, "uptime_s": int(time.time() - START), "ram_gb": ram_gb})

@app.route("/api/ram")
def api_ram():
    import psutil
    v = psutil.virtual_memory()
    return jsonify({"free": v.available >> 30, "total": v.total >> 30, "percent": v.percent})

@app.route("/api/models")
def api_models():
    try:
        r = _req.get("http://localhost:11434/api/tags", timeout=2)
        if r.status_code == 200:
            models = [m["name"] for m in r.json().get("models", [])]
            return jsonify({
                "models": models,
                "recommendations": {
                    "scripting": "qwen2.5-coder:3b",
                    "reasoning": "llama3.2:3b",
                    "creative": "mistral"
                }
            })
    except: pass
    return jsonify({"models": ["llama3", "mistral"], "recommendations": {}})

@app.route("/api/assets")
def api_assets():
    assets = {"backgrounds": [], "characters": [], "music": []}
    bg_dir = PROJECT_ROOT / "assets" / "backgrounds"
    if bg_dir.exists():
        assets["backgrounds"] = [f.name for f in bg_dir.glob("*") if f.is_file() and f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp')]
    char_dir = PROJECT_ROOT / "assets" / "characters"
    if char_dir.exists():
        assets["characters"] = [f.name for f in char_dir.glob("*") if f.is_file() and f.suffix.lower() in ('.png', '.webp')]
    music_dir = PROJECT_ROOT / "assets" / "music"
    if music_dir.exists():
        assets["music"] = [f.name for f in music_dir.glob("*") if f.is_file() and f.suffix.lower() in ('.mp3', '.wav', '.m4a')]
    return jsonify(assets)

@app.route("/api/run/<mode>", methods=["POST"])
def api_run(mode):
    if mode not in MODE_COMMANDS: return jsonify({"error": "unknown mode"}), 400
    data = request.json or {}
    count = max(1, min(10, int(data.get("count", 1))))
    dry_run = "True" if data.get("dry_run") == "y" else "False"
    voice = data.get("voice", "en_US-ryan-high")
    env = os.environ.copy()
    env["OLLAMA_MODEL"] = data.get("llm_model", "llama3")
    env["YOUR_NAME"] = data.get("author_name", "SuperShorts")
    env["LLM_TEMPERATURE"] = str(data.get("temperature", "0.7"))
    if data.get("hd_mode") == "y": env["RENDER_HD"] = "1"
    if data.get("background"): env["CUSTOM_BG"] = str(PROJECT_ROOT / "assets" / "backgrounds" / data.get("background"))
    if data.get("character"): env["CUSTOM_CHAR"] = str(PROJECT_ROOT / "assets" / "characters" / data.get("character"))

    job_id = str(uuid.uuid4())[:8]
    JOBS[job_id] = {"status": "running", "output": [], "mode": mode}

    def run():
        code = MODE_COMMANDS[mode].format(count=count, dry_run=dry_run, voice=voice)
        cmd = [PYTHON, "-c", f"import sys; sys.path.insert(0,'{PROJECT_ROOT}'); {code}"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE, cwd=str(PROJECT_ROOT), env=env, text=True)
        if data.get("stdin_input"): proc.stdin.write(data["stdin_input"]); proc.stdin.flush()
        for line in iter(proc.stdout.readline, ""):
            JOBS[job_id]["output"].append(line.strip())
        proc.wait()
        JOBS[job_id]["status"] = "finished" if proc.returncode == 0 else "failed"

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"job_id": job_id})

@app.route("/api/stream/<job_id>")
def api_stream(job_id):
    if job_id not in JOBS: return Response("event: error\ndata: unknown job\n\n", mimetype="text/event-stream")
    def g():
        idx = 0
        while True:
            if idx < len(JOBS[job_id]["output"]):
                yield f"data: {JOBS[job_id]['output'][idx]}\n\n"
                idx += 1
            elif JOBS[job_id]["status"] != "running":
                yield "data: [DONE]\n\n"; break
            else: time.sleep(0.1)
    return Response(stream_with_context(g()), mimetype="text/event-stream")

@app.route("/api/gallery")
def api_gallery():
    out_dir = PROJECT_ROOT / "output"
    if not out_dir.exists(): return jsonify([])
    vids = []
    for f in out_dir.glob("*.mp4"):
        s = f.stat()
        vids.append({"name": f.name, "size_mb": s.st_size >> 20, "created": datetime.datetime.fromtimestamp(s.st_ctime).isoformat()})
    return jsonify(sorted(vids, key=lambda x: x["created"], reverse=True))

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/output/<filename>")
def serve_output(filename):
    return send_from_directory(PROJECT_ROOT / "output", filename)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    print(f"🎬  SuperShorts Dashboard v3.0  →  http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, threaded=True)
