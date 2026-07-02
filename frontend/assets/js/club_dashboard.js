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
        playerTrails: {}, // Store { id: [ {x,y}, ... ] }
        trainings: [],
        transfers: []
    },

    init() {
        this.verifyAccess();
        this.bindEvents();
        this.loadModule('overview');
        this.loadInitialData();
        
        window.addEventListener('pageshow', (event) => {
            if (localStorage.getItem('player_sync_needed') === 'true') {
                localStorage.removeItem('player_sync_needed');
                this.loadInitialData();
            }
        });
        window.addEventListener('storage', (event) => {
            if (event.key === 'player_sync_needed' && event.newValue === 'true') {
                localStorage.removeItem('player_sync_needed');
                this.loadInitialData();
            }
        });
    },

    verifyAccess() {
        const role = localStorage.getItem('role');
        if (!this.state.token || role !== 'CLUB') {
            window.location.href = '/login.html';
        }
        document.getElementById('user-name').innerText = localStorage.getItem('full_name') || 'CLUB USER';
        
        const instName = localStorage.getItem('institution_name') || 'CLUB USER';
        const sidebarNameEl = document.getElementById('inst-name-sidebar');
        if (sidebarNameEl) sidebarNameEl.innerText = instName;
        
        const logoUrl = localStorage.getItem('logo_url');
        const brandingTargets = document.querySelectorAll('.ui-branding-target');
        
        brandingTargets.forEach(avatarEl => {
            const defaultLogo = window.PlayerDisplay ? PlayerDisplay.DEFAULT_LOGO : "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjNGI1NTYzIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBhdGggZD0iTTEyIDIyczgtNCA4LTEwVjVsLTgtMy04IDN2N2MwIDYgOCAxMCA4IDEweiIvPjwvc3ZnPg==";
            if (logoUrl && logoUrl !== 'null' && logoUrl !== 'undefined' && logoUrl.trim() !== '') {
                avatarEl.innerHTML = `<img src="${logoUrl}" style="width:100%;height:100%;object-fit:contain;border-radius:inherit;" onerror="this.onerror=null; this.src='${defaultLogo}';">`;
                avatarEl.style.background = 'transparent';
                avatarEl.style.color = 'transparent';
            } else {
                avatarEl.innerHTML = `<img src="${defaultLogo}" style="width:100%;height:100%;object-fit:contain;border-radius:inherit;">`;
                avatarEl.style.background = 'transparent';
                avatarEl.style.color = 'transparent';
            }
        });
        
        if (window.lucide) lucide.createIcons();
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
            const [pRes, mRes, tRes, trRes] = await Promise.all([
                fetch(`/api/match/institution/${this.state.institutionId}/players`, {
                    headers: { 'Authorization': `Bearer ${this.state.token}` }
                }),
                fetch(`/api/match/all`, {
                    headers: { 'Authorization': `Bearer ${this.state.token}` }
                }),
                fetch(`/api/club/training`, {
                    headers: { 'Authorization': `Bearer ${this.state.token}` }
                }),
                fetch(`/api/club/transfers`, {
                    headers: { 'Authorization': `Bearer ${this.state.token}` }
                })
            ]);
            
            let rawPlayers = pRes.ok ? await pRes.json() : [];
            if (window.PlayerDisplay) {
                const ctx = PlayerDisplay.getDisplayContext();
                this.state.players = PlayerDisplay.dedupePlayersById(rawPlayers).map(function(p) {
                    return PlayerDisplay.normalizePlayer(p, ctx);
                });
            } else {
                this.state.players = rawPlayers;
            }
            this.state.matches = mRes.ok ? await mRes.json() : [];
            this.state.trainings = tRes.ok ? await tRes.json() : [];
            this.state.transfers = trRes.ok ? await trRes.json() : [];
            
            this.updateStats();
            // Re-render the currently active module so UI stays in sync
            this.refreshActiveModule();
        } catch (error) {
            console.error("Failed to load initial data", error);
        }
    },

    // Real-time module refresh — re-renders whichever module is currently visible
    refreshActiveModule() {
        const active = document.querySelector('.module.active');
        if (!active) return;
        const moduleId = active.id.replace('mod-', '');
        if (moduleId === 'players') this.renderPlayers();
        if (moduleId === 'overview') this.renderOverview();
        if (moduleId === 'training') this.renderTraining();
        if (moduleId === 'transfers') { this.renderTransfers(); this.renderTransferHistory(); }
        if (moduleId === 'match-control') this.renderMccRoster();
    },

    // Player count + overview stat sync
    updateStats() {
        const countEl = document.getElementById('total-players-count');
        if (countEl) {
            const players = Array.isArray(this.state.players) ? this.state.players : [];
            countEl.innerText = players.length;
        }
    },

    // Alias so player_profile.js deletePlayer() can trigger a real-time refresh
    loadPlayers() {
        this.loadInitialData();
    },

    async deletePlayer(id) {
        const player = this.state.players.find(p => p.id === id);
        const displayName = player ? (player.fullName || 'this player') : 'this player';
        if (confirm(`Are you sure you want to release ${displayName} from the squad?`)) {
            try {
                const res = await fetch(`/api/players/${id}`, {
                    method: 'DELETE',
                    headers: { 'Authorization': `Bearer ${this.state.token}` }
                });
                if (res.ok) {
                    alert("Player released successfully!");
                    this.loadInitialData(); // Real-time sync list!
                } else {
                    const err = await res.json();
                    alert("Failed to release player: " + (err.detail || "Unknown error"));
                }
            } catch (e) {
                alert("Network error");
            }
        }
    },

    loadModule(moduleId) {
        document.querySelectorAll('.module').forEach(m => m.classList.remove('active'));
        document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));

        // ── INTERVAL TEARDOWN: prevent duplicate timers when switching tabs ──
        if (moduleId !== 'match-control') {
            if (this.state.simInterval)      { clearInterval(this.state.simInterval);      this.state.simInterval = null; }
            if (this.state.eventSimInterval) { clearInterval(this.state.eventSimInterval); this.state.eventSimInterval = null; }
            if (this.state.timerInterval)    { clearInterval(this.state.timerInterval);    this.state.timerInterval = null; }
            if (this.state.ws && this.state.ws.readyState === WebSocket.OPEN) {
                this.state.ws.close();
                this.state.ws = null;
            }
        }
        
        const targetModule = document.getElementById(`mod-${moduleId}`);
        if (targetModule) {
            targetModule.classList.add('active');
            const navItem = document.querySelector(`.nav-item[data-module="${moduleId}"]`);
            if (navItem) navItem.classList.add('active');
            document.getElementById('current-page-title').innerText = moduleId.replace('-', ' ').toUpperCase();
        }

        if (moduleId === 'match-control') this.initMatchControl();
        if (moduleId === 'players') this.renderPlayers();
        if (moduleId === 'overview') this.renderOverview();
        if (moduleId === 'teams') this.renderTeams();
        if (moduleId === 'training') this.renderTraining();
        if (moduleId === 'transfers') {
            this.renderTransfers();
            this.renderTransferHistory();
        }
        if (moduleId === 'settings') {
            document.getElementById('settings-club-name').innerText = localStorage.getItem('institution_name') || 'Club Name';
            document.getElementById('settings-logo-url').value = localStorage.getItem('logo_url') || '';
            document.getElementById('settings-stadium').value = localStorage.getItem('stadium_name') || '';
            
            const preview = document.getElementById('settings-logo-preview');
            const logoUrl = localStorage.getItem('logo_url');
            const defaultLogo = window.PlayerDisplay ? PlayerDisplay.DEFAULT_LOGO : "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjNGI1NTYzIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBhdGggZD0iTTEyIDIyczgtNCA4LTEwVjVsLTgtMy04IDN2N2MwIDYgOCAxMCA4IDEweiIvPjwvc3ZnPg==";
            if (logoUrl && logoUrl !== 'null' && logoUrl !== 'undefined' && logoUrl.trim() !== '') {
                preview.innerHTML = `<img src="${logoUrl}" style="width:100%;height:100%;object-fit:contain;border-radius:50%;" onerror="this.onerror=null; this.src='${defaultLogo}';">`;
            } else {
                preview.innerHTML = `<img src="${defaultLogo}" style="width:100%;height:100%;object-fit:contain;border-radius:50%;">`;
            }
        }
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
        const tbody = document.getElementById('players-table');
        if (!tbody) return;

        const ctx = window.PlayerDisplay ? PlayerDisplay.getDisplayContext() : {};
        
        let playersToRender = this.state.players;
        
        // Filtering logic
        const searchInput = document.getElementById('player-registry-search');
        const posInput = document.getElementById('player-registry-pos');
        
        const q = searchInput ? searchInput.value.toLowerCase() : '';
        const pos = posInput ? posInput.value : '';
        
        if (q || pos) {
            playersToRender = playersToRender.filter(p => {
                const norm = PlayerDisplay.normalizePlayer(p, ctx);
                let match = true;
                if (q) {
                    const matchName = (norm.fullName || '').toLowerCase().includes(q);
                    const matchId = (norm.playerId || '').toLowerCase().includes(q);
                    if (!matchName && !matchId) match = false;
                }
                if (pos && norm.position !== pos) {
                    match = false;
                }
                return match;
            });
        }

        const normalized = PlayerDisplay.dedupePlayersById(playersToRender).map(function (p) {
            return PlayerDisplay.normalizePlayer(p, ctx);
        });

        tbody.innerHTML = normalized.map(function (n) {
            return PlayerDisplay.rowHtml(
                n,
                'PlayerProfile.open(' + n.id + ')',
                'window.location.href=\'../players/add_player.html?id=' + n.id + '\'',
                'PlayerProfile.open(' + n.id + ')',
                'ClubDashboard.deletePlayer(' + n.id + ')',
                'alert(\'Transfer coming soon.\')'
            );
        }).join('');
        
        if (window.lucide) window.lucide.createIcons();
    },
    
    filterPlayers() {
        this.renderPlayers();
    },

    openPlayerModal(playerId) {
        const raw = this.state.players.find(p => p.id === playerId);
        if (!raw) return;

        const player = window.PlayerDisplay
            ? PlayerDisplay.normalizePlayer(raw, PlayerDisplay.getDisplayContext())
            : null;

        document.getElementById('modal-player-name').innerText = player ? player.fullName : raw.name;
        document.getElementById('modal-player-pos').innerText = player
            ? `${player.position} | #${player.jerseyNumber} · ${player.teamLabel}`
            : `${raw.position} | #${raw.jersey_number || '--'}`;
        document.getElementById('modal-player-rating').innerText = (player && player.rating != null) ? player.rating : (raw.rating || '—');
        document.getElementById('modal-player-goals').innerText = (player && player.goals != null) ? player.goals : (raw.goals || 0);
        document.getElementById('modal-player-assists').innerText = (player && player.assists != null) ? player.assists : (raw.assists || 0);

        const medicalEl = document.getElementById('modal-player-medical');
        if (medicalEl) {
            if (player) {
                medicalEl.innerText = player.medical.fitnessLevel + ' · ' + player.statusLabel.toUpperCase();
                medicalEl.className = 'badge ' + player.statusBadgeClass;
            } else {
                medicalEl.innerText = (raw.fitness_status || 'FIT').toUpperCase();
                medicalEl.className = 'badge badge-success';
            }
            medicalEl.style.display = 'block';
            medicalEl.style.marginTop = '0.5rem';
            medicalEl.style.textAlign = 'center';
        }

        const photoBox = document.querySelector('#player-modal [style*="aspect-ratio"]');
        if (photoBox) {
            const rawUrl = player ? player.photoUrl : raw.photo_url;
            const defaultAvatar = window.PlayerDisplay ? PlayerDisplay.DEFAULT_AVATAR :
                "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjNGI1NTYzIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PGNpcmNsZSBjeD0iMTIiIGN5PSI4IiByPSI0Ii8+PHBhdGggZD0iTTQgMjBjMC00IDQtNyA4LTdzOCAzIDggN1wiLz48L3N2Zz4=";
            const url = (window.PlayerDisplay && rawUrl)
                ? PlayerDisplay.normalizePhotoUrl(rawUrl)
                : (rawUrl || '');
            const img = document.createElement('img');
            img.style.cssText = 'width:100%;height:100%;object-fit:cover;';
            img.alt = '';
            img.src = url || defaultAvatar;
            img.onerror = function() {
                this.onerror = null;
                this.src = defaultAvatar;
            };
            photoBox.innerHTML = '';
            photoBox.appendChild(img);
        }
        
        const editBtn = document.getElementById('modal-edit-btn');
        const deleteBtn = document.getElementById('modal-delete-btn');
        const displayName = player ? player.fullName : raw.name;
        const pid = player ? player.id : raw.id;

        if (editBtn) {
            editBtn.onclick = () => {
                window.location.href = `../players/add_player.html?id=${pid}`;
            };
        }
        if (deleteBtn) {
            deleteBtn.onclick = async () => {
                if (confirm(`Are you sure you want to release ${displayName} from the squad?`)) {
                    try {
                        const res = await fetch(`/api/players/${pid}`, {
                            method: 'DELETE',
                            headers: { 'Authorization': `Bearer ${this.state.token}` }
                        });
                        if (res.ok) {
                            alert("Player released successfully!");
                            this.closePlayerModal();
                            this.loadInitialData(); // Real-time sync list!
                        } else {
                            const err = await res.json();
                            alert("Failed to release player: " + (err.detail || "Unknown error"));
                        }
                    } catch (e) {
                        alert("Network error");
                    }
                }
            };
        }

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
        const nameVal = document.getElementById('reg-name').value.trim();
        const posVal = document.getElementById('reg-position').value;
        const jerseyVal = parseInt(document.getElementById('reg-jersey').value);

        if (!nameVal) { alert('Please enter a player name.'); return; }

        const payload = {
            name: nameVal,
            position: posVal,
            jersey_number: jerseyVal
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
                this.closeRegisterModal();
                // Clear form fields for next use
                document.getElementById('reg-name').value = '';
                document.getElementById('reg-jersey').value = '';
                // Real-time sync: re-fetch + re-render immediately
                localStorage.setItem('player_sync_needed', 'true');
                await this.loadInitialData();
                alert("Player Registered Successfully!");
            } else {
                const d = await r.json();
                alert("Registration Failed: " + (d.detail || "Unknown error"));
            }
        } catch (e) { 
            console.error('submitPlayer error:', e);
            alert("Network Error"); 
        }
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
                    <div style="width: 20px;">${isSelected ? '<i data-lucide="circle" style="color:var(--success)"></i>' : '<i data-lucide="circle"></i>'}</div>
                </div>
            `;
        }).join('');

        // Render Mini Preview
        preview.innerHTML = this.state.players.filter(p => this.state.selectedSquad.includes(p.id)).map(p => `
            <div style="background: var(--bg-tertiary); padding: 8px 16px; border-radius: 10px; font-size: 0.75rem; font-weight: 800; border: 1px solid var(--border); display: flex; align-items: center; gap: 8px;">
                <span style="color: var(--accent-primary)">#${p.jersey_number}</span> ${p.name.split(' ')[0]}
                <i data-lucide="x" style="cursor:pointer; color:var(--danger);" onclick="ClubDashboard.toggleMccPlayer(${p.id})"></i>
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
                        <div style="padding: 1rem; background: ${isXi ? 'rgba(22, 163, 74, 0.1)' : '#000'}; border: 1px solid ${isXi ? 'var(--accent-primary)' : 'var(--border)'}; border-radius: 12px; cursor: pointer; display: flex; justify-content: space-between; align-items: center;" onclick="ClubDashboard.toggleXiPlayer(${p.id})">
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
        if (this.state.simInterval) clearInterval(this.state.simInterval);
        this.state.simInterval = setInterval(() => {
            const frames = Array.from({length: 22}, (_, i) => ({
                id: i,
                x: Math.random() * 100,
                y: Math.random() * 100,
                team_side: i < 11 ? 'home' : 'away',
                jersey: i < 11 ? i+1 : i-10
            }));
            this.renderPitch(frames);
        }, 1000);

        if (this.state.eventSimInterval) clearInterval(this.state.eventSimInterval);
        this.state.eventSimInterval = setInterval(() => {
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
                const color = f.team_side === 'home' ? '#16A34A' : '#ef4444';
                trailsLayer.innerHTML += `<path d="${d}" stroke="${color}" stroke-width="2" fill="none" opacity="0.3" />`;
            }

            if (f.is_ball) {
                ball.style.display = 'block';
                ball.setAttribute('cx', x);
                ball.setAttribute('cy', y);
            } else {
                const color = f.team_side === 'home' ? '#16A34A' : '#ef4444';
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

    renderTraining() {
        const list = document.getElementById('training-list');
        const empty = document.getElementById('training-empty');
        const table = document.getElementById('training-table');
        if (!list) return;

        const sessions = this.state.trainings || [];
        
        // Compute statistics
        document.getElementById('train-total').innerText = sessions.length;
        document.getElementById('train-active').innerText = this.state.players.length;
        
        const now = new Date();
        const upcomingCount = sessions.filter(s => new Date(s.date) > now).length;
        document.getElementById('train-upcoming').innerText = upcomingCount;
        
        if (sessions.length > 0) {
            const sumRate = sessions.reduce((sum, s) => sum + (s.attendance_rate || 0), 0);
            document.getElementById('train-rate').innerText = (sumRate / sessions.length).toFixed(1) + '%';
        } else {
            document.getElementById('train-rate').innerText = '0%';
        }

        if (sessions.length === 0) {
            empty.style.display = 'block';
            table.style.display = 'none';
        } else {
            empty.style.display = 'none';
            table.style.display = 'table';
            list.innerHTML = sessions.map(s => {
                let coach = "Jean-Pierre Kwizera";
                let category = "Tactical";
                let rawNotes = s.notes || "";
                
                try {
                    if (rawNotes.startsWith("{")) {
                        const parsed = JSON.parse(rawNotes);
                        coach = parsed.coach || coach;
                        category = parsed.category || category;
                        rawNotes = parsed.notes || "";
                    }
                } catch(e) {}
                
                const sessionDate = new Date(s.date);
                const isUpcoming = sessionDate > now;
                const statusBadge = isUpcoming ? 
                    `<span class="badge" style="background: rgba(245, 158, 11, 0.15); color: var(--accent-secondary);">UPCOMING</span>` :
                    `<span class="badge badge-success">COMPLETED</span>`;
                
                return `
                <tr style="cursor: pointer;" onclick="if(event.target.tagName !== 'BUTTON' && event.target.tagName !== 'I') ClubDashboard.openTrainingDetailsModal(${s.id})">
                    <td style="font-weight: 800; color: white;">${s.topic}</td>
                    <td>${coach}</td>
                    <td><span class="badge" style="background: rgba(255,255,255,0.05); color: var(--text-secondary); border: 1px solid var(--border);">${category}</span></td>
                    <td>${sessionDate.toLocaleDateString()} ${sessionDate.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</td>
                    <td>
                        <div style="display:flex; align-items:center; gap:10px;">
                            <div style="flex:1; background:rgba(255,255,255,0.05); height:6px; border-radius:3px; overflow:hidden; min-width: 60px;">
                                <div style="width:${s.attendance_rate}%; background:var(--success); height:100%; border-radius:3px;"></div>
                            </div>
                            <span style="font-size:0.75rem; font-weight:800; color:var(--success);">${s.attendance_rate}%</span>
                        </div>
                    </td>
                    <td>${statusBadge}</td>
                    <td>
                        <div style="display:flex; gap:5px;">
                            <button class="btn btn-sm" style="color:var(--accent-primary); background:rgba(22, 163, 74, 0.1); border:1px solid rgba(22, 163, 74, 0.2); padding: 5px 8px;" onclick="event.stopPropagation(); ClubDashboard.openEditTrainingModal(${s.id})"><i data-lucide="edit-3" style="width:12px; height:12px;"></i></button>
                            <button class="btn btn-sm" style="color:var(--danger); background:rgba(239, 68, 68, 0.1); border:1px solid rgba(239, 68, 68, 0.2); padding: 5px 8px;" onclick="event.stopPropagation(); ClubDashboard.deleteTraining(${s.id})"><i data-lucide="trash-2" style="width:12px; height:12px;"></i></button>
                        </div>
                    </td>
                </tr>
            `}).join('');
            
            if (window.lucide) lucide.createIcons();
        }
    },

    openCreateTrainingModal() {
        this.state.editingSessionId = null;
        document.getElementById('training-modal-title').innerText = "Schedule Training";
        document.getElementById('train-date').value = "";
        document.getElementById('train-topic').value = "";
        document.getElementById('train-coach').value = "Jean-Pierre Kwizera";
        document.getElementById('train-category').value = "Tactical";
        document.getElementById('train-att').value = "100";
        document.getElementById('train-notes').value = "";
        document.getElementById('training-modal').style.display = 'flex';
    },

    openEditTrainingModal(id) {
        const s = this.state.trainings.find(x => x.id === id);
        if (!s) return;
        
        this.state.editingSessionId = id;
        document.getElementById('training-modal-title').innerText = "Edit Training Session";
        
        // Parse date for input
        let dateVal = "";
        if (s.date) {
            const d = new Date(s.date);
            const pad = num => String(num).padStart(2, '0');
            dateVal = `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
        }
        
        document.getElementById('train-date').value = dateVal;
        document.getElementById('train-topic').value = s.topic || "";
        document.getElementById('train-att').value = s.attendance_rate || "100";
        
        let coach = "Jean-Pierre Kwizera";
        let category = "Tactical";
        let notesText = s.notes || "";
        
        try {
            if (notesText.startsWith("{")) {
                const parsed = JSON.parse(notesText);
                coach = parsed.coach || coach;
                category = parsed.category || category;
                notesText = parsed.notes || "";
            }
        } catch(e) {}
        
        document.getElementById('train-coach').value = coach;
        document.getElementById('train-category').value = category;
        document.getElementById('train-notes').value = notesText;
        
        document.getElementById('training-modal').style.display = 'flex';
    },

    closeTrainingModal() {
        document.getElementById('training-modal').style.display = 'none';
        this.state.editingSessionId = null;
    },

    async submitTraining() {
        const topic = document.getElementById('train-topic').value;
        const coach = document.getElementById('train-coach').value;
        const category = document.getElementById('train-category').value;
        const notes = document.getElementById('train-notes').value;
        
        const encodedNotes = JSON.stringify({ notes, coach, category });
        
        const payload = {
            date: document.getElementById('train-date').value,
            topic: topic,
            attendance_rate: parseFloat(document.getElementById('train-att').value) || 100,
            notes: encodedNotes
        };
        
        const isEditing = this.state.editingSessionId != null;
        const url = isEditing ? `/api/club/training/${this.state.editingSessionId}` : '/api/club/training';
        const method = isEditing ? 'PUT' : 'POST';
        
        try {
            const r = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${this.state.token}` },
                body: JSON.stringify(payload)
            });
            if (r.ok) {
                this.closeTrainingModal();
                await this.loadInitialData();
                this.renderTraining();
            } else { 
                const err = await r.json();
                alert("Failed to save session: " + (err.detail || "Error")); 
            }
        } catch (e) { alert("Network Error"); }
    },

    async deleteTraining(id) {
        if (!confirm("Delete this training session?")) return;
        try {
            const r = await fetch(`/api/club/training/${id}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${this.state.token}` }
            });
            if (r.ok) {
                await this.loadInitialData();
                this.renderTraining();
            }
        } catch (e) { alert("Error deleting session."); }
    },

    openTrainingDetailsModal(id) {
        const s = this.state.trainings.find(x => x.id === id);
        if (!s) return;
        
        let coach = "Jean-Pierre Kwizera";
        let category = "Tactical";
        let notesText = s.notes || "";
        
        try {
            if (notesText.startsWith("{")) {
                const parsed = JSON.parse(notesText);
                coach = parsed.coach || coach;
                category = parsed.category || category;
                notesText = parsed.notes || "";
            }
        } catch(e) {}
        
        document.getElementById('detail-topic').innerText = s.topic;
        document.getElementById('detail-coach').innerText = coach;
        document.getElementById('detail-category').innerText = category;
        document.getElementById('detail-date').innerText = new Date(s.date).toLocaleDateString() + " " + new Date(s.date).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        document.getElementById('detail-attendance').innerText = s.attendance_rate + "%";
        document.getElementById('detail-notes').innerText = notesText || "No session feedback notes entered.";
        
        // Populate Attendance tracking widget
        const attContainer = document.getElementById('training-attendance-section');
        const players = this.state.players || [];
        if (players.length === 0) {
            attContainer.innerHTML = `<div style="color:var(--text-secondary);font-size:0.8rem;text-align:center;padding:1rem;">No players registered to show squad roster.</div>`;
        } else {
            attContainer.innerHTML = players.map((p, idx) => {
                const isPresent = (idx / players.length) * 100 <= s.attendance_rate;
                const statusColor = isPresent ? 'var(--success)' : 'var(--danger)';
                const statusLabel = isPresent ? 'PRESENT' : 'ABSENT';
                return `
                    <div style="display:flex; justify-content:space-between; align-items:center; background:rgba(255,255,255,0.02); padding:10px 15px; border-radius:8px; border:1px solid var(--border);">
                        <span style="font-weight:700;">${p.name}</span>
                        <span style="font-size:0.7rem; font-weight:900; color:${statusColor};">${statusLabel}</span>
                    </div>
                `;
            }).join('');
        }
        
        // Populate Player Performance widget
        const perfContainer = document.getElementById('training-performance-section');
        if (players.length === 0) {
            perfContainer.innerHTML = `<div style="color:var(--text-secondary);font-size:0.8rem;text-align:center;padding:1rem;">No players registered to show performance metrics.</div>`;
        } else {
            perfContainer.innerHTML = players.slice(0, 4).map(p => {
                const sessionRating = (8.0 + Math.random() * 2).toFixed(1);
                return `
                    <div style="background:rgba(255,255,255,0.02); padding:12px; border-radius:8px; border:1px solid var(--border);">
                        <div style="display:flex; justify-content:space-between; margin-bottom: 5px;">
                            <span style="font-weight:700; font-size:0.85rem;">${p.name}</span>
                            <span style="font-weight:800; font-size:0.85rem; color:var(--accent-secondary);">${sessionRating}</span>
                        </div>
                        <div style="height:4px; background:rgba(255,255,255,0.05); border-radius:2px; overflow:hidden;">
                            <div style="height:100%; width:${sessionRating*10}%; background:var(--accent-secondary);"></div>
                        </div>
                    </div>
                `;
            }).join('');
        }
        
        // Populate Tactical Coach notes widget
        const notesLog = document.getElementById('training-notes-section');
        notesLog.innerHTML = `
            <div style="width: 100%; text-align: left;">
                <div style="font-size: 0.75rem; font-weight:700; color: var(--accent-primary); margin-bottom: 5px;">COACH FEEDBACK BUBBLE</div>
                <div style="color: white; font-size: 0.85rem; font-style: italic; line-height: 1.5;">"${notesText || 'No comments log'}"</div>
                <div style="font-size: 0.7rem; color: var(--text-secondary); font-weight: 700; text-transform: uppercase; margin-top: 15px; text-align: right;">- Signed, ${coach}</div>
            </div>
        `;
        
        document.getElementById('training-detail-modal').style.display = 'flex';
    },

    renderTransfers() {
        const list = document.getElementById('transfer-list');
        const empty = document.getElementById('transfer-empty');
        const table = document.getElementById('transfer-table');
        if (!list) return;
        const esc = window.PlayerDisplay ? PlayerDisplay.escapeHtml.bind(PlayerDisplay) : (v) => String(v == null ? '' : v);

        const transfers = this.state.transfers || [];

        if (transfers.length === 0) {
            empty.style.display = 'block';
            table.style.display = 'none';
        } else {
            empty.style.display = 'none';
            table.style.display = 'table';
            list.innerHTML = transfers.map(t => {
                let badgeClass = 'badge-primary';
                if (t.status === 'APPROVED' || t.status === 'COMPLETED') badgeClass = 'badge-success';
                if (t.status === 'REJECTED' || t.status === 'CANCELLED') badgeClass = 'badge-danger';
                
                const ageLabel = t.age ? `, ${t.age}y` : "";
                const catLabel = t.team_category && t.team_category !== "-" ? ` | ${t.team_category}` : "";
                
                // Beautiful team logo styling
                const fromName = esc(t.from_institution || 'Unknown');
                const toName = esc(t.to_institution || 'Unknown');
                const fromLogoHtml = `<div style="display:inline-flex; align-items:center; gap:8px;"><div style="width:20px; height:20px; border-radius:50%; background:var(--accent-secondary); color:black; font-size:0.6rem; font-weight:900; display:flex; align-items:center; justify-content:center;">${fromName[0] || '?'}</div><span>${fromName}</span></div>`;
                const toLogoHtml = `<div style="display:inline-flex; align-items:center; gap:8px;"><div style="width:20px; height:20px; border-radius:50%; background:var(--accent-primary); color:black; font-size:0.6rem; font-weight:900; display:flex; align-items:center; justify-content:center;">${toName[0] || '?'}</div><span>${toName}</span></div>`;
                
                // Show role-appropriate workflow actions
                let actionHtml = "";
                if (t.status === 'PENDING') {
                    if (t.from_institution_id == this.state.institutionId) {
                        // Senders see APPROVE / REJECT
                        actionHtml = `
                            <div style="display:flex; gap:5px;">
                                <button class="btn btn-sm btn-outline" style="border-color:var(--success); color:var(--success); padding: 4px 8px; font-size:0.7rem;" onclick="ClubDashboard.updateTransferStatus(${t.id}, 'APPROVED')">APPROVE</button>
                                <button class="btn btn-sm btn-outline" style="border-color:var(--danger); color:var(--danger); padding: 4px 8px; font-size:0.7rem;" onclick="ClubDashboard.updateTransferStatus(${t.id}, 'REJECTED')">REJECT</button>
                            </div>
                        `;
                    } else if (t.to_institution_id == this.state.institutionId) {
                        // Requestors see CANCEL
                        actionHtml = `<button class="btn btn-sm btn-outline" style="border-color:var(--danger); color:var(--danger); padding: 4px 8px; font-size:0.7rem;" onclick="ClubDashboard.updateTransferStatus(${t.id}, 'CANCELLED')">CANCEL</button>`;
                    }
                } else {
                    actionHtml = `<span style="font-size:0.7rem; color:var(--text-secondary); font-weight:700; text-transform:uppercase;">ARCHIVED</span>`;
                }

                return `
                <tr>
                    <td>${new Date(t.transfer_date).toLocaleDateString()}</td>
                    <td><strong>${esc(t.player_name || 'Unknown Player')}</strong> <span style="font-size:0.7rem;color:var(--text-secondary); font-weight:700;">(${esc(t.position || '--')}${ageLabel}${catLabel})</span></td>
                    <td>${fromLogoHtml}</td>
                    <td>${toLogoHtml}</td>
                    <td style="font-variant-numeric: tabular-nums; font-weight: 800; color: white;">$${t.fee.toLocaleString()}</td>
                    <td><span class="badge ${badgeClass}">${t.status}</span></td>
                    <td>${actionHtml}</td>
                </tr>
            `}).join('');
        }
    },

    renderTransferHistory() {
        const histContainer = document.getElementById('transfer-history-list');
        if (!histContainer) return;
        const esc = window.PlayerDisplay ? PlayerDisplay.escapeHtml.bind(PlayerDisplay) : (v) => String(v == null ? '' : v);
        
        const transfers = this.state.transfers || [];
        if (transfers.length === 0) {
            histContainer.innerHTML = `<div style="color:var(--text-secondary);font-size:0.85rem;text-align:center;padding:2rem 0;">No club transfer timeline entries to display.</div>`;
            return;
        }
        
        histContainer.innerHTML = transfers.map(t => {
            let timelineColor = 'var(--accent-secondary)';
            let statusText = `requested transition to ${t.to_institution}`;
            if (t.status === 'APPROVED' || t.status === 'COMPLETED') {
                timelineColor = 'var(--success)';
                statusText = `completed contract movement to ${t.to_institution}`;
            } else if (t.status === 'REJECTED') {
                timelineColor = 'var(--danger)';
                statusText = `transfer offer rejected by ${t.from_institution}`;
            } else if (t.status === 'CANCELLED') {
                timelineColor = 'var(--text-secondary)';
                statusText = `transfer offer cancelled by ${t.to_institution}`;
            }
            
            return `
                <div style="display:flex; gap:15px; align-items:flex-start; padding: 12px; background:rgba(255,255,255,0.01); border-radius:8px; border-left:3px solid ${timelineColor};">
                    <div style="font-variant-numeric: tabular-nums; font-size:0.75rem; font-weight:800; color:var(--text-secondary); width: 80px; flex-shrink: 0;">${new Date(t.transfer_date).toLocaleDateString()}</div>
                    <div style="flex:1;">
                        <span style="font-weight:800; color:white;">${esc(t.player_name || 'Unknown Player')}</span>
                        <span style="color:var(--text-secondary); font-size:0.85rem;">${esc(statusText)} for a fee of $${t.fee.toLocaleString()}</span>
                    </div>
                </div>
            `;
        }).join('');
    },

    async submitTransfer() {
        const payload = {
            player_id: parseInt(document.getElementById('trans-player').value),
            to_institution_id: parseInt(document.getElementById('trans-to').value),
            fee: parseFloat(document.getElementById('trans-fee').value) || 0.0
        };
        try {
            const r = await fetch('/api/club/transfers/request', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${this.state.token}` },
                body: JSON.stringify(payload)
            });
            if (r.ok) {
                document.getElementById('transfer-modal').style.display = 'none';
                await this.loadInitialData();
                this.renderTransfers();
                this.renderTransferHistory();
                alert("Transfer Request Submitted");
            } else {
                const err = await r.json();
                alert("Request Failed: " + (err.detail || "Error"));
            }
        } catch (e) { alert("Network Error"); }
    },

    async updateTransferStatus(id, status) {
        if (!confirm(`Are you sure you want to set status to ${status}?`)) return;
        try {
            const r = await fetch(`/api/club/transfers/${id}/status`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${this.state.token}` },
                body: JSON.stringify({ status })
            });
            if (r.ok) {
                await this.loadInitialData();
                this.renderTransfers();
                this.renderTransferHistory();
            } else {
                const err = await r.json();
                alert("Action failed: " + (err.detail || "Error"));
            }
        } catch (e) { alert("Error updating transfer"); }
    },

    async saveBrandingSettings() {
        const logoUrl = document.getElementById('settings-logo-url').value;
        const stadiumName = document.getElementById('settings-stadium').value;
        
        try {
            const r = await fetch('/api/club/institution', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${this.state.token}` },
                body: JSON.stringify({ logo_url: logoUrl, stadium_name: stadiumName })
            });
            
            if (r.ok) {
                const data = await r.json();
                
                // Update local storage so that dynamic branding target renders instantly
                localStorage.setItem('logo_url', logoUrl);
                localStorage.setItem('stadium_name', stadiumName);
                
                // Run global identity target synchronizer
                this.verifyAccess();
                
                // Re-populate settings preview
                const preview = document.getElementById('settings-logo-preview');
                const defaultLogo = window.PlayerDisplay ? PlayerDisplay.DEFAULT_LOGO : "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjNGI1NTYzIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBhdGggZD0iTTEyIDIyczgtNCA4LTEwVjVsLTgtMy04IDN2N2MwIDYgOCAxMCA4IDEweiIvPjwvc3ZnPg==";
                if (logoUrl && logoUrl !== 'null' && logoUrl !== 'undefined' && logoUrl.trim() !== '') {
                    preview.innerHTML = `<img src="${logoUrl}" style="width:100%;height:100%;object-fit:contain;border-radius:50%;" onerror="this.onerror=null; this.src='${defaultLogo}';">`;
                } else {
                    preview.innerHTML = `<img src="${defaultLogo}" style="width:100%;height:100%;object-fit:contain;border-radius:50%;">`;
                }
                
                alert("Branding identity saved successfully!");
            } else {
                const err = await r.json();
                alert("Failed to save branding settings: " + (err.detail || "Error"));
            }
        } catch (e) {
            alert("Network Error");
        }
    },

    logout() {
        localStorage.clear();
        window.location.href = '/login.html';
    }
};

document.addEventListener('DOMContentLoaded', () => ClubDashboard.init());
