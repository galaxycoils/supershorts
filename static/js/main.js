/* main.js — SuperShorts Frontend Engine */

// ── STATE ──────────────────────────────────────────────────────────
let _modalMode = null;
let _modalStep = 1;
let _selectedChars = [];
let _selectedStyle = null;
let _lastJobId = null;

const MODES = [
    { id: 'brainrot', name: 'Brainrot with Gameplay', desc: 'Drop a topic — AI handles the script, characters, voices & gameplay.', price: 'Free', icon: '💀' },
    { id: 'tcm',      name: 'Teaches', desc: 'Give us your topic — AI writes script, picks visuals & generates everything.', price: 'Free', badge: 'Popular', icon: '🎓' },
    { id: 'viral',    name: 'Storytelling', desc: 'Characters act out a story you describe.', price: 'Free', icon: '🎬' },
    { id: 'clipper',  name: 'Reddit Story', desc: 'Paste a story — AI reads it with captions over gameplay footage.', price: 'Free', badge: 'New', icon: '📱' },
    { id: 'rotgen',   name: 'Custom Editor', desc: 'Full creative control — build your video from scratch.', price: '10 cr', badge: 'Beta', icon: '✏️' }
];

const CHARACTERS = [
    { id: 'en_US-ryan-high', name: 'Adam', img: 'peter.png' },
    { id: 'en_US-lessac-high', name: 'Antoni', img: 'peter_finance.png' },
    { id: 'en_US-amy-medium', name: 'Amy', img: 'stewie.png' },
    { id: 'en_GB-alan-medium', name: 'Arnold', img: 'spongebob.png' },
    { id: 'en_US-hfc_female-medium', name: 'Rachel', img: 'squidward.png' },
    { id: 'en_US-joe-medium', name: 'Joe', img: 'patrick.png' },
    { id: 'en_US-kristin-medium', name: 'Kristin', img: 'trump.png' }
];

// ── NAVIGATION ─────────────────────────────────────────────────────
function navTo(id, btn) {
    document.querySelectorAll('.dashboard-section').forEach(s => s.classList.remove('active'));
    document.querySelector(id).classList.add('active');
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    
    // Close sidebar on mobile
    if (window.innerWidth <= 768) {
        document.getElementById('sidebar').classList.remove('open');
    }
}

document.getElementById('menu-toggle')?.addEventListener('click', () => {
    document.getElementById('sidebar').classList.toggle('open');
});

// ── API SYNC ───────────────────────────────────────────────────────
async function refreshStats() {
    try {
        const s = await fetch('/api/stats').then(r => r.json());
        document.getElementById('kpi-total').textContent = s.uploads_total || 0;
        document.getElementById('kpi-brainrot').textContent = (s.mode_breakdown || {}).brainrot || 0;
        document.getElementById('kpi-edu').textContent = (s.mode_breakdown || {}).educational || 0;
    } catch (e) {}
}

async function refreshHealth() {
    try {
        const h = await fetch('/api/health').then(r => r.json());
        const led = document.getElementById('ollama-led');
        led.className = 'led ' + (h.ollama ? 'on' : 'off');
        document.getElementById('ollama-txt').textContent = h.ollama ? 'ollama · ready' : 'ollama · down';
    } catch (e) {}
}

async function refreshGallery() {
    const videos = await fetch('/api/gallery').then(r => r.json()).catch(() => []);
    const grid = document.getElementById('gallery-grid');
    if (!videos.length) {
        grid.innerHTML = '<div class="tl sys">No productions found.</div>';
        return;
    }
    grid.innerHTML = videos.map(v => `
        <div class="gallery-item">
            <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
                <span class="badge" style="background:var(--accent-gradient); color:#fff; padding:2px 8px; font-size:9px; border-radius:12px; font-weight:700;">MP4</span>
                <span style="font-size:10px; color:var(--text-dim);">${v.size_mb} MB</span>
            </div>
            <div style="font-size:13px; font-weight:600; margin-bottom:6px; color:var(--text); word-break:break-all;">${v.name}</div>
            <div style="font-size:10px; color:var(--text-dim); font-family:'Fira Code',monospace; margin-bottom:16px;">${v.created.slice(0,16).replace('T',' ')}</div>
            <div style="display:flex; gap:8px;">
                <a href="/output/${v.name}" target="_blank" class="nav-btn" style="flex:1; justify-content:center; background:rgba(139,92,246,0.1); color:#8B5CF6; border-radius:8px; padding:8px;">Play ▶</a>
                <a href="/output/${v.name}" download class="nav-btn" style="border:1px solid var(--border); color:var(--text-dim); border-radius:8px; padding:8px;">DL ↓</a>
            </div>
        </div>
    `).join('');
}

// ── MODAL ENGINE ──────────────────────────────────────────────────
function openModal(modeId) {
    _modalMode = modeId;
    _modalStep = 1;
    _selectedChars = [];
    document.getElementById('modal-overlay').style.display = 'flex';
    renderStep();
}

function closeModal() {
    document.getElementById('modal-overlay').style.display = 'none';
}

function modalNextStep() {
    if (_modalStep < 3) {
        _modalStep++;
        renderStep();
    } else {
        launchProduction();
    }
}

function modalPrevStep() {
    if (_modalStep > 1) {
        _modalStep--;
        renderStep();
    }
}

