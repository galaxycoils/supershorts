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

WORKFLOW_COMMANDS = {
    "daily":         f"python3 {PROJECT_ROOT}/run_workflow.py {PROJECT_ROOT}/workflows/daily.workflow.json",
    "tcm-weekly":    f"python3 {PROJECT_ROOT}/run_workflow.py {PROJECT_ROOT}/workflows/tcm-weekly.workflow.json",
    "full-pipeline": f"python3 {PROJECT_ROOT}/run_workflow.py {PROJECT_ROOT}/workflows/full-pipeline.workflow.json",
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
    count = max(1, min(10, int((request.json or {}).get("count", 1))))
    code  = MODE_COMMANDS[mode].format(count=count)
    cmd   = [PYTHON, "-c",
             f"import sys; sys.path.insert(0,'{PROJECT_ROOT}'); {code}"]
    proc  = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             cwd=str(PROJECT_ROOT))
    job_id = str(uuid.uuid4())[:8]
    JOBS[job_id] = {"proc": proc, "output": [], "status": "running", "mode": mode}
    threading.Thread(target=_stream_job, args=(job_id, proc), daemon=True).start()
    return jsonify({"job_id": job_id, "mode": mode, "count": count})

@app.route("/api/workflow/<name>", methods=["POST"])
def api_workflow(name):
    if name not in WORKFLOW_COMMANDS:
        return jsonify({"error": "unknown workflow"}), 400
    cmd  = [PYTHON] + WORKFLOW_COMMANDS[name].split()[1:]  # replace python3 with venv python
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
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,700;0,9..144,900;1,9..144,400&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
:root {
  --bg:      #0c0a09;
  --bg2:     #141210;
  --bg3:     #1e1b18;
  --bg4:     #252118;
  --coral:   #ff6b35;
  --coral2:  #c84d1f;
  --cream:   #f0e0c8;
  --cream2:  #b8a898;
  --mint:    #7cffa4;
  --red:     #ff4040;
  --dim:     #6b6058;
  --border:  #2a2420;
  --border2: #3a3028;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body { height: 100%; }

body {
  display: flex;
  background: var(--bg);
  color: var(--cream);
  font-family: 'Space Mono', monospace;
  font-size: 12px;
  line-height: 1.5;
  overflow-x: hidden;
}

/* grain filter */
svg.grain { position: fixed; width: 0; height: 0; }

body::after {
  content: '';
  position: fixed; inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='1'/%3E%3C/svg%3E");
  opacity: 0.028;
  pointer-events: none;
  z-index: 9998;
}

/* ── SIDEBAR ─────────────────────────────────────────────────────── */
.sidebar {
  width: 220px;
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

/* perforated film-strip edge */
.sidebar::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 6px;
  background-image: repeating-linear-gradient(
    to bottom,
    transparent 0px,
    transparent 10px,
    var(--border2) 10px,
    var(--border2) 18px
  );
}

.sidebar-logo {
  padding: 28px 20px 20px 20px;
  border-bottom: 1px solid var(--border);
}

.logo-word {
  font-family: 'Fraunces', serif;
  font-weight: 900;
  font-size: 26px;
  line-height: 1;
  letter-spacing: -0.5px;
  color: var(--cream);
  display: block;
}
.logo-word span { color: var(--coral); }
.logo-sub {
  font-size: 9px;
  letter-spacing: 3px;
  color: var(--dim);
  text-transform: uppercase;
  margin-top: 4px;
  display: block;
}

.nav-section { padding: 16px 0 8px 0; }
.nav-label {
  padding: 0 16px 6px 20px;
  font-size: 9px;
  letter-spacing: 3px;
  color: var(--dim);
  text-transform: uppercase;
}

.nav-btn {
  display: block;
  width: 100%;
  text-align: left;
  padding: 8px 16px 8px 20px;
  background: transparent;
  border: none;
  color: var(--cream2);
  font-family: 'Space Mono', monospace;
  font-size: 11px;
  cursor: pointer;
  border-left: 3px solid transparent;
  transition: all .15s;
}
.nav-btn:hover { background: var(--bg3); color: var(--cream); border-left-color: var(--border2); }
.nav-btn.active { color: var(--coral); border-left-color: var(--coral); background: rgba(255,107,53,.06); }

/* workflow buttons */
.wf-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  width: calc(100% - 24px);
  margin: 3px 12px;
  padding: 7px 10px;
  background: var(--bg3);
  border: 1px solid var(--border2);
  color: var(--cream2);
  font-family: 'Space Mono', monospace;
  font-size: 10px;
  cursor: pointer;
  transition: all .15s;
  text-align: left;
}
.wf-btn:hover { border-color: var(--coral); color: var(--coral); }
.wf-btn.running { border-color: var(--coral); color: var(--coral); animation: pulse .9s ease infinite; }
.wf-icon { font-size: 14px; flex-shrink: 0; }

