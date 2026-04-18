"""
dashboard.py — SuperShorts Web Dashboard
Run: pip install flask && python3 dashboard.py
Visit: http://localhost:5050
"""
import json
import os
import sys
import uuid
import datetime
import subprocess
import threading
from pathlib import Path
from flask import Flask, Response, jsonify, request, stream_with_context

PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

app = Flask(__name__)

# ── job registry ─────────────────────────────────────────────────────────────
JOBS: dict[str, dict] = {}  # job_id -> {proc, output, status, mode}

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

MODE_LABELS = {
    "educational": ("📚", "Educational"),
    "brainrot":    ("🧠", "Brain Rot"),
    "rotgen":      ("🎭", "RotGen"),
    "tcm":         ("🌿", "TCM"),
    "tutorial":    ("🎓", "Tutorial"),
    "viral":       ("🎮", "Viral Gameplay"),
    "ideas":       ("💡", "YT Ideas"),
    "learning":    ("📈", "Learning"),
    "package":     ("📦", "Content Pkg"),
    "clipper":     ("✂️",  "Clipper"),
}

# ── helpers ───────────────────────────────────────────────────────────────────

def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text()) if path.exists() else default
    except Exception:
        return default

def _stats():
    plan      = _read_json(PROJECT_ROOT / "content_plan.json", {"lessons": []})
    brainrot  = _read_json(PROJECT_ROOT / "brainrot_plan.json", {"topics": []})
    rotgen    = _read_json(PROJECT_ROOT / "rotgen_plan.json",   {"videos": []})
    log       = _read_json(PROJECT_ROOT / "performance_log.json", [])
    if not isinstance(log, list): log = []

    today = datetime.date.today().isoformat()
    uploads_today = sum(1 for e in log if str(e.get("timestamp","")).startswith(today))

    lessons   = plan.get("lessons", [])
    ed_done   = sum(1 for l in lessons if l.get("status") == "complete")
    br_topics = brainrot.get("topics", [])
    br_done   = sum(1 for t in br_topics if t.get("status") == "complete")
    rg_vids   = rotgen.get("videos", [])
    rg_done   = sum(1 for v in rg_vids if v.get("status") == "complete")

    modes = {}
    for e in log:
        m = e.get("mode", "unknown")
        modes[m] = modes.get(m, 0) + 1

    return {
        "educational":    {"done": ed_done, "total": len(lessons) or 20},
        "brainrot":       {"done": br_done, "total": len(br_topics)},
        "rotgen":         {"done": rg_done, "total": len(rg_vids)},
        "uploads_today":  uploads_today,
        "uploads_total":  len(log),
        "mode_breakdown": modes,
        "lessons":        lessons,
        "log_recent":     log[-20:] if log else [],
    }

def _stream_job(job_id: str, proc: subprocess.Popen):
    job = JOBS[job_id]
    for line in iter(proc.stdout.readline, b""):
        decoded = line.decode("utf-8", errors="replace").rstrip()
        job["output"].append(decoded)
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

@app.route("/api/run/<mode>", methods=["POST"])
def api_run(mode):
    if mode not in MODE_COMMANDS:
        return jsonify({"error": "unknown mode"}), 400

    count = int(request.json.get("count", 1)) if request.json else 1
    count = max(1, min(10, count))

    code = MODE_COMMANDS[mode].format(count=count)
    cmd  = [sys.executable, "-c",
            f"import sys; sys.path.insert(0,'{PROJECT_ROOT}'); {code}"]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=str(PROJECT_ROOT),
    )
    job_id = str(uuid.uuid4())[:8]
    JOBS[job_id] = {"proc": proc, "output": [], "status": "running", "mode": mode}
    threading.Thread(target=_stream_job, args=(job_id, proc), daemon=True).start()

    return jsonify({"job_id": job_id, "mode": mode, "count": count})

