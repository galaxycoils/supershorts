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
    "brainrot":    "from src.brainrot import run_brainrot_pipeline; run_brainrot_pipeline({count})",
    "rotgen":      "from src.rotgen import run_rotgen_pipeline; run_rotgen_pipeline({count})",
    "tcm":         "from src.tcm_mode import run_tcm_mode; run_tcm_mode()",
    "tutorial":    "from src.generator import start_tutorial_generation; start_tutorial_generation()",
    "viral":       "from src.generator import start_viral_gameplay_mode; start_viral_gameplay_mode()",
    "ideas":       "from src.ideagenerator import start_idea_generator; start_idea_generator()",
    "learning":    "from src.learning import suggest_improvements; suggest_improvements()",
    "package":     "from src.generator import generate_youtube_content_package; generate_youtube_content_package()",
    "clipper":     "from src.clipper_mode import run_video_clipper; run_video_clipper()",
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

@app.route("/api/run/<mode>", methods=["POST"])
def api_run(mode):
    if mode not in MODE_COMMANDS:
        return jsonify({"error": "unknown mode"}), 400
    try:
        count = max(1, min(10, int((request.json or {}).get("count", 1))))
    except (ValueError, TypeError):
        count = 1
    code  = MODE_COMMANDS[mode].format(count=count)
    cmd   = [PYTHON, "-c",
             f"import sys; sys.path.insert(0,'{PROJECT_ROOT}'); {code}"]
    proc  = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             stdin=subprocess.PIPE, cwd=str(PROJECT_ROOT))
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

# ── HTML ──────────────────────────────────────────────────────────────────────

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SuperShorts — Production Suite</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Fira+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
:root {
  --bg:      #080808;
  --bg2:     #0f0f0f;
  --bg3:     #161616;
  --bg4:     #1c1c1c;
  --coral:   #ff6b35;
  --coral2:  #c84d1f;
  --coral3:  rgba(255,107,53,.1);
  --cream:   #e8ddd4;
  --cream2:  #a09088;
  --mint:    #4ade80;
  --red:     #f87171;
  --dim:     #524840;
  --border:  #181410;
  --border2: #242018;
  --sidebar: 220px;
  /* Spacing */
  --sp-1: 4px; --sp-2: 8px; --sp-3: 12px; --sp-4: 16px;
  --sp-5: 20px; --sp-6: 24px; --sp-8: 32px;
  /* Border radius */
  --r-sm: 2px; --r-md: 4px; --r-lg: 6px;
  /* Shadows */
  --shadow-card: 0 1px 4px rgba(0,0,0,.5);
  --shadow-modal: 0 8px 32px rgba(0,0,0,.7);
  --shadow-glow: 0 0 12px rgba(255,107,53,.15);
  /* Transitions */
  --t-fast: 0.12s ease; --t-base: 0.18s ease; --t-slow: 0.3s ease;
  /* Z-index stack */
  --z-tooltip: 200; --z-topbar: 300; --z-modal: 500;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body { height: 100%; }

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: .01ms !important; transition-duration: .01ms !important; }
}

body {
  display: flex;
  background: var(--bg);
  color: var(--cream);
  font-family: 'Fira Sans', system-ui, sans-serif;
  font-size: 13px;
  line-height: 1.5;
  overflow-x: hidden;
}

:focus-visible { outline: 2px solid var(--coral); outline-offset: 2px; }

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
}

.sidebar::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 3px;
  background-image: repeating-linear-gradient(
    to bottom,
    transparent 0px, transparent 8px,
    var(--border2) 8px, var(--border2) 14px
  );
  pointer-events: none;
}

.sidebar-logo {
  padding: 22px 16px 18px 18px;
  border-bottom: 1px solid var(--border);
}