/* sidebar bottom */
.sidebar-bottom {
  margin-top: auto;
  padding: 12px 16px 16px 20px;
  border-top: 1px solid var(--border);
}

.ollama-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  font-size: 10px;
  color: var(--dim);
}
.led {
  width: 7px; height: 7px;
  border-radius: 50%;
  background: var(--dim);
  flex-shrink: 0;
}
.led.on  { background: var(--mint); box-shadow: 0 0 6px var(--mint); }
.led.off { background: var(--red);  box-shadow: 0 0 6px rgba(255,64,64,.5); }

.disk-label { font-size: 9px; color: var(--dim); margin-bottom: 4px; letter-spacing: 1px; }
.disk-bar { height: 3px; background: var(--border); border-radius: 2px; overflow: hidden; }
.disk-fill { height: 100%; background: linear-gradient(90deg, var(--coral2), var(--coral)); transition: width .6s ease; }
.disk-text { font-size: 10px; color: var(--dim); margin-top: 4px; }

/* ── MAIN ────────────────────────────────────────────────────────── */
.main {
  flex: 1;
  overflow-y: auto;
  min-width: 0;
}

/* header strip */
.topbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 20px;
  padding: 12px 32px;
  border-bottom: 1px solid var(--border);
  background: var(--bg2);
  position: sticky;
  top: 0;
  z-index: 100;
}

.producing-badge {
  display: none;
  align-items: center;
  gap: 6px;
  font-size: 10px;
  letter-spacing: 2px;
  color: var(--coral);
  font-weight: 700;
}
.producing-badge.active { display: flex; }
.producing-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--coral);
  box-shadow: 0 0 10px var(--coral);
  animation: pulse .7s ease-in-out infinite;
}
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.25} }

#clock { color: var(--dim); font-size: 11px; }

.content { padding: 28px 32px; }

/* section titles */
h2 {
  font-family: 'Fraunces', serif;
  font-weight: 700;
  font-size: 16px;
  color: var(--cream);
  letter-spacing: .5px;
  margin-bottom: 14px;
}
h2 small {
  font-family: 'Space Mono', monospace;
  font-size: 10px;
  color: var(--dim);
  font-weight: 400;
  letter-spacing: 2px;
  margin-left: 10px;
  text-transform: uppercase;
}

section { margin-bottom: 36px; }

/* ── KPI row ─────────────────────────────────────────────────────── */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 36px;
}

.kpi {
  background: var(--bg2);
  border: 1px solid var(--border);
  padding: 20px 22px 16px;
  position: relative;
  overflow: hidden;
}

.kpi::after {
  content: '';
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--coral), transparent);
  opacity: .4;
}

.kpi-label {
  font-size: 9px;
  letter-spacing: 3px;
  color: var(--dim);
  text-transform: uppercase;
  margin-bottom: 10px;
}

.kpi-value {
  font-family: 'Fraunces', serif;
  font-weight: 900;
  font-size: 54px;
  color: var(--coral);
  line-height: 1;
  letter-spacing: -2px;
}

.kpi-sub { font-size: 10px; color: var(--dim); margin-top: 6px; }

.kpi-prog {
  height: 1px;
  background: var(--border);
  margin-top: 12px;
}
.kpi-prog-fill {
  height: 100%;
  background: var(--coral);
  opacity: .6;
  transition: width .8s ease;
}

/* ── two-col layout ──────────────────────────────────────────────── */
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }

/* ── production slates ───────────────────────────────────────────── */
.mode-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.slate {
  background: var(--bg2);
  border: 1px solid var(--border);
  padding: 14px 16px;
  position: relative;
  overflow: hidden;
  transition: border-color .15s, background .15s;
}
.slate:hover { border-color: var(--coral); background: var(--bg3); }
.slate::before {
  /* clapperboard corner mark */
  content: '';
  position: absolute;
  top: 0; right: 0;
  width: 18px; height: 18px;
  background: linear-gradient(225deg, var(--border2) 50%, transparent 50%);
  transition: background .15s;
}
.slate:hover::before { background: linear-gradient(225deg, var(--coral) 50%, transparent 50%); }

.slate-icon { font-size: 20px; margin-bottom: 6px; display: block; }

.slate-name {
  font-family: 'Fraunces', serif;
  font-weight: 700;
  font-size: 15px;
  color: var(--cream);
  line-height: 1.1;
  margin-bottom: 2px;
}

.slate-desc { font-size: 10px; color: var(--dim); margin-bottom: 10px; line-height: 1.4; }

.slate-controls { display: flex; align-items: center; gap: 8px; }

.cnt-btn {
  background: var(--bg3);
  border: 1px solid var(--border2);
  color: var(--cream2);
  width: 22px; height: 22px;
  font-size: 15px;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all .1s;
  flex-shrink: 0;
}
.cnt-btn:hover { background: var(--coral); border-color: var(--coral); color: #000; }

.cnt-val {
  font-family: 'Fraunces', serif;
  font-size: 22px;
  font-weight: 900;
  color: var(--coral);
  width: 22px;
  text-align: center;
  line-height: 1;
}

.run-btn {
  margin-left: auto;
  background: transparent;
  border: 1px solid var(--coral);
  color: var(--coral);
  font-family: 'Space Mono', monospace;
  font-size: 10px;
  letter-spacing: 2px;
  padding: 5px 12px;
  cursor: pointer;
  transition: all .15s;
  text-transform: uppercase;
}
.run-btn:hover  { background: var(--coral); color: #000; }
.run-btn:disabled { opacity: .35; cursor: default; }
.run-btn.active  {
  background: rgba(255,107,53,.12);
  border-color: var(--coral);
  color: var(--coral);
  animation: pulse .7s ease infinite;
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
  font-family: 'Space Mono', monospace;
  font-size: 9px;
  letter-spacing: 2px;
  padding: 3px 8px;
  cursor: pointer;
  transition: all .15s;
}
.term-clear:hover { border-color: var(--coral); color: var(--coral); }

.terminal {
  background: #050302;
  border: 1px solid var(--border);
  border-top: 2px solid var(--coral);
  height: 340px;
  overflow-y: auto;
  padding: 14px 16px;
  font-size: 11px;
  line-height: 1.65;
}

.tl { color: var(--cream2); }
.tl.ok   { color: var(--mint); }
.tl.err  { color: var(--red); }
.tl.sys  { color: var(--dim); font-style: italic; }
.tl.done { color: var(--coral); font-weight: 700; }
.tl.prompt { color: var(--coral); }

/* ── heatmap strip ───────────────────────────────────────────────── */
.heatmap {
  display: flex;
  gap: 4px;
  align-items: flex-end;
  margin-bottom: 20px;
}
.hm-col { display: flex; flex-direction: column; align-items: center; gap: 3px; }
.hm-block {
  width: 32px; height: 32px;
  background: var(--bg3);
  border: 1px solid var(--border);
  transition: background .4s ease;
  position: relative;
}
.hm-block[data-tip]:hover::after {
  content: attr(data-tip);
  position: absolute;
  bottom: 38px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--bg4);
  border: 1px solid var(--border2);
  color: var(--cream);
  font-size: 10px;
  padding: 3px 8px;
  white-space: nowrap;
  pointer-events: none;
}
.hm-date { font-size: 9px; color: var(--dim); letter-spacing: -.5px; }

/* ── tables ──────────────────────────────────────────────────────── */
.table-wrap { max-height: 320px; overflow-y: auto; }

table { width: 100%; border-collapse: collapse; font-size: 11px; }

th {
  text-align: left;
  padding: 7px 12px;
  color: var(--dim);
  letter-spacing: 2px;
  font-size: 9px;
  border-bottom: 1px solid var(--border);
  font-weight: 400;
  text-transform: uppercase;
  position: sticky; top: 0;
  background: var(--bg2);
}

td {
  padding: 8px 12px;
  border-bottom: 1px solid rgba(42,36,32,.8);
  color: var(--cream2);
  vertical-align: middle;
}
tr:hover td { background: var(--bg3); color: var(--cream); }

.pill {
  display: inline-block;
  padding: 2px 8px;
  font-size: 9px;
  letter-spacing: 1px;
  text-transform: uppercase;
}
.pill-done { background: rgba(124,255,164,.08); color: var(--mint); border: 1px solid rgba(124,255,164,.2); }
.pill-pend { background: rgba(107,96,88,.1);   color: var(--dim); border: 1px solid var(--border); }
.pill-mode { background: rgba(255,107,53,.08);  color: var(--coral); border: 1px solid rgba(255,107,53,.2); }

.yt-link { color: var(--coral); text-decoration: none; font-size: 10px; }
.yt-link:hover { text-decoration: underline; }

/* breakdown */
.breakdown { display: flex; flex-direction: column; gap: 7px; margin-top: 10px; }
.bd-row { display: flex; align-items: center; gap: 10px; }
.bd-label { width: 90px; font-size: 10px; color: var(--dim); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.bd-bar { flex: 1; height: 4px; background: var(--border); }
.bd-fill { height: 100%; background: var(--coral); opacity: .7; transition: width .6s ease; }
.bd-cnt { font-size: 10px; color: var(--coral); width: 28px; text-align: right; }

/* scrollbars */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border2); }
::-webkit-scrollbar-thumb:hover { background: var(--coral); }