@app.route("/api/stream/<job_id>")
def api_stream(job_id):
    if job_id not in JOBS:
        return jsonify({"error": "job not found"}), 404

    def generate():
        job     = JOBS[job_id]
        sent    = 0
        import time
        while True:
            lines = job["output"]
            while sent < len(lines):
                yield f"data: {lines[sent]}\n\n"
                sent += 1
            if job["status"] != "running":
                yield f"data: [JOB {job_id} {job['status'].upper()}]\n\n"
                break
            time.sleep(0.3)

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

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SUPERSHORTS — Control Room</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=JetBrains+Mono:wght@300;400;700&display=swap" rel="stylesheet">
<style>
  :root {
    --bg:      #080808;
    --bg2:     #111111;
    --bg3:     #1a1a1a;
    --amber:   #f5a623;
    --amber2:  #c47d0a;
    --teal:    #00d4ff;
    --red:     #ff3232;
    --green:   #39ff14;
    --text:    #e8e0d0;
    --dim:     #666;
    --border:  #2a2a2a;
  }

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    min-height: 100vh;
    overflow-x: hidden;
  }

  /* scanlines overlay */
  body::before {
    content: '';
    position: fixed; inset: 0;
    background: repeating-linear-gradient(
      0deg,
      transparent,
      transparent 2px,
      rgba(0,0,0,.15) 2px,
      rgba(0,0,0,.15) 4px
    );
    pointer-events: none;
    z-index: 9999;
  }

  /* ── header ── */
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 32px;
    height: 60px;
    background: var(--bg2);
    border-bottom: 2px solid var(--amber);
    position: sticky; top: 0; z-index: 100;
  }

  .logo {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 32px;
    letter-spacing: 6px;
    color: var(--amber);
    text-shadow: 0 0 20px rgba(245,166,35,.4);
  }

  .logo span { color: var(--teal); }

  .header-right { display: flex; align-items: center; gap: 24px; }

  .live-badge {
    display: flex; align-items: center; gap: 6px;
    font-size: 11px; letter-spacing: 2px; color: var(--teal);
  }
  .live-dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--teal);
    box-shadow: 0 0 8px var(--teal);
    animation: blink 1.2s ease-in-out infinite;
  }
  @keyframes blink { 0%,100%{opacity:1} 50%{opacity:.2} }

  #clock { color: var(--dim); font-size: 12px; }

  /* ── layout ── */
  main { padding: 24px 32px; max-width: 1600px; margin: 0 auto; }

  h2 {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 20px;
    letter-spacing: 4px;
    color: var(--amber);
    margin-bottom: 12px;
    border-bottom: 1px solid var(--border);
    padding-bottom: 6px;
  }

  section { margin-bottom: 32px; }

  /* ── KPI cards ── */
  .kpi-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 32px;
  }

  .kpi {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-top: 2px solid var(--amber);
    padding: 16px 20px;
    position: relative;
    overflow: hidden;
  }
  .kpi::after {
    content: '';
    position: absolute; bottom: 0; left: 0; right: 0; height: 40px;
    background: linear-gradient(to top, rgba(245,166,35,.04), transparent);
  }

  .kpi-label {
    font-size: 10px;
    letter-spacing: 3px;
    color: var(--dim);
    text-transform: uppercase;
    margin-bottom: 8px;
  }

  .kpi-value {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 44px;
    color: var(--amber);
    line-height: 1;
    text-shadow: 0 0 30px rgba(245,166,35,.3);
  }

  .kpi-sub { font-size: 11px; color: var(--dim); margin-top: 4px; }

  /* progress bar inside kpi */
  .kpi-bar {
    height: 2px;
    background: var(--border);
    margin-top: 10px;
    border-radius: 1px;
    overflow: hidden;
  }
  .kpi-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--amber2), var(--amber));
    transition: width .6s ease;
  }

  /* ── two-column layout ── */
  .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }

  /* ── control panel ── */
  .mode-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
  }

  .mode-card {
    background: var(--bg2);
    border: 1px solid var(--border);
    padding: 12px 14px;
    display: flex;
    align-items: center;
    gap: 10px;
    transition: border-color .15s, background .15s;
  }
  .mode-card:hover { border-color: var(--amber); background: var(--bg3); }

  .mode-icon { font-size: 18px; flex-shrink: 0; }

  .mode-info { flex: 1; min-width: 0; }
  .mode-name { font-size: 11px; letter-spacing: 1px; color: var(--text); }
  .mode-controls { display: flex; align-items: center; gap: 6px; margin-top: 6px; }

  .count-btn {
    background: var(--border);
    border: none;
    color: var(--text);
    width: 20px; height: 20px;
    cursor: pointer;
    font-size: 14px;
    display: flex; align-items: center; justify-content: center;
    transition: background .1s;
  }
  .count-btn:hover { background: var(--amber); color: #000; }

  .count-display {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 18px;
    color: var(--amber);
    width: 20px;
    text-align: center;
  }

  .run-btn {
    margin-left: auto;
    background: transparent;
    border: 1px solid var(--amber);
    color: var(--amber);
    font-family: 'Bebas Neue', sans-serif;
    font-size: 13px;
    letter-spacing: 2px;
    padding: 4px 10px;
    cursor: pointer;
    transition: background .15s, color .15s;
    white-space: nowrap;
  }
  .run-btn:hover { background: var(--amber); color: #000; }
  .run-btn:disabled { opacity: .4; cursor: not-allowed; }
  .run-btn.running { border-color: var(--teal); color: var(--teal); animation: pulse .8s ease infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.5} }

  /* ── terminal ── */
  .terminal {
    background: #030303;
    border: 1px solid var(--border);
    border-top: 2px solid var(--teal);
    height: 320px;
    overflow-y: auto;
    padding: 12px 16px;
    font-size: 12px;
    line-height: 1.6;
    scroll-behavior: smooth;
  }

  .terminal-line { color: var(--green); }
  .terminal-line.err { color: var(--red); }
  .terminal-line.sys { color: var(--dim); font-style: italic; }
  .terminal-line.done { color: var(--amber); }

  .terminal-prompt {
    color: var(--teal);
    margin-bottom: 4px;
    font-size: 11px;
    letter-spacing: 1px;
  }

  /* ── tables ── */
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
  }

  th {
    text-align: left;
    padding: 6px 10px;
    color: var(--dim);
    letter-spacing: 2px;
    font-size: 10px;
    border-bottom: 1px solid var(--border);
    font-weight: 400;
    text-transform: uppercase;
  }

  td {
    padding: 7px 10px;
    border-bottom: 1px solid rgba(42,42,42,.5);
    color: var(--text);
  }

  tr:hover td { background: var(--bg3); }

  .status-pill {
    display: inline-block;
    padding: 2px 8px;
    font-size: 10px;
    letter-spacing: 1px;
    text-transform: uppercase;
    border-radius: 2px;
  }
  .status-pill.complete { background: rgba(57,255,20,.1); color: var(--green); border: 1px solid rgba(57,255,20,.3); }
  .status-pill.pending  { background: rgba(102,102,102,.1); color: var(--dim); border: 1px solid var(--border); }

  .mode-badge {
    display: inline-block;
    padding: 2px 6px;
    font-size: 10px;
    background: rgba(245,166,35,.1);
    color: var(--amber);
    border: 1px solid rgba(245,166,35,.2);
    letter-spacing: 1px;
    text-transform: uppercase;
  }

  .yt-link { color: var(--teal); text-decoration: none; }
  .yt-link:hover { text-decoration: underline; }

  .table-wrap { max-height: 340px; overflow-y: auto; }

  /* ── scrollbars ── */
  ::-webkit-scrollbar { width: 4px; height: 4px; }
  ::-webkit-scrollbar-track { background: var(--bg); }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }
  ::-webkit-scrollbar-thumb:hover { background: var(--amber); }

  /* ── mode breakdown ── */
  .breakdown { display: flex; flex-direction: column; gap: 6px; margin-top: 8px; }
  .breakdown-row { display: flex; align-items: center; gap: 10px; }
  .breakdown-label { width: 100px; font-size: 11px; color: var(--dim); }
  .breakdown-bar { flex: 1; height: 6px; background: var(--border); border-radius: 3px; overflow: hidden; }
  .breakdown-fill { height: 100%; background: linear-gradient(90deg, var(--amber2), var(--amber)); transition: width .5s ease; }
  .breakdown-count { font-size: 11px; color: var(--amber); width: 30px; text-align: right; }

  /* ── responsive ── */
  @media (max-width: 900px) {
    .kpi-row { grid-template-columns: repeat(2,1fr); }
    .two-col { grid-template-columns: 1fr; }
  }