.logo-mark {
  font-family: 'Fira Code', monospace;
  font-weight: 600;
  font-size: 16px;
  letter-spacing: -0.5px;
  color: var(--cream);
  display: flex;
  align-items: baseline;
  gap: 1px;
}
.logo-mark .accent { color: var(--coral); }
.logo-mark .slash  { color: var(--dim); font-weight: 400; margin: 0 2px; }

.logo-sub {
  font-size: 9px;
  letter-spacing: 2.5px;
  color: var(--dim);
  text-transform: uppercase;
  margin-top: 5px;
  font-weight: 500;
}

.nav-section { padding: 14px 0 6px; }
.nav-label {
  padding: 0 14px 6px 18px;
  font-size: 9px;
  letter-spacing: 2.5px;
  color: var(--dim);
  text-transform: uppercase;
  font-weight: 600;
}

.nav-btn {
  display: flex;
  align-items: center;
  gap: 9px;
  width: 100%;
  padding: 7px 14px 7px 18px;
  background: transparent;
  border: none;
  border-left: 2px solid transparent;
  color: var(--cream2);
  font-family: 'Fira Sans', sans-serif;
  font-size: 12px;
  font-weight: 400;
  cursor: pointer;
  transition: color .15s, background .15s, border-color .15s;
  text-align: left;
}
.nav-btn svg { flex-shrink: 0; opacity: .55; transition: opacity .15s; }
.nav-btn:hover { background: var(--bg3); color: var(--cream); border-left-color: var(--border2); }
.nav-btn:hover svg { opacity: 1; }
.nav-btn.active { color: var(--coral); border-left-color: var(--coral); background: var(--coral3); font-weight: 500; }
.nav-btn.active svg { opacity: 1; stroke: var(--coral); }

.wf-section { padding: 4px 10px 8px; }
.wf-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 10px;
  margin-bottom: 4px;
  background: var(--bg3);
  border: 1px solid var(--border2);
  border-radius: var(--r-sm);
  color: var(--cream2);
  font-family: 'Fira Code', monospace;
  font-size: 10px;
  cursor: pointer;
  transition: border-color var(--t-fast), color var(--t-fast), background var(--t-fast);
  text-align: left;
}
.wf-btn svg { flex-shrink: 0; opacity: .6; transition: opacity .15s; }
.wf-btn:hover { border-color: var(--coral); color: var(--coral); background: var(--coral3); }
.wf-btn:hover svg { stroke: var(--coral); opacity: 1; }
.wf-btn.running { border-color: var(--coral); color: var(--coral); background: var(--coral3); animation: blink .9s ease infinite; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.45} }

.sidebar-bottom {
  margin-top: auto;
  padding: 12px 14px 16px 18px;
  border-top: 1px solid var(--border);
}

.ollama-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 10px;
  color: var(--dim);
  font-family: 'Fira Code', monospace;
}
.led {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--dim);
  flex-shrink: 0;
  transition: background .3s, box-shadow .3s;
}
.led.on  { background: var(--mint); box-shadow: 0 0 6px var(--mint); }
.led.off { background: var(--red);  box-shadow: 0 0 5px rgba(248,113,113,.4); }

.disk-label { font-size: 9px; color: var(--dim); margin-bottom: 5px; letter-spacing: 1.5px; text-transform: uppercase; }
.disk-bar   { height: 2px; background: var(--border2); overflow: hidden; }
.disk-fill  { height: 100%; background: linear-gradient(90deg, var(--coral2), var(--coral)); transition: width .6s ease; }
.disk-text  { font-size: 10px; color: var(--dim); margin-top: 4px; font-family: 'Fira Code', monospace; }

/* ── MAIN ────────────────────────────────────────────────────────── */
.main { flex: 1; overflow-y: auto; min-width: 0; }

.topbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 20px;
  padding: 10px 28px;
  border-bottom: 1px solid var(--border);
  background: var(--bg2);
  position: sticky;
  top: 0;
  z-index: var(--z-topbar);
}

