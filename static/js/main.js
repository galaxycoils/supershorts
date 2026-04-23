/* main.js — SuperShorts Frontend Engine (v3.1) */

// ── STATE ──────────────────────────────────────────────────────────
let _modalMode = null;
let _modalStep = 1;
let _selectedChars = [];
let _selectedTone = 'educational';
let _lastJobId = null;
let _modalData = {}; // Store inputs across steps

const MODES = [
    { id: 'tcm',      name: 'Educational (TCM)', desc: 'Knowledge curriculum production on autopilot.', price: 'Free', badge: 'Popular', icon: '🎓' },
    { id: 'brainrot', name: 'Brainrot (Viral)', desc: 'High-engagement viral facts over gameplay footage.', price: 'Free', icon: '💀' },
    { id: 'rotgen',   name: 'RotGen Character', desc: 'Split-screen AI character stories & gameplay.', price: 'Free', badge: 'New', icon: '✏️' },
    { id: 'tutorial', name: 'Tutorial Maker', desc: 'Step-by-step coding or technical guides.', price: 'Free', icon: '📖' },
    { id: 'viral',    name: 'Viral Stories', desc: 'Dynamic storytelling with AI actors.', price: 'Free', icon: '🎬' },
    { id: 'clipper',  name: 'Video Clipper', desc: 'Long-form to vertical short-form transformation.', price: 'Free', icon: '📱' },
    { id: 'ideas',    name: 'YT Studio Ideas', desc: 'Generate viral video concepts from trends.', price: 'Free', icon: '💡' },
    { id: 'package',  name: 'Content Package', desc: 'Bundle scripts, assets, and metadata.', price: 'Free', icon: '📦' },
    { id: 'learning', name: 'Smart Optimizer', desc: 'Self-improving production feedback loop.', price: 'Free', icon: '🧠' },
    { id: 'educational', name: 'Standard Edu', desc: 'Traditional automated educational shorts.', price: 'Free', icon: '🏫' }
];

const CHARACTERS = [
    { id: 'en_US-ryan-high', name: 'Adam', archetype: 'Architect', img: 'peter.png' },
    { id: 'en_US-lessac-high', name: 'Antoni', archetype: 'Analyst', img: 'peter_finance.png' },
    { id: 'en_US-amy-medium', name: 'Amy', archetype: 'Runner', img: 'stewie.png' },
    { id: 'en_GB-alan-medium', name: 'Arnold', archetype: 'Guardian', img: 'spongebob.png' },
    { id: 'en_US-hfc_female-medium', name: 'Rachel', archetype: 'Weaver', img: 'squidward.png' },
    { id: 'en_US-joe-medium', name: 'Joe', archetype: 'Engineer', img: 'patrick.png' },
    { id: 'en_US-kristin-medium', name: 'Kristin', archetype: 'Visionary', img: 'trump.png' }
];

// ── NAVIGATION ─────────────────────────────────────────────────────
function navTo(id, btn) {
    document.querySelectorAll('.dashboard-section').forEach(s => s.classList.remove('active'));
    const section = document.querySelector(id);
    if (section) section.classList.add('active');
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    if (window.innerWidth <= 768) document.getElementById('sidebar').classList.remove('open');
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
        document.getElementById('kpi-edu').textContent = (s.mode_breakdown || {}).educational || (s.mode_breakdown || {}).tcm || 0;
    } catch (e) {}
}

async function refreshHealth() {
    try {
        const h = await fetch('/api/health').then(r => r.json());
        const led = document.getElementById('ollama-led');
        led.className = h.ollama ? 'led on' : 'led off';
        document.getElementById('ollama-txt').textContent = h.ollama ? 'ollama · ready' : 'ollama · down';
        if (h.ram_gb !== undefined) {
            const ramTxt = document.getElementById('ram-text');
            if (ramTxt) ramTxt.textContent = h.ram_gb + ' GB';
            const ramFill = document.getElementById('ram-fill');
            if (ramFill) ramFill.style.width = Math.min(100, (h.ram_gb / 16) * 100) + '%';
        }
    } catch (e) {}
}

async function refreshDisk() {
    try {
        const d = await fetch('/api/disk').then(r => r.json());
        const text = document.getElementById('disk-text');
        const fill = document.getElementById('disk-fill');
        if (text) text.textContent = d.output_mb + ' MB';
        if (fill) fill.style.width = Math.min(100, (d.output_mb / 1024) * 100) + '%';
    } catch (e) {}
}

