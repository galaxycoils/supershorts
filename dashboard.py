"""
dashboard.py — SuperShorts Production Suite Dashboard  v3.0
Refactored for componentized UI & RotGen V2 Aesthetic
"""
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import json
import os
import sys
import uuid
import time
import datetime
import threading
import shutil
import re
import io
import requests as _req
from pathlib import Path
from flask import Flask, Response, jsonify, request, stream_with_context, render_template, send_from_directory

# Clean Architecture Imports
from src.infrastructure.llm import OllamaLLMService
from src.infrastructure.tts import StandardTTSService
from src.infrastructure.browser_uploader import YouTubeBrowserUploader
from src.infrastructure.video_engine_impl import StandardVideoEngine
from src.infrastructure.broll_selector import AIBRollSelector

# Mode Runner Imports
from src.modes.tcm_educational import run_tcm_mode
from src.modes.brainrot import run_brainrot_pipeline
from src.modes.rotgen import run_rotgen_pipeline
from src.modes.tutorial import start_tutorial_generation
from src.modes.studio_ideas import start_idea_generator
from src.modes.viral import start_viral_gameplay_mode, generate_youtube_content_package
from src.modes.clipper import run_video_clipper
from src.core.learning import start_learning_mode, suggest_improvements
from main import main_flow

PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

app   = Flask(__name__, template_folder="templates", static_folder="static")
START = time.time()

# ── stdout redirection for threads ───────────────────────────────────────────

class ThreadLocalStdout(io.TextIOBase):
    def __init__(self, original_stdout):
        self.original_stdout = original_stdout
        self.outputs = {} # thread_id -> list of strings
        self.lock = threading.Lock()

    def write(self, s):
        tid = threading.get_ident()
        with self.lock:
            if tid in self.outputs:
                # Split by lines to keep it clean
                for line in s.splitlines():
                    if line.strip():
                        self.outputs[tid].append(line.strip())
            self.original_stdout.write(s)
        return len(s)

    def flush(self):
        self.original_stdout.flush()

    def register_thread(self, tid, output_list):
        with self.lock:
            self.outputs[tid] = output_list

    def unregister_thread(self, tid):
        with self.lock:
            if tid in self.outputs:
                del self.outputs[tid]

thread_local_stdout = ThreadLocalStdout(sys.stdout)
sys.stdout = thread_local_stdout
sys.stderr = thread_local_stdout

# ── job registry ──────────────────────────────────────────────────────────────
JOBS: dict[str, dict] = {}

RUNNERS = {
    "educational": main_flow,
    "brainrot":    run_brainrot_pipeline,
    "rotgen":      run_rotgen_pipeline,
    "tcm":         run_tcm_mode,
    "tutorial":    start_tutorial_generation,
    "viral":       start_viral_gameplay_mode,
    "ideas":       start_idea_generator,
    "learning":    suggest_improvements,
    "package":     generate_youtube_content_package,
    "clipper":     run_video_clipper,
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
    if mode not in RUNNERS: return jsonify({"error": "unknown mode"}), 400
    data = request.json or {}
    
    job_id = str(uuid.uuid4())[:8]
    JOBS[job_id] = {"status": "running", "output": [], "mode": mode}

    def run_job():
        tid = threading.get_ident()
        thread_local_stdout.register_thread(tid, JOBS[job_id]["output"])
        
        # Set up environment for the thread (some modes still use os.environ)
        os.environ["OLLAMA_MODEL"] = data.get("llm_model", "llama3")
        os.environ["YOUR_NAME"] = data.get("author_name", "SuperShorts")
        os.environ["LLM_TEMPERATURE"] = str(data.get("temperature", "0.7"))
        os.environ["LLM_TONE"] = data.get("tone", "educational")
        
        if data.get("hd_mode") == "y": os.environ["RENDER_HD"] = "1"
        if data.get("background"): os.environ["CUSTOM_BG"] = str(PROJECT_ROOT / "assets" / "backgrounds" / data.get("background"))
        if data.get("character"): os.environ["CUSTOM_CHAR"] = str(PROJECT_ROOT / "assets" / "characters" / data.get("character"))
        if data.get("music"): os.environ["CUSTOM_MUSIC"] = str(PROJECT_ROOT / "assets" / "music" / data.get("music"))

        # Instantiate services
        llm = OllamaLLMService()
        tts = StandardTTSService()
        uploader = YouTubeBrowserUploader()
        broll_selector = AIBRollSelector(llm)
        engine = StandardVideoEngine(broll_selector=broll_selector)
        
        count = max(1, min(10, int(data.get("count", 1))))
        dry_run = data.get("dry_run") == "y"
        voice = data.get("voice", "en_US-ryan-high")
        topic = data.get("topic")

        try:
            runner = RUNNERS[mode]
            if mode == "educational":
                runner(lessons_per_run=count, llm_service=llm, tts_service=tts, uploader_service=uploader, video_engine=engine)
            elif mode in ["brainrot", "rotgen"]:
                runner(shorts_per_run=count, llm_service=llm, tts_service=tts, uploader_service=uploader, video_engine=engine, dry_run=dry_run, voice=voice, topic=topic)
            elif mode == "tcm":
                tcm_map = {"1": "Traditional Chinese Medicine", "2": "Eastern Medicine", "3": "Ayurvedic Medicine", "4": "Holistic Wellness"}
                tcm_topic = tcm_map.get(str(data.get("tcm_topic", "1")), "Traditional Chinese Medicine")
                extra = data.get("topic", "")
                runner(llm_service=llm, tts_service=tts, uploader_service=uploader, video_engine=engine, dry_run=dry_run, voice=voice, topic=tcm_topic, extra=extra, count=count)
            elif mode == "tutorial":
                runner(llm_service=llm, tts_service=tts, uploader_service=uploader, video_engine=engine, dry_run=dry_run, voice=voice, topic=topic)
            else:
                # viral, ideas, learning, package, clipper
                runner(llm_service=llm, tts_service=tts, uploader_service=uploader, video_engine=engine, dry_run=dry_run, voice=voice)
            
            JOBS[job_id]["status"] = "finished"
        except Exception as e:
            import traceback
            JOBS[job_id]["output"].append(f"❌ Error: {str(e)}")
            JOBS[job_id]["output"].append(traceback.format_exc())
            JOBS[job_id]["status"] = "failed"
        finally:
            thread_local_stdout.unregister_thread(tid)

    threading.Thread(target=run_job, daemon=True).start()
    return jsonify({"job_id": job_id})

@app.route("/api/disk")
def api_disk():
    return jsonify({
        "output_mb": _dir_mb(PROJECT_ROOT / "output"),
        "pexels_mb": _dir_mb(PROJECT_ROOT / "assets" / "pexels"),
        "assets_mb": _dir_mb(PROJECT_ROOT / "assets")
    })

@app.route("/api/terminate/<job_id>", methods=["POST"])
def api_terminate(job_id):
    if job_id not in JOBS: return jsonify({"error": "not found"}), 404
    job = JOBS[job_id]
    if job["status"] == "running":
        # We can't easily kill a thread in Python. 
        # For now, we just mark it as terminated.
        job["status"] = "terminated"
        return jsonify({"status": "terminated"})
    return jsonify({"error": "job not running"}), 400

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