.producing-badge {
  display: none;
  align-items: center;
  gap: 6px;
  font-size: 9px;
  letter-spacing: 2.5px;
  color: var(--coral);
  font-weight: 600;
  text-transform: uppercase;
  font-family: 'Fira Code', monospace;
}
.producing-badge.active { display: flex; }
.producing-dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  background: var(--coral);
  box-shadow: 0 0 8px var(--coral);
  animation: pulse .8s ease-in-out infinite;
}
@keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.3;transform:scale(.85)} }

#clock {
  color: var(--dim);
  font-size: 11px;
  font-family: 'Fira Code', monospace;
  letter-spacing: .5px;
}

.content { padding: 22px 28px; }

h2 {
  font-family: 'Fira Sans', sans-serif;
  font-weight: 600;
  font-size: 11px;
  color: var(--cream);
  letter-spacing: 2px;
  margin-bottom: 14px;
  text-transform: uppercase;
}
h2 small {
  font-family: 'Fira Code', monospace;
  font-size: 10px;
  color: var(--dim);
  font-weight: 400;
  letter-spacing: 1px;
  margin-left: 10px;
  text-transform: none;
}

section { margin-bottom: 30px; }

/* ── KPI row ─────────────────────────────────────────────────────── */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-bottom: 30px;
}

.kpi {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--r-sm);
  box-shadow: var(--shadow-card);
  padding: 18px 20px 14px;
  position: relative;
  overflow: hidden;
}

.kpi::after {
  content: '';
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--coral), transparent);
  opacity: .3;
}

.kpi-label {
  font-size: 9px;
  letter-spacing: 2.5px;
  color: var(--dim);
  text-transform: uppercase;
  margin-bottom: 10px;
  font-weight: 600;
}

.kpi-value {
  font-family: 'Fira Code', monospace;
  font-weight: 600;
  font-size: 46px;
  color: var(--coral);
  line-height: 1;
  letter-spacing: -2px;
  text-shadow: 0 0 28px rgba(255,107,53,.2);
}

.kpi-sub { font-size: 10px; color: var(--dim); margin-top: 8px; font-family: 'Fira Code', monospace; }

.kpi-prog {
  height: 1px;
  background: var(--border2);
  margin-top: 12px;
  overflow: hidden;
}
.kpi-prog-fill {
  height: 100%;
  background: var(--coral);
  opacity: .5;
  transition: width .8s ease;
}

/* ── two-col ─────────────────────────────────────────────────────── */
.two-col { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; }

/* ── production slates ───────────────────────────────────────────── */
.mode-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
}

.slate {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--r-sm);
  box-shadow: var(--shadow-card);
  padding: 13px 14px;
  position: relative;
  overflow: hidden;
  cursor: pointer;
  min-width: 0;
  transition: border-color var(--t-fast), background var(--t-fast);
}
.slate:hover { border-color: var(--coral); background: var(--bg3); }

.slate::after {
  content: '';
  position: absolute;
  top: 0; right: 0;
  border-style: solid;
  border-width: 0 14px 14px 0;
  border-color: transparent var(--border2) transparent transparent;
  transition: border-color .15s;
}
.slate:hover::after { border-color: transparent var(--coral) transparent transparent; }

.slate-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px; height: 26px;
  background: var(--bg3);
  border: 1px solid var(--border2);
  margin-bottom: 8px;
}
.slate-icon svg { stroke: var(--coral); }

.slate-name {
  font-family: 'Fira Sans', sans-serif;
  font-weight: 600;
  font-size: 13px;
  color: var(--cream);
  line-height: 1.1;
  margin-bottom: 2px;
}

.slate-desc { font-size: 10px; color: var(--dim); margin-bottom: 10px; line-height: 1.4; }

.slate-controls { display: flex; align-items: center; gap: 6px; }