async function refreshGallery() {
    const videos = await fetch('/api/gallery').then(r => r.json()).catch(() => []);
    const grid = document.getElementById('gallery-grid');
    if (!grid) return;
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
async function openModal(modeId) {
    _modalMode = modeId;
    _modalStep = 1;
    _selectedChars = [];
    _selectedTone = 'educational';
    _modalData = {}; 
    _modalData.availableModels = await fetch('/api/models').then(r => r.json()).catch(() => ({models:['llama3'], recommendations:{}}));
    document.getElementById('modal-overlay').style.display = 'flex';
    renderStep();
}

function closeModal() {
    document.getElementById('modal-overlay').style.display = 'none';
}

function modalNextStep() {
    if (_modalStep === 2) {
        _modalData.topic = document.getElementById('modal-topic')?.value || '';
        if (_modalMode === 'tcm') {
            _modalData.tcmTopic = document.getElementById('tcm-topic')?.value || '1';
            _modalData.tcmCount = document.getElementById('tcm-count')?.value || '3';
        }
        if (_modalMode === 'brainrot') {
            _modalData.autoGen = document.getElementById('auto-gen-toggle')?.checked;
        }
    }
    
    if (_modalStep < 3) {
        _modalStep++;
        renderStep();
    } else {
        _modalData.dryRun = document.getElementById('btn-dry')?.classList.contains('active');
        _modalData.temp = document.getElementById('modal-temp')?.value || '0.7';
        _modalData.model = document.getElementById('modal-model')?.value;
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
    try {
        const body = document.getElementById('modal-body');
        const title = document.getElementById('modal-title-el');
        const subtitle = document.getElementById('modal-subtitle-el');
        const nextBtn = document.getElementById('btn-modal-next');
        const indicator = document.getElementById('modal-steps-indicator');
        const backBtn = document.getElementById('modal-back');

        if (!body || !title || !nextBtn) return;

        backBtn.style.visibility = _modalStep === 1 ? 'hidden' : 'visible';
        indicator.textContent = `STEP ${_modalStep} / 3`;
        nextBtn.textContent = _modalStep === 3 ? 'FINALIZE & RUN ▶' : 'CONTINUE';
        nextBtn.disabled = false;

        const hint = document.getElementById('modal-hint');
        if (_modalStep === 1) hint.textContent = "select at least one character";
        else if (_modalStep === 2) hint.textContent = "describe your vision or use defaults";
        else hint.textContent = "final verification before launch";

        if (_modalStep === 1) {
            title.textContent = "Choose Characters";
            subtitle.textContent = "Select up to 4 AI avatars for this video.";
            body.innerHTML = `
                <div class="character-grid">
                    ${CHARACTERS.map(c => `
                        <div class="char-card ${_selectedChars.includes(c.id)?'selected':''}" onclick="toggleChar('${c.id}')">
                            <div class="char-img-container">
                                <div class="char-img" style="background-image:url('/static/img/${c.img}'), linear-gradient(135deg, #1e293b, #0f172a)"></div>
                                <div class="char-archetype-tag">${c.archetype}</div>
                            </div>
                            <div class="char-name">${c.name}</div>
                        </div>
                    `).join('')}
                </div>
            `;
            nextBtn.disabled = _selectedChars.length === 0;
        } else if (_modalStep === 2) {
            title.textContent = "Topic & Script";
            subtitle.textContent = "Configure the content for " + _modalMode;
            
            let fields = '';
            if (_modalMode === 'tcm') {
                fields = `
                    <div class="field">
                        <label>TOPIC FOCUS</label>
                        <select id="tcm-topic" style="width:100%; background:#111; border:1px solid #222; color:#fff; padding:10px; border-radius:8px;">
                            <option value="1">Traditional Chinese Medicine</option>
                            <option value="2">Eastern Medicine</option>
                            <option value="3">Ayurvedic Medicine</option>
                            <option value="4">Holistic Wellness</option>
                            <option value="5">Custom...</option>
                        </select>
                    </div>
                    <div class="field">
                        <label>EXTRA DETAILS</label>
                        <textarea id="modal-topic" placeholder="e.g. focus on anxiety, sleep..." style="width:100%; height:80px; background:#111; border:1px solid #222; border-radius:8px; color:#fff; padding:12px;"></textarea>
                    </div>
                    <div class="field">
                        <label>VIDEOS TO GENERATE</label>
                        <input type="number" id="tcm-count" value="3" min="1" max="10" style="background:#111; border:1px solid #222; color:#fff; padding:10px; border-radius:8px; width:80px;">
                    </div>
                `;
            } else if (_modalMode === 'brainrot') {
                fields = `
                    <div class="field">
                        <label>TOPIC / HOOK</label>
                        <textarea id="modal-topic" placeholder="Write a specific topic or leave blank for auto-generate" style="width:100%; height:100px; background:#111; border:1px solid #222; border-radius:8px; color:#fff; padding:12px;"></textarea>
                    </div>
                    <div style="display:flex; align-items:center; gap:10px; margin-bottom:15px;">
                        <label class="switch" style="width:34px; height:18px;">
                            <input type="checkbox" id="auto-gen-toggle" checked>
                            <span class="slider" style="border-radius:18px;"></span>
                        </label>
                        <span style="font-size:12px; color:var(--text-dim);">Auto-generate from viral trends</span>
                    </div>
                `;
            } else {
                fields = `
                    <div class="field">
                        <label>TOPIC OR URL</label>
                        <textarea id="modal-topic" placeholder="Write your topic here or paste a URL..." style="width:100%; height:100px; background:#111; border:1px solid #222; border-radius:8px; color:#fff; padding:12px;"></textarea>
                    </div>
                `;
            }
            
            body.innerHTML = `
                <div style="width:100%">
                    ${fields}
                    <div class="modal-section-label" style="margin-top:20px;">TONE</div>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px">
                        <div class="char-card ${_selectedTone==='educational'?'selected':''}" style="padding:12px; height:auto; border-radius:8px;" onclick="setTone('educational')">🧠 Educational</div>
                        <div class="char-card ${_selectedTone==='funny'?'selected':''}" style="padding:12px; height:auto; border-radius:8px;" onclick="setTone('funny')">😂 Funny</div>
                    </div>
                </div>
            `;
            if (_modalData.topic !== undefined) document.getElementById('modal-topic').value = _modalData.topic;
            if (_modalMode === 'tcm' && _modalData.tcmTopic) document.getElementById('tcm-topic').value = _modalData.tcmTopic;
            if (_modalMode === 'tcm' && _modalData.tcmCount) document.getElementById('tcm-count').value = _modalData.tcmCount;
            if (_modalMode === 'brainrot' && _modalData.autoGen !== undefined) document.getElementById('auto-gen-toggle').checked = _modalData.autoGen;

        } else {
            const data = _modalData.availableModels || {models:['llama3'], recommendations:{}};
            title.textContent = "Production Knobs";
            subtitle.textContent = "Fine-tune the rendering engine.";
            
            const recs = data.recommendations || {};
            const recList = Object.entries(recs).map(([k, v]) => `<li><b>${k}:</b> ${v}</li>`).join('');

            body.innerHTML = `
                <div style="width:100%">
                    <div class="field">
                        <label>LLM MODEL</label>
                        <select id="modal-model" style="width:100%; background:#111; border:1px solid #222; color:#fff; padding:10px; border-radius:8px;">
                            ${data.models.map(m => {
                                let label = m;
                                if (m === recs.scripting) label += " (Scripting ★)";
                                if (m === recs.reasoning) label += " (Reasoning ★)";
                                if (m === recs.creative) label += " (Creative ★)";
                                return `<option value="${m}" ${_modalData.model === m ? 'selected' : ''}>${label}</option>`;
                            }).join('')}
                        </select>
                    </div>
                    ${recList ? `<div style="font-size:11px; color:var(--text-dim); margin-bottom:15px; background:rgba(139,92,246,0.05); padding:10px; border-radius:8px; border:1px solid var(--border)">
                        <div style="font-weight:700; color:var(--accent); margin-bottom:4px; text-transform:uppercase; letter-spacing:1px">System Recommendations</div>
                        <ul style="padding-left:15px">${recList}</ul>
                    </div>` : ''}
                    <div class="field">
                        <label>PIPELINE MODE</label>
                        <div style="display:flex; gap:8px">
                            <button class="nav-btn ${_modalData.dryRun === false || _modalData.dryRun === undefined ? 'active' : ''}" style="flex:1; justify-content:center; border:1px solid var(--border); border-radius:12px;" id="btn-prod" onclick="setDry(false)">Production</button>
                            <button class="nav-btn ${_modalData.dryRun === true ? 'active' : ''}" style="flex:1; justify-content:center; border:1px solid var(--border); border-radius:12px;" id="btn-dry" onclick="setDry(true)">Dry Run</button>
                        </div>
                    </div>
                    <div class="field">
                        <label>LLM TEMPERATURE: <span id="temp-val" style="color:var(--accent)">${_modalData.temp || '0.7'}</span></label>
                        <p style="font-size:11px; color:var(--text-dim); margin-bottom:8px;">0.0 = Precise/Technical | 1.0 = Creative/Random</p>
                        <input type="range" id="modal-temp" min="0" max="1" step="0.1" value="${_modalData.temp || '0.7'}" style="width:100%; accent-color:#8B5CF6;" oninput="document.getElementById('temp-val').textContent=this.value">
                    </div>
                </div>
            `;
        }
    } catch (e) {
        console.error("Render error:", e);
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

function setTone(t) {
    _selectedTone = t;
    renderStep();
}

function setDry(val) {
    _modalData.dryRun = val;
    const prodBtn = document.getElementById('btn-prod');
    const dryBtn = document.getElementById('btn-dry');
    if (prodBtn) prodBtn.classList.toggle('active', !val);
    if (dryBtn) dryBtn.classList.toggle('active', val);
}

// ── PRODUCTION ─────────────────────────────────────────────────────
async function launchProduction() {
    const mode = _modalMode;
    const dry_run = _modalData.dryRun ? 'y' : 'n';
    const voice = _selectedChars[0] || 'en_US-ryan-high';
    const temp = _modalData.temp || '0.7';
    const model = _modalData.model || document.getElementById('global-model')?.value || 'llama3';
    
    let stdin_input = '';
    let count = 1;
    
    if (mode === 'tcm') {
        count = parseInt(_modalData.tcmCount) || 3;
        stdin_input = `n\n${_modalData.tcmTopic}\n${_modalData.topic}\n${count}\n`;
    } else if (mode === 'brainrot') {
        stdin_input = _modalData.autoGen ? '\n' : (_modalData.topic + '\n');
    } else {
        stdin_input = (_modalData.topic || '') + '\n';
    }
    
    closeModal();
    termLine(`🚀 Initializing ${mode} pipeline...`, 'ok');
    
    try {
        const res = await fetch(`/api/run/${mode}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                count: count,
                stdin_input: stdin_input,
                dry_run: dry_run,
                voice: voice,
                temperature: temp,
                llm_model: model,
                tone: _selectedTone
            })
        });
        const data = await res.json();
        if (data.job_id) openStream(data.job_id);
        else if (data.error) termLine(`❌ Error: ${data.error}`, 'err');
    } catch (e) {
        termLine(`❌ Fetch Error: ${e.message}`, 'err');
    }
}

function openStream(job_id) {
    _lastJobId = job_id;
    const badge = document.getElementById('producing-badge');
    if (badge) badge.classList.add('active');
    const evt = new EventSource(`/api/stream/${job_id}`);
    evt.onmessage = e => {
        if (e.data === '[DONE]') {
            evt.close();
            if (badge) badge.classList.remove('active');
            termLine(`✅ Job ${job_id} complete.`, 'ok');
            refreshGallery();
            refreshStats();
            return;
        }
        termLine(e.data);
    };
    evt.onerror = () => {
        evt.close();
        if (badge) badge.classList.remove('active');
    };
}

function termLine(text, cls = '') {
    const term = document.getElementById('terminal');
    if (!term) return;
    const line = document.createElement('div');
    line.className = 'tl ' + cls;
    line.textContent = text;
    term.appendChild(line);
    term.scrollTop = term.scrollHeight;
}

function termClear() {
    const term = document.getElementById('terminal');
    if (term) term.innerHTML = '<div class="tl sys">Terminal cleared...<span class="term-cursor"></span></div>';
}

function buildModeGrid() {
    const grid = document.getElementById('mode-grid');
    if (!grid) return;
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

function saveGlobalSettings() {
    const author = document.getElementById('global-author')?.value;
    const model = document.getElementById('global-model')?.value;
    const advanced = document.getElementById('adv-toggle')?.checked;
    localStorage.setItem('supershorts_settings', JSON.stringify({author, model, advanced}));
    termLine(`⚙️ Settings saved.`, 'ok');
}

function loadGlobalSettings() {
    const s = JSON.parse(localStorage.getItem('supershorts_settings') || '{}');
    if (s.author && document.getElementById('global-author')) document.getElementById('global-author').value = s.author;
    if (s.model && document.getElementById('global-model')) document.getElementById('global-model').value = s.model;
    if (s.advanced && document.getElementById('adv-toggle')) {
        document.getElementById('adv-toggle').checked = true;
        document.body.classList.add('advanced-mode-active');
    }
}

function toggleAdvancedMode() {
    const isAdv = document.getElementById('adv-toggle')?.checked;
    document.body.classList.toggle('advanced-mode-active', isAdv);
    saveGlobalSettings();
}

// ── INIT ──────────────────────────────────────────────────────────
buildModeGrid();
refreshStats();
refreshHealth();
refreshDisk();
refreshGallery();
loadGlobalSettings();
setInterval(refreshStats, 15000);
setInterval(refreshHealth, 8000);
setInterval(refreshDisk, 30000);
setInterval(() => {
    const clock = document.getElementById('clock');
    if (clock) clock.textContent = new Date().toLocaleTimeString('en-US', { hour12: false });
}, 1000);
