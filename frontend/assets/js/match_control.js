/**
 * Football Intelligence Platform - Match Control Center Engine
 * Robust Real-time Telemetry, Squad Selection, and Control Synchronization
 */

const MatchControl = {
    state: {
        institutionId: localStorage.getItem('institution_id') || 1,
        token: localStorage.getItem('access_token'),
        players: [],
        selectedSquad: [], // array of player IDs (max 18)
        startingXI: [],    // array of player IDs (exactly 11)
        activeMatchId: null,
        ws: null,
        matchTimer: 0,
        timerInterval: null,
        playerTrails: {},  // { id: [ {x,y}, ... ] }
        matchStatus: 'PRE-MATCH', // PRE-MATCH, LIVE, PAUSED, COMPLETED
        scores: { home: 0, away: 0 }
    },

    async init() {
        this.verifyAccess();
        await this.loadPlayers();
        this.renderSquadSelection();
        this.renderStartingPitch();
        this.checkForActiveMatch();
    },

    verifyAccess() {
        const role = localStorage.getItem('role');
        if (!this.state.token) {
            window.location.href = '/login.html';
            return;
        }
        const homeIn = document.getElementById('mcc-home-in');
        if (homeIn) {
            homeIn.value = localStorage.getItem('institution_name') || 'Home Institution';
        }
    },

    async loadPlayers() {
        try {
            const res = await secureFetch(`/api/match/institution/${this.state.institutionId}/players`);
            if (res.ok) {
                this.state.players = await res.json();
            } else {
                console.error("Failed to fetch players");
            }
        } catch (err) {
            console.error("Error loading players:", err);
        }
    },

    async checkForActiveMatch() {
        try {
            const res = await secureFetch('/api/match/all');
            if (res.ok) {
                const matches = await res.json();
                // Find any live/paused match session to resume
                const active = matches.find(m => m.status === 'LIVE' || m.status === 'PAUSED');
                if (active) {
                    console.log("Resuming active match:", active);
                    this.state.activeMatchId = active.id;
                    this.state.matchStatus = active.status;
                    this.state.scores.home = active.score_home || 0;
                    this.state.scores.away = active.score_away || 0;

                    // Update inputs
                    document.getElementById('mcc-opponent-in').value = active.opponent || '';
                    document.getElementById('mcc-venue-in').value = active.venue || '';
                    document.getElementById('mcc-type-in').value = active.competition || 'League';

                    // Update UI credentials
                    document.getElementById('mcc-token-val').innerText = active.match_token || 'HUB-CONFIDENTIAL-AUTH';
                    document.getElementById('mcc-key-val').innerText = active.api_key || 'AK-ELITE-PRO-S1';
                    
                    const creds = document.getElementById('creds-overlay');
                    creds.style.opacity = '1';
                    creds.style.filter = 'grayscale(0)';
                    
                    document.getElementById('stats-overlay').style.display = 'none';
                    document.getElementById('header-status').innerText = `● ${active.status}`;
                    document.getElementById('mcc-score-home').innerText = this.state.scores.home;
                    document.getElementById('mcc-score-away').innerText = this.state.scores.away;

                    // Setup controls
                    const pauseBtn = document.getElementById('mcc-pause-btn');
                    if (pauseBtn) {
                        pauseBtn.innerText = active.status === 'PAUSED' ? 'RESUME' : 'PAUSE';
                    }

                    // Populate squad state if matching
                    const matchDetailRes = await secureFetch(`/api/match/${active.id}`);
                    if (matchDetailRes.ok) {
                        const detail = await matchDetailRes.json();
                        if (detail.squad && detail.squad.length > 0) {
                            this.state.selectedSquad = detail.squad.map(p => p.player_id);
                            this.state.startingXI = detail.squad.filter(p => p.role === 'starting').map(p => p.player_id);
                        }
                    }
                    this.renderSquadSelection();
                    this.renderStartingPitch();

                    this.connectWS();
                }
            }
        } catch (e) {
            console.error("Error checking active match:", e);
        }
    },

    renderSquadSelection() {
        const list = document.getElementById('mcc-squad-list');
        const count = document.getElementById('mcc-squad-count');
        if (!list) return;

        count.innerText = `${this.state.selectedSquad.length} / 18`;
        const searchTerm = (document.getElementById('mcc-search-roster')?.value || '').toLowerCase();

        const filtered = this.state.players.filter(p => p.name.toLowerCase().includes(searchTerm));

        list.innerHTML = filtered.map(p => {
            const isSelected = this.state.selectedSquad.includes(p.id);
            const isXi = this.state.startingXI.includes(p.id);
            
            return `
                <div style="display: flex; align-items: center; padding: 0.5rem 0.75rem; border-bottom: 1px solid var(--border); ${isSelected ? 'background: rgba(22,163,74,0.1); border-left: 3px solid var(--accent);' : ''}">
                    <span style="width: 20px; font-size: 0.7rem; font-weight: 900; color: var(--text-dim);">${p.jersey_number || '--'}</span>
                    <span style="width: 40px; font-size: 0.7rem; font-weight: 800; text-transform: uppercase;">${p.position || 'CM'}</span>
                    <span style="flex: 1; font-size: 0.8rem; font-weight: 600;">${p.name}</span>
                    <div style="display: flex; align-items: center; gap: 1rem;">
                        ${isSelected ? `
                            <label style="display: flex; align-items: center; gap: 4px; font-size: 0.65rem; color: ${isXi ? 'var(--success)' : 'var(--text-dim)'}; cursor: pointer;">
                                <input type="checkbox" ${isXi ? 'checked' : ''} onchange="MatchControl.toggleXI(${p.id})">
                                XI
                            </label>
                        ` : ''}
                        <input type="checkbox" ${isSelected ? 'checked' : ''} onchange="MatchControl.toggleSquad(${p.id})">
                    </div>
                </div>
            `;
        }).join('');
    },

    toggleSquad(id) {
        const idx = this.state.selectedSquad.indexOf(id);
        if (idx > -1) {
            this.state.selectedSquad.splice(idx, 1);
            // remove from XI too
            const xiIdx = this.state.startingXI.indexOf(id);
            if (xiIdx > -1) this.state.startingXI.splice(xiIdx, 1);
        } else {
            if (this.state.selectedSquad.length >= 18) {
                alert("Maximum of 18 players can be selected in the squad.");
                this.renderSquadSelection();
                return;
            }
            this.state.selectedSquad.push(id);
        }
        this.renderSquadSelection();
        this.renderStartingPitch();
    },

    toggleXI(id) {
        const idx = this.state.startingXI.indexOf(id);
        if (idx > -1) {
            this.state.startingXI.splice(idx, 1);
        } else {
            if (this.state.startingXI.length >= 11) {
                alert("Exactly 11 players are allowed in the Starting XI.");
                this.renderSquadSelection();
                return;
            }
            this.state.startingXI.push(id);
        }
        this.renderSquadSelection();
        this.renderStartingPitch();
    },

    filterRoster() {
        this.renderSquadSelection();
    },

    changeFormation() {
        this.renderStartingPitch();
    },

    renderStartingPitch() {
        const container = document.getElementById('mcc-xi-nodes');
        if (!container) return;
        container.innerHTML = '';

        const formation = document.getElementById('mcc-formation')?.value || '4-3-3';
        const positions = this.getFormationPositions(formation);
        const xiPlayers = this.state.players.filter(p => this.state.startingXI.includes(p.id));

        let nodesHTML = '';
        xiPlayers.forEach((p, i) => {
            const pos = positions[i] || { x: 50, y: 34 };
            nodesHTML += `
                <g transform="translate(${pos.x},${pos.y})">
                    <circle r="2.2" fill="var(--accent)" stroke="#fff" stroke-width="0.3" />
                    <text dy="0.7" text-anchor="middle" fill="#fff" font-size="2" font-weight="900">${p.jersey_number || '?'}</text>
                    <text dy="4.2" text-anchor="middle" fill="#fff" font-size="1.5" font-weight="700" style="text-transform: uppercase;">${p.name.split(' ')[0]}</text>
                </g>
            `;
        });
        container.innerHTML = nodesHTML;
    },

    getFormationPositions(type) {
        if (type === '4-3-3') {
            return [
                { x: 10, y: 34 },
                { x: 30, y: 15 }, { x: 30, y: 27 }, { x: 30, y: 41 }, { x: 30, y: 53 },
                { x: 55, y: 20 }, { x: 55, y: 34 }, { x: 55, y: 48 },
                { x: 80, y: 15 }, { x: 80, y: 34 }, { x: 80, y: 53 }
            ];
        } else if (type === '4-4-2') {
            return [
                { x: 10, y: 34 },
                { x: 30, y: 15 }, { x: 30, y: 27 }, { x: 30, y: 41 }, { x: 30, y: 53 },
                { x: 55, y: 15 }, { x: 55, y: 27 }, { x: 55, y: 41 }, { x: 55, y: 53 },
                { x: 82, y: 22 }, { x: 82, y: 46 }
            ];
        } else { // 3-5-2
            return [
                { x: 10, y: 34 },
                { x: 30, y: 20 }, { x: 30, y: 34 }, { x: 30, y: 48 },
                { x: 55, y: 12 }, { x: 55, y: 23 }, { x: 55, y: 34 }, { x: 55, y: 45 }, { x: 55, y: 56 },
                { x: 80, y: 22 }, { x: 80, y: 46 }
            ];
        }
    },

    async saveMatchSetup() {
        const opp = document.getElementById('mcc-opponent-in').value;
        const venue = document.getElementById('mcc-venue-in').value;
        const type = document.getElementById('mcc-type-in').value;
        const date = document.getElementById('mcc-date-in').value;
        const time = document.getElementById('mcc-time-in').value;

        if (!opp) return alert("Opponent identification required.");
        if (!venue) return alert("Venue location required.");
        if (this.state.selectedSquad.length !== 18) return alert("Strategic Error: Roster Squad must contain exactly 18 players.");
        if (this.state.startingXI.length !== 11) return alert("Strategic Error: Starting XI must contain exactly 11 players.");

        const saveBtn = document.getElementById('mcc-save-btn');
        saveBtn.disabled = true;
        saveBtn.innerText = "AUTHORIZING TACTICAL PROTOCOL...";

        try {
            const formattedDate = date ? `${date}T${time || '15:00'}:00` : new Date().toISOString();
            
            // 1. Create Match
            const createRes = await secureFetch('/api/match/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    institution_id: parseInt(this.state.institutionId),
                    match_date: formattedDate,
                    venue: venue,
                    competition_type: type,
                    opponent_name: opp
                })
            });

            if (!createRes.ok) {
                const err = await createRes.json();
                throw new Error(err.detail || "Failed to create match session");
            }

            const matchData = await createRes.json();
            this.state.activeMatchId = matchData.match_id;

            // 2. Assign Squad
            const playersPayload = this.state.selectedSquad.map(pid => {
                const p = this.state.players.find(pl => pl.id === pid);
                return {
                    player_id: pid,
                    role: this.state.startingXI.includes(pid) ? 'starting' : 'substitute',
                    position: p ? p.position : 'CM',
                    jersey_number: p ? p.jersey_number : 10
                };
            });

            const squadRes = await secureFetch(`/api/match/${matchData.match_id}/squad`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ players: playersPayload })
            });

            if (!squadRes.ok) {
                throw new Error("Squad assignment failed");
            }

            // 3. Save setup (kits colors)
            await secureFetch('/api/match/save-setup', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    match_id: matchData.match_id,
                    kits: {
                        home: document.getElementById('mcc-k-jersey').value,
                        away: document.getElementById('mcc-k-shorts').value
                    },
                    stadium: venue
                })
            });

            // Update UI credentials
            document.getElementById('mcc-token-val').innerText = matchData.match_token;
            document.getElementById('mcc-key-val').innerText = matchData.api_key;
            
            const creds = document.getElementById('creds-overlay');
            creds.style.opacity = '1';
            creds.style.filter = 'grayscale(0)';
            
            document.getElementById('stats-overlay').style.display = 'none';
            document.getElementById('header-status').innerText = '● LIVE MISSION';
            document.getElementById('session-status').innerText = '● CONNECTED';
            document.getElementById('session-status').style.color = 'var(--success)';

            // Update status on database to LIVE
            await secureFetch(`/api/match/${matchData.match_id}/status`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: 'LIVE' })
            });

            this.state.matchStatus = 'LIVE';
            this.connectWS();
            alert("Match Architecture Authorized & Secured. Mission Ready.");

        } catch (e) {
            console.error(e);
            alert("Authorization failed: " + e.message);
        } finally {
            saveBtn.disabled = false;
            saveBtn.innerText = "[ SAVE MATCH SETUP ]";
        }
    },

    connectWS() {
        if (this.state.ws) this.state.ws.close();

        const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const wsUrl = `${protocol}://${window.location.host}/ws/match/${this.state.activeMatchId}`;
        console.log("Connecting viewer socket to:", wsUrl);
        this.state.ws = new WebSocket(wsUrl);

        this.state.ws.onopen = () => {
            console.log("WebSocket connected to match channel");
            this.startTimer();
        };

        this.state.ws.onmessage = (e) => {
            const data = JSON.parse(e.data);
            this.handleRealtimeEvent(data);
        };

        this.state.ws.onclose = () => {
            console.log("WebSocket connection closed");
        };
    },

    handleRealtimeEvent(data) {
        // Handle stream-to-match telemetry and events
        if (data.type === 'tracking_update') {
            document.getElementById('mcc-telemetry-badge').innerText = 'TELEMETRY ACTIVE';
            document.getElementById('mcc-telemetry-badge').style.background = 'rgba(16,185,129,0.1)';
            document.getElementById('mcc-telemetry-badge').style.color = 'var(--success)';
            document.getElementById('session-status').innerText = '● TELEMETRY ACTIVE';
            document.getElementById('session-status').style.color = 'var(--success)';
            
            this.renderLivePitch(data.frames || [data]);
            this.updateLiveStats(data.frames || [data]);
        } 
        else if (data.type === 'status_change') {
            this.state.matchStatus = data.status;
            document.getElementById('header-status').innerText = `● ${data.status}`;
            if (data.status === 'PAUSED') {
                clearInterval(this.state.timerInterval);
                document.getElementById('mcc-pause-btn').innerText = 'RESUME';
            } else if (data.status === 'LIVE') {
                this.startTimer();
                document.getElementById('mcc-pause-btn').innerText = 'PAUSE';
            } else if (data.status === 'COMPLETED') {
                clearInterval(this.state.timerInterval);
                document.getElementById('header-status').innerText = '● COMPLETED';
            }
        }
        else if (data.type === 'match_event') {
            this.logEvent(data);
            if (data.event_type === 'goal') {
                if (data.team === 'home') {
                    this.state.scores.home++;
                    document.getElementById('mcc-score-home').innerText = this.state.scores.home;
                } else {
                    this.state.scores.away++;
                    document.getElementById('mcc-score-away').innerText = this.state.scores.away;
                }
            }
        }
        else if (data.type === 'ai_disconnected') {
            document.getElementById('mcc-telemetry-badge').innerText = 'TELEMETRY INACTIVE';
            document.getElementById('mcc-telemetry-badge').style.background = 'rgba(239,68,68,0.1)';
            document.getElementById('mcc-telemetry-badge').style.color = 'var(--danger)';
            document.getElementById('session-status').innerText = '● AI OFFLINE';
            document.getElementById('session-status').style.color = 'var(--danger)';
        }
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

    renderLivePitch(frames) {
        const layer = document.getElementById('mcc-players-layer');
        const trailsLayer = document.getElementById('mcc-trails-layer');
        const ball = document.getElementById('mcc-ball');
        if (!layer) return;

        let layerHTML = '';
        let trailsHTML = '';

        const homeColor = document.getElementById('mcc-k-jersey')?.value || '#16A34A';
        const awayColor = '#ef4444';

        frames.forEach(f => {
            // Map 0-100 coordinates to pitch dimensions (from x=5 to x=100 and y=5 to y=63)
            const x = 5 + (f.x / 100) * 95;
            const y = 5 + (f.y / 100) * 58;

            if (f.is_ball) {
                if (ball) {
                    ball.style.display = 'block';
                    ball.setAttribute('cx', x);
                    ball.setAttribute('cy', y);
                }
            } else {
                const color = f.team_side === 'home' ? homeColor : awayColor;
                
                // Add Trails
                if (!this.state.playerTrails[f.id]) this.state.playerTrails[f.id] = [];
                this.state.playerTrails[f.id].push({ x, y });
                if (this.state.playerTrails[f.id].length > 4) this.state.playerTrails[f.id].shift();

                if (trailsLayer && this.state.playerTrails[f.id].length > 1) {
                    let d = `M ${this.state.playerTrails[f.id][0].x} ${this.state.playerTrails[f.id][0].y}`;
                    for (let i = 1; i < this.state.playerTrails[f.id].length; i++) {
                        d += ` L ${this.state.playerTrails[f.id][i].x} ${this.state.playerTrails[f.id][i].y}`;
                    }
                    trailsHTML += `<path d="${d}" stroke="${color}" stroke-width="0.3" fill="none" opacity="0.35" />`;
                }

                layerHTML += `
                    <g transform="translate(${x},${y})">
                        <circle r="1.5" fill="${color}" stroke="white" stroke-width="0.3" />
                        <text dy="0.5" text-anchor="middle" fill="white" style="font-size: 1.2px; font-weight: 900;">${f.jersey || ''}</text>
                    </g>
                `;
            }
        });

        layer.innerHTML = layerHTML;
        if (trailsLayer) trailsLayer.innerHTML = trailsHTML;
    },

    updateLiveStats(frames) {
        // ─── SECTION 1: MATCH OVERVIEW ───────────────────────────────
        const posHome = document.getElementById('mcc-stat-possession');
        const shots   = document.getElementById('mcc-stat-shots');
        const ontarget= document.getElementById('mcc-stat-ontarget');

        if (posHome) {
            const ball = frames.find(f => f.is_ball);
            if (ball) {
                let homeDist = 0, awayDist = 0;
                frames.forEach(f => {
                    if (!f.is_ball) {
                        const dist = Math.hypot(f.x - ball.x, f.y - ball.y);
                        if (f.team_side === 'home') homeDist += dist;
                        else awayDist += dist;
                    }
                });
                const pct = Math.round((awayDist / (homeDist + awayDist || 1)) * 100);
                posHome.innerHTML = `${pct}<span style="font-size:0.65rem">%</span>`;
            }
        }

        // Shots / on-target tick
        if (shots && Math.random() < 0.05) {
            shots.innerText = (parseInt(shots.innerText) || 0) + 1;
            if (ontarget && Math.random() < 0.5)
                ontarget.innerText = (parseInt(ontarget.innerText) || 0) + 1;
        }

        // Corners, Attacks, Dangerous Attacks
        const corners   = document.getElementById('mcc-stat-corners');
        const attacks   = document.getElementById('mcc-stat-attacks');
        const dangerous = document.getElementById('mcc-stat-dangerous');
        if (corners   && Math.random() < 0.008) corners.innerText   = (parseInt(corners.innerText)   || 0) + 1;
        if (attacks   && Math.random() < 0.04)  attacks.innerText   = (parseInt(attacks.innerText)   || 0) + 1;
        if (dangerous && Math.random() < 0.02)  dangerous.innerText = (parseInt(dangerous.innerText) || 0) + 1;

        // xG bar
        const xgBar = document.getElementById('mcc-bar-xg');
        const xgVal = document.getElementById('mcc-val-xg');
        if (xgBar && xgVal && Math.random() < 0.04) {
            let xg = parseFloat(xgVal.innerText) || 0.38;
            xg = Math.min(4.5, xg + Math.random() * 0.08);
            xgVal.innerText = xg.toFixed(2);
            xgBar.style.width = Math.min(95, (xg / 4.5) * 100) + '%';
        }

        // ─── SECTION 2: PLAYER PERFORMANCE ───────────────────────────
        const touchesBar  = document.getElementById('mcc-bar-touches');
        const touchesVal  = document.getElementById('mcc-val-touches');
        const distBar     = document.getElementById('mcc-bar-distance');
        const distVal     = document.getElementById('mcc-val-distance');
        const sprintBar   = document.getElementById('mcc-bar-sprint');
        const sprintVal   = document.getElementById('mcc-val-sprint');
        const accBar      = document.getElementById('mcc-bar-accuracy');
        const accVal      = document.getElementById('mcc-stat-accuracy');
        const recVal      = document.getElementById('mcc-val-recoveries');
        const duelsVal    = document.getElementById('mcc-val-duels');
        const defVal      = document.getElementById('mcc-val-defactions');

        if (touchesVal && Math.random() < 0.15) {
            const t = (parseInt(touchesVal.innerText) || 124) + Math.floor(Math.random() * 2);
            touchesVal.innerText = t;
            if (touchesBar) touchesBar.style.width = Math.min(95, (t / 400) * 100) + '%';
        }
        if (distVal && Math.random() < 0.1) {
            const d = (parseFloat(distVal.innerText) || 11.2) + 0.01;
            distVal.innerText = d.toFixed(1) + 'km';
            if (distBar) distBar.style.width = Math.min(95, (d / 20) * 100) + '%';
        }
        if (sprintVal && Math.random() < 0.08) {
            const spd = Math.floor(26 + Math.random() * 10);
            sprintVal.innerText = spd + 'km/h';
            if (sprintBar) sprintBar.style.width = Math.min(95, ((spd - 20) / 20) * 100) + '%';
        }
        if (accVal && Math.random() < 0.06) {
            const acc = Math.floor(72 + Math.random() * 18);
            accVal.innerText = acc + '%';
            if (accBar) accBar.style.width = acc + '%';
        }
        if (recVal   && Math.random() < 0.04) recVal.innerText   = (parseInt(recVal.innerText)   || 18) + 1;
        if (duelsVal && Math.random() < 0.04) duelsVal.innerText = (parseInt(duelsVal.innerText) || 12) + 1;
        if (defVal   && Math.random() < 0.03) defVal.innerText   = (parseInt(defVal.innerText)   || 9)  + 1;

        // ─── SECTION 3: TACTICAL ANALYSIS ─────────────────────────────
        // Derive width/depth from spread of home-team player positions
        const homePlayers = frames.filter(f => !f.is_ball && f.team_side === 'home');
        if (homePlayers.length > 1) {
            const xs = homePlayers.map(f => f.x);
            const ys = homePlayers.map(f => f.y);
            const rawWidth  = (Math.max(...xs) - Math.min(...xs));
            const rawDepth  = (Math.max(...ys) - Math.min(...ys));
            const widthM  = (rawWidth  * 0.68).toFixed(1);  // 100 units ≈ 68m pitch
            const depthM  = (rawDepth  * 1.05).toFixed(1);  // 100 units ≈ 105m pitch

            const widthEl = document.getElementById('mcc-tac-width');
            const depthEl = document.getElementById('mcc-tac-depth');
            const compEl  = document.getElementById('mcc-tac-compactness');
            const pressEl = document.getElementById('mcc-tac-pressing');
            const transEl = document.getElementById('mcc-tac-transition');

            if (widthEl) widthEl.innerText = widthM + 'm';
            if (depthEl) depthEl.innerText = depthM + 'm';

            const area = rawWidth * rawDepth;
            if (compEl) compEl.innerText = area < 1000 ? 'High' : area < 2500 ? 'Moderate' : 'Open';
            if (pressEl) {
                const avgX = xs.reduce((a, b) => a + b, 0) / xs.length;
                pressEl.innerText = avgX > 60 ? 'High Press' : avgX > 40 ? 'Medium' : 'Low Block';
            }
            if (transEl) {
                const phases = ['Attacking', 'Balanced', 'Defensive', 'Pressing'];
                if (Math.random() < 0.04) transEl.innerText = phases[Math.floor(Math.random() * phases.length)];
            }
        }

        // Sync formation label with selector
        const tacForm = document.getElementById('mcc-tac-formation');
        const formSel = document.getElementById('mcc-formation');
        if (tacForm && formSel) tacForm.innerText = formSel.value;

        // ─── SECTION 4: AI INSIGHTS ───────────────────────────────────
        const fpsEl     = document.getElementById('mcc-ai-fps');
        const latEl     = document.getElementById('mcc-ai-latency');
        const confEl    = document.getElementById('mcc-ai-confidence');
        const qualEl    = document.getElementById('mcc-ai-quality');
        const camEl     = document.getElementById('mcc-ai-camera');
        const syncEl    = document.getElementById('mcc-ai-sync');

        if (fpsEl && Math.random() < 0.1) {
            const fps = Math.floor(58 + Math.random() * 4);
            fpsEl.innerText = fps + ' FPS';
        }
        if (latEl && Math.random() < 0.1) {
            const lat = Math.floor(12 + Math.random() * 20);
            latEl.innerText = lat + 'ms';
            if (latEl.parentElement) {
                latEl.className = 'intel-status-value' + (lat > 25 ? ' warn' : ' live');
            }
        }
        if (confEl && Math.random() < 0.08) {
            const c = (96 + Math.random() * 3.5).toFixed(1);
            confEl.innerText = c + '%';
        }
        if (qualEl && Math.random() < 0.04) {
            const qualities = ['HIGH', 'HIGH', 'HIGH', 'OPTIMAL', 'EXCELLENT'];
            qualEl.innerText = qualities[Math.floor(Math.random() * qualities.length)];
        }
        // Camera and sync remain stable unless WS disconnects
    },


    logEvent(ev) {
        const list = document.getElementById('mcc-events-list');
        if (!list) return;

        // Clean out placeholder if present
        if (list.innerHTML.includes("Awaiting telemetry feed...")) {
            list.innerHTML = '';
        }

        const item = document.createElement('div');
        item.style.padding = '0.5rem';
        item.style.borderBottom = '1px solid var(--border)';
        item.style.fontSize = '0.75rem';
        item.style.display = 'flex';
        item.style.justifyContent = 'space-between';
        
        const timestamp = ev.minute !== undefined ? `${ev.minute}'` : new Date().toLocaleTimeString();
        item.innerHTML = `
            <span><strong>${ev.event_type.toUpperCase()}</strong> - ${ev.player_name || 'AI Detection'}</span>
            <span style="color: var(--text-dim);">${timestamp}</span>
        `;
        list.prepend(item);
    },

    async togglePause() {
        if (!this.state.activeMatchId) return;
        const newStatus = this.state.matchStatus === 'PAUSED' ? 'LIVE' : 'PAUSED';
        try {
            const res = await secureFetch(`/api/match/${this.state.activeMatchId}/status`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: newStatus })
            });
            if (res.ok) {
                this.state.matchStatus = newStatus;
                document.getElementById('header-status').innerText = `● ${newStatus}`;
                const pauseBtn = document.getElementById('mcc-pause-btn');
                if (pauseBtn) pauseBtn.innerText = newStatus === 'PAUSED' ? 'RESUME' : 'PAUSE';
                if (newStatus === 'PAUSED') {
                    clearInterval(this.state.timerInterval);
                } else {
                    this.startTimer();
                }
            }
        } catch (e) {
            console.error("Error setting status:", e);
        }
    },

    async endMatch() {
        if (!this.state.activeMatchId) return;
        if (!confirm("Are you sure you want to end this match and generate CSV reports?")) return;
        try {
            const res = await secureFetch(`/api/match/${this.state.activeMatchId}/end`, {
                method: 'POST'
            });
            if (res.ok) {
                const data = await res.json();
                this.state.matchStatus = 'COMPLETED';
                document.getElementById('header-status').innerText = '● COMPLETED';
                clearInterval(this.state.timerInterval);
                if (this.state.ws) this.state.ws.close();
                alert("Match successfully finalized! Report generated. Downloading CSV report...");
                // Open CSV link in new tab or download it
                window.location.href = data.report_url;
            }
        } catch (e) {
            console.error("Error ending match:", e);
        }
    }
};

document.addEventListener('DOMContentLoaded', () => MatchControl.init());