.cnt-btn {
  background: var(--bg3);
  border: 1px solid var(--border2);
  border-radius: var(--r-sm);
  color: var(--cream2);
  width: 28px; height: 28px;
  font-size: 14px;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: background var(--t-fast), border-color var(--t-fast), color var(--t-fast);
  flex-shrink: 0;
  font-family: 'Fira Code', monospace;
}
.cnt-btn:hover { background: var(--coral); border-color: var(--coral); color: #000; }

.cnt-val {
  font-family: 'Fira Code', monospace;
  font-size: 18px;
  font-weight: 600;
  color: var(--coral);
  width: 22px;
  text-align: center;
  line-height: 1;
}

.run-btn {
  margin-left: auto;
  background: transparent;
  border: 1px solid var(--border2);
  border-radius: var(--r-sm);
  color: var(--cream2);
  font-family: 'Fira Code', monospace;
  font-size: 9px;
  letter-spacing: 1.5px;
  padding: 4px 10px;
  cursor: pointer;
  transition: border-color var(--t-fast), color var(--t-fast), background var(--t-fast);
  text-transform: uppercase;
}
.run-btn:hover  { border-color: var(--coral); color: var(--coral); background: var(--coral3); }
.run-btn:disabled { opacity: .3; cursor: default; }
.run-btn.active {
  border-color: var(--coral); color: var(--coral);
  background: var(--coral3);
  animation: blink .7s ease infinite;
}

/* ── terminal ────────────────────────────────────────────────────── */
.term-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.term-clear {
  background: transparent;
  border: 1px solid var(--border2);
  color: var(--dim);
  font-family: 'Fira Code', monospace;
  font-size: 9px;
  letter-spacing: 1.5px;
  padding: 3px 8px;
  cursor: pointer;
  transition: border-color .15s, color .15s;
  text-transform: uppercase;
}
.term-clear:hover { border-color: var(--coral); color: var(--coral); }

.terminal {
  background: #040404;
  border: 1px solid var(--border);
  border-top: 2px solid var(--coral);
  border-radius: var(--r-sm);
  min-height: 280px;
  max-height: 420px;
  overflow-y: auto;
  padding: 12px 14px;
  font-family: 'Fira Code', monospace;
  font-size: 11px;
  line-height: 1.7;
}

.term-cursor {
  display: inline-block;
  width: 6px; height: 12px;
  background: var(--coral);
  opacity: .7;
  animation: cursor-blink 1.1s ease-in-out infinite;
  vertical-align: middle;
  margin-left: 1px;
}
@keyframes cursor-blink { 0%,100%{opacity:.7} 50%{opacity:0} }  /* smooth ease via animation-timing-function on .term-cursor */

.tl { color: var(--cream2); }
.tl.ok   { color: var(--mint); }
.tl.err  { color: var(--red); }
.tl.sys  { color: var(--dim); font-style: italic; }
.tl.done { color: var(--coral); font-weight: 600; }
.tl.prompt { color: var(--coral); }

/* ── heatmap ─────────────────────────────────────────────────────── */
.heatmap { display: flex; gap: 4px; align-items: flex-end; margin-bottom: 18px; }
.hm-col { display: flex; flex-direction: column; align-items: center; gap: 3px; }
.hm-block {
  width: 34px; height: 34px;
  background: var(--bg3);
  border: 1px solid var(--border);
  transition: background .4s ease;
  cursor: default;
  position: relative;
}
.hm-block[data-tip]:hover::after {
  content: attr(data-tip);
  position: absolute;
  bottom: 40px; left: 50%;
  transform: translateX(-50%);
  background: var(--bg4);
  border: 1px solid var(--border2);
  color: var(--cream);
  font-size: 10px;
  font-family: 'Fira Code', monospace;
  padding: 3px 8px;
  white-space: nowrap;
  pointer-events: none;
  z-index: var(--z-tooltip);
}
.hm-date { font-size: 9px; color: var(--dim); font-family: 'Fira Code', monospace; }

/* ── tables ──────────────────────────────────────────────────────── */
.table-wrap { max-height: 300px; overflow-y: auto; }
table { width: 100%; border-collapse: collapse; font-size: 11px; }
th {
  text-align: left;
  padding: 6px 10px;
  color: var(--dim);
  letter-spacing: 2px;
  font-size: 9px;
  border-bottom: 1px solid var(--border);
  font-weight: 600;
  text-transform: uppercase;
  position: sticky; top: 0;
  background: var(--bg2);
  font-family: 'Fira Code', monospace;
}
td {
  padding: 7px 10px;
  border-bottom: 1px solid rgba(24,20,16,.9);
  color: var(--cream2);
  vertical-align: middle;
}
tr:hover td { background: var(--bg3); color: var(--cream); }

.pill {
  display: inline-block;
  padding: 2px 7px;
  font-size: 9px;
  letter-spacing: 1px;
  text-transform: uppercase;
  font-family: 'Fira Code', monospace;
}
.pill-done { background: rgba(74,222,128,.07); color: var(--mint); border: 1px solid rgba(74,222,128,.15); }
.pill-pend { background: rgba(82,72,64,.1); color: var(--dim); border: 1px solid var(--border); }
.pill-mode { background: var(--coral3); color: var(--coral); border: 1px solid rgba(255,107,53,.15); }

.yt-link { color: var(--coral); text-decoration: none; font-size: 10px; font-family: 'Fira Code', monospace; }
.yt-link:hover { text-decoration: underline; }

.breakdown { display: flex; flex-direction: column; gap: 7px; margin-top: 8px; }
.bd-row { display: flex; align-items: center; gap: 10px; }
.bd-label { width: 86px; font-size: 10px; color: var(--dim); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-family: 'Fira Code', monospace; }
.bd-bar { flex: 1; height: 2px; background: var(--border2); overflow: hidden; }
.bd-fill { height: 100%; background: var(--coral); opacity: .6; transition: width .6s ease; }
.bd-cnt { font-size: 10px; color: var(--coral); width: 24px; text-align: right; font-family: 'Fira Code', monospace; }

::-webkit-scrollbar { width: 3px; height: 3px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border2); }
::-webkit-scrollbar-thumb:hover { background: var(--coral); }