</style>
</head>
<body>

<header>
  <div class="logo">SUPER<span>SHORTS</span></div>
  <div class="header-right">
    <div class="live-badge">
      <div class="live-dot"></div>
      CONTROL ROOM
    </div>
    <div id="clock">--:--:--</div>
  </div>
</header>

<main>

  <!-- KPI row -->
  <div class="kpi-row">
    <div class="kpi">
      <div class="kpi-label">Total Uploads</div>
      <div class="kpi-value" id="kpi-total">—</div>
      <div class="kpi-sub" id="kpi-today">— today</div>
    </div>
    <div class="kpi">
      <div class="kpi-label">Educational</div>
      <div class="kpi-value" id="kpi-ed">—</div>
      <div class="kpi-sub" id="kpi-ed-sub">of 20 lessons</div>
      <div class="kpi-bar"><div class="kpi-bar-fill" id="kpi-ed-bar" style="width:0%"></div></div>
    </div>
    <div class="kpi">
      <div class="kpi-label">Brain Rot Topics</div>
      <div class="kpi-value" id="kpi-br">—</div>
      <div class="kpi-sub" id="kpi-br-sub">complete</div>
    </div>
    <div class="kpi">
      <div class="kpi-label">RotGen Videos</div>
      <div class="kpi-value" id="kpi-rg">—</div>
      <div class="kpi-sub" id="kpi-rg-sub">complete</div>
    </div>
  </div>

  <div class="two-col">

    <!-- Control Panel -->
    <section>
      <h2>CONTROL PANEL</h2>
      <div class="mode-grid" id="mode-grid">
        <!-- injected by JS -->
      </div>
    </section>

    <!-- Live Terminal -->
    <section>
      <h2>LIVE OUTPUT</h2>
      <div class="terminal" id="terminal">
        <div class="terminal-line sys">Waiting for job…</div>
      </div>
    </section>

  </div>

  <div class="two-col">

    <!-- Content Plan -->
    <section>
      <h2>CONTENT PLAN</h2>
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>Ch</th><th>Title</th><th>Status</th><th>YT</th>
          </tr></thead>
          <tbody id="plan-tbody"></tbody>
        </table>
      </div>
    </section>

    <!-- Upload Log + Breakdown -->
    <section>
      <h2>UPLOAD LOG</h2>
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>Time</th><th>Mode</th><th>Title</th>
          </tr></thead>
          <tbody id="log-tbody"></tbody>
        </table>
      </div>
      <br>
      <h2>MODE BREAKDOWN</h2>
      <div class="breakdown" id="breakdown"></div>
    </section>

  </div>

