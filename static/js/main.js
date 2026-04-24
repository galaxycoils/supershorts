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
    { id: 'en_US-ryan-high',      name: 'Adam',    archetype: 'Architect',  img: 'adam_avatar.png',    voice: 'Ryan · High' },
    { id: 'en_US-lessac-high',    name: 'Antoni',  archetype: 'Analyst',    img: 'antoni_avatar.png',  voice: 'Lessac · High' },
    { id: 'en_US-amy-medium',     name: 'Amy',     archetype: 'Runner',     img: 'amy_avatar.png',     voice: 'Amy · Med' },
    { id: 'en_GB-alan-medium',    name: 'Arnold',  archetype: 'Guardian',   img: 'arnold_avatar.png',  voice: 'Alan · Med' },
    { id: 'en_US-hfc_female-medium', name: 'Rachel', archetype: 'Weaver',   img: 'rachel_avatar.png',  voice: 'HFC · Med' },
    { id: 'en_US-joe-medium',     name: 'Joe',     archetype: 'Engineer',   img: 'joe_avatar.png',     voice: 'Joe · Med' },
    { id: 'en_US-kristin-medium', name: 'Kristin', archetype: 'Visionary',  img: 'kristin_avatar.png', voice: 'Kristin · Med' },
];

const POPULAR_TOPICS = [
    "Why AI Will Replace 90% of Jobs by 2030",
    "This Free AI Tool Changes Everything",
    "The Truth About Intermittent Fasting",
    "How Billionaires Think Differently",
    "3 Habits That Rewire Your Brain",
    "Why Most People Never Build Wealth",
    "The Hidden Cost of Social Media",
    "How to Learn Anything 10x Faster",
    "The Science Behind Deep Sleep",
    "Why Your Morning Routine Matters",
    "The Untold History of Cryptocurrency",
    "How to Read 52 Books in a Year",
    "The Real Reason Diets Fail",
    "Why Stoicism Is Going Viral Again",
    "How Top Athletes Train Their Mind",
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
            const total = h.ram_total_gb || 16;
            if (ramTxt) ramTxt.textContent = h.ram_gb + ' / ' + total + ' GB';
            const ramFill = document.getElementById('ram-fill');
            const usedPct = h.ram_pct !== undefined ? h.ram_pct : (h.ram_gb / total * 100);
            if (ramFill) ramFill.style.width = Math.min(100, usedPct) + '%';
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
                            <div style="font-size:9px; color:var(--text-dim); margin-top:2px;">${c.voice}</div>
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
                    <div style="display:flex; align-items:center; gap:10px; margin-bottom:15px;">
                        <button onclick="autoPickTopic()" style="background:rgba(139,92,246,0.15); border:1px solid rgba(139,92,246,0.3); color:#a78bfa; padding:6px 14px; border-radius:8px; cursor:pointer; font-size:12px; font-weight:700;">🎲 Auto from Trending</button>
                        <span style="font-size:11px; color:var(--text-dim);">Picks a random viral subject</span>
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
                    <div style="display:flex; align-items:center; gap:10px; margin-bottom:15px;">
                        <button onclick="autoPickTopic()" style="background:rgba(139,92,246,0.15); border:1px solid rgba(139,92,246,0.3); color:#a78bfa; padding:6px 14px; border-radius:8px; cursor:pointer; font-size:12px; font-weight:700;">🎲 Auto from Trending</button>
                        <span style="font-size:11px; color:var(--text-dim);">Picks a random viral topic</span>
                    </div>
                `;
            }

            body.innerHTML = `
                <div style="width:100%">
                    ${fields}
                    <div class="modal-section-label" style="margin-top:20px; margin-bottom:8px; font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:1px; color:var(--text-dim);">TONE</div>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-bottom:8px;">
                        <button type="button" data-tone="educational" class="tone-btn ${_selectedTone==='educational'?'tone-selected':''}" onclick="setTone('educational')" style="padding:12px; border-radius:8px; border:1px solid ${_selectedTone==='educational'?'#8B5CF6':'#222'}; background:${_selectedTone==='educational'?'rgba(139,92,246,0.12)':'#111'}; color:#fff; cursor:pointer; font-size:14px; font-weight:600; transition:all 0.2s;">🧠 Educational</button>
                        <button type="button" data-tone="funny" class="tone-btn ${_selectedTone==='funny'?'tone-selected':''}" onclick="setTone('funny')" style="padding:12px; border-radius:8px; border:1px solid ${_selectedTone==='funny'?'#8B5CF6':'#222'}; background:${_selectedTone==='funny'?'rgba(139,92,246,0.12)':'#111'}; color:#fff; cursor:pointer; font-size:14px; font-weight:600; transition:all 0.2s;">😂 Funny</button>
                    </div>
                </div>
            `;
            if (_modalData.topic !== undefined) document.getElementById('modal-topic')?.value && (document.getElementById('modal-topic').value = _modalData.topic);
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
                            ${(data.model_info || data.models.map(m=>({name:m,label:m}))).map(mi => {
                                let label = mi.label;
                                if (mi.name === recs.scripting) label += " (Scripting ★)";
                                if (mi.name === recs.reasoning) label += " (Reasoning ★)";
                                if (mi.name === recs.creative) label += " (Creative ★)";
                                return `<option value="${mi.name}" ${_modalData.model === mi.name ? 'selected' : ''}>${label}</option>`;
                            }).join('')}
                        </select>
                        ${data.models.length === 0 ? '<p style="font-size:11px; color:#ef4444; margin-top:6px;">⚠ No Ollama models found. Run: <code>ollama pull llama3.2:3b</code></p>' : ''}
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
                        <label style="display:flex; justify-content:space-between; align-items:center;">
                            LLM TEMPERATURE
                            <span id="temp-val" style="color:var(--accent); font-family:'Fira Code',monospace; font-size:16px; font-weight:800;">${_modalData.temp || '0.7'}</span>
                        </label>
                        <input type="range" id="modal-temp" min="0" max="1" step="0.1" value="${_modalData.temp || '0.7'}" style="width:100%; accent-color:#8B5CF6; margin:10px 0;" oninput="updateTempInfo(this.value)">
                        <div id="temp-info" style="font-size:11px; color:var(--text-dim); background:rgba(139,92,246,0.05); padding:8px 10px; border-radius:6px; border:1px solid var(--border);"></div>
                    </div>
                </div>
            `;
            // Init temp info display
            setTimeout(() => updateTempInfo(_modalData.temp || '0.7'), 0);
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
    document.querySelectorAll('.tone-btn').forEach(btn => {
        const isSel = btn.dataset.tone === t;
        btn.style.borderColor = isSel ? '#8B5CF6' : '#222';
        btn.style.background = isSel ? 'rgba(139,92,246,0.12)' : '#111';
    });
}