@media (max-width: 960px) {
  .kpi-row { grid-template-columns: repeat(2, 1fr); }
  .two-col  { grid-template-columns: 1fr; }
  .sidebar  { width: 180px; }
}

@media (max-width: 768px) {
  .sidebar { width: 0; overflow: hidden; border: none; }
  .main { margin-left: 0; }
  .kpi-row { grid-template-columns: 1fr 1fr; }
  .mode-grid { grid-template-columns: 1fr; }
  .modal { width: calc(100vw - 24px); }
}

/* ── MODAL ────────────────────────────────────────────────────────── */
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,.75);
  z-index: var(--z-modal);
  display: flex; align-items: center; justify-content: center;
  animation: fade-in .15s ease;
}
@keyframes fade-in { from{opacity:0} to{opacity:1} }

.modal {
  background: var(--bg2);
  border: 1px solid var(--border2);
  border-top: 2px solid var(--coral);
  border-radius: var(--r-md);
  box-shadow: var(--shadow-modal);
  width: 480px;
  max-width: calc(100vw - 40px);
  max-height: calc(100vh - 80px);
  overflow-y: auto;
  padding: 22px 24px 20px;
  animation: slide-up .18s ease;
}
@keyframes slide-up { from{transform:translateY(12px);opacity:0} to{transform:translateY(0);opacity:1} }

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.modal-title {
  font-family: 'Fira Sans', sans-serif;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--cream);
}
.modal-title span { color: var(--coral); margin-right: 6px; }
.modal-close {
  background: transparent;
  border: 1px solid var(--border2);
  color: var(--dim);
  width: 24px; height: 24px;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px;
  font-family: 'Fira Code', monospace;
  transition: border-color .15s, color .15s;
}
.modal-close:hover { border-color: var(--red); color: var(--red); }