@media (max-width: 960px) {
  .kpi-row { grid-template-columns: repeat(2, 1fr); }
  .two-col  { grid-template-columns: 1fr; }
  .sidebar  { width: 180px; }
}
</style>
</head>
<body>

<!-- ── Sidebar ─────────────────────────────────────────────────── -->
<aside class="sidebar">

  <div class="sidebar-logo">
    <span class="logo-word">SUPER<span>SHORTS</span></span>
    <span class="logo-sub">Production Suite</span>
  </div>

  <nav class="nav-section">
    <div class="nav-label">Navigate</div>
    <button class="nav-btn active" onclick="scrollTo('#kpis')">Dashboard</button>
    <button class="nav-btn" onclick="scrollTo('#productions')">Productions</button>
    <button class="nav-btn" onclick="scrollTo('#plan')">Content Plan</button>
    <button class="nav-btn" onclick="scrollTo('#log')">Upload Log</button>
  </nav>

  <div class="nav-section">
    <div class="nav-label">Workflows</div>
    <button class="wf-btn" id="wf-daily" onclick="runWorkflow('daily')">
      <span class="wf-icon">🔁</span>Daily (9 AM)
    </button>
    <button class="wf-btn" id="wf-tcm-weekly" onclick="runWorkflow('tcm-weekly')">
      <span class="wf-icon">🌿</span>TCM Weekly
    </button>
    <button class="wf-btn" id="wf-full-pipeline" onclick="runWorkflow('full-pipeline')">
      <span class="wf-icon">⚡</span>Full Pipeline
    </button>
  </div>

  <div class="sidebar-bottom">
    <div class="ollama-row">
      <div class="led" id="ollama-led"></div>
      <span id="ollama-txt">Ollama —</span>
    </div>
    <div class="disk-label">DISK · OUTPUT</div>
    <div class="disk-bar"><div class="disk-fill" id="disk-fill" style="width:0%"></div></div>
    <div class="disk-text" id="disk-text">— MB</div>
  </div>

</aside>

<!-- ── Main ───────────────────────────────────────────────────── -->
<div class="main">

  <div class="topbar">
    <div class="producing-badge" id="producing-badge">
      <div class="producing-dot"></div>NOW PRODUCING
    </div>
    <div id="clock">--:--:--</div>
  </div>

  <div class="content">

    <!-- KPI row -->
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

    <!-- 7-day heatmap -->
    <section>
      <h2>This Week <small>uploads per day</small></h2>
      <div class="heatmap" id="heatmap"></div>
    </section>

    <!-- Productions -->
    <div class="two-col" id="productions">

      <section>
        <h2>Productions <small>select &amp; run</small></h2>
        <div class="mode-grid" id="mode-grid"></div>
      </section>

      <section>
        <div class="term-header">
          <h2>Live Output <small>sse stream</small></h2>
          <button class="term-clear" onclick="termClear()">CLEAR</button>
        </div>
        <div class="terminal" id="terminal">
          <div class="tl sys">Awaiting production order…</div>
        </div>
      </section>

    </div>

    <!-- Content Plan -->
    <section id="plan">
      <h2>Content Plan <small>educational curriculum</small></h2>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Ch</th><th>Title</th><th>Status</th><th>YouTube</th></tr></thead>
          <tbody id="plan-tbody"></tbody>
        </table>
      </div>
    </section>

    <!-- Upload Log + Breakdown -->
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

  </div><!-- /content -->