</main>

<script>
const MODES = [
  ["educational","📚","Educational"],
  ["brainrot",   "🧠","Brain Rot"],
  ["rotgen",     "🎭","RotGen"],
  ["tcm",        "🌿","TCM"],
  ["tutorial",   "🎓","Tutorial"],
  ["viral",      "🎮","Viral Gameplay"],
  ["ideas",      "💡","YT Ideas"],
  ["learning",   "📈","Learning"],
  ["package",    "📦","Content Pkg"],
  ["clipper",    "✂️","Clipper"],
];

let currentJobId = null;
let currentEvt   = null;
const counts = {};
MODES.forEach(([id]) => counts[id] = 1);

// ── build control panel ───────────────────────────────────────────────────
function buildModeGrid() {
  const grid = document.getElementById('mode-grid');
  grid.innerHTML = MODES.map(([id, icon, label]) => `
    <div class="mode-card" id="card-${id}">
      <div class="mode-icon">${icon}</div>
      <div class="mode-info">
        <div class="mode-name">${label.toUpperCase()}</div>
        <div class="mode-controls">
          <button class="count-btn" onclick="adjustCount('${id}',-1)">−</button>
          <div class="count-display" id="count-${id}">1</div>
          <button class="count-btn" onclick="adjustCount('${id}',1)">+</button>
        </div>
      </div>
      <button class="run-btn" id="run-${id}" onclick="runMode('${id}')">RUN</button>
    </div>
  `).join('');
}

function adjustCount(id, delta) {
  counts[id] = Math.max(1, Math.min(10, (counts[id] || 1) + delta));
  document.getElementById('count-' + id).textContent = counts[id];
}

// ── run mode ─────────────────────────────────────────────────────────────
async function runMode(id) {
  const btn = document.getElementById('run-' + id);
  btn.textContent = '…';
  btn.classList.add('running');
  btn.disabled = true;

  const resp = await fetch(`/api/run/${id}`, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({count: counts[id]})
  });
  const {job_id} = await resp.json();
  currentJobId = job_id;

  termClear();
  termLine(`[${id.toUpperCase()} × ${counts[id]}] started — job ${job_id}`, 'sys');

  if (currentEvt) currentEvt.close();
  currentEvt = new EventSource(`/api/stream/${job_id}`);
  currentEvt.onmessage = e => {
    const line = e.data;
    if (line.startsWith('[JOB')) {
      const isDone = line.includes('DONE');
      termLine(line, isDone ? 'done' : 'err');
      currentEvt.close();
      btn.textContent = 'RUN';
      btn.classList.remove('running');
      btn.disabled = false;
      refreshStats();
    } else {
      const cls = line.startsWith('❌') ? 'err' : '';
      termLine(line, cls);
    }
  };
  currentEvt.onerror = () => {
    btn.textContent = 'RUN';
    btn.classList.remove('running');
    btn.disabled = false;
  };
}