.modal-section { margin-bottom: 18px; }
.modal-section-label {
  font-size: 9px;
  letter-spacing: 2px;
  color: var(--dim);
  text-transform: uppercase;
  font-weight: 600;
  margin-bottom: 8px;
  font-family: 'Fira Code', monospace;
}

/* Clickable option cards */
.opt-cards { display: flex; flex-direction: column; gap: 4px; }
.opt-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border: 1px solid var(--border);
  background: var(--bg3);
  cursor: pointer;
  transition: border-color .15s, background .15s;
  user-select: none;
}
.opt-card:hover { border-color: var(--border2); }
.opt-card.selected { border-color: var(--coral); background: var(--coral3); }
.opt-dot {
  width: 10px; height: 10px;
  border-radius: 50%;
  border: 1.5px solid var(--dim);
  flex-shrink: 0;
  transition: border-color .15s, background .15s;
}
.opt-card.selected .opt-dot { border-color: var(--coral); background: var(--coral); }
.opt-label { font-size: 12px; color: var(--cream2); font-family: 'Fira Sans', sans-serif; }
.opt-card.selected .opt-label { color: var(--cream); }

/* Text / number fields */
.field { margin-bottom: 14px; }
.field label {
  display: block;
  font-size: 9px;
  letter-spacing: 2px;
  color: var(--dim);
  text-transform: uppercase;
  font-weight: 600;
  margin-bottom: 6px;
  font-family: 'Fira Code', monospace;
}
.field input[type=text], .field input[type=number], .field input[type=url] {
  width: 100%;
  background: var(--bg3);
  border: 1px solid var(--border2);
  border-bottom: 2px solid var(--border2);
  color: var(--cream);
  font-family: 'Fira Code', monospace;
  font-size: 12px;
  padding: 8px 10px;
  outline: none;
  transition: border-color .15s;
}
.field input:focus { border-color: var(--coral); border-bottom-color: var(--coral); }
.field input::placeholder { color: var(--dim); }
.field input[type=number] { width: 80px; }
.field-hint { font-size: 10px; color: var(--dim); margin-top: 4px; font-family: 'Fira Code', monospace; }

/* Toggle row (yes/no) */
.toggle-row { display: flex; gap: 6px; }
.toggle-btn {
  flex: 1;
  padding: 8px;
  background: var(--bg3);
  border: 1px solid var(--border);
  color: var(--cream2);
  font-family: 'Fira Code', monospace;
  font-size: 11px;
  cursor: pointer;
  text-align: center;
  transition: border-color .15s, color .15s, background .15s;
}
.toggle-btn:hover { border-color: var(--border2); }
.toggle-btn.selected { border-color: var(--coral); color: var(--coral); background: var(--coral3); }

.modal-footer {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  margin-top: 22px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}
.btn-cancel {
  background: transparent;
  border: 1px solid var(--border2);
  color: var(--dim);
  font-family: 'Fira Code', monospace;
  font-size: 10px;
  letter-spacing: 1px;
  padding: 7px 16px;
  cursor: pointer;
  transition: border-color .15s, color .15s;
}
.btn-cancel:hover { border-color: var(--cream2); color: var(--cream2); }
.btn-launch {
  background: var(--coral);
  border: none;
  color: #080808;
  font-family: 'Fira Code', monospace;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 1.5px;
  padding: 7px 22px;
  cursor: pointer;
  transition: opacity .15s;
  text-transform: uppercase;
}
.btn-launch:hover { opacity: .88; }
.btn-launch:disabled { opacity: .35; cursor: default; }
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
    <div class="disk-label">Output Disk</div>
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
          <button class="term-clear" onclick="termClear()" aria-label="Clear terminal">clr</button>
        </div>
        <div class="terminal" id="terminal" role="log" aria-live="polite">
          <div class="tl sys">awaiting production order<span class="term-cursor"></span></div>
        </div>
      </section>
    </div>

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

  const res = await fetch(`/api/run/${id}`, {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({count: counts[id]})
  });
  const {job_id} = await res.json();

  openStream(job_id, () => {
    btn.textContent = 'run ▶'; btn.classList.remove('active'); btn.disabled = false;
    refreshStats();
  });
}