function autoPickTopic() {
    const topic = POPULAR_TOPICS[Math.floor(Math.random() * POPULAR_TOPICS.length)];
    const el = document.getElementById('modal-topic');
    if (el) { el.value = topic; el.focus(); }
}

function updateTempInfo(v) {
    document.getElementById('temp-val').textContent = v;
    const info = document.getElementById('temp-info');
    if (!info) return;
    const f = parseFloat(v);
    let label, desc;
    if (f <= 0.2)      { label = '❄️ Very Precise'; desc = 'Near-deterministic. Factual, consistent, no variation. Best for data-heavy or code-heavy scripts.'; }
    else if (f <= 0.4) { label = '📐 Precise'; desc = 'Low creativity. Structured, reliable output. Good for educational or technical content.'; }
    else if (f <= 0.6) { label = '⚖️ Balanced (recommended)'; desc = 'Moderate creativity. Reliable yet engaging. Best for most content types.'; }
    else if (f <= 0.8) { label = '✨ Creative'; desc = 'Higher variation. More expressive, playful tone. Good for entertainment or storytelling.'; }
    else               { label = '🔥 Very Creative'; desc = 'Maximum randomness. Unexpected ideas, sometimes off-topic. Use for brainstorming only.'; }
    info.innerHTML = `<strong style="color:var(--accent)">${label}</strong><br>${desc}`;
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
        stdin_input = '';  // TCM reads from env vars now
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
                tone: _selectedTone,
                tcm_topic: _modalData.tcmTopic || '1',
                tcm_extra: _modalData.topic || '',
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

// ── GLOBAL MODEL SELECT ───────────────────────────────────────────
async function populateGlobalModelSelect() {
    const sel = document.getElementById('global-model');
    if (!sel) return;
    let data;
    try {
        data = await fetch('/api/models').then(r => r.json());
    } catch (e) {
        data = { models: ['llama3', 'mistral'], model_info: [{name:'llama3',label:'llama3'},{name:'mistral',label:'mistral'}], recommendations: {} };
    }
    const recs = data.recommendations || {};
    const modelInfo = data.model_info || (data.models || []).map(m => ({ name: m, label: m }));
    // Remember previously saved model
    const saved = JSON.parse(localStorage.getItem('supershorts_settings') || '{}').model;
    sel.innerHTML = modelInfo.map(mi => {
        let label = mi.label || mi.name;
        if (mi.name === recs.scripting) label += ' (Scripting ★)';
        if (mi.name === recs.reasoning) label += ' (Reasoning ★)';
        if (mi.name === recs.creative)  label += ' (Creative ★)';
        const selected = saved ? mi.name === saved : false;
        return `<option value="${mi.name}" ${selected ? 'selected' : ''}>${label}</option>`;
    }).join('');
}

// ── INIT ──────────────────────────────────────────────────────────
buildModeGrid();
refreshStats();
refreshHealth();
refreshDisk();
refreshGallery();
loadGlobalSettings();
populateGlobalModelSelect();
setInterval(refreshStats, 15000);
setInterval(refreshHealth, 8000);
setInterval(refreshDisk, 30000);
setInterval(() => {
    const clock = document.getElementById('clock');
    if (clock) clock.textContent = new Date().toLocaleTimeString('en-US', { hour12: false });
}, 1000);