// ── terminal helpers ──────────────────────────────────────────────────────
function termClear() { document.getElementById('terminal').innerHTML = ''; }
function termLine(text, cls='') {
  const t = document.getElementById('terminal');
  const d = document.createElement('div');
  d.className = 'terminal-line' + (cls ? ' ' + cls : '');
  d.textContent = text;
  t.appendChild(d);
  t.scrollTop = t.scrollHeight;
}

// ── stats refresh ─────────────────────────────────────────────────────────
async function refreshStats() {
  const s = await fetch('/api/stats').then(r => r.json());

  document.getElementById('kpi-total').textContent = s.uploads_total;
  document.getElementById('kpi-today').textContent = `${s.uploads_today} today`;

  const ed = s.educational;
  document.getElementById('kpi-ed').textContent = ed.done;
  document.getElementById('kpi-ed-sub').textContent = `of ${ed.total} lessons`;
  document.getElementById('kpi-ed-bar').style.width = `${(ed.done/ed.total)*100}%`;

  const br = s.brainrot;
  document.getElementById('kpi-br').textContent = br.done;
  document.getElementById('kpi-br-sub').textContent = `of ${br.total} topics`;

  const rg = s.rotgen;
  document.getElementById('kpi-rg').textContent = rg.done;
  document.getElementById('kpi-rg-sub').textContent = `of ${rg.total} videos`;

  // content plan table
  const tbody = document.getElementById('plan-tbody');
  tbody.innerHTML = (s.lessons || []).map(l => {
    const yt = l.youtube_id && l.youtube_id.length === 11
      ? `<a class="yt-link" href="https://youtube.com/watch?v=${l.youtube_id}" target="_blank">${l.youtube_id}</a>`
      : '<span style="color:var(--border)">—</span>';
    const pill = l.status === 'complete'
      ? '<span class="status-pill complete">done</span>'
      : '<span class="status-pill pending">pending</span>';
    return `<tr>
      <td>${l.chapter}</td>
      <td style="max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${l.title}</td>
      <td>${pill}</td>
      <td>${yt}</td>
    </tr>`;
  }).join('');

  // upload log
  const log = await fetch('/api/log').then(r => r.json());
  const ltbody = document.getElementById('log-tbody');
  ltbody.innerHTML = [...log].reverse().map(e => {
    const ts = String(e.timestamp || '').slice(0,16).replace('T',' ');
    const badge = `<span class="mode-badge">${e.mode || '?'}</span>`;
    const title = String(e.title || '').slice(0, 50);
    return `<tr><td>${ts}</td><td>${badge}</td><td>${title}</td></tr>`;
  }).join('');

  // breakdown
  const total = s.uploads_total || 1;
  const bd = document.getElementById('breakdown');
  bd.innerHTML = Object.entries(s.mode_breakdown || {})
    .sort((a,b) => b[1]-a[1])
    .slice(0, 8)
    .map(([mode, count]) => `
      <div class="breakdown-row">
        <div class="breakdown-label">${mode}</div>
        <div class="breakdown-bar">
          <div class="breakdown-fill" style="width:${(count/total*100).toFixed(1)}%"></div>
        </div>
        <div class="breakdown-count">${count}</div>
      </div>
    `).join('');
}

// ── clock ─────────────────────────────────────────────────────────────────
function updateClock() {
  document.getElementById('clock').textContent =
    new Date().toLocaleTimeString('en-US', {hour12:false});
}

// ── init ──────────────────────────────────────────────────────────────────
buildModeGrid();
refreshStats();
setInterval(refreshStats, 15000);
setInterval(updateClock, 1000);
updateClock();
</script>
</body>
</html>"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    print(f"🎬 SuperShorts Dashboard → http://localhost:{port}")
    print("   Stop with Ctrl+C")
    app.run(host="0.0.0.0", port=port, threaded=True)