// ── Run workflow ──────────────────────────────────────────────────
async function runWorkflow(name) {
  const btn = document.getElementById('wf-'+name);
  btn.classList.add('running');

  const res = await fetch(`/api/workflow/${name}`, {method:'POST'});
  const {job_id} = await res.json();

  openStream(job_id, () => {
    btn.classList.remove('running');
    refreshStats();
  });
}

// ── SSE stream ────────────────────────────────────────────────────
function openStream(job_id, onDone) {
  termClear();
  termLine(`▶ job ${job_id} starting…`, 'prompt');
  document.getElementById('producing-badge').classList.add('active');
  activeJobs.add(job_id);

  if (currentEvt) currentEvt.close();
  currentEvt = new EventSource(`/api/stream/${job_id}`);

  currentEvt.onmessage = e => {
    const line = e.data;
    if (line.startsWith('[JOB')) {
      const ok = line.includes('DONE');
      termLine(line, ok ? 'done' : 'err');
      currentEvt.close();
      activeJobs.delete(job_id);
      if (activeJobs.size === 0)
        document.getElementById('producing-badge').classList.remove('active');
      if (onDone) onDone();
    } else {
      const cls = (line.includes('❌')||line.includes('ERROR')) ? 'err'
                : (line.includes('✅')||line.includes('✓')) ? 'ok'
                : '';
      termLine(line, cls);
    }
  };
  currentEvt.onerror = () => {
    activeJobs.delete(job_id);
    if (activeJobs.size === 0)
      document.getElementById('producing-badge').classList.remove('active');
    if (onDone) onDone();
  };
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
    const yt = l.youtube_id && l.youtube_id.length===11
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

// Modes that need a config dialog before launching
const NEEDS_CONFIG = new Set(['tcm','tutorial','viral','ideas','clipper']);

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

async function openModal(mode) {
  _modalMode = mode;
  const overlay = document.getElementById('modal-overlay');
  const title = document.getElementById('modal-title-el');
  const body = document.getElementById('modal-body');

  if (mode === 'tcm') {
    title.innerHTML = '<span>TCM</span> Configure';
    const ps = await fetch('/api/plan-status').then(r=>r.json()).catch(()=>({tcm_pending:0}));
    const hasPending = ps.tcm_pending > 0;
    body.innerHTML = `
      ${hasPending ? `
      <div class="modal-section">
        <div class="modal-section-label">Existing Plan · ${ps.tcm_pending} lessons pending</div>
        <div class="toggle-row">
          <button class="toggle-btn selected" data-group="use_existing" data-value="y"
            onclick="toggleBtn(this,'use_existing');toggleTcmSections()">
            continue existing plan
          </button>
          <button class="toggle-btn" data-group="use_existing" data-value="n"
            onclick="toggleBtn(this,'use_existing');toggleTcmSections()">
            generate new plan
          </button>
        </div>
      </div>` : ''}
      <div id="tcm-topic-section" ${hasPending?'style="display:none"':''}>
        <div class="modal-section">
          <div class="modal-section-label">Topic Focus</div>
          <div class="opt-cards" data-key="topic" data-value="1">
            ${optCard('1','Traditional Chinese Medicine (TCM)',true)}
            ${optCard('2','Eastern Medicine',false)}
            ${optCard('3','Ayurvedic Medicine',false)}
            ${optCard('4','Holistic Wellness',false)}
            ${optCard('5','Custom…',false)}
          </div>
        </div>
        <div class="field" data-show-if="topic=5" style="display:none">
          <label for="tcm-custom">Custom Topic</label>
          <input type="text" id="tcm-custom" placeholder="e.g. Qi Gong for beginners">
        </div>
        <div class="field">
          <label for="tcm-extra">Sub-topics / extra details <span style="color:var(--dim);font-weight:400">(optional)</span></label>
          <input type="text" id="tcm-extra" placeholder="e.g. focus on anxiety, sleep, herbal remedies">
        </div>
      </div>
      <div class="field" id="tcm-count-field">
        <label for="tcm-count">Videos to generate</label>
        <input type="number" id="tcm-count" value="3" min="1" max="10">
        <div class="field-hint">1–10 · recommended ≤5 on 8 GB RAM</div>
      </div>
    `;
    _modalStdinFn = () => {
      const hasPending2 = !!document.querySelector('[data-group="use_existing"]');
      if (hasPending2) {
        const useExisting = getToggleVal('use_existing');
        const count = document.getElementById('tcm-count').value || '3';
        if (useExisting === 'y') return `y\n${count}\n`;
        // user chose new plan
        const topic = document.querySelector('.opt-cards[data-key="topic"]')?.dataset.value || '1';
        const custom = (document.getElementById('tcm-custom')?.value || '').replace(/[\n\r]/g, ' ');
        const extra  = (document.getElementById('tcm-extra')?.value || '').replace(/[\n\r]/g, ' ');
        return `n\n${topic}\n${topic==='5'?custom+'\n':''}${extra}\n${count}\n`;
      } else {
        const topic = document.querySelector('.opt-cards[data-key="topic"]')?.dataset.value || '1';
        const custom = (document.getElementById('tcm-custom')?.value || '').replace(/[\n\r]/g, ' ');
        const extra  = (document.getElementById('tcm-extra')?.value || '').replace(/[\n\r]/g, ' ');
        const count = document.getElementById('tcm-count').value || '3';
        return `${topic}\n${topic==='5'?custom+'\n':''}${extra}\n${count}\n`;
      }
    };

  } else if (mode === 'tutorial') {
    title.innerHTML = '<span>Tutorial</span> Topic';
    body.innerHTML = `
      <div class="field">
        <label for="tut-topic">Tutorial topic</label>
        <input type="text" id="tut-topic" placeholder="e.g. Python decorators (blank = auto-pick)">
      </div>`;
    _modalStdinFn = () => (document.getElementById('tut-topic').value || '') + '\n';

  } else if (mode === 'viral') {
    title.innerHTML = '<span>Viral</span> Topic';
    body.innerHTML = `
      <div class="field">
        <label for="viral-topic">Video topic</label>
        <input type="text" id="viral-topic" placeholder="e.g. satisfying marble runs (blank = random)">
      </div>`;
    _modalStdinFn = () => (document.getElementById('viral-topic').value || '') + '\n';

  } else if (mode === 'ideas') {
    title.innerHTML = '<span>YT Ideas</span> API Key';
    body.innerHTML = `
      <div class="field">
        <label for="ideas-key">YouTube Data API v3 key</label>
        <input type="text" id="ideas-key" placeholder="AIza… (blank = Ollama-only mode)">
        <div class="field-hint">Optional — leave blank to use Ollama for idea generation</div>
      </div>`;
    _modalStdinFn = () => (document.getElementById('ideas-key').value || '') + '\n';

  } else if (mode === 'clipper') {
    title.innerHTML = '<span>Clipper</span> Source';
    body.innerHTML = `
      <div class="field">
        <label for="clip-url">YouTube URL or local video path</label>
        <input type="url" id="clip-url" placeholder="https://youtube.com/watch?v=...">
      </div>`;
    _modalStdinFn = () => (document.getElementById('clip-url').value || '') + '\n';
  }

  overlay.style.display = 'flex';
  // Focus first input or launch button
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
  closeModal();

  const btn = document.getElementById('rb-'+mode);
  if (btn) { btn.textContent = '…'; btn.classList.add('active'); btn.disabled = true; }

  const res = await fetch(`/api/run/${mode}`, {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ count: counts[mode] || 1, stdin_input })
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
