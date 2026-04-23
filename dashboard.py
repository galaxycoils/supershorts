"""
dashboard.py — SuperShorts Production Suite Dashboard  v2.9
Run: python3 dashboard.py
Visit: http://localhost:5050
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
from flask import Flask, Response, jsonify, request, stream_with_context

PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

# Use venv python if present (has all deps), else fall back to current interpreter
_VENV_PY = PROJECT_ROOT / "venv" / "bin" / "python3"
PYTHON = str(_VENV_PY) if _VENV_PY.exists() else sys.executable

app   = Flask(__name__)
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

# Stored as arg lists — avoids split() breaking on paths with spaces
WORKFLOW_COMMANDS = {
    "daily":         [str(PROJECT_ROOT / "run_workflow.py"), str(PROJECT_ROOT / "workflows/daily.workflow.json")],
    "tcm-weekly":    [str(PROJECT_ROOT / "run_workflow.py"), str(PROJECT_ROOT / "workflows/tcm-weekly.workflow.json")],
    "full-pipeline": [str(PROJECT_ROOT / "run_workflow.py"), str(PROJECT_ROOT / "workflows/full-pipeline.workflow.json")],
}

MODE_META = {
    "educational": ("📚", "Educational",  "Curriculum-based long-form + Short"),
    "brainrot":    ("🧠", "Brain Rot",    "Viral sensationalized AI shorts"),
    "rotgen":      ("🎭", "RotGen",       "ByteBot character + gameplay"),
    "tcm":         ("🌿", "TCM",          "Traditional Chinese Medicine series"),
    "tutorial":    ("🎓", "Tutorial",     "~10 min deep-dive + linked Short"),
    "viral":       ("🎮", "Viral",        "Subway Surfers gameplay overlay"),
    "ideas":       ("💡", "YT Ideas",     "Real YT suggestions + Ollama scripts"),
    "learning":    ("📈", "Learning",     "Analyse uploads, suggest improvements"),
    "package":     ("📦", "Content Pkg",  "Expert AI topic → 5-min video"),
    "clipper":     ("✂️",  "Clipper",     "Long video → vertical Shorts"),
}

# ── helpers ───────────────────────────────────────────────────────────────────

def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text()) if path.exists() else default
    except Exception:
        return default

def _dir_mb(p: Path) -> float:
    if not p.exists():
        return 0.0
    total = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
    return round(total / 1_048_576, 1)

def _ram_gb():
    try:
        if sys.platform == "darwin":
            out = subprocess.check_output(["sysctl", "hw.memsize"]).decode()
            total_b = int(out.split(":")[1].strip())
            # Simple free memory estimation on macOS
            vm = subprocess.check_output(["vm_stat"]).decode()
            free_p = int(re.search(r"Pages free:\s+(\d+)", vm).group(1))
            return round(total_b / 1073741824, 1), round(free_p * 4096 / 1073741824, 1)
    except Exception:
        pass
    return 8.0, 4.0

def _stats():
    plan     = _read_json(PROJECT_ROOT / "content_plan.json",    {"lessons": []})
    brainrot = _read_json(PROJECT_ROOT / "brainrot_plan.json",   {"topics": []})
    rotgen   = _read_json(PROJECT_ROOT / "rotgen_plan.json",     {"videos": []})
    log      = _read_json(PROJECT_ROOT / "performance_log.json", [])
    if not isinstance(log, list):
        log = []

    today = datetime.date.today().isoformat()
    uploads_today = sum(1 for e in log if str(e.get("timestamp", "")).startswith(today))

    lessons  = plan.get("lessons", [])
    ed_done  = sum(1 for l in lessons if l.get("status") == "complete")
    br_list  = brainrot.get("topics", [])
    br_done  = sum(1 for t in br_list if t.get("status") == "complete")
    rg_list  = rotgen.get("videos", [])
    rg_done  = sum(1 for v in rg_list if v.get("status") == "complete")

    # 7-day heatmap
    heatmap = {}
    for i in range(6, -1, -1):
        d = (datetime.date.today() - datetime.timedelta(days=i)).isoformat()
        heatmap[d] = 0
    for e in log:
        day = str(e.get("timestamp", ""))[:10]
        if day in heatmap:
            heatmap[day] += 1

    modes: dict[str, int] = {}
    for e in log:
        m = e.get("mode", "unknown")
        modes[m] = modes.get(m, 0) + 1

    total_ram, free_ram = _ram_gb()

    return {
        "educational":    {"done": ed_done, "total": max(len(lessons), 20)},
        "brainrot":       {"done": br_done, "total": len(br_list)},
        "rotgen":         {"done": rg_done, "total": len(rg_list)},
        "uploads_today":  uploads_today,
        "uploads_total":  len(log),
        "mode_breakdown": modes,
        "lessons":        lessons,
        "log_recent":     log[-20:],
        "heatmap":        heatmap,
        "ram":            {"total": total_ram, "free": free_ram},
    }

def _stream_job(job_id: str, proc: subprocess.Popen):
    job = JOBS[job_id]
    for line in iter(proc.stdout.readline, b""):
        job["output"].append(line.decode("utf-8", errors="replace").rstrip())
    proc.wait()
    job["status"] = "done" if proc.returncode == 0 else "error"

# ── routes ────────────────────────────────────────────────────────────────────

@app.route("/api/stats")
def api_stats():
    return jsonify(_stats())

@app.route("/api/log")
def api_log():
    log = _read_json(PROJECT_ROOT / "performance_log.json", [])
    return jsonify(log[-20:] if isinstance(log, list) else [])

@app.route("/api/disk")
def api_disk():
    return jsonify({
        "output_mb": _dir_mb(PROJECT_ROOT / "output"),
        "pexels_mb": _dir_mb(PROJECT_ROOT / "assets" / "pexels"),
        "assets_mb": _dir_mb(PROJECT_ROOT / "assets"),
    })

@app.route("/api/health")
def api_health():
    ollama_ok = False
    try:
        r = _req.get("http://localhost:11434/api/tags", timeout=2)
        ollama_ok = r.status_code == 200
    except Exception:
        pass
    return jsonify({"ollama": ollama_ok, "uptime_s": int(time.time() - START)})

@app.route("/api/terminate/<job_id>", methods=["POST"])
def api_terminate(job_id):
    if job_id not in JOBS:
        return jsonify({"error": "job not found"}), 404
    job = JOBS[job_id]
    if job["status"] == "running" and job["proc"]:
        try:
            job["proc"].terminate()
            job["status"] = "terminated"
            return jsonify({"status": "terminated"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"status": job["status"]})

@app.route("/api/gallery")
def api_gallery():
    output_dir = PROJECT_ROOT / "output"
    if not output_dir.exists():
        return jsonify([])
    videos = []
    for p in sorted(output_dir.glob("*.mp4"), key=os.path.getmtime, reverse=True):
        videos.append({
            "name": p.name,
            "size_mb": round(p.stat().st_size / 1_048_576, 1),
            "created": datetime.datetime.fromtimestamp(p.stat().st_mtime).isoformat()
        })
    return jsonify(videos)

@app.route("/api/workflow-info/<name>")
def api_workflow_info(name):
    if name not in WORKFLOW_COMMANDS:
        return jsonify({"error": "unknown workflow"}), 404
    path = Path(WORKFLOW_COMMANDS[name][1])
    if path.exists():
        return jsonify(json.loads(path.read_text()))
    return jsonify({"error": "file not found"}), 404

@app.route("/api/models")
def api_models():
    try:
        r = _req.get("http://localhost:11434/api/tags", timeout=2)
        if r.status_code == 200:
            return jsonify([m["name"] for m in r.json().get("models", [])])
    except: pass
    return jsonify(["llama3", "mistral", "phi3"])

@app.route("/api/assets")
def api_assets():
    """List available backgrounds, characters, and music."""
    assets = {
        "backgrounds": [],
        "characters": [],
        "music": []
    }
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
    if mode not in MODE_COMMANDS:
        return jsonify({"error": "unknown mode"}), 400
    try:
        data  = request.json or {}
        count = max(1, min(10, int(data.get("count", 1))))
        dry_run = "True" if data.get("dry_run") == "y" else "False"
        voice   = data.get("voice", "en_US-ryan-high")
        
        # Advanced Params
        llm_model = data.get("llm_model", "llama3")
        hd_mode   = "True" if data.get("hd_mode") == "y" else "False"
        author    = data.get("author_name", "SuperShorts")
        
        # New Params
        bg_asset   = data.get("background", "")
        char_asset = data.get("character", "")
        music_asset = data.get("music", "")
        temp       = data.get("temperature", "0.7")
        
    except (ValueError, TypeError):
        count = 1
        dry_run = "False"
        voice   = "en_US-ryan-high"
        llm_model = "llama3"
        hd_mode = "False"
        author = "SuperShorts"
        bg_asset = ""
        char_asset = ""
        music_asset = ""
        temp = "0.7"

    # Injecting environment variable overrides for the subprocess
    env = os.environ.copy()
    env["OLLAMA_MODEL"] = llm_model
    env["YOUR_NAME"] = author
    env["LLM_TEMPERATURE"] = str(temp)
    if hd_mode == "True":
        env["RENDER_HD"] = "1"
    if bg_asset:
        env["CUSTOM_BG"] = str(PROJECT_ROOT / "assets" / "backgrounds" / bg_asset)
    if char_asset:
        env["CUSTOM_CHAR"] = str(PROJECT_ROOT / "assets" / "characters" / char_asset)
    if music_asset:
        env["CUSTOM_MUSIC"] = str(PROJECT_ROOT / "assets" / "music" / music_asset)

    print(f"🚀 Launching {mode} with params: count={count}, dry_run={dry_run}, voice={voice}")
    print(f"   Env overrides: CUSTOM_BG={env.get('CUSTOM_BG')}, CUSTOM_CHAR={env.get('CUSTOM_CHAR')}, LLM_TEMP={env.get('LLM_TEMPERATURE')}")

    code  = MODE_COMMANDS[mode].format(count=count, dry_run=dry_run, voice=voice)
    cmd   = [PYTHON, "-c",
             f"import sys; sys.path.insert(0,'{PROJECT_ROOT}'); {code}"]
    proc  = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             stdin=subprocess.PIPE, cwd=str(PROJECT_ROOT), env=env)
    # Feed stdin: explicit input from UI modal, or auto-accept defaults.
    stdin_input = (request.json or {}).get("stdin_input", None)
    try:
        data = stdin_input.encode() if stdin_input is not None else b"\n" * 30
        proc.stdin.write(data)
        proc.stdin.close()
    except OSError:
        pass
    job_id = str(uuid.uuid4())[:8]
    JOBS[job_id] = {"proc": proc, "output": [], "status": "running", "mode": mode}
    threading.Thread(target=_stream_job, args=(job_id, proc), daemon=True).start()
    return jsonify({"job_id": job_id, "mode": mode, "count": count})

@app.route("/api/workflow/<name>", methods=["POST"])
def api_workflow(name):
    if name not in WORKFLOW_COMMANDS:
        return jsonify({"error": "unknown workflow"}), 400
    cmd  = [PYTHON] + WORKFLOW_COMMANDS[name]  # list already excludes interpreter
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            cwd=str(PROJECT_ROOT))
    job_id = str(uuid.uuid4())[:8]
    JOBS[job_id] = {"proc": proc, "output": [], "status": "running", "mode": f"workflow:{name}"}
    threading.Thread(target=_stream_job, args=(job_id, proc), daemon=True).start()
    return jsonify({"job_id": job_id, "workflow": name})

@app.route("/api/stream/<job_id>")
def api_stream(job_id):
    if job_id not in JOBS:
        return jsonify({"error": "job not found"}), 404
    def generate():
        job  = JOBS[job_id]
        sent = 0
        while True:
            while sent < len(job["output"]):
                yield f"data: {job['output'][sent]}\n\n"
                sent += 1
            if job["status"] != "running":
                yield f"data: [JOB {job_id} {job['status'].upper()}]\n\n"
                break
            time.sleep(0.25)
    return Response(stream_with_context(generate()),
                    mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@app.route("/api/plan-status")
def api_plan_status():
    tcm = _read_json(PROJECT_ROOT / "tcm_plan.json", {})
    tcm_pending = sum(1 for l in tcm.get("lessons", []) if l.get("status") == "pending")
    return jsonify({"tcm_pending": tcm_pending})

@app.route("/api/jobs")
def api_jobs():
    return jsonify({
        jid: {"status": j["status"], "mode": j["mode"], "lines": len(j["output"])}
        for jid, j in JOBS.items()
    })

@app.route("/")
def index():
    return DASHBOARD_HTML

@app.route("/output/<filename>")
def serve_output(filename):
    return stream_with_context(open(PROJECT_ROOT / "output" / filename, "rb"))

# ── HTML ──────────────────────────────────────────────────────────────────────

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SuperShorts — Production Suite</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
:root {
  --bg:      #050505;
  --bg2:     #0a0a0a;
  --bg3:     #121212;
  --bg4:     #1e1e1e;
  --cyan:    #3B82F6; /* RotGen Blue */
  --pink:    #8B5CF6; /* RotGen Purple */
  --coral:   #8B5CF6;
  --mint:    #10B981;
  --red:     #EF4444;
  --text:    #ffffff;
  --dim:     #A1A1AA;
  --border:  #27272A;
  --border2: #3F3F46;
  --sidebar: 260px;
  --r-sm: 8px; --r-md: 12px; --r-lg: 16px;
  --t-fast: 0.15s ease; --t-base: 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  --z-tooltip: 200; --z-topbar: 300; --z-modal: 500;
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
  --glass: rgba(18, 18, 18, 0.7);
  --glass-border: rgba(255, 255, 255, 0.05);
  --accent-gradient: linear-gradient(135deg, #8B5CF6, #3B82F6);
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body { height: 100%; -webkit-font-smoothing: antialiased; }

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: .01ms !important; transition-duration: .01ms !important; }
}

body {
  display: flex;
  background: var(--bg);
  background-image: radial-gradient(circle at 50% -20%, rgba(59,130,246,0.05) 0%, var(--bg) 70%);
  color: var(--text);
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 14px;
  line-height: 1.6;
  overflow: hidden;
}

/* ── ADVANCED MODE TOGGLE ────────────────────────────────────────── */
.advanced-only { display: none !important; }
body.advanced-mode-active .advanced-only { display: block !important; }
body.advanced-mode-active .advanced-only-inline { display: inline-block !important; }
body.advanced-mode-active .advanced-only-flex { display: flex !important; }

/* ── SIDEBAR ─────────────────────────────────────────────────────── */
.sidebar {
  width: var(--sidebar);
  flex-shrink: 0;
  background: var(--bg2);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  position: sticky;
  top: 0;
  height: 100vh;
  overflow-y: auto;
  backdrop-filter: blur(12px);
}

.sidebar-logo {
  padding: 32px 24px 24px;
  border-bottom: 1px solid var(--border);
}

.logo-mark {
  font-family: 'Fira Code', monospace;
  font-weight: 700;
  font-size: 20px;
  letter-spacing: -1px;
  color: var(--text);
}
.logo-mark .accent { 
    color: var(--cyan);
    text-shadow: 0 0 15px rgba(0,200,255,0.4);
}
.logo-mark .slash  { color: var(--dim); margin: 0 2px; }

.logo-sub {
  font-size: 9px;
  letter-spacing: 3px;
  color: var(--dim);
  text-transform: uppercase;
  margin-top: 6px;
  font-weight: 500;
}

.nav-section { padding: 24px 0 12px; }
.nav-label {
  padding: 0 24px 12px;
  font-size: 10px;
  letter-spacing: 2px;
  color: var(--dim);
  text-transform: uppercase;
  font-weight: 700;
}

.nav-btn {
  display: flex;
  align-items: center;
  gap: 14px;
  width: 100%;
  padding: 12px 24px;
  background: transparent;
  border: none;
  color: var(--dim);
  font-size: 14px;
  cursor: pointer;
  transition: all var(--t-base);
  text-align: left;
}
.nav-btn svg { transition: transform var(--t-base); }
.nav-btn:hover { background: var(--bg3); color: var(--text); }
.nav-btn:hover svg { transform: translateX(2px); }
.nav-btn.active { 
    color: var(--cyan); 
    background: linear-gradient(90deg, rgba(0,200,255,0.1) 0%, transparent 100%); 
    border-right: 3px solid var(--cyan); 
}

.wf-section { padding: 4px 12px 8px; }
.wf-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 12px;
  margin-bottom: 6px;
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: var(--r-sm);
  color: var(--text);
  font-family: 'Fira Code', monospace;
  font-size: 11px;
  cursor: pointer;
  transition: all var(--t-base);
  text-align: left;
}
.wf-btn svg { flex-shrink: 0; opacity: .6; transition: all var(--t-base); }
.wf-btn:hover { border-color: var(--coral); background: var(--bg4); transform: translateY(-1px); box-shadow: var(--shadow-md); }
.wf-btn:hover svg { stroke: var(--coral); opacity: 1; transform: rotate(15deg); }
.wf-btn.running { 
    border-color: var(--coral); 
    color: var(--coral); 
    background: rgba(255,107,53,0.1); 
    animation: pulse-border 1.5s ease infinite; 
}
@keyframes pulse-border {
    0% { border-color: var(--coral); box-shadow: 0 0 0 0 rgba(255,107,53,0.4); }
    70% { border-color: var(--coral); box-shadow: 0 0 0 10px rgba(255,107,53,0); }
    100% { border-color: var(--coral); box-shadow: 0 0 0 0 rgba(255,107,53,0); }
}

.sidebar-bottom {
  margin-top: auto;
  padding: 24px;
  border-top: 1px solid var(--border);
  background: rgba(8, 11, 20, 0.5);
}

.ollama-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
  font-size: 11px;
  color: var(--dim);
  font-family: 'Fira Code', monospace;
}
.led {
  width: 10px; height: 10px;
  border-radius: 50%;
  background: var(--dim);
  transition: all 0.5s ease;
}
.led.on  { background: var(--mint); box-shadow: 0 0 12px var(--mint); }
.led.off { background: var(--red); box-shadow: 0 0 12px var(--red); }

.disk-label { font-size: 10px; color: var(--dim); margin-bottom: 8px; letter-spacing: 1.5px; text-transform: uppercase; font-weight: 600; }
.disk-bar   { height: 6px; background: var(--bg4); border-radius: 3px; overflow: hidden; border: 1px solid var(--glass-border); }
.disk-fill  { height: 100%; background: linear-gradient(90deg, var(--cyan), var(--mint)); transition: width 1s cubic-bezier(0.4, 0, 0.2, 1); }
.disk-text  { font-size: 11px; color: var(--dim); margin-top: 8px; font-family: 'Fira Code', monospace; }

/* ── MAIN ────────────────────────────────────────────────────────── */
.main { flex: 1; overflow-y: auto; min-width: 0; }

.topbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 24px;
  padding: 16px 32px;
  border-bottom: 1px solid var(--border);
  background: rgba(12, 17, 29, 0.8);
  backdrop-filter: blur(10px);
  position: sticky;
  top: 0;
  z-index: 100;
}

.producing-badge {
  display: none;
  align-items: center;
  gap: 10px;
  font-size: 11px;
  letter-spacing: 2px;
  color: var(--pink);
  font-weight: 700;
  text-transform: uppercase;
  background: rgba(255, 30, 80, 0.1);
  padding: 6px 14px;
  border-radius: 20px;
  border: 1px solid rgba(255, 30, 80, 0.2);
}
.producing-badge.active { display: flex; animation: fade-in-scale 0.3s ease; }
@keyframes fade-in-scale { from{opacity:0;transform:scale(0.9)} to{opacity:1;transform:scale(1)} }

.producing-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--pink);
  box-shadow: 0 0 12px var(--pink);
  animation: pulse-glow 1.2s ease infinite;
}
@keyframes pulse-glow { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.5;transform:scale(1.2)} }

#clock {
  color: var(--dim);
  font-size: 13px;
  font-family: 'Fira Code', monospace;
  font-weight: 500;
}

.content { padding: 32px 40px; max-width: 1400px; margin: 0 auto; }

h2 {
  font-family: 'Fira Sans', sans-serif;
  font-weight: 700;
  font-size: 12px;
  color: var(--text);
  letter-spacing: 2px;
  margin-bottom: 20px;
  text-transform: uppercase;
  display: flex;
  align-items: center;
}
h2 small {
  font-family: 'Fira Code', monospace;
  font-size: 10px;
  color: var(--dim);
  font-weight: 400;
  letter-spacing: 1px;
  margin-left: 12px;
  text-transform: none;
}

section { margin-bottom: 48px; }

/* ── KPI row ─────────────────────────────────────────────────────── */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 40px;
}

.kpi {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
  padding: 28px;
  position: relative;
  transition: all var(--t-base);
  overflow: hidden;
}
.kpi::before {
    content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 2px;
    background: linear-gradient(90deg, transparent, var(--cyan), transparent);
    opacity: 0; transition: opacity var(--t-base);
}
.kpi:hover { border-color: var(--cyan); transform: translateY(-4px); box-shadow: 0 20px 40px -20px rgba(0,200,255,0.2); }
.kpi:hover::before { opacity: 1; }

.kpi-label {
  font-size: 10px;
  letter-spacing: 2px;
  color: var(--dim);
  text-transform: uppercase;
  margin-bottom: 16px;
  font-weight: 700;
}

.kpi-value {
  font-family: 'Fira Code', monospace;
  font-weight: 700;
  font-size: 44px;
  color: var(--text);
  line-height: 1;
  letter-spacing: -2px;
}

.kpi-sub { font-size: 12px; color: var(--dim); margin-top: 12px; font-weight: 500; }

.kpi-prog { height: 3px; background: var(--bg4); margin-top: 16px; border-radius: 2px; overflow: hidden; }
.kpi-prog-fill { height: 100%; background: var(--cyan); box-shadow: 0 0 10px var(--cyan); transition: width 1.2s cubic-bezier(0.4, 0, 0.2, 1); }

/* ── mode grid ───────────────────────────────────────────── */
.mode-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.slate {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
  padding: 24px;
  cursor: pointer;
  transition: all var(--t-base);
  display: flex;
  flex-direction: column;
}
.slate:hover { 
    border-color: var(--cyan); 
    background: var(--bg3); 
    transform: translateY(-2px);
    box-shadow: 0 12px 24px -12px rgba(0,0,0,0.5);
}

.slate-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px; height: 40px;
  background: var(--bg4);
  border-radius: var(--r-sm);
  margin-bottom: 20px;
  color: var(--cyan);
  border: 1px solid var(--glass-border);
  transition: all var(--t-base);
}
.slate:hover .slate-icon { background: var(--cyan); color: var(--bg); transform: scale(1.1); }

.slate-name {
  font-weight: 700;
  font-size: 16px;
  color: var(--text);
  margin-bottom: 6px;
}

.slate-desc { font-size: 13px; color: var(--dim); margin-bottom: 20px; flex-grow: 1; }

.slate-controls { display: flex; align-items: center; gap: 8px; }

.cnt-btn {
  background: var(--bg4);
  border: 1px solid var(--border2);
  border-radius: var(--r-sm);
  color: var(--text);
  width: 32px; height: 32px;
  font-size: 16px;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all var(--t-fast);
  flex-shrink: 0;
  font-family: 'Fira Code', monospace;
}
.cnt-btn:hover { background: var(--coral); border-color: var(--coral); color: var(--bg); }

.cnt-val {
  font-family: 'Fira Code', monospace;
  font-size: 18px;
  font-weight: 700;
  color: var(--coral);
  width: 28px;
  text-align: center;
  line-height: 1;
}

.run-btn {
  margin-left: auto;
  background: var(--bg4);
  border: 1px solid var(--border2);
  border-radius: var(--r-sm);
  color: var(--text);
  font-family: 'Fira Code', monospace;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 1.5px;
  padding: 6px 14px;
  cursor: pointer;
  transition: all var(--t-fast);
  text-transform: uppercase;
}
.run-btn:hover  { border-color: var(--mint); color: var(--mint); background: rgba(74,222,128,0.1); }
.run-btn:disabled { opacity: .3; cursor: default; }

/* ── terminal ────────────────────────────────────────────────────── */
.terminal {
  background: #04060b;
  border: 1px solid var(--border);
  border-top: 3px solid var(--cyan);
  border-radius: var(--r-sm);
  min-height: 380px;
  max-height: 520px;
  overflow-y: auto;
  padding: 20px;
  font-family: 'Fira Code', monospace;
  font-size: 12px;
  line-height: 1.8;
  box-shadow: 0 20px 50px rgba(0,0,0,0.6);
}

.term-header {
    display: flex; align-items: center; justify-content: space-between; margin-bottom: 2px;
}

.term-clear {
  background: transparent;
  border: 1px solid var(--border2);
  border-radius: 4px;
  color: var(--dim);
  font-family: 'Fira Code', monospace;
  font-size: 10px;
  padding: 2px 8px;
  cursor: pointer;
  transition: all var(--t-fast);
}
.term-clear:hover { border-color: var(--text); color: var(--text); }

/* ── gallery ─────────────────────────────────────────────────────── */
.gallery-item {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: var(--r-md);
    padding: 16px;
    transition: all var(--t-base);
    position: relative;
    overflow: hidden;
}
.gallery-item:hover { 
    transform: translateY(-4px); 
    border-color: var(--cyan);
    box-shadow: 0 10px 20px -10px rgba(0,200,255,0.3);
}

/* ── toggle switch ───────────────────────────────────────────────── */
.switch {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 22px;
}
.switch input { opacity: 0; width: 0; height: 0; }
.slider {
  position: absolute;
  cursor: pointer;
  inset: 0;
  background-color: var(--bg4);
  transition: .4s;
  border-radius: 22px;
  border: 1px solid var(--border2);
}
.slider:before {
  position: absolute;
  content: "";
  height: 14px;
  width: 14px;
  left: 3px;
  bottom: 3px;
  background-color: var(--dim);
  transition: .4s;
  border-radius: 50%;
}
input:checked + .slider { background-color: rgba(0,200,255,0.2); border-color: var(--cyan); }
input:checked + .slider:before { transform: translateX(22px); background-color: var(--cyan); }

/* ── MODAL ────────────────────────────────────────────────────────── */
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,.8);
  backdrop-filter: blur(4px);
  z-index: var(--z-modal);
  display: flex; align-items: center; justify-content: center;
  animation: fade-in .2s ease;
}
@keyframes fade-in { from{opacity:0} to{opacity:1} }

.modal {
  background: var(--bg2);
  border: 1px solid var(--border2);
  border-radius: var(--r-lg);
  box-shadow: var(--shadow-lg);
  width: 900px;
  max-width: calc(100vw - 40px);
  max-height: calc(100vh - 80px);
  overflow-y: auto;
  padding: 0;
  animation: slide-up .2s ease;
  display: flex;
  flex-direction: column;
}
@keyframes slide-up { from{transform:translateY(20px);opacity:0} to{transform:translateY(0);opacity:1} }

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border);
}
.modal-title {
  font-family: 'Inter', sans-serif;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--text);
}
.modal-title span { color: var(--coral); margin-right: 8px; }
.modal-close {
  background: transparent;
  border: 1px solid var(--border2);
  border-radius: var(--r-sm);
  color: var(--dim);
  width: 28px; height: 28px;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px;
  font-family: 'Fira Code', monospace;
  transition: all var(--t-fast);
}
.modal-close:hover { border-color: var(--red); color: var(--red); background: rgba(239, 68, 68, 0.1); }

.kpi {
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  padding: 28px;
  position: relative;
  transition: all var(--t-base);
  overflow: hidden;
  box-shadow: var(--shadow-md);
}
.kpi:hover { border-color: var(--cyan); transform: translateY(-4px); box-shadow: 0 20px 40px -20px rgba(59,130,246,0.3); }

.slate {
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  padding: 24px;
  cursor: pointer;
  transition: all var(--t-base);
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-md);
}
.slate:hover { 
    border-color: var(--cyan); 
    background: var(--bg4); 
    transform: translateY(-2px);
    box-shadow: 0 12px 24px -12px rgba(0,0,0,0.5);
}

.two-col {
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  gap: 32px;
  align-items: start;
}

/* ── MODAL ────────────────────────────────────────────────────────── */
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,.85);
  backdrop-filter: blur(8px);
  z-index: var(--z-modal);
  display: flex; align-items: center; justify-content: center;
  animation: fade-in .2s ease;
}

.modal {
  background: var(--bg2);
  border: 1px solid var(--border2);
  border-radius: var(--r-lg);
  box-shadow: 0 20px 40px -10px rgba(0,0,0,0.8);
  width: 1000px;
  max-width: calc(100vw - 40px);
  max-height: calc(100vh - 80px);
  overflow-y: auto;
  padding: 0;
  animation: slide-up .25s cubic-bezier(0.2, 0.8, 0.2, 1);
  display: flex;
  flex-direction: column;
}

#modal-body {
  padding: 0;
  display: flex;
  overflow-x: auto;
}

.modal-pane {
  flex: 1;
  min-width: 300px;
  padding: 24px;
  border-right: 1px solid var(--border);
  background: var(--bg2);
}
.modal-pane:last-child { border-right: none; background: var(--bg); }

.modal-header {

.modal-section { margin-bottom: 18px; }
.modal-section-label {
  font-size: 10px;
  letter-spacing: 2px;
  color: var(--dim);
  text-transform: uppercase;
  font-weight: 700;
  margin-bottom: 10px;
  font-family: 'Fira Code', monospace;
}

/* Clickable option cards */
.opt-cards { display: flex; flex-direction: column; gap: 6px; }
.opt-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: var(--r-sm);
  background: var(--bg3);
  cursor: pointer;
  transition: all var(--t-fast);
  user-select: none;
}
.opt-card:hover { border-color: var(--cyan); transform: translateY(-1px); }
.opt-card.selected { border-color: var(--cyan); background: rgba(59, 130, 246, 0.1); box-shadow: 0 0 10px rgba(59,130,246,0.2); }
.opt-dot {
  width: 12px; height: 12px;
  border-radius: 50%;
  border: 2px solid var(--dim);
  flex-shrink: 0;
  transition: all var(--t-fast);
}
.opt-card.selected .opt-dot { border-color: var(--cyan); background: var(--cyan); }
.opt-label { font-size: 13px; color: var(--text); font-family: 'Inter', sans-serif; }

/* Text / number fields */
.field { margin-bottom: 16px; }
.field label {
  display: block;
  font-size: 10px;
  letter-spacing: 2px;
  color: var(--dim);
  text-transform: uppercase;
  font-weight: 700;
  margin-bottom: 8px;
  font-family: 'Fira Code', monospace;
}
.field input[type=text], .field input[type=number], .field input[type=url] {
  width: 100%;
  background: var(--bg3);
  border: 1px solid var(--border2);
  border-radius: var(--r-sm);
  color: var(--text);
  font-family: 'Fira Code', monospace;
  font-size: 13px;
  padding: 10px 12px;
  outline: none;
  transition: all var(--t-fast);
}
.field input:focus { border-color: var(--cyan); box-shadow: 0 0 0 2px rgba(59,130,246,0.2); }
.field input::placeholder { color: var(--dim); }
.field input[type=number] { width: 100px; }
.field-hint { font-size: 11px; color: var(--dim); margin-top: 6px; font-family: 'Fira Code', monospace; }

/* Toggle row (yes/no) */
.toggle-row { display: flex; gap: 8px; }
.toggle-btn {
  flex: 1;
  padding: 10px;
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: var(--r-sm);
  color: var(--text);
  font-family: 'Fira Code', monospace;
  font-size: 12px;
  cursor: pointer;
  text-align: center;
  transition: all var(--t-fast);
}
.toggle-btn:hover { border-color: var(--cyan); }
.toggle-btn.selected { border-color: var(--cyan); color: var(--text); background: var(--accent-gradient); box-shadow: 0 4px 10px rgba(59,130,246,0.3); }

.modal-footer {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  padding: 20px 24px;
  border-top: 1px solid var(--border);
  background: var(--bg3);
}
.btn-cancel {
  background: transparent;
  border: 1px solid var(--border2);
  border-radius: var(--r-sm);
  color: var(--dim);
  font-family: 'Fira Code', monospace;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 1px;
  padding: 8px 20px;
  cursor: pointer;
  transition: all var(--t-fast);
  text-transform: uppercase;
}
.btn-cancel:hover { border-color: var(--text); color: var(--text); }
.btn-launch {
  background: var(--accent-gradient);
  border: none;
  border-radius: var(--r-sm);
  color: #fff;
  font-family: 'Fira Code', monospace;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 2px;
  padding: 8px 24px;
  cursor: pointer;
  transition: all var(--t-fast);
  text-transform: uppercase;
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.4);
}
.btn-launch:hover { opacity: .9; transform: translateY(-1px); box-shadow: 0 6px 15px rgba(139, 92, 246, 0.6); }
.btn-launch:disabled { opacity: .35; cursor: default; transform: none; box-shadow: none; }

/* ── RESPONSIVENESS ────────────────────────────────────────────────── */
@media (max-width: 1200px) {
  .sidebar { width: 80px; }
  .nav-btn { padding: 12px; justify-content: center; }
  .nav-btn span, .logo-sub, .nav-label, .sidebar-bottom, .logo-mark span:not(.accent) { display: none; }
  .logo-mark { font-size: 24px; text-align: center; }
  .main { margin-left: 0; }
}

@media (max-width: 900px) {
  .kpi-row { grid-template-columns: repeat(2, 1fr); }
  .two-col { grid-template-columns: 1fr; }
  .modal { width: 95%; max-height: 90vh; }
  #modal-body { display: grid; grid-template-columns: 1fr; }
}

@media (max-width: 600px) {
  .kpi-row { grid-template-columns: 1fr; }
  .topbar { padding: 12px 20px; }
  .content { padding: 20px; }
}
</style>
</head>
<body>

<aside class="sidebar" role="navigation" aria-label="Main navigation">

  <div class="sidebar-logo">
    <div class="logo-mark">SUPER<span class="slash">/</span><span class="accent">SHORTS</span></div>
    <div class="logo-sub">Production Suite</div>
  </div>

  <nav class="nav-section">
    <div class="nav-label">Navigate</div>
    <button class="nav-btn active" onclick="navTo('#kpis',this)" aria-label="Dashboard">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/></svg>
      Dashboard
    </button>
    <button class="nav-btn" onclick="navTo('#productions',this)" aria-label="Productions">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="m22 8-6 4 6 4V8Z"/><rect width="14" height="12" x="2" y="6" rx="2"/></svg>
      Productions
    </button>
    <button class="nav-btn" onclick="navTo('#plan',this)" aria-label="Content Plan">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><line x1="8" x2="21" y1="6" y2="6"/><line x1="8" x2="21" y1="12" y2="12"/><line x1="8" x2="21" y1="18" y2="18"/><line x1="3" x2="3.01" y1="6" y2="6"/><line x1="3" x2="3.01" y1="12" y2="12"/><line x1="3" x2="3.01" y1="18" y2="18"/></svg>
      Content Plan
    </button>
    <button class="nav-btn" onclick="navTo('#log',this)" aria-label="Upload Log">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" x2="12" y1="3" y2="15"/></svg>
      Upload Log
    </button>
    <button class="nav-btn" onclick="navTo('#gallery',this);refreshGallery()" aria-label="Gallery">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/></svg>
      Gallery
    </button>
    <button class="nav-btn" onclick="navTo('#settings',this)" aria-label="Settings">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>
      Settings
    </button>
  </nav>

  <div class="nav-section">
    <div class="nav-label">Workflows</div>
    <div class="wf-section">
      <button class="wf-btn" id="wf-daily" onclick="runWorkflow('daily')" aria-label="Run daily workflow">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/></svg>
        daily · 9am
      </button>
      <button class="wf-btn" id="wf-tcm-weekly" onclick="runWorkflow('tcm-weekly')" aria-label="Run TCM weekly workflow">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10z"/><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/></svg>
        tcm · weekly
      </button>
      <button class="wf-btn" id="wf-full-pipeline" onclick="runWorkflow('full-pipeline')" aria-label="Run full pipeline workflow">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
        full · pipeline
      </button>
    </div>
  </div>

    <div class="sidebar-bottom">
    <div class="ollama-row">
      <div class="led" id="ollama-led" role="status" aria-label="Ollama connection status"></div>
      <span id="ollama-txt">ollama —</span>
    </div>
    <div class="disk-label">System RAM</div>
    <div class="disk-bar"><div class="disk-fill" id="ram-fill" style="width:0%; background:var(--pink)"></div></div>
    <div class="disk-text" id="ram-text">— gb free</div>
    
    <div class="disk-label" style="margin-top:12px">Output Disk</div>
    <div class="disk-bar"><div class="disk-fill" id="disk-fill" style="width:0%"></div></div>
    <div class="disk-text" id="disk-text">— mb</div>
  </div>

</aside>

<div class="main" role="main">

  <div class="topbar">
    <div class="producing-badge" id="producing-badge" role="status">
      <div class="producing-dot"></div>now producing
    </div>
    <div id="clock" aria-live="off">--:--:--</div>
  </div>

  <div class="content">

    <div class="kpi-row" id="kpis">
      <div class="kpi">
        <div class="kpi-label">Total Uploads</div>
        <div class="kpi-value" id="kv-total" data-target="0">0</div>
        <div class="kpi-sub" id="ks-today">— today</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">Educational</div>
        <div class="kpi-value" id="kv-ed" data-target="0">0</div>
        <div class="kpi-sub" id="ks-ed">of 20 lessons</div>
        <div class="kpi-prog"><div class="kpi-prog-fill" id="kp-ed" style="width:0%"></div></div>
      </div>
      <div class="kpi">
        <div class="kpi-label">Brain Rot</div>
        <div class="kpi-value" id="kv-br" data-target="0">0</div>
        <div class="kpi-sub" id="ks-br">topics done</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">RotGen</div>
        <div class="kpi-value" id="kv-rg" data-target="0">0</div>
        <div class="kpi-sub" id="ks-rg">videos done</div>
      </div>
    </div>

    <section>
      <h2>This Week <small>uploads / day</small></h2>
      <div class="heatmap" id="heatmap"></div>
    </section>

    <div class="two-col" id="productions">
      <section>
        <h2>Productions <small>select · run</small></h2>
        <div class="mode-grid" id="mode-grid"></div>
      </section>
      <section>
        <div class="term-header">
          <h2>Live Output <small>sse</small></h2>
          <div style="display:flex; gap:8px">
            <button class="term-clear" id="stop-btn" onclick="terminateActiveJob()" style="display:none; border-color:var(--red); color:var(--red)">stop ■</button>
            <button class="term-clear" onclick="termClear()" aria-label="Clear terminal">clr</button>
          </div>
        </div>
        <div class="terminal" id="terminal" role="log" aria-live="polite">
          <div class="tl sys">awaiting production order<span class="term-cursor"></span></div>
        </div>
      </section>
    </div>

    <section id="gallery">
      <h2>Recent Productions <small>gallery</small></h2>
      <div id="gallery-grid" style="display:grid; grid-template-columns:repeat(auto-fill, minmax(200px, 1fr)); gap:16px">
        <div class="tl sys">Gallery loading...</div>
      </div>
    </section>

    <section id="settings">
      <h2>Global Settings <small>persistence</small></h2>
      <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap:20px">
        <div class="slate" style="cursor:default">
          <div class="field">
            <label>Author Name</label>
            <input type="text" id="global-author" value="SuperShorts" onchange="saveGlobalSettings()">
          </div>
          <div class="field">
            <label>Ollama Model (Global)</label>
            <select id="global-model" style="width:100%; background:var(--bg3); color:var(--text); border:1px solid var(--border2); padding:10px; border-radius:var(--r-sm)" onchange="saveGlobalSettings()">
              <option value="llama3">llama3</option>
              <option value="mistral">mistral</option>
              <option value="phi3">phi3</option>
            </select>
          </div>
        </div>
        
        <div class="slate" style="cursor:default">
          <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:16px">
            <div>
                <div style="font-weight:700; font-size:14px; color:var(--text)">Advanced View Mode</div>
                <div style="font-size:11px; color:var(--dim)">Expose additional knobs and parameters</div>
            </div>
            <label class="switch">
              <input type="checkbox" id="adv-toggle" onchange="toggleAdvancedMode()">
              <span class="slider"></span>
            </label>
          </div>
          <div style="display:flex; align-items:center; justify-content:space-between">
            <div>
                <div style="font-weight:700; font-size:14px; color:var(--text)">Auto-Refresh Stats</div>
                <div style="font-size:11px; color:var(--dim)">Update dashboard KPIs every 15s</div>
            </div>
            <label class="switch">
              <input type="checkbox" checked disabled>
              <span class="slider"></span>
            </label>
          </div>
        </div>
      </div>
    </section>

    <section id="plan">
      <h2>Content Plan <small>curriculum</small></h2>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Ch</th><th>Title</th><th>Status</th><th>YouTube</th></tr></thead>
          <tbody id="plan-tbody"></tbody>
        </table>
      </div>
    </section>

    <div class="two-col" id="log">
      <section>
        <h2>Upload Log <small>last 20</small></h2>
        <div class="table-wrap">
          <table>
            <thead><tr><th>Time</th><th>Mode</th><th>Title</th></tr></thead>
            <tbody id="log-tbody"></tbody>
          </table>
        </div>
      </section>
      <section>
        <h2>Mode Breakdown</h2>
        <div class="breakdown" id="breakdown"></div>
      </section>
    </div>

  </div>
</div>

<!-- ── Config Modal ──────────────────────────────────────────── -->
<div class="modal-overlay" id="modal-overlay" style="display:none" role="dialog" aria-modal="true" aria-labelledby="modal-title">
  <div class="modal" id="modal">
    <div class="modal-header">
      <div class="modal-title" id="modal-title-el"></div>
      <button class="modal-close" onclick="closeModal()" aria-label="Close modal">✕</button>
    </div>
    <div id="modal-body"></div>
    <div class="modal-footer">
      <button class="btn-cancel" onclick="closeModal()">cancel</button>
      <button class="btn-launch" id="btn-modal-launch" onclick="launchFromModal()">launch ▶</button>
    </div>
  </div>
</div>

<script>
// ── SVG Icons (Lucide) ────────────────────────────────────────────
const ICONS = {
  educational: '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>',
  brainrot:    '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
  rotgen:      '<path d="M20.2 6 3 11l-.9-2.4c-.3-1.1.3-2.2 1.3-2.6l13.5-4c1.1-.3 2.2.3 2.6 1.3Z"/><path d="m6.2 5.3 3.1 3.9"/><path d="m12.4 3.4 3.1 3.9"/><path d="M3 11h18v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/>',
  tcm:         '<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10z"/><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/>',
  tutorial:    '<circle cx="12" cy="12" r="10"/><polygon points="10 8 16 12 10 16 10 8"/>',
  viral:       '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>',
  ideas:       '<path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"/><path d="M9 18h6"/><path d="M10 22h4"/>',
  learning:    '<line x1="18" x2="18" y1="20" y2="10"/><line x1="12" x2="12" y1="20" y2="4"/><line x1="6" x2="6" y1="20" y2="14"/>',
  package:     '<path d="m7.5 4.27 9 5.15"/><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/>',
  clipper:     '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><line x1="20" x2="8.12" y1="4" y2="15.88"/><line x1="14.47" x2="20" y1="14.48" y2="20"/><line x1="8.12" x2="12" y1="8.12" y2="12"/>',
};

function svgIcon(id, size=13) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[id]||''}</svg>`;
}

// ── State ─────────────────────────────────────────────────────────
const MODES = [
  ["educational","Educational","Curriculum long-form + Short"],
  ["brainrot",   "Brain Rot",  "Viral sensationalized AI shorts"],
  ["rotgen",     "RotGen",     "ByteBot character + gameplay"],
  ["tcm",        "TCM",        "Traditional Chinese Medicine"],
  ["tutorial",   "Tutorial",   "~10 min deep-dive + linked Short"],
  ["viral",      "Viral",      "Subway Surfers gameplay overlay"],
  ["ideas",      "YT Ideas",   "Real YT suggestions + scripts"],
  ["learning",   "Learning",   "Analyse uploads, suggest tips"],
  ["package",    "Content Pkg","Expert AI → 5-min video"],
  ["clipper",    "Clipper",    "Long video → vertical Shorts"],
];

const counts = {};
MODES.forEach(([id]) => counts[id] = 1);
let activeJobs = new Set();
let currentEvt = null;

// ── Scroll nav ────────────────────────────────────────────────────
function navTo(sel, btn) {
  const el = document.querySelector(sel);
  if (el) el.scrollIntoView({behavior:'smooth', block:'start'});
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
}

// ── Build mode grid ───────────────────────────────────────────────
function buildModeGrid() {
  document.getElementById('mode-grid').innerHTML = MODES.map(([id,name,desc]) => `
    <div class="slate" id="slate-${id}">
      <div class="slate-icon">${svgIcon(id)}</div>
      <div class="slate-name">${name}</div>
      <div class="slate-desc">${desc}</div>
      <div class="slate-controls">
        <button class="cnt-btn" onclick="adj('${id}',-1)" aria-label="Decrease count">−</button>
        <div class="cnt-val" id="cv-${id}" aria-live="polite">1</div>
        <button class="cnt-btn" onclick="adj('${id}',1)" aria-label="Increase count">+</button>
        <button class="run-btn" id="rb-${id}" onclick="runMode('${id}')">run ▶</button>
      </div>
    </div>
  `).join('');
}

function adj(id, d) {
  counts[id] = Math.max(1, Math.min(10, (counts[id]||1) + d));
  document.getElementById('cv-'+id).textContent = counts[id];
}

// ── Run mode ──────────────────────────────────────────────────────
async function runMode(id) {
  // Interactive modes open a config modal first
  if (NEEDS_CONFIG.has(id)) { openModal(id); return; }

  const btn = document.getElementById('rb-'+id);
  btn.textContent = '…'; btn.classList.add('active'); btn.disabled = true;

  try {
    const res = await fetch(`/api/run/${id}`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({count: counts[id]})
    });
    const {job_id} = await res.json();
    openStream(job_id, () => {
      btn.textContent = 'run ▶'; btn.classList.remove('active'); btn.disabled = false;
      refreshStats();
    });
  } catch(e) {
    termLine(`error: ${e.message}`, 'err');
    btn.textContent = 'run ▶'; btn.classList.remove('active'); btn.disabled = false;
  }
}

// ── Run workflow ──────────────────────────────────────────────────
async function runWorkflow(name) {
  const btn = document.getElementById('wf-'+name);
  btn.classList.add('running');

  try {
    const res = await fetch(`/api/workflow/${name}`, {method:'POST'});
    const {job_id} = await res.json();
    openStream(job_id, () => {
      btn.classList.remove('running');
      refreshStats();
    });
  } catch(e) {
    termLine(`error: ${e.message}`, 'err');
    btn.classList.remove('running');
  }
}

let lastJobId = null;

// ── SSE stream ────────────────────────────────────────────────────
function openStream(job_id, onDone) {
  lastJobId = job_id;
  termClear();
  termLine(`▶ job ${job_id} starting…`, 'prompt');
  document.getElementById('producing-badge').classList.add('active');
  document.getElementById('stop-btn').style.display = 'block';
  activeJobs.add(job_id);

  if (currentEvt) currentEvt.close();
  currentEvt = new EventSource(`/api/stream/${job_id}`);

  currentEvt.onmessage = e => {
    const line = e.data;
    if (line.startsWith('[JOB')) {
      const ok = line.includes('DONE');
      termLine(line, ok ? 'done' : 'err');
      finishJob(job_id, onDone);
    } else {
      const cls = (line.includes('❌')||line.includes('ERROR')) ? 'err'
                : (line.includes('✅')||line.includes('✓')) ? 'ok'
                : '';
      termLine(line, cls);
    }
  };
  currentEvt.onerror = () => finishJob(job_id, onDone);
}

function finishJob(job_id, onDone) {
    if (currentEvt) currentEvt.close();
    activeJobs.delete(job_id);
    if (activeJobs.size === 0) {
        document.getElementById('producing-badge').classList.remove('active');
        document.getElementById('stop-btn').style.display = 'none';
    }
    if (onDone) onDone();
    refreshGallery();
}

async function terminateActiveJob() {
    if (!lastJobId) return;
    termLine(`⏹ Terminating job ${lastJobId}...`, 'err');
    await fetch(`/api/terminate/${lastJobId}`, {method:'POST'});
}

async function refreshGallery() {
    const videos = await fetch('/api/gallery').then(r=>r.json()).catch(()=>[]);
    const grid = document.getElementById('gallery-grid');
    if (!videos.length) {
        grid.innerHTML = '<div class="tl sys">No videos produced yet.</div>';
        return;
    }
    grid.innerHTML = videos.map(v => `
        <div class="gallery-item">
            <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
                <span class="badge" style="background:var(--accent-gradient); color:#fff; padding:2px 8px; font-size:9px; border-radius:12px; font-weight:700;">MP4</span>
                <span style="font-size:10px; color:var(--dim);">${v.size_mb} MB</span>
            </div>
            <div style="font-family:'Inter',sans-serif; font-size:13px; font-weight:600; margin-bottom:6px; color:var(--text); word-break:break-all;">${v.name}</div>
            <div style="font-size:10px; color:var(--dim); font-family:'Fira Code',monospace; margin-bottom:16px;">${v.created.slice(0,16).replace('T',' ')}</div>
            <div style="display:flex; gap:8px;">
                <a href="/output/${v.name}" target="_blank" class="run-btn" style="flex:1; text-align:center; text-decoration:none; background:rgba(59,130,246,0.1); border-color:var(--cyan); color:var(--cyan);">Play ▶</a>
                <a href="/output/${v.name}" download class="run-btn" style="text-decoration:none; border-color:var(--border2); color:var(--dim);">DL ↓</a>
            </div>
        </div>
    `).join('');
}

function saveGlobalSettings() {
    const settings = {
        author: document.getElementById('global-author').value,
        model: document.getElementById('global-model').value,
        advanced: document.getElementById('adv-toggle').checked
    };
    localStorage.setItem('supershorts_settings', JSON.stringify(settings));
    termLine(`⚙️ Settings saved to local storage.`, 'ok');
}

function loadGlobalSettings() {
    const s = JSON.parse(localStorage.getItem('supershorts_settings') || '{}');
    if (s.author) document.getElementById('global-author').value = s.author;
    if (s.model)  document.getElementById('global-model').value  = s.model;
    if (s.advanced) {
        document.getElementById('adv-toggle').checked = true;
        document.body.classList.add('advanced-mode-active');
    }
}

function toggleAdvancedMode() {
    const isAdv = document.getElementById('adv-toggle').checked;
    if (isAdv) {
        document.body.classList.add('advanced-mode-active');
        termLine('🚀 Advanced View Mode enabled.', 'done');
    } else {
        document.body.classList.remove('advanced-mode-active');
        termLine('🛡️ Standard View Mode restored.', 'sys');
    }
    saveGlobalSettings();
}

function termClear() {
  document.getElementById('terminal').innerHTML =
    '<div class="tl sys">terminal cleared<span class="term-cursor"></span></div>';
}
function termLine(text, cls='') {
  const t = document.getElementById('terminal');
  const cursor = t.querySelector('.term-cursor');
  if (cursor) cursor.remove();
  const d = document.createElement('div');
  d.className = 'tl' + (cls ? ' '+cls : '');
  d.textContent = text;
  t.appendChild(d);
  if (cls !== 'done' && cls !== 'err') {
    const c = document.createElement('span');
    c.className = 'term-cursor';
    t.appendChild(c);
  }
  t.scrollTop = t.scrollHeight;
}

// ── Count-up animation ────────────────────────────────────────────
function countUp(el, target, dur=600) {
  const start = parseInt(el.textContent) || 0;
  if (start === target) return;
  const t0 = performance.now();
  const step = ts => {
    const p = Math.min((ts-t0)/dur, 1);
    el.textContent = Math.round(start + (target-start) * p);
    if (p < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

// ── Stats refresh ─────────────────────────────────────────────────
async function refreshStats() {
  const s = await fetch('/api/stats').then(r=>r.json()).catch(()=>null);
  if (!s) return;

  countUp(document.getElementById('kv-total'), s.uploads_total);
  countUp(document.getElementById('kv-ed'),    s.educational.done);
  countUp(document.getElementById('kv-br'),    s.brainrot.done);
  countUp(document.getElementById('kv-rg'),    s.rotgen.done);

  document.getElementById('ks-today').textContent = `${s.uploads_today} today`;
  document.getElementById('ks-ed').textContent    = `of ${s.educational.total} lessons`;
  document.getElementById('ks-br').textContent    = `${s.brainrot.total} tracked`;
  document.getElementById('ks-rg').textContent    = `${s.rotgen.total} tracked`;
  document.getElementById('kp-ed').style.width    = `${(s.educational.done/s.educational.total*100).toFixed(1)}%`;

  // RAM
  if (s.ram) {
    const freePct = (s.ram.free / s.ram.total * 100);
    document.getElementById('ram-fill').style.width = `${(100 - freePct).toFixed(1)}%`;
    document.getElementById('ram-text').textContent = `${s.ram.free} GB / ${s.ram.total} GB free`;
  }

  // heatmap
  const hmap = document.getElementById('heatmap');
  const max  = Math.max(1, ...Object.values(s.heatmap||{}));
  hmap.innerHTML = Object.entries(s.heatmap||{}).map(([date,cnt]) => {
    const pct   = cnt/max;
    const alpha = cnt === 0 ? 0 : 0.15 + pct*0.85;
    const col   = `rgba(255,107,53,${alpha.toFixed(2)})`;
    const label = date.slice(5);
    return `<div class="hm-col">
      <div class="hm-block" style="background:${col};border-color:${cnt?'rgba(255,107,53,.3)':'var(--border)'}" data-tip="${date}: ${cnt} upload${cnt!==1?'s':''}"></div>
      <div class="hm-date">${label}</div>
    </div>`;
  }).join('');

  // content plan
  const pb = document.getElementById('plan-tbody');
  pb.innerHTML = (s.lessons||[]).map(l => {
    const yt = l.youtube_id?.length===11
      ? `<a class="yt-link" href="https://youtube.com/watch?v=${l.youtube_id}" target="_blank">${l.youtube_id}</a>`
      : '<span style="color:var(--border2)">—</span>';
    const pill = l.status==='complete'
      ? '<span class="pill pill-done">Done</span>'
      : '<span class="pill pill-pend">Pending</span>';
    return `<tr>
      <td style="color:var(--coral);font-weight:600;font-family:'Fira Code',monospace">${l.chapter}</td>
      <td style="max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${l.title||''}</td>
      <td>${pill}</td><td>${yt}</td>
    </tr>`;
  }).join('');

  // upload log
  const log = await fetch('/api/log').then(r=>r.json()).catch(()=>[]);
  const lb  = document.getElementById('log-tbody');
  lb.innerHTML = [...log].reverse().map(e => {
    const ts  = String(e.timestamp||'').slice(0,16).replace('T',' ');
    const ttl = String(e.title||'').slice(0,48);
    return `<tr>
      <td style="white-space:nowrap;color:var(--dim)">${ts}</td>
      <td><span class="pill pill-mode">${e.mode||'?'}</span></td>
      <td>${ttl}</td>
    </tr>`;
  }).join('');

  // breakdown
  const total = s.uploads_total || 1;
  document.getElementById('breakdown').innerHTML =
    Object.entries(s.mode_breakdown||{})
      .sort((a,b)=>b[1]-a[1]).slice(0,8)
      .map(([m,c]) => `
        <div class="bd-row">
          <div class="bd-label">${m}</div>
          <div class="bd-bar"><div class="bd-fill" style="width:${(c/total*100).toFixed(1)}%"></div></div>
          <div class="bd-cnt">${c}</div>
        </div>`
      ).join('');
}

// ── Health + Disk ─────────────────────────────────────────────────
async function refreshHealth() {
  try {
    const h = await fetch('/api/health').then(r=>r.json());
    const led = document.getElementById('ollama-led');
    const txt = document.getElementById('ollama-txt');
    led.className = 'led ' + (h.ollama ? 'on' : 'off');
    txt.textContent = h.ollama ? 'ollama · ok' : 'ollama · down';
  } catch(e) {}
}

async function refreshDisk() {
  try {
    const d = await fetch('/api/disk').then(r=>r.json());
    const MAX = 2000; // assume 2GB cap for display
    document.getElementById('disk-fill').style.width = `${Math.min(100, d.output_mb/MAX*100).toFixed(1)}%`;
    document.getElementById('disk-text').textContent = `${d.output_mb} mb output`;
  } catch(e) {}
}

// ── Clock ─────────────────────────────────────────────────────────
function tick() {
  document.getElementById('clock').textContent =
    new Date().toLocaleTimeString('en-US',{hour12:false});
}

// ── Modal system ──────────────────────────────────────────────────
let _modalMode = null;
let _modalStdinFn = null;

const PIPER_VOICES = [
  { id: 'en_US-ryan-high', name: 'Adam (English - US)', category: 'US' },
  { id: 'en_US-lessac-high', name: 'Antoni (English - US)', category: 'US' },
  { id: 'en_US-amy-medium', name: 'Amy (English - US)', category: 'US' },
  { id: 'en_GB-alan-medium', name: 'Arnold (English - UK)', category: 'UK' },
  { id: 'en_US-hfc_female-medium', name: 'Rachel (English - US)', category: 'US' },
  { id: 'en_US-joe-medium', name: 'Joe (English - US)', category: 'US' },
  { id: 'en_US-kristin-medium', name: 'Kristin (English - US)', category: 'US' },
  { id: 'en_GB-northern_english_male-medium', name: 'Callum (English - UK)', category: 'UK' },
  { id: 'en_US-libritts-high', name: 'Josh (English - US)', category: 'US' }
];

function optCard(value, label, selected) {
  return `<div class="opt-card${selected?' selected':''}" onclick="selectOpt(this,'${value}')" tabindex="0"
              onkeydown="if(event.key==='Enter'||event.key===' ')selectOpt(this,'${value}')">
    <div class="opt-dot"></div>
    <div class="opt-label">${label}</div>
  </div>`;
}

function selectOpt(el, value) {
  const cards = el.closest('.opt-cards');
  cards.querySelectorAll('.opt-card').forEach(c => c.classList.remove('selected'));
  el.classList.add('selected');
  cards.dataset.value = value;
  // Show/hide conditional fields
  const conditional = document.querySelectorAll('[data-show-if]');
  conditional.forEach(f => {
    const [key, val] = f.dataset.showIf.split('=');
    const container = document.querySelector(`.opt-cards[data-key="${key}"]`);
    if (container) f.style.display = (container.dataset.value === val) ? '' : 'none';
  });
}

function toggleBtn(el, group) {
  document.querySelectorAll(`[data-group="${group}"]`).forEach(b => b.classList.remove('selected'));
  el.classList.add('selected');
}

function getToggleVal(group) {
  const el = document.querySelector(`[data-group="${group}"].selected`);
  return el ? el.dataset.value : null;
}

// Modes that need a config dialog before launching
const NEEDS_CONFIG = new Set(['tcm','brainrot','tutorial','viral','ideas','clipper','rotgen']);

async function openModal(mode) {
  _modalMode = mode;
  const overlay = document.getElementById('modal-overlay');
  const title = document.getElementById('modal-title-el');
  const body = document.getElementById('modal-body');

  // Fetch dynamic assets
  const [models, assets, ps] = await Promise.all([
    fetch('/api/models').then(r=>r.json()).catch(()=>['llama3','mistral']),
    fetch('/api/assets').then(r=>r.json()).catch(()=>({backgrounds:[],characters:[],music:[]})),
    mode === 'tcm' ? fetch('/api/plan-status').then(r=>r.json()).catch(()=>({tcm_pending:0})) : Promise.resolve({tcm_pending:0})
  ]);
  const hasPending = ps.tcm_pending > 0;

  const voiceOptions = PIPER_VOICES.map(v => optCard(v.id, v.name, v.id === 'en_US-ryan-high')).join('');
  const bgOptions = [optCard('', 'Random/Default', true), ...assets.backgrounds.map(b => optCard(b, b, false))].join('');
  const charOptions = [optCard('', 'Default', true), ...assets.characters.map(c => optCard(c, c, false))].join('');

  const advFields = `
    <div class="advanced-only" style="margin-top:20px; padding-top:20px; border-top:1px dashed var(--border2)">
        <div class="modal-section-label" style="color:var(--cyan)">Advanced Parameters</div>
        <div class="field">
          <label>LLM Temperature</label>
          <input type="range" id="modal-temp" min="0" max="1" step="0.1" value="0.7" oninput="this.nextElementSibling.textContent = this.value">
          <span class="cnt-val" style="display:inline-block; vertical-align:middle; margin-left:10px">0.7</span>
        </div>
        <div class="field">
          <label>LLM Model Override</label>
          <select id="modal-model" style="width:100%; background:var(--bg3); color:var(--text); border:1px solid var(--border2); padding:10px; border-radius:var(--r-sm)">
            ${models.map(m => `<option value="${m}" ${m==='llama3'?'selected':''}>${m}</option>`).join('')}
          </select>
        </div>
        <div class="field">
          <label>Resolution</label>
          <div class="toggle-row">
            <button class="toggle-btn selected" data-group="hd_mode" data-value="n" onclick="toggleBtn(this,'hd_mode')">720p (Draft)</button>
            <button class="toggle-btn" data-group="hd_mode" data-value="y" onclick="toggleBtn(this,'hd_mode')">1080p (HD)</button>
          </div>
        </div>
    </div>
  `;

  const visualSection = `
    <div class="modal-section">
      <div class="modal-section-label">Background Asset</div>
      <div class="opt-cards" data-key="background" data-value="" style="max-height:120px; overflow-y:auto">
        ${bgOptions}
      </div>
    </div>
    <div class="modal-section">
      <div class="modal-section-label">Character Asset</div>
      <div class="opt-cards" data-key="character" data-value="" style="max-height:100px; overflow-y:auto">
        ${charOptions}
      </div>
    </div>
  `;

  const pane1 = `
    <div class="modal-pane">
      <div class="modal-section-label">Config & Content</div>
      ${mode === 'tcm' ? `
        ${hasPending ? `
        <div class="modal-section">
          <div class="modal-section-label">Existing Plan · ${ps.tcm_pending} pending</div>
          <div class="toggle-row">
            <button class="toggle-btn selected" data-group="use_existing" data-value="y" onclick="toggleBtn(this,'use_existing');toggleTcmSections()">continue</button>
            <button class="toggle-btn" data-group="use_existing" data-value="n" onclick="toggleBtn(this,'use_existing');toggleTcmSections()">new plan</button>
          </div>
        </div>` : ''}
        <div id="tcm-topic-section" ${hasPending?'style="display:none"':''}>
          <div class="modal-section">
            <div class="opt-cards" data-key="topic" data-value="1">
              ${optCard('1','Traditional Chinese Medicine',true)}
              ${optCard('2','Eastern Medicine',false)}
              ${optCard('3','Ayurvedic Medicine',false)}
              ${optCard('4','Holistic Wellness',false)}
              ${optCard('5','Custom…',false)}
            </div>
          </div>
          <div class="field" data-show-if="topic=5" style="display:none"><input type="text" id="tcm-custom" placeholder="Custom topic..."></div>
          <div class="field"><label>Sub-topics</label><input type="text" id="tcm-extra" placeholder="Details (anxiety, sleep...)"></div>
        </div>
        <div class="field"><label>Count</label><input type="number" id="tcm-count" value="3" min="1" max="10"></div>
      ` : ''}
      ${mode === 'brainrot' ? `<div class="field"><label>Topic / Hook</label><input type="text" id="br-hook" placeholder="Auto-generate from viral trends"></div>` : ''}
      ${mode === 'tutorial' ? `<div class="field"><label>Topic</label><input type="text" id="tut-topic" placeholder="e.g. Python decorators"></div>` : ''}
      ${mode === 'viral' ? `<div class="field"><label>Topic</label><input type="text" id="viral-topic" placeholder="e.g. satisfying crafts"></div>` : ''}
      ${mode === 'clipper' ? `<div class="field"><label>Source URL</label><input type="url" id="clip-url" placeholder="YouTube or local path"></div>` : ''}
    </div>
  `;

  const pane2 = `
    <div class="modal-pane">
      <div class="modal-section-label">Assets & Voice</div>
      <div class="modal-section">
        <label style="font-size:10px; color:var(--dim); text-transform:uppercase; font-weight:700; display:block; margin-bottom:8px">Voice Selection</label>
        <div class="opt-cards" data-key="voice" data-value="en_US-ryan-high" style="max-height:180px; overflow-y:auto">
          ${voiceOptions}
        </div>
      </div>
      <div class="modal-section">
        <label style="font-size:10px; color:var(--dim); text-transform:uppercase; font-weight:700; display:block; margin-bottom:8px">Background</label>
        <div class="opt-cards" data-key="background" data-value="" style="max-height:120px; overflow-y:auto">
          ${bgOptions}
        </div>
      </div>
    </div>
  `;

  const pane3 = `
    <div class="modal-pane">
      <div class="modal-section-label">Pipeline & Advanced</div>
      <div class="field">
        <label>Pipeline Mode</label>
        <div class="toggle-row">
          <button class="toggle-btn selected" data-group="dry_run" data-value="n" onclick="toggleBtn(this,'dry_run')">Production</button>
          <button class="toggle-btn" data-group="dry_run" data-value="y" onclick="toggleBtn(this,'dry_run')">Dry Run</button>
        </div>
      </div>
      ${visualSection}
      ${advFields}
      <div class="advanced-only" style="margin-top:20px; color:var(--dim); font-size:11px">
        * Advanced mode enables deeper customization of the production pipeline.
      </div>
    </div>
  `;

  body.innerHTML = pane1 + pane2 + pane3;

  if (mode === 'tcm') {
    title.innerHTML = '<span>TCM</span> Configure';
    _modalStdinFn = () => {
      const hasPending2 = !!document.querySelector('[data-group="use_existing"]');
      const count = document.getElementById('tcm-count').value || '3';
      if (hasPending2) {
        const useExisting = getToggleVal('use_existing');
        if (useExisting === 'y') return `y\n${count}\n`;
        const topic = document.querySelector('.opt-cards[data-key="topic"]')?.dataset.value || '1';
        const custom = (document.getElementById('tcm-custom')?.value || '').replace(/[\n\r]/g, ' ');
        const extra  = (document.getElementById('tcm-extra')?.value || '').replace(/[\n\r]/g, ' ');
        return `n\n${topic}\n${topic==='5'?custom+'\n':''}${extra}\n${count}\n`;
      } else {
        const topic = document.querySelector('.opt-cards[data-key="topic"]')?.dataset.value || '1';
        const custom = (document.getElementById('tcm-custom')?.value || '').replace(/[\n\r]/g, ' ');
        const extra  = (document.getElementById('tcm-extra')?.value || '').replace(/[\n\r]/g, ' ');
        return `${topic}\n${topic==='5'?custom+'\n':''}${extra}\n${count}\n`;
      }
    };
  } else if (mode === 'brainrot') {
    title.innerHTML = '<span>Brainrot</span> Configure';
    _modalStdinFn = () => "\n";
  } else if (mode === 'rotgen') {
    title.innerHTML = '<span>RotGen</span> Character + Gameplay';
    _modalStdinFn = () => "\n";
  } else if (mode === 'tutorial') {
    title.innerHTML = '<span>Tutorial</span> Topic';
    _modalStdinFn = () => (document.getElementById('tut-topic').value || '') + '\n';
  } else if (mode === 'viral') {
    title.innerHTML = '<span>Viral</span> Topic';
    _modalStdinFn = () => (document.getElementById('viral-topic').value || '') + '\n';
  } else if (mode === 'clipper') {
    title.innerHTML = '<span>Clipper</span> Source';
    _modalStdinFn = () => (document.getElementById('clip-url').value || '') + '\n';
  } else {
    title.innerHTML = `<span>${mode.toUpperCase()}</span> Configure`;
    _modalStdinFn = () => "\n";
  }

  overlay.style.display = 'flex';
  setTimeout(() => {
    const first = body.querySelector('input,button');
    if (first) first.focus();
  }, 50);
}

function toggleTcmSections() {
  const useExisting = getToggleVal('use_existing');
  const section = document.getElementById('tcm-topic-section');
  if (section) section.style.display = useExisting === 'n' ? '' : 'none';
}

function closeModal() {
  document.getElementById('modal-overlay').style.display = 'none';
  _modalMode = null;
  _modalStdinFn = null;
}

async function launchFromModal() {
  if (!_modalMode || !_modalStdinFn) return;
  const stdin_input = _modalStdinFn();
  if (stdin_input == null) { closeModal(); return; }
  const mode = _modalMode;
  
  // Extract fields from modal
  const dryRunVal    = getToggleVal('dry_run') || 'n';
  const voiceVal     = document.querySelector('.opt-cards[data-key="voice"]')?.dataset.value || 'en_US-ryan-high';
  const bgVal        = document.querySelector('.opt-cards[data-key="background"]')?.dataset.value || '';
  const charVal      = document.querySelector('.opt-cards[data-key="character"]')?.dataset.value || '';
  
  // Advanced / Global fallbacks
  const llmModel    = document.getElementById('modal-model')?.value || document.getElementById('global-model').value;
  const hdMode      = getToggleVal('hd_mode') || 'n';
  const author      = document.getElementById('global-author').value;
  const temperature = document.getElementById('modal-temp')?.value || '0.7';

  closeModal();

  const btn = document.getElementById('rb-'+mode);
  if (btn) { btn.textContent = '…'; btn.classList.add('active'); btn.disabled = true; }

  const res = await fetch(`/api/run/${mode}`, {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ 
        count: counts[mode] || 1, 
        stdin_input,
        dry_run: dryRunVal,
        voice: voiceVal,
        background: bgVal,
        character: charVal,
        llm_model: llmModel,
        hd_mode: hdMode,
        author_name: author,
        temperature: temperature
    })
  });
  const {job_id} = await res.json();

  openStream(job_id, () => {
    if (btn) { btn.textContent = 'run ▶'; btn.classList.remove('active'); btn.disabled = false; }
    refreshStats();
  });
}

// Close modal on overlay click or Escape
document.getElementById('modal-overlay').addEventListener('click', e => {
  if (e.target === e.currentTarget) closeModal();
});
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && document.getElementById('modal-overlay').style.display !== 'none') closeModal();
});

// ── Init ──────────────────────────────────────────────────────────
buildModeGrid();
refreshStats();
refreshHealth();
refreshDisk();
loadGlobalSettings();
refreshGallery();
setInterval(refreshStats,  15000);
setInterval(refreshHealth,  8000);
setInterval(refreshDisk,   30000);
setInterval(tick, 1000);
tick();
</script>
</body>
</html>"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    print(f"🎬  SuperShorts Dashboard  →  http://localhost:{port}")
    print(f"    Project root: {PROJECT_ROOT}")
    print("    Stop with Ctrl+C\n")
    app.run(host="0.0.0.0", port=port, threaded=True)