function renderStep() {
    const body = document.getElementById('modal-body');
    const title = document.getElementById('modal-title-el');
    const subtitle = document.getElementById('modal-subtitle-el');
    const nextBtn = document.getElementById('btn-modal-next');
    const indicator = document.getElementById('modal-steps-indicator');
    const backBtn = document.getElementById('modal-back');

    backBtn.style.visibility = _modalStep === 1 ? 'hidden' : 'visible';
    indicator.textContent = `STEP ${_modalStep} / 3`;
    nextBtn.textContent = _modalStep === 3 ? 'FINALIZE & RUN ▶' : 'CONTINUE';

    if (_modalStep === 1) {
        title.textContent = "Choose a Character";
        subtitle.textContent = "Select up to 4 AI avatars for this video.";
        body.innerHTML = `
            <div class="character-grid">
                ${CHARACTERS.map(c => `
                    <div class="char-card ${_selectedChars.includes(c.id)?'selected':''}" onclick="toggleChar('${c.id}')">
                        <div class="char-img" style="background-image:url('/static/img/${c.img}')"></div>
                        <div class="char-name">${c.name}</div>
                    </div>
                `).join('')}
            </div>
        `;
        nextBtn.disabled = _selectedChars.length === 0;
    } else if (_modalStep === 2) {
        title.textContent = "Topic & Script";
        subtitle.textContent = "What should this video be about?";
        body.innerHTML = `
            <div class="field">
                <label>TOPIC</label>
                <textarea id="modal-topic" placeholder="Write your topic here... e.g. Why AI is taking over the world" style="width:100%; height:120px; background:var(--surface); border:1px solid var(--border); border-radius:12px; color:#fff; padding:12px; font-family:inherit; outline:none; border-color:#10b981;"></textarea>
            </div>
            <div class="modal-section-label">TONE</div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px">
                <div class="char-card selected" style="padding:12px; height:auto">🧠 Educational</div>
                <div class="char-card" style="padding:12px; height:auto">😂 Funny</div>
            </div>
        `;
    } else {
        title.textContent = "Production Knobs";
        subtitle.textContent = "Fine-tune the rendering engine.";
        body.innerHTML = `
            <div class="field">
                <label>PIPELINE MODE</label>
                <div style="display:flex; gap:8px">
                    <button class="nav-btn active" style="flex:1; justify-content:center; border:1px solid var(--border); border-radius:12px;" id="btn-prod" onclick="setDry(false)">Production</button>
                    <button class="nav-btn" style="flex:1; justify-content:center; border:1px solid var(--border); border-radius:12px;" id="btn-dry" onclick="setDry(true)">Dry Run</button>
                </div>
            </div>
            <div class="field">
                <label>LLM TEMPERATURE</label>
                <input type="range" id="modal-temp" min="0" max="1" step="0.1" value="0.7" style="width:100%">
            </div>
        `;
    }
}

function toggleChar(id) {
    if (_selectedChars.includes(id)) {
        _selectedChars = _selectedChars.filter(x => x !== id);
    } else if (_selectedChars.length < 4) {
        _selectedChars.push(id);
    }
    renderStep();
}

// ── PRODUCTION ─────────────────────────────────────────────────────
async function launchProduction() {
    const topic = document.getElementById('modal-topic')?.value || '';
    const dryRun = document.getElementById('btn-dry')?.classList.contains('active') ? 'y' : 'n';
    const voice = _selectedChars[0] || 'en_US-ryan-high';
    
    closeModal();
    termLine(`🚀 Initializing ${_modalMode} pipeline...`, 'ok');
    
    const res = await fetch(`/api/run/${_modalMode}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            count: 1,
            stdin_input: topic + '\n',
            dry_run: dryRun,
            voice: voice,
            temperature: document.getElementById('modal-temp')?.value || '0.7'
        })
    });
    
    const { job_id } = await res.json();
    openStream(job_id);
}

function openStream(job_id) {
    _lastJobId = job_id;
    document.getElementById('producing-badge').classList.add('active');
    
    const evt = new EventSource(`/api/stream/${job_id}`);
    evt.onmessage = e => {
        if (e.data === '[DONE]') {
            evt.close();
            document.getElementById('producing-badge').classList.remove('active');
            termLine(`✅ Job ${job_id} complete.`, 'ok');
            refreshGallery();
            refreshStats();
            return;
        }
        termLine(e.data);
    };
    evt.onerror = () => evt.close();
}

function termLine(text, cls = '') {
    const term = document.getElementById('terminal');
    const line = document.createElement('div');
    line.className = 'tl ' + cls;
    line.textContent = text;
    term.appendChild(line);
    term.scrollTop = term.scrollHeight;
}

function termClear() {
    document.getElementById('terminal').innerHTML = '<div class="tl sys">Terminal cleared...<span class="term-cursor"></span></div>';
}

function buildModeGrid() {
    const grid = document.getElementById('mode-grid');
    grid.innerHTML = MODES.map(m => `
        <div class="mode-card" onclick="openModal('${m.id}')">
            <div class="mode-icon">${m.icon}</div>
            <div style="display:flex; align-items:center; gap:8px">
                <div class="mode-name">${m.name}</div>
                ${m.badge ? `<span class="badge" style="background:#8B5CF6; font-size:9px; padding:2px 6px; border-radius:4px;">${m.badge}</span>` : ''}
            </div>
            <div class="mode-desc">${m.desc}</div>
            <div style="margin-top:auto; padding-top:16px; color:#10b981; font-weight:700; font-size:12px;">${m.price}</div>
        </div>
    `).join('');
}

// ── INIT ──────────────────────────────────────────────────────────
buildModeGrid();
refreshStats();
refreshHealth();
refreshGallery();
setInterval(refreshStats, 15000);
setInterval(refreshHealth, 8000);
setInterval(() => {
    document.getElementById('clock').textContent = new Date().toLocaleTimeString('en-US', { hour12: false });
}, 1000);
