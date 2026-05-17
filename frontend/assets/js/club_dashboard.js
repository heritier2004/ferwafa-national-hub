/**
 * Professional Club Dashboard Engine
 * Handles State Management, Navigation, and Live AI Intelligence
 */

const ClubDashboard = {
    state: {
        currentModule: 'overview',
        institutionId: localStorage.getItem('institution_id') || 1,
        token: localStorage.getItem('access_token'),
        players: [],
        matches: [],
        activeMatchId: null,
        ws: null,
        matchTimer: 0,
        timerInterval: null,
        playerTrails: {} // Store { id: [ {x,y}, ... ] }
    },

    init() {
        this.verifyAccess();
        this.bindEvents();
        this.loadModule('overview');
        this.loadInitialData();
    },

    verifyAccess() {
        const role = localStorage.getItem('role');
        if (!this.state.token || role !== 'CLUB') {
            window.location.href = '/login.html';
        }
        document.getElementById('user-name').innerText = localStorage.getItem('full_name') || 'CLUB USER';
    },

    bindEvents() {
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const moduleId = e.currentTarget.dataset.module;
                if (moduleId) {
                    this.loadModule(moduleId);
                }
            });
        });
    },

    async loadInitialData() {
        try {
            const [pRes, mRes] = await Promise.all([
                fetch(`/api/match/institution/${this.state.institutionId}/players`, {
                    headers: { 'Authorization': `Bearer ${this.state.token}` }
                }),
                fetch(`/api/match/all`, {
                    headers: { 'Authorization': `Bearer ${this.state.token}` }
                })
            ]);
            
            this.state.players = await pRes.json();
            this.state.matches = await mRes.json();
            
            this.updateStats();
        } catch (error) {
            console.error("Failed to load initial data", error);
        }
    },

    loadModule(moduleId) {
        // Update UI
        document.querySelectorAll('.module').forEach(m => m.classList.remove('active'));
        document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
        
        const targetModule = document.getElementById(`mod-${moduleId}`);
        if (targetModule) {
            targetModule.classList.add('active');
            document.querySelector(`.nav-item[data-module="${moduleId}"]`).classList.add('active');
            document.getElementById('current-page-title').innerText = moduleId.replace('-', ' ').toUpperCase();
        }

        // Module Specific Init
        if (moduleId === 'match-control') this.initMatchControl();
        if (moduleId === 'players') this.renderPlayers();
        if (moduleId === 'overview') this.renderOverview();
        if (moduleId === 'teams') this.renderTeams();
    },

    renderTeams() {
        // Placeholder for teams data
        console.log("Rendering Teams Module");
    },

    renderOverview() {
        const list = document.getElementById('recent-matches-list');
        if (list) {
            const matches = Array.isArray(this.state.matches) ? this.state.matches : [];
            if (matches.length === 0) {
                list.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-secondary);">No recent matches found</td></tr>`;
            } else {
                list.innerHTML = matches.slice(0, 5).map(m => `
                    <tr>
                        <td>${new Date(m.match_date).toLocaleDateString()}</td>
                        <td>${m.opponent_name || 'OPPONENT'}</td>
                        <td>${m.stadium || 'Unknown Venue'}</td>
                        <td><span class="badge badge-success">${m.score_home} - ${m.score_away}</span></td>
                    </tr>
                `).join('');
            }
        }

        const countEl = document.getElementById('total-players-count');
        if (countEl) {
            const players = Array.isArray(this.state.players) ? this.state.players : [];
            countEl.innerText = players.length;
        }
    },

    renderPlayers() {
        const grid = document.getElementById('players-grid');
        if (!grid) return;

        grid.innerHTML = this.state.players.map(p => `
            <div class="card stat-card" style="cursor: pointer;" onclick="ClubDashboard.openPlayerModal(${p.id})">
                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                    <div>
                        <div style="font-weight:700; font-size:1.1rem;">${p.name}</div>
                        <div class="stat-label">${p.position} | #${p.jersey_number || '--'}</div>
                    </div>
                    <div class="badge badge-success">ACTIVE</div>
                </div>
                <div style="margin-top:1rem; display:grid; grid-template-columns: 1fr 1fr; gap:1rem;">
                    <div>
                        <div class="stat-label">Rating</div>
                        <div style="font-weight:700; color:var(--accent-secondary);">${p.rating || '8.4'}</div>
                    </div>
                    <div>
                        <div class="stat-label">Goals</div>
                        <div style="font-weight:700;">${p.goals || 0}</div>
                    </div>
                </div>
            </div>
        `).join('');
    },

    openPlayerModal(playerId) {
        const player = this.state.players.find(p => p.id === playerId);
        if (!player) return;

        document.getElementById('modal-player-name').innerText = player.name;
        document.getElementById('modal-player-pos').innerText = `${player.position} | #${player.jersey_number || '--'}`;
        document.getElementById('modal-player-rating').innerText = player.rating || '8.4';
        document.getElementById('modal-player-goals').innerText = player.goals || 0;
        document.getElementById('modal-player-assists').innerText = player.assists || 0;
        
        document.getElementById('player-modal').style.display = 'flex';
    },

    closePlayerModal() {
        document.getElementById('player-modal').style.display = 'none';
    },

    openRegisterModal() {
        document.getElementById('register-modal').style.display = 'flex';
    },

    closeRegisterModal() {
        document.getElementById('register-modal').style.display = 'none';
    },

    async submitPlayer() {
        const payload = {
            name: document.getElementById('reg-name').value,
            position: document.getElementById('reg-position').value,
            jersey_number: parseInt(document.getElementById('reg-jersey').value)
        };

        try {
            const r = await fetch('/api/club/player/create', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.state.token}`
                },
                body: JSON.stringify(payload)
            });
            if (r.ok) {
                alert("Player Registered Successfully!");
                this.closeRegisterModal();
                this.loadInitialData(); // Refresh list
                if (this.state.activeModule === 'match-control') this.initMatchControl();
            } else {
                const d = await r.json();
                alert("Registration Failed: " + (d.detail || "Unknown error"));
            }
        } catch (e) { alert("Network Error"); }
    },

    /* --- MATCH CONTROL CENTER LOGIC --- */
    initMatchControl() {
        this.state.selectedSquad = this.state.selectedSquad || [];
        this.state.startingXI = this.state.startingXI || [];
        
        document.getElementById('mcc-home-in').value = localStorage.getItem('institution_name') || 'OUR INSTITUTION';
        this.renderMccRoster();
        this.renderStartingPitch();
        
        if (this.state.activeMatchId) {
            this.revealLiveModules();
        }
    },

    renderMccRoster() {
        const list = document.getElementById('mcc-squad-list');
        const count = document.getElementById('mcc-squad-count');
        const preview = document.getElementById('mcc-selected-preview');
        if (!list) return;
        
        count.innerText = `${this.state.selectedSquad.length} / 18`;
        
        // Render List
        list.innerHTML = this.state.players.map(p => {
            const isSelected = this.state.selectedSquad.includes(p.id);
            return `
                <div class="player-row ${isSelected ? 'selected' : ''}" onclick="ClubDashboard.toggleMccPlayer(${p.id})">
                    <div style="width: 30px; font-weight: 900; color: ${isSelected ? 'var(--accent-primary)' : 'var(--text-secondary)'};">${p.jersey_number || '??'}</div>
                    <div style="flex: 1; font-weight: 700;">${p.name}</div>
                    <div style="font-size: 0.7rem; color: var(--text-secondary); font-weight: 800; text-transform: uppercase;">${p.position}</div>
                    <div style="width: 20px;">${isSelected ? '<i class="fa-solid fa-circle-check" style="color:var(--success)"></i>' : '<i class="fa-regular fa-circle"></i>'}</div>
                </div>
            `;
        }).join('');

        // Render Mini Preview
        preview.innerHTML = this.state.players.filter(p => this.state.selectedSquad.includes(p.id)).map(p => `
            <div style="background: var(--bg-tertiary); padding: 8px 16px; border-radius: 10px; font-size: 0.75rem; font-weight: 800; border: 1px solid var(--border); display: flex; align-items: center; gap: 8px;">
                <span style="color: var(--accent-primary)">#${p.jersey_number}</span> ${p.name.split(' ')[0]}
                <i class="fa-solid fa-xmark" style="cursor:pointer; color:var(--danger);" onclick="ClubDashboard.toggleMccPlayer(${p.id})"></i>
            </div>
        `).join('');

        this.renderXiSelectionList();
    },

    toggleMccPlayer(id) {
        const idx = this.state.selectedSquad.indexOf(id);
        if (idx > -1) {
            this.state.selectedSquad.splice(idx, 1);
            // Also remove from XI if it was there
            const xiIdx = this.state.startingXI.indexOf(id);
            if (xiIdx > -1) this.state.startingXI.splice(xiIdx, 1);
        } else {
            if (this.state.selectedSquad.length >= 18) return alert("Maximum 18 players allowed in Squadron.");
            this.state.selectedSquad.push(id);
        }
        this.renderMccRoster();
        this.renderStartingPitch();
    },

    renderXiSelectionList() {
        const xiBox = document.getElementById('mcc-xi-list');
        if (!xiBox) return;
        
        const squadPlayers = this.state.players.filter(p => this.state.selectedSquad.includes(p.id));
        
        xiBox.innerHTML = `
            <h3 style="font-size: 0.9rem; margin-bottom: 1.5rem; font-weight: 800; color: var(--text-secondary);">STARTING LINEUP (${this.state.startingXI.length} / 11)</h3>
            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                ${squadPlayers.map(p => {
                    const isXi = this.state.startingXI.includes(p.id);
                    return `
                        <div style="padding: 1rem; background: ${isXi ? 'rgba(99, 102, 241, 0.1)' : '#000'}; border: 1px solid ${isXi ? 'var(--accent-primary)' : 'var(--border)'}; border-radius: 12px; cursor: pointer; display: flex; justify-content: space-between; align-items: center;" onclick="ClubDashboard.toggleXiPlayer(${p.id})">
                            <div style="font-weight: 700; font-size: 0.9rem;">#${p.jersey_number} ${p.name}</div>
                            <div style="font-size: 0.6rem; font-weight: 800; text-transform: uppercase; color: var(--text-secondary);">${p.position}</div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    },

    toggleXiPlayer(id) {
        const idx = this.state.startingXI.indexOf(id);
        if (idx > -1) {
            this.state.startingXI.splice(idx, 1);
        } else {
            if (this.state.startingXI.length >= 11) return alert("Maximum 11 players in Starting XI.");
            this.state.startingXI.push(id);
        }
        this.renderMccRoster();
        this.renderStartingPitch();
    },

    renderStartingPitch() {
        const container = document.getElementById('mcc-xi-nodes');
        if (!container) return;
        container.innerHTML = '';
        
        const xiPlayers = this.state.players.filter(p => this.state.startingXI.includes(p.id));
        const formation = document.getElementById('mcc-formation')?.value || '4-3-3';
        
        const positions = this.getFormationPositions(formation);

        xiPlayers.forEach((p, i) => {
            const pos = positions[i] || { x: 500, y: 325 };
            container.innerHTML += `
                <g>
                    <circle cx="${pos.x}" cy="${pos.y}" r="25" fill="var(--accent-primary)" stroke="#fff" stroke-width="2" />
                    <text x="${pos.x}" y="${pos.y + 5}" text-anchor="middle" fill="#fff" font-size="14" font-weight="900">${p.jersey_number || '?'}</text>
                    <text x="${pos.x}" y="${pos.y + 45}" text-anchor="middle" fill="#fff" font-size="10" font-weight="700" style="text-transform: uppercase;">${p.name.split(' ')[0]}</text>
                </g>
            `;
        });
    },

    getFormationPositions(type) {
        if (type === '4-3-3') {
            return [
                { x: 100, y: 325 },
                { x: 300, y: 150 }, { x: 300, y: 260 }, { x: 300, y: 390 }, { x: 300, y: 500 },
                { x: 550, y: 200 }, { x: 550, y: 325 }, { x: 550, y: 450 },
                { x: 800, y: 150 }, { x: 800, y: 325 }, { x: 800, y: 500 }
            ];
        } else if (type === '4-4-2') {
            return [
                { x: 100, y: 325 },
                { x: 300, y: 150 }, { x: 300, y: 260 }, { x: 300, y: 390 }, { x: 300, y: 500 },
                { x: 550, y: 150 }, { x: 550, y: 260 }, { x: 550, y: 390 }, { x: 550, y: 500 },
                { x: 820, y: 250 }, { x: 820, y: 400 }
            ];
        } else {
            return [
                { x: 100, y: 325 },
                { x: 300, y: 200 }, { x: 300, y: 325 }, { x: 300, y: 450 },
                { x: 550, y: 120 }, { x: 550, y: 220 }, { x: 550, y: 325 }, { x: 550, y: 430 }, { x: 550, y: 530 },
                { x: 800, y: 250 }, { x: 800, y: 400 }
            ];
        }
    },

    applyFormation() {
        this.renderStartingPitch();
    },

    copyText(id) {
        const text = document.getElementById(id).innerText;
        navigator.clipboard.writeText(text);
        alert("Secure Link Copied: " + text);
    },

    async saveMatchSetup() {
        const opp = document.getElementById('mcc-opponent-in').value;
        const venue = document.getElementById('mcc-venue-in').value;
        const type = document.getElementById('mcc-type-in').value;
        const comp = document.getElementById('mcc-comp-in').value;
        const date = document.getElementById('mcc-date-in').value;
        const time = document.getElementById('mcc-time-in').value;

        if (!opp) return alert("Opponent identification required.");
        if (this.state.startingXI.length !== 11) return alert("Strategic Error: Starting XI must contain exactly 11 players.");

        const saveBtn = event.currentTarget;
        saveBtn.disabled = true;
        saveBtn.innerText = "AUTHORIZING TACTICAL PROTOCOL...";

        try {
            const r = await fetch('/api/matches/', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json', 
                    'Authorization': `Bearer ${this.state.token}` 
                },
                body: JSON.stringify({
                    home_team_id: parseInt(this.state.institutionId),
                    opponent_name: opp,
                    stadium: venue,
                    match_date: date ? `${date}T${time || '00:00'}:00` : new Date().toISOString(),
                    competition_name: comp,
                    match_type: type,
                    squad: this.state.selectedSquad,
                    starting_xi: this.state.startingXI,
                    kit_colors: {
                        jersey: document.getElementById('mcc-k-jersey').value,
                        shorts: document.getElementById('mcc-k-shorts').value,
                        socks: document.getElementById('mcc-k-socks').value
                    }
                })
            });
            const d = await r.json();
            this.state.activeMatchId = d.match_id;
            
            // Update UI
            document.getElementById('mcc-token-val').innerText = d.match_token || 'HUB-CONFIDENTIAL-AUTH';
            document.getElementById('mcc-key-val').innerText = d.api_key || 'AK-ELITE-PRO-S1';
            document.getElementById('mcc-ai-conn').innerText = "CONNECTED";
            document.getElementById('mcc-ai-conn').style.color = "var(--success)";
            
            this.revealLiveModules();
            alert("Match Architecture Authorized & Secured. Mission Ready.");
        } catch (e) { alert("Authorization failed."); }
        finally {
            saveBtn.disabled = false;
            saveBtn.innerText = "[ AUTHORIZE & SAVE MATCH SETUP ]";
        }
    },

    revealLiveModules() {
        document.getElementById('mcc-creds-box').style.display = 'block';
        document.getElementById('mcc-live-panel').style.display = 'block';
        document.getElementById('mcc-intel-panel').style.display = 'block';
        
        // Auto scroll to credentials
        document.getElementById('mcc-creds-box').scrollIntoView({ behavior: 'smooth' });
    },

    copyText(id) {
        const text = document.getElementById(id).innerText;
        navigator.clipboard.writeText(text);
        alert("Copied to Secure Clipboard: " + text);
    },

    copyToken() {
        const token = document.getElementById('mcc-token-display').innerText;
        navigator.clipboard.writeText(token);
        alert("Token copied to clipboard.");
    },

    downloadAI(os) {
        alert(`Downloading AI Machine Client for ${os.toUpperCase()}...\nTarget: Enterprise Edge Processor\nStatus: Secure Connection Initialized`);
    },

    async manualEvent(type) {
        if (!this.state.activeMatchId) return alert("No active match.");
        try {
            const r = await fetch(`/api/matches/${this.state.activeMatchId}/manual-event?event_type=${type}`, { method: 'POST' });
            if (r.ok) {
                this.processEvent({
                    event_type: type,
                    player_name: "Manual Entry",
                    minute: Math.floor(this.state.matchTimer / 60),
                    is_confirmed: true
                });
            }
        } catch (e) { console.error(e); }
    },

    async autoGenerateSquad() {
        if (!this.state.activeMatchId) return alert("Authorize session first.");
        try {
            const r = await fetch(`/api/matches/${this.state.activeMatchId}/squad/auto-generate`, { 
                method: 'POST',
                headers: { 'Authorization': `Bearer ${this.state.token}` }
            });
            if (r.ok) {
                alert("18-Man Squad Synchronized.");
                this.loadSquad();
            }
        } catch (e) { alert("Auto-generation failed."); }
    },

    async loadSquad() {
        const list = document.getElementById('mcc-squad-list');
        try {
            const r = await fetch(`/api/ferwafa/matches/${this.state.activeMatchId}/squad`);
            const squad = await r.json();
            list.innerHTML = squad.map(p => `
                <div style="display:flex; justify-content:space-between; padding:5px; border-bottom:1px solid var(--border); font-size:0.75rem;">
                    <span>#${p.jersey_number} ${p.player_name}</span>
                    <span style="color:var(--accent-primary);">${p.role.toUpperCase()}</span>
                </div>
            `).join('');
        } catch (e) { list.innerHTML = "Error loading squad."; }
    },

    connectLiveWS() {
        if (this.state.ws) this.state.ws.close();
        
        // Mocking live connection for demo if no real backend
        const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
        this.state.ws = new WebSocket(`${protocol}://${window.location.host}/ws/match/${this.state.activeMatchId}`);
        
        this.state.ws.onmessage = (e) => {
            const data = JSON.parse(e.data);
            if (data.type === 'tracking_update') this.renderPitch(data.frames || [data]);
            if (data.type === 'match_event') this.processEvent(data);
        };

        // Simulated data if socket fails (for demo)
        setTimeout(() => {
            if (this.state.ws.readyState !== 1) this.startSimulation();
        }, 2000);

        this.startTimer();
    },

    startSimulation() {
        console.log("Starting Live Tactical Simulation...");
        setInterval(() => {
            const frames = Array.from({length: 22}, (_, i) => ({
                id: i,
                x: Math.random() * 100,
                y: Math.random() * 100,
                team_side: i < 11 ? 'home' : 'away',
                jersey: i < 11 ? i+1 : i-10
            }));
            this.renderPitch(frames);
        }, 1000);

        setInterval(() => {
            const types = ['goal', 'foul', 'shot', 'pass'];
            this.processEvent({
                event_type: types[Math.floor(Math.random() * types.length)],
                player_name: "Simulated AI Player",
                minute: Math.floor(this.state.matchTimer / 60),
                is_confirmed: false
            });
        }, 15000);
    },

    startTimer() {
        clearInterval(this.state.timerInterval);
        this.state.timerInterval = setInterval(() => {
            this.state.matchTimer++;
            const m = Math.floor(this.state.matchTimer / 60).toString().padStart(2, '0');
            const s = (this.state.matchTimer % 60).toString().padStart(2, '0');
            document.getElementById('mcc-timer').innerText = `${m}:${s}`;
        }, 1000);
    },

    renderPitch(frames) {
        const layer = document.getElementById('mcc-players-layer');
        const trailsLayer = document.getElementById('mcc-trails-layer');
        const ball = document.getElementById('mcc-ball');
        if (!layer) return;
        
        layer.innerHTML = '';
        if (trailsLayer) trailsLayer.innerHTML = '';

        frames.forEach(f => {
            const x = 50 + (f.x / 100) * 900;
            const y = 50 + (f.y / 100) * 550;
            
            // Handle Trails
            if (!this.state.playerTrails[f.id]) this.state.playerTrails[f.id] = [];
            this.state.playerTrails[f.id].push({x, y});
            if (this.state.playerTrails[f.id].length > 5) this.state.playerTrails[f.id].shift();

            if (trailsLayer && this.state.playerTrails[f.id].length > 1) {
                let d = `M ${this.state.playerTrails[f.id][0].x} ${this.state.playerTrails[f.id][0].y}`;
                for (let i = 1; i < this.state.playerTrails[f.id].length; i++) {
                    d += ` L ${this.state.playerTrails[f.id][i].x} ${this.state.playerTrails[f.id][i].y}`;
                }
                const color = f.team_side === 'home' ? '#6366f1' : '#ef4444';
                trailsLayer.innerHTML += `<path d="${d}" stroke="${color}" stroke-width="2" fill="none" opacity="0.3" />`;
            }

            if (f.is_ball) {
                ball.style.display = 'block';
                ball.setAttribute('cx', x);
                ball.setAttribute('cy', y);
            } else {
                const color = f.team_side === 'home' ? '#6366f1' : '#ef4444';
                layer.innerHTML += `
                    <g transform="translate(${x},${y})">
                        <circle r="12" fill="${color}" stroke="white" stroke-width="1.5" />
                        <text dy="4" text-anchor="middle" fill="white" style="font-size:10px; font-weight:900;">${f.jersey || ''}</text>
                    </g>
                `;
            }
        });
    },

    processEvent(ev) {
        const feed = document.getElementById('mcc-event-feed');
        if (!feed) return;

        const item = document.createElement('div');
        item.style.padding = '0.75rem';
        item.style.borderLeft = `3px solid ${ev.is_confirmed ? 'var(--success)' : 'var(--accent-primary)'}`;
        item.style.marginBottom = '0.5rem';
        item.style.backgroundColor = 'rgba(255,255,255,0.02)';
        item.innerHTML = `
            <div style="font-size:0.7rem; color:var(--text-secondary);">${ev.minute || 0}'</div>
            <div style="font-weight:700;">${ev.event_type.toUpperCase()}</div>
            <div style="font-size:0.8rem;">${ev.player_name || 'AI Detection'}</div>
        `;
        feed.prepend(item);
    },

    logout() {
        localStorage.clear();
        window.location.href = '/login.html';
    }
};

document.addEventListener('DOMContentLoaded', () => ClubDashboard.init());