</div><!-- /main -->

<script>
// ── State ─────────────────────────────────────────────────────────
const MODES = [
  ["educational","📚","Educational","Curriculum long-form + Short"],
  ["brainrot",   "🧠","Brain Rot",  "Viral sensationalized AI shorts"],
  ["rotgen",     "🎭","RotGen",     "ByteBot character + gameplay"],
  ["tcm",        "🌿","TCM",        "Traditional Chinese Medicine"],
  ["tutorial",   "🎓","Tutorial",   "~10 min deep-dive + linked Short"],
  ["viral",      "🎮","Viral",      "Subway Surfers gameplay overlay"],
  ["ideas",      "💡","YT Ideas",   "Real YT suggestions + scripts"],
  ["learning",   "📈","Learning",   "Analyse uploads, suggest tips"],
  ["package",    "📦","Content Pkg","Expert AI → 5-min video"],
  ["clipper",    "✂️","Clipper",    "Long video → vertical Shorts"],
];

const counts = {};
MODES.forEach(([id]) => counts[id] = 1);
let activeJobs = new Set();
let currentEvt = null;

// ── Scroll nav ────────────────────────────────────────────────────
function scrollTo(sel) {
  const el = document.querySelector(sel);
  if (el) el.scrollIntoView({behavior:'smooth', block:'start'});
}

// ── Build mode grid ───────────────────────────────────────────────
function buildModeGrid() {
  document.getElementById('mode-grid').innerHTML = MODES.map(([id,icon,name,desc]) => `
    <div class="slate" id="slate-${id}">
      <span class="slate-icon">${icon}</span>
      <div class="slate-name">${name}</div>
      <div class="slate-desc">${desc}</div>
      <div class="slate-controls">
        <button class="cnt-btn" onclick="adj('${id}',-1)">−</button>
        <div class="cnt-val" id="cv-${id}">1</div>
        <button class="cnt-btn" onclick="adj('${id}',1)">+</button>
        <button class="run-btn" id="rb-${id}" onclick="runMode('${id}')">RUN ▶</button>
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
  const btn = document.getElementById('rb-'+id);
  btn.textContent = '…'; btn.classList.add('active'); btn.disabled = true;

  const res = await fetch(`/api/run/${id}`, {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({count: counts[id]})
  });
  const {job_id} = await res.json();

  openStream(job_id, () => {
    btn.textContent = 'RUN ▶'; btn.classList.remove('active'); btn.disabled = false;
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

function termClear() { document.getElementById('terminal').innerHTML = ''; }
function termLine(text, cls='') {
  const t = document.getElementById('terminal');
  const d = document.createElement('div');
  d.className = 'tl' + (cls ? ' '+cls : '');
  d.textContent = text;
  t.appendChild(d);
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
    const label = date.slice(5); // MM-DD
    return `<div class="hm-col">
      <div class="hm-block" style="background:${col};border-color:${cnt?'var(--coral2)':'var(--border)'}" data-tip="${date}: ${cnt} upload${cnt!==1?'s':''}"></div>
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
      <td style="color:var(--coral);font-weight:700">${l.chapter}</td>
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
    txt.textContent = h.ollama ? 'Ollama · connected' : 'Ollama · offline';
  } catch(e) {}
}

async function refreshDisk() {
  try {
    const d = await fetch('/api/disk').then(r=>r.json());
    const MAX = 2000; // assume 2GB cap for display
    document.getElementById('disk-fill').style.width = `${Math.min(100, d.output_mb/MAX*100).toFixed(1)}%`;
    document.getElementById('disk-text').textContent = `${d.output_mb} MB output`;
  } catch(e) {}
}

// ── Clock ─────────────────────────────────────────────────────────
function tick() {
  document.getElementById('clock').textContent =
    new Date().toLocaleTimeString('en-US',{hour12:false});
}

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
