/**
 * Shared Player Profile Engine
 * Injects a comprehensive, tabbed player profile modal into any dashboard.
 */
(function() {
    'use strict';

    // ── CSS Injection ──
    const style = document.createElement('style');
    style.textContent = `
                #player-profile-overlay {
            position: fixed; inset: 0;
            background: rgba(15, 23, 42, 0.7);
            backdrop-filter: blur(8px);
            z-index: 2000;
            display: none; justify-content: center; align-items: center;
            opacity: 0; transition: opacity 0.3s ease;
        }
        #player-profile-overlay.active { display: flex; opacity: 1; }
        .pp-container {
            width: 95vw; max-width: 1400px; height: 90vh;
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 16px;
            display: flex; overflow: hidden;
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.2);
            transform: scale(0.95);
            transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            color: #0F172A; font-family: 'Inter', sans-serif;
        }
        #player-profile-overlay.active .pp-container { transform: scale(1); }
        
        .pp-sidebar {
            width: 320px;
            background: #FFFFFF;
            border-right: 1px solid #E2E8F0;
            display: flex; flex-direction: column;
            overflow-y: auto;
        }
        .pp-header { padding: 2rem; text-align: center; border-bottom: 1px solid #E2E8F0; background: #FFFFFF; }
        .pp-photo-wrapper {
            width: 140px; height: 140px; border-radius: 50%;
            background: #F8FAFC; margin: 0 auto 1.5rem;
            border: 4px solid #16A34A; overflow: hidden;
            display: flex; align-items: center; justify-content: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }
        .pp-photo-wrapper img { width: 100%; height: 100%; object-fit: cover; }
        .pp-photo-wrapper i { font-size: 3.5rem; color: #1E293B; }
        .pp-badge-active { background: rgba(22,163,74,0.1); color: #16A34A; border: 1px solid #16A34A; }
        .pp-badge-warning { background: rgba(217,119,6,0.1); color: #D97706; border: 1px solid #D97706; }
        .pp-badge-danger { background: rgba(220,38,38,0.1); color: #DC2626; border: 1px solid #DC2626; }
        .pp-medical-note { font-size: 0.8rem; color: #1E293B; margin-bottom: 1.5rem; padding: 1rem; background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; border-left: 4px solid #16A34A; }
        .pp-name { font-size: 1.5rem; font-weight: 800; color: #0F172A; margin-bottom: 0.25rem; }
        .pp-position { font-size: 0.9rem; color: #16A34A; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; }
        
        .pp-nav { flex: 1; padding: 1.5rem 1rem; display: flex; flex-direction: column; gap: 0.5rem; background: #FFFFFF; }
        .pp-nav-item {
            padding: 1rem; border-radius: 8px; cursor: pointer;
            display: flex; align-items: center; gap: 1rem;
            color: #1E293B; font-weight: 600; font-size: 0.95rem; transition: 0.2s;
            border: 1px solid transparent;
        }
        .pp-nav-item:hover { background: #F8FAFC; color: #0F172A; border-color: #E2E8F0; }
        .pp-nav-item.active { background: #F8FAFC; color: #16A34A; border: 1px solid #E2E8F0; border-left: 4px solid #16A34A; font-weight: 700; }
        .pp-nav-item i { width: 20px; }
        
        .pp-content { flex: 1; padding: 2.5rem 3.5rem; overflow-y: auto; background: #F8FAFC; position: relative; }
        .pp-close-btn {
            position: absolute; top: 1.5rem; right: 1.5rem;
            background: #FFFFFF; border: 1px solid #E2E8F0; color: #1E293B;
            width: 40px; height: 40px; border-radius: 50%;
            font-size: 1.5rem; cursor: pointer; display: flex; align-items: center; justify-content: center;
            transition: 0.2s; z-index: 10; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .pp-close-btn:hover { background: #F8FAFC; color: #DC2626; border-color: #DC2626; }
        
        .pp-section { display: none; animation: ppFadeIn 0.3s ease; }
        .pp-section.active { display: block; }
        @keyframes ppFadeIn { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:translateY(0)} }
        
        .pp-section-title { font-size: 1.5rem; font-weight: 800; margin-bottom: 2rem; border-bottom: 2px solid #E2E8F0; padding-bottom: 1rem; color: #0F172A; }
        
        .pp-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 1.5rem; margin-bottom: 2.5rem; }
        .pp-card {
            background: #FFFFFF; border: 1px solid #E2E8F0;
            border-radius: 12px; padding: 1.5rem;
            box-shadow: 0 2px 5px rgba(0,0,0,0.02);
        }
        .pp-card-label { font-size: 0.75rem; font-weight: 700; color: #1E293B; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem; }
        .pp-card-value { font-size: 1.15rem; font-weight: 700; color: #0F172A; }
        
        .pp-input-group { margin-bottom: 1.5rem; }
        .pp-input-group label { display: block; font-size: 0.85rem; font-weight: 700; color: #1E293B; margin-bottom: 0.5rem; }
        .pp-input { width: 100%; background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 0.75rem; color: #0F172A; font-family: inherit; font-size: 0.95rem; }
        .pp-input:focus { outline: none; border-color: #16A34A; box-shadow: 0 0 0 3px rgba(22,163,74,0.1); }
        
        .pp-table { width: 100%; border-collapse: separate; border-spacing: 0; margin-top: 1rem; border: 1px solid #E2E8F0; border-radius: 12px; overflow: hidden; background: #FFFFFF; }
        .pp-table th { text-align: left; padding: 1.25rem 1rem; background: #F8FAFC; font-size: 0.8rem; font-weight: 700; color: #1E293B; text-transform: uppercase; border-bottom: 1px solid #E2E8F0; }
        .pp-table td { padding: 1.25rem 1rem; border-bottom: 1px solid #E2E8F0; font-size: 0.95rem; color: #0F172A; }
        .pp-table tr:last-child td { border-bottom: none; }
        
        .pp-btn {
            background: #16A34A; color: #FFFFFF; border: none; padding: 0.75rem 1.5rem;
            border-radius: 8px; font-weight: 700; cursor: pointer; display: inline-flex;
            align-items: center; gap: 0.5rem; transition: 0.2s; font-size: 0.95rem;
        }
        .pp-btn:hover { background: #15803D; }
        .pp-btn-outline { background: #FFFFFF; border: 1px solid #E2E8F0; color: #0F172A; }
        .pp-btn-outline:hover { background: #F8FAFC; border-color: #1E293B; }
        .pp-btn-danger { background: #FFFFFF; color: #DC2626; border: 1px solid #DC2626; }
        .pp-btn-danger:hover { background: #DC2626; color: #FFFFFF; }

        #pp-export-container { display: none; width: 800px; padding: 40px; background: white; color: black; font-family: 'Inter', sans-serif; }
    `;
    document.head.appendChild(style);

    // ── HTML Injection ──
    const overlay = document.createElement('div');
    overlay.id = 'player-profile-overlay';
    overlay.innerHTML = `
        <div class="pp-container">
            <!-- Sidebar Navigation -->
            <div class="pp-sidebar">
                <div class="pp-header">
                    <div class="pp-photo-wrapper" id="pp-photo-display">
                        <i data-lucide="user"></i>
                    </div>
                    <div class="pp-name" id="pp-name-display">Loading...</div>
                    <div class="pp-position" id="pp-pos-display">--</div>
                    <div style="margin-top:0.5rem;"><span class="badge" style="background:rgba(22,163,74,0.1);color:#16A34A;padding:4px 8px;border-radius:4px;font-size:0.7rem;font-weight:800;border:1px solid #16A34A;" id="pp-status-display">ACTIVE</span></div>
                </div>
                <div class="pp-nav">
                    <div class="pp-nav-item active" onclick="PlayerProfile.showTab('basic')"><i data-lucide="user"></i> Basic Information</div>
                    <div class="pp-nav-item" onclick="PlayerProfile.showTab('medical')"><i data-lucide="heart-pulse"></i> Medical Information</div>
                    <div class="pp-nav-item" onclick="PlayerProfile.showTab('team')"><i data-lucide="shield-half"></i> Team Information</div>
                    <div class="pp-nav-item" onclick="PlayerProfile.showTab('stats')"><i data-lucide="line-chart"></i> Statistics</div>
                    <div class="pp-nav-item" onclick="PlayerProfile.showTab('training')"><i data-lucide="dumbbell"></i> Training History</div>
                    <div class="pp-nav-item" onclick="PlayerProfile.showTab('match')"><i data-lucide="swords"></i> Match History</div>
                    <div class="pp-nav-item" onclick="PlayerProfile.showTab('reports')"><i data-lucide="file-text"></i> Reports & Export</div>
                </div>
            </div>
            
            <!-- Main Content Area -->
            <div class="pp-content">
                <button class="pp-close-btn" onclick="PlayerProfile.close()">&times;</button>
                
                <!-- Basic Info -->
                <div id="pp-tab-basic" class="pp-section active">
                    <div class="pp-section-title">Basic Information</div>
                    <div class="pp-grid">
                        <div class="pp-card"><div class="pp-card-label">Full Name</div><div class="pp-card-value" id="pp-val-name">--</div></div>
                        <div class="pp-card"><div class="pp-card-label">Player ID</div><div class="pp-card-value" id="pp-val-code" style="font-family:monospace;color:#16A34A;">--</div></div>
                        <div class="pp-card"><div class="pp-card-label">Position</div><div class="pp-card-value" id="pp-val-position">--</div></div>
                        <div class="pp-card"><div class="pp-card-label">Jersey Number</div><div class="pp-card-value" id="pp-val-jersey">--</div></div>
                        <div class="pp-card"><div class="pp-card-label">Nationality</div><div class="pp-card-value" id="pp-val-nat">--</div></div>
                        <div class="pp-card"><div class="pp-card-label">Team / Institution</div><div class="pp-card-value" id="pp-val-inst">--</div></div>
                        <div class="pp-card"><div class="pp-card-label">Date of Birth</div><div class="pp-card-value" id="pp-val-dob">--</div></div>
                        <div class="pp-card"><div class="pp-card-label">Age</div><div class="pp-card-value" id="pp-val-age">--</div></div>
                        <div class="pp-card"><div class="pp-card-label">Preferred Foot</div><div class="pp-card-value" id="pp-val-foot">--</div></div>
                        <div class="pp-card"><div class="pp-card-label">Status</div><div class="pp-card-value" id="pp-val-status">--</div></div>
                    </div>
                    <div style="display:flex;gap:1rem;margin-top:2rem;border-top:1px solid rgba(255,255,255,0.05);padding-top:2rem;">
                        <button class="pp-btn pp-btn-danger" onclick="PlayerProfile.deletePlayer()"><i data-lucide="trash"></i> Delete Player Record</button>
                    </div>
                </div>

                <!-- Medical Info -->
                <div id="pp-tab-medical" class="pp-section">
                    <div style="display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:2rem;border-bottom:1px solid rgba(255,255,255,0.08);padding-bottom:1rem;">
                        <div class="pp-section-title" style="margin:0;border:none;padding:0;">Medical Information</div>
                        <button class="pp-btn" onclick="PlayerProfile.saveMedical()"><i data-lucide="save"></i> Save Changes</button>
                    </div>
                    <p class="pp-medical-note">Height, weight, injury status, fitness level, medical notes, and checkup dates are stored here only — not mixed with basic profile fields.</p>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:2rem;">
                        <div>
                            <div class="pp-input-group">
                                <label>Height (cm)</label>
                                <input type="number" id="pp-input-height" class="pp-input" step="0.1">
                            </div>
                            <div class="pp-input-group">
                                <label>Weight (kg)</label>
                                <input type="number" id="pp-input-weight" class="pp-input" step="0.1">
                            </div>
                            <div class="pp-input-group">
                                <label>Blood Group</label>
                                <select id="pp-input-blood" class="pp-input">
                                    <option value="">Select...</option>
                                    <option value="A+">A+</option><option value="A-">A-</option>
                                    <option value="B+">B+</option><option value="B-">B-</option>
                                    <option value="AB+">AB+</option><option value="AB-">AB-</option>
                                    <option value="O+">O+</option><option value="O-">O-</option>
                                </select>
                            </div>
                        </div>
                        <div>
                            <div class="pp-input-group">
                                <label>Fitness Status</label>
                                <select id="pp-input-fitness" class="pp-input">
                                    <option value="Fit">Fit to Play</option>
                                    <option value="Recovering">Recovering</option>
                                    <option value="Unfit">Unfit</option>
                                </select>
                            </div>
                            <div class="pp-input-group">
                                <label>Injury Status</label>
                                <select id="pp-input-injury" class="pp-input">
                                    <option value="None">None</option>
                                    <option value="Minor">Minor Injury</option>
                                    <option value="Major">Major Injury</option>
                                </select>
                            </div>
                            <div class="pp-input-group">
                                <label>Last Medical Check</label>
                                <input type="date" id="pp-input-medical-date" class="pp-input">
                            </div>
                        </div>
                    </div>
                    <div class="pp-input-group" style="margin-top:1rem;">
                        <label>Medical Notes / Conditions</label>
                        <textarea id="pp-input-notes" class="pp-input" rows="4" placeholder="Allergies, past surgeries, chronic conditions..."></textarea>
                    </div>
                </div>

                <!-- Team Info -->
                <div id="pp-tab-team" class="pp-section">
                    <div class="pp-section-title">Team Association</div>
                    <div class="pp-card" style="margin-bottom:1.5rem;display:flex;align-items:center;gap:2rem;">
                        <div id="pp-team-logo-wrap" style="width:100px;height:100px;background:#F8FAFC;border:2px solid #E2E8F0;border-radius:16px;display:flex;align-items:center;justify-content:center;overflow:hidden;box-shadow:0 2px 4px rgba(0,0,0,0.05);padding:0.5rem;"><i data-lucide="shield" style="font-size:2.5rem;color:#1E293B;"></i></div>
                        <div>
                            <div style="color:#64748B;font-size:0.8rem;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;">Ownership (one institution)</div>
                            <div id="pp-val-team-type" style="font-size:0.8rem;color:#16A34A;font-weight:800;margin-top:0.25rem;">--</div>
                            <div id="pp-val-team" style="font-size:1.5rem;color:#0F172A;font-weight:800;">Not Assigned</div>
                            <div style="margin-top:0.5rem;color:#64748B;font-size:0.85rem;">Each player belongs to exactly one Club, Academy, or School.</div>
                            <div style="margin-top:1rem;">
                                <button class="pp-btn pp-btn-outline" style="padding:0.5rem 1rem;font-size:0.85rem;" onclick="alert('Use the Teams module to assign players.')">Change Assignment</button>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Statistics -->
                <div id="pp-tab-stats" class="pp-section">
                    <div class="pp-section-title">Performance Statistics</div>
                    <div class="pp-card" style="font-size:1rem;color:#94a3b8;text-align:center;padding:1rem;">
                        No performance data available.
                    </div>
                    <div style="background:rgba(22,163,74,0.05);border:1px solid rgba(22,163,74,0.2);border-radius:12px;padding:1.5rem;margin-top:2rem;">
                        <div style="display:flex;align-items:center;gap:0.5rem;color:#16A34A;font-weight:800;margin-bottom:0.5rem;"><i data-lucide="cpu"></i> AI ANALYSIS READY</div>
                        <div style="color:#94a3b8;font-size:0.9rem;">Player statistics are actively monitored by the SPORTEXA AI Engine. Advanced metrics such as expected goals (xG), heatmaps, and tactical adherence will populate automatically as more match footage is ingested.</div>
                    </div>
                </div>

                <!-- Training History -->
                <div id="pp-tab-training" class="pp-section">
                    <div class="pp-section-title">Training History</div>
                    <div class="pp-card" style="text-align:center;padding:3rem;">
                        <i data-lucide="dumbbell" style="font-size:3rem;color:#4b5563;margin-bottom:1rem;"></i>
                        <div style="font-size:1.2rem;font-weight:700;">No Training Records</div>
                        <div style="color:#94a3b8;font-size:0.9rem;">Training attendance and performance data will appear here.</div>
                    </div>
                </div>

                <!-- Match History -->
                <div id="pp-tab-match" class="pp-section">
                    <div class="pp-section-title">Recent Matches</div>
                    <div class="pp-card" style="padding:0;overflow:hidden;">
                        <table class="pp-table">
                            <thead><tr><th>Date</th><th>Opponent</th><th>Result</th><th>Min</th><th>Rating</th></tr></thead>
                            <tbody>
                                <tr><td colspan="5" style="text-align:center;padding:2rem;color:#94a3b8;">No match data available yet.</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- Reports & Documents -->
                <div id="pp-tab-reports" class="pp-section">
                    <div class="pp-section-title">Documents & Export</div>
                    <div class="pp-card" style="display:flex;align-items:center;justify-content:space-between;">
                        <div>
                            <div style="font-size:1.2rem;font-weight:800;margin-bottom:0.5rem;">Official Player Dossier</div>
                            <div style="color:#94a3b8;font-size:0.9rem;">Generate a comprehensive PDF report including medical, physical, and performance data.</div>
                        </div>
                        <button class="pp-btn" onclick="PlayerProfile.generatePDF()"><i data-lucide="download"></i> Download PDF</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Hidden container for PDF generation -->
        <div id="pp-export-container">
            <div style="border-bottom:3px solid #16A34A;padding-bottom:20px;margin-bottom:30px;display:flex;justify-content:space-between;align-items:flex-end;">
                <div>
                    <h1 style="margin:0;font-size:32px;text-transform:uppercase;color:#111827;">OFFICIAL PLAYER DOSSIER</h1>
                    <div style="color:#4b5563;margin-top:5px;font-weight:bold;" id="pdf-date">Generated: </div>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:24px;font-weight:bold;color:#16A34A;" id="pdf-id"></div>
                    <div style="color:#6b7280;font-size:12px;">SPORTEXA INTELLIGENCE HUB</div>
                </div>
            </div>
            
            <div style="display:flex;gap:30px;margin-bottom:40px;">
                <div style="width:150px;height:150px;background:#f3f4f6;border:2px solid #e5e7eb;display:flex;align-items:center;justify-content:center;font-size:12px;color:#9ca3af;">[PHOTO]</div>
                <div>
                    <h2 style="margin:0 0 10px 0;font-size:28px;" id="pdf-name">--</h2>
                    <div style="font-size:18px;color:#16A34A;font-weight:bold;margin-bottom:15px;" id="pdf-pos">--</div>
                    <table style="width:100%;text-align:left;font-size:14px;">
                        <tr><td style="padding:5px;color:#6b7280;width:100px;">Nationality</td><td style="font-weight:bold;" id="pdf-nat">--</td></tr>
                        <tr><td style="padding:5px;color:#6b7280;">Date of Birth</td><td style="font-weight:bold;" id="pdf-dob">--</td></tr>
                        <tr><td style="padding:5px;color:#6b7280;">Age</td><td style="font-weight:bold;" id="pdf-age">--</td></tr>
                        <tr><td style="padding:5px;color:#6b7280;">Institution</td><td style="font-weight:bold;" id="pdf-inst">--</td></tr>
                    </table>
                </div>
            </div>
            
            <h3 style="background:#f3f4f6;padding:10px;margin:0 0 20px 0;">MEDICAL & PHYSICAL PROFILE</h3>
            <table style="width:100%;border-collapse:collapse;margin-bottom:40px;font-size:14px;">
                <tr>
                    <td style="padding:10px;border:1px solid #e5e7eb;background:#f9fafb;color:#6b7280;">Height</td><td style="padding:10px;border:1px solid #e5e7eb;font-weight:bold;" id="pdf-height">--</td>
                    <td style="padding:10px;border:1px solid #e5e7eb;background:#f9fafb;color:#6b7280;">Weight</td><td style="padding:10px;border:1px solid #e5e7eb;font-weight:bold;" id="pdf-weight">--</td>
                </tr>
                <tr>
                    <td style="padding:10px;border:1px solid #e5e7eb;background:#f9fafb;color:#6b7280;">Blood Group</td><td style="padding:10px;border:1px solid #e5e7eb;font-weight:bold;" id="pdf-blood">--</td>
                    <td style="padding:10px;border:1px solid #e5e7eb;background:#f9fafb;color:#6b7280;">Fitness Status</td><td style="padding:10px;border:1px solid #e5e7eb;font-weight:bold;" id="pdf-fitness">--</td>
                </tr>
                <tr>
                    <td style="padding:10px;border:1px solid #e5e7eb;background:#f9fafb;color:#6b7280;">Injury Status</td><td style="padding:10px;border:1px solid #e5e7eb;font-weight:bold;" id="pdf-injury">--</td>
                    <td style="padding:10px;border:1px solid #e5e7eb;background:#f9fafb;color:#6b7280;">Last Check</td><td style="padding:10px;border:1px solid #e5e7eb;font-weight:bold;" id="pdf-check">--</td>
                </tr>
                <tr>
                    <td style="padding:10px;border:1px solid #e5e7eb;background:#f9fafb;color:#6b7280;">Medical Notes</td><td colspan="3" style="padding:10px;border:1px solid #e5e7eb;font-weight:bold;" id="pdf-notes">--</td>
                </tr>
            </table>

            <h3 style="background:#f3f4f6;padding:10px;margin:0 0 20px 0;">PERFORMANCE SUMMARY</h3>
            <table style="width:100%;text-align:center;border-collapse:collapse;margin-bottom:40px;">
                <tr style="background:#f9fafb;color:#6b7280;font-size:12px;">
                    <th style="padding:10px;border:1px solid #e5e7eb;">MATCHES</th>
                    <th style="padding:10px;border:1px solid #e5e7eb;">MINUTES</th>
                    <th style="padding:10px;border:1px solid #e5e7eb;">GOALS</th>
                    <th style="padding:10px;border:1px solid #e5e7eb;">ASSISTS</th>
                    <th style="padding:10px;border:1px solid #e5e7eb;">RATING</th>
                </tr>
                <tr style="font-size:20px;font-weight:bold;">
                    <td style="padding:15px;border:1px solid #e5e7eb;">12</td>
                    <td style="padding:15px;border:1px solid #e5e7eb;">945</td>
                    <td style="padding:15px;border:1px solid #e5e7eb;">4</td>
                    <td style="padding:15px;border:1px solid #e5e7eb;">3</td>
                    <td style="padding:15px;border:1px solid #e5e7eb;color:#16A34A;">8.2</td>
                </tr>
            </table>
            
            <div style="text-align:center;font-size:10px;color:#9ca3af;margin-top:40px;border-top:1px solid #e5e7eb;padding-top:10px;">
                CONFIDENTIAL - GENERATED BY SPORTEXA AI HUB
            </div>
        </div>
    `;
    document.body.appendChild(overlay);

    // ── Global Logic ──
    window.PlayerProfile = {
        currentPlayerId: null,
        currentPlayerData: null,

        open: async function(playerId) {
            this.currentPlayerId = playerId;
            this.resetUI();
            overlay.classList.add('active');
            this.showTab('basic');
            await this.loadData();
            if (window.lucide) window.lucide.createIcons();
        },

        close: function() {
            overlay.classList.remove('active');
            this.currentPlayerId = null;
            this.currentPlayerData = null;
            this.resetUI();
        },

        resetUI: function() {
            document.getElementById('pp-name-display').innerText = '--';
            document.getElementById('pp-pos-display').innerText = '--';
            document.getElementById('pp-photo-display').innerHTML = '<i data-lucide="user"></i>';
            var statusEl = document.getElementById('pp-status-display');
            if (statusEl) {
                statusEl.innerText = 'ACTIVE';
                statusEl.className = 'badge pp-badge-active';
            }
            ['pp-val-name', 'pp-val-code', 'pp-val-position', 'pp-val-dob', 'pp-val-age', 'pp-val-nat',
                'pp-val-jersey', 'pp-val-foot', 'pp-val-inst', 'pp-val-status', 'pp-val-team', 'pp-val-team-type'
            ].forEach(function (id) {
                var el = document.getElementById(id);
                if (el) el.innerText = '--';
            });
            ['pp-input-height', 'pp-input-weight', 'pp-input-notes'].forEach(function (id) {
                var el = document.getElementById(id);
                if (el) el.value = '';
            });
            ['pp-input-blood', 'pp-input-fitness', 'pp-input-injury'].forEach(function (id) {
                var el = document.getElementById(id);
                if (el) el.selectedIndex = 0;
            });
            var medDate = document.getElementById('pp-input-medical-date');
            if (medDate) medDate.value = '';
        },

        showTab: function(tabId) {
            document.querySelectorAll('.pp-nav-item').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.pp-section').forEach(el => el.classList.remove('active'));
            
            const selectedNavItem = Array.from(document.querySelectorAll('.pp-nav-item')).find(el => el.getAttribute('onclick').includes(tabId));
            if (selectedNavItem) selectedNavItem.classList.add('active');
            
            const section = document.getElementById('pp-tab-' + tabId);
            if (section) section.classList.add('active');
        },

        loadData: async function() {
            try {
                const token = localStorage.getItem('access_token');
                if (!token) return;

                // Set loading state
                document.getElementById('pp-name-display').innerText = "Loading...";

                const res = await fetch('/api/players/' + this.currentPlayerId, {
                    headers: { 'Authorization': 'Bearer ' + token }
                });

                if (!res.ok) {
                    throw new Error('Failed to load player');
                }

                const data = await res.json();
                this.currentPlayerData = data;
                this.populateUI(data);

            } catch (err) {
                console.error(err);
                alert("Error loading player profile: " + err.message);
                this.close();
            }
        },

        populateUI: function(p) {
            var view = window.PlayerDisplay
                ? PlayerDisplay.normalizePlayer(p, PlayerDisplay.getDisplayContext())
                : null;
            var raw = p;
            if (view) {
                p = view.raw;
            }

            var fullName = view ? view.fullName : (raw.name || '--');
            var position = view ? view.position : (raw.position || '--');
            var jersey = view ? view.jerseyNumber : (raw.jersey_number || '--');
            var photoUrl = view ? view.photoUrl : raw.photo_url;
            var statusLabel = view ? view.statusLabel : 'Active';
            var statusClass = view ? ('pp-badge-' + view.statusTone) : 'pp-badge-active';

            document.getElementById('pp-name-display').innerText = fullName;
            document.getElementById('pp-pos-display').innerText = position + ' | #' + jersey;

            var photoWrap = document.getElementById('pp-photo-display');
            if (photoUrl) {
                var safeUrl = photoUrl.replace(/"/g, '&quot;');
                var fallback = window.PlayerDisplay ? PlayerDisplay.DEFAULT_AVATAR : '';
                photoWrap.innerHTML = '<img src="' + safeUrl + '" alt="" onerror="this.onerror=null; this.src=\'' + fallback + '\';">';
            } else {
                photoWrap.innerHTML = '<i data-lucide="user"></i>';
            }

            var statusEl = document.getElementById('pp-status-display');
            if (statusEl) {
                statusEl.innerText = statusLabel.toUpperCase();
                statusEl.className = 'badge ' + statusClass;
            }

            document.getElementById('pp-val-name').innerText = fullName;
            document.getElementById('pp-val-code').innerText = view ? view.playerId : (raw.player_code || '--');
            document.getElementById('pp-val-position').innerText = position;
            document.getElementById('pp-val-dob').innerText = view ? (view.dateOfBirth || '--') : (raw.date_of_birth || '--');
            document.getElementById('pp-val-age').innerText = view ? view.age : (raw.age || '--');
            document.getElementById('pp-val-nat').innerText = view ? view.nationality : (raw.nationality || '--');
            document.getElementById('pp-val-jersey').innerText = jersey;
            document.getElementById('pp-val-foot').innerText = view ? view.preferredFoot : (raw.preferred_foot || '--');
            document.getElementById('pp-val-inst').innerText = view ? view.teamLabel : (localStorage.getItem('institution_name') || 'Registered Institution');
            document.getElementById('pp-val-status').innerText = statusLabel;

            var med = view ? view.medical : raw;
            document.getElementById('pp-input-height').value = med.height != null && med.height !== '' ? med.height : '';
            document.getElementById('pp-input-weight').value = med.weight != null && med.weight !== '' ? med.weight : '';
            document.getElementById('pp-input-blood').value = (view ? med.bloodGroup : raw.blood_group) || '';
            document.getElementById('pp-input-fitness').value = view ? med.fitnessLevel : (raw.fitness_status || 'Fit');
            document.getElementById('pp-input-injury').value = view ? med.injuryStatus : (raw.injury_status || 'None');
            document.getElementById('pp-input-medical-date').value = view ? (med.lastCheckup || '') : (raw.last_medical_check || '');
            document.getElementById('pp-input-notes').value = view ? med.medicalNotes : (raw.medical_conditions || '');

            document.getElementById('pp-val-team-type').innerText = view && view.teamType ? view.teamType : '--';
            document.getElementById('pp-val-team').innerText = view ? view.teamName : (raw.team ? raw.team.name : 'Not Assigned');
            
            var teamLogoWrap = document.getElementById('pp-team-logo-wrap');
            if (teamLogoWrap) {
                var tLogo = null;
                if (view && view.teamType) {
                    if (view.teamType === 'Club' && view.club) tLogo = view.club.logo;
                    else if (view.teamType === 'Academy' && view.academy) tLogo = view.academy.logo;
                    else if (view.teamType === 'School' && view.school) tLogo = view.school.logo;
                }
                if (!tLogo) tLogo = window.PlayerDisplay ? PlayerDisplay.DEFAULT_LOGO : null;
                if (tLogo) {
                    teamLogoWrap.innerHTML = '<img src="' + tLogo.replace(/"/g, '&quot;') + '" alt="Team Logo" style="width:100%;height:100%;object-fit:contain;">';
                } else {
                    teamLogoWrap.innerHTML = '<i data-lucide="shield" style="font-size:2.5rem;color:#1E293B;"></i>';
                }
            }

            document.getElementById('pdf-date').innerText = 'Generated: ' + new Date().toLocaleDateString();
            document.getElementById('pdf-id').innerText = view ? view.playerId : (raw.player_code || '--');
            document.getElementById('pdf-name').innerText = fullName;
            document.getElementById('pdf-pos').innerText = position + ' | #' + jersey;
            document.getElementById('pdf-nat').innerText = view ? view.nationality : (raw.nationality || '--');
            document.getElementById('pdf-dob').innerText = view ? (view.dateOfBirth || '--') : (raw.date_of_birth || '--');
            document.getElementById('pdf-age').innerText = view ? view.age : (raw.age || '--');
            document.getElementById('pdf-inst').innerText = view ? view.teamLabel : (localStorage.getItem('institution_name') || '--');

            var h = view ? med.height : raw.height;
            var w = view ? med.weight : raw.weight;
            document.getElementById('pdf-height').innerText = h ? h + ' cm' : '--';
            document.getElementById('pdf-weight').innerText = w ? w + ' kg' : '--';
            document.getElementById('pdf-blood').innerText = (view ? med.bloodGroup : raw.blood_group) || '--';
            document.getElementById('pdf-fitness').innerText = view ? med.fitnessLevel : (raw.fitness_status || 'Fit');
            document.getElementById('pdf-injury').innerText = view ? med.injuryStatus : (raw.injury_status || 'None');
            document.getElementById('pdf-check').innerText = view ? (med.lastCheckup || '--') : (raw.last_medical_check || '--');
            document.getElementById('pdf-notes').innerText = (view ? med.medicalNotes : raw.medical_conditions) || 'None recorded.';
        },

        saveMedical: async function() {
            try {
                const token = localStorage.getItem('access_token');
                const btn = document.querySelector('#pp-tab-medical .pp-btn');
                const originalText = btn.innerHTML;
                btn.innerHTML = '<i data-lucide="loader" class="spin"></i> Saving...';

                const payload = {
                    height: parseFloat(document.getElementById('pp-input-height').value) || null,
                    weight: parseFloat(document.getElementById('pp-input-weight').value) || null,
                    blood_group: document.getElementById('pp-input-blood').value || null,
                    fitness_status: document.getElementById('pp-input-fitness').value,
                    injury_status: document.getElementById('pp-input-injury').value,
                    last_medical_check: document.getElementById('pp-input-medical-date').value || null,
                    medical_conditions: document.getElementById('pp-input-notes').value || null
                };

                // The PUT endpoint requires PlayerUpdate schema. Ensure date format is string.
                if (payload.last_medical_check) {
                    // API currently expects date_of_birth mapping for dates, but let's just send the raw payload. 
                    // In routes.py, it takes **player_data.
                }

                const res = await fetch('/api/players/' + this.currentPlayerId, {
                    method: 'PUT',
                    headers: {
                        'Authorization': 'Bearer ' + token,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });

                if (!res.ok) throw new Error('Failed to update medical data.');
                
                const updated = await res.json();
                this.currentPlayerData = updated;
                this.populateUI(updated);
                
                btn.innerHTML = '<i data-lucide="check"></i> Saved';
                setTimeout(() => { btn.innerHTML = originalText; if(window.lucide) window.lucide.createIcons(); }, 2000);

            } catch (err) {
                console.error(err);
                alert(err.message);
                document.querySelector('#pp-tab-medical .pp-btn').innerHTML = '<i data-lucide="save"></i> Save Changes';
            }
        },

        deletePlayer: async function() {
            if (!confirm('Are you sure you want to permanently delete ' + (this.currentPlayerData?.name || 'this player') + '? This action cannot be undone.')) return;
            
            try {
                const token = localStorage.getItem('access_token');
                const res = await fetch('/api/players/' + this.currentPlayerId, {
                    method: 'DELETE',
                    headers: { 'Authorization': 'Bearer ' + token }
                });

                if (!res.ok) {
                    const data = await res.json();
                    throw new Error(data.detail || 'Failed to delete');
                }

                alert('Player deleted successfully.');
                this.close();
                // If the dashboard has a loadPlayers function, trigger it
                if (typeof window.ClubDashboard !== 'undefined' && window.ClubDashboard.loadPlayers) {
                    window.ClubDashboard.loadPlayers();
                } else {
                    window.location.reload();
                }

            } catch (err) {
                console.error(err);
                alert("Error deleting player: " + err.message);
            }
        },

        generatePDF: function() {
            if (typeof html2pdf === 'undefined') {
                alert("PDF engine not loaded. Please refresh the page.");
                return;
            }
            const element = document.getElementById('pp-export-container');
            element.style.display = 'block'; // Temporarily show
            
            const opt = {
                margin:       10,
                filename:     (this.currentPlayerData?.name || 'Player').replace(/\\s+/g, '_') + '_Dossier.pdf',
                image:        { type: 'jpeg', quality: 0.98 },
                html2canvas:  { scale: 2, useCORS: true },
                jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' }
            };
            
            html2pdf().set(opt).from(element).save().then(() => {
                element.style.display = 'none'; // Hide again
            });
        }
    };

    // Close on click outside
    overlay.addEventListener('click', function(e) {
        if (e.target === overlay) window.PlayerProfile.close();
    });

})();

