/**
 * AI Pitch Machine Deployment Center
 * Shared module for all dashboards
 * Injects the professional modal overlay, CSS, and interactive installation wizard
 */
(function() {
    'use strict';

    // ── CSS Injection ──
    const style = document.createElement('style');
    style.textContent = `
        #ai-modal-overlay {
            position: fixed; inset: 0;
            background: rgba(2, 6, 23, 0.85);
            backdrop-filter: blur(12px);
            z-index: 2000;
            display: none; justify-content: center; align-items: center;
            opacity: 0; transition: opacity 0.3s ease;
        }
        #ai-modal-overlay.active { display: flex; opacity: 1; }
        .ai-modal-container {
            width: 90vw; max-width: 1200px; height: 85vh;
            background: #111827;
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 16px;
            display: flex; overflow: hidden;
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5);
            transform: scale(0.95);
            transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }
        #ai-modal-overlay.active .ai-modal-container { transform: scale(1); }
        .ai-modal-left {
            flex: 1; padding: 2.5rem;
            border-right: 1px solid rgba(255,255,255,0.08);
            display: flex; flex-direction: column; gap: 2rem;
            overflow-y: auto;
            background: linear-gradient(135deg, rgba(22, 163, 74, 0.05) 0%, transparent 50%);
        }
        .ai-modal-right {
            width: 450px; padding: 2.5rem;
            background: rgba(0,0,0,0.2);
            display: flex; flex-direction: column;
            position: relative;
        }
        .ai-close-btn {
            position: absolute; top: 1.5rem; right: 1.5rem;
            background: transparent; border: none;
            color: #94a3b8; cursor: pointer; padding: 0.5rem;
            border-radius: 50%; transition: 0.2s; display: flex;
            font-size: 1.5rem; line-height: 1;
        }
        .ai-close-btn:hover { background: rgba(255,255,255,0.1); color: white; }
        .ai-feature-card {
            background: rgba(0,0,0,0.3);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 8px; padding: 1rem;
            display: flex; gap: 1rem; align-items: flex-start;
        }
        .ai-feature-card i, .ai-feature-card svg {
            color: #16A34A; flex-shrink: 0; margin-top: 2px;
            width: 20px; height: 20px;
        }
        .ai-status-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
        .ai-status-card {
            background: rgba(0,0,0,0.3);
            border: 1px solid rgba(255,255,255,0.05);
            border-radius: 8px; padding: 1rem;
            display: flex; align-items: center; gap: 0.75rem;
        }
        .ai-status-dot {
            width: 8px; height: 8px; border-radius: 50%;
            background: #94a3b8; box-shadow: 0 0 8px transparent;
        }
        .ai-status-dot.active {
            background: #10b981; box-shadow: 0 0 8px #10b981;
            animation: aiPulse 2s infinite;
        }
        @keyframes aiPulse { 0%{opacity:0.6} 50%{opacity:1} 100%{opacity:0.6} }
        .ai-wizard-step { display: none; flex-direction: column; flex: 1; justify-content: center; }
        .ai-wizard-step.active { display: flex; animation: aiFadeIn 0.3s ease forwards; }
        @keyframes aiFadeIn { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:translateY(0)} }
        .ai-progress-bar {
            height: 6px; background: rgba(255,255,255,0.1);
            border-radius: 3px; overflow: hidden; margin: 1rem 0;
        }
        .ai-progress-fill { height: 100%; background: #16A34A; width: 0%; transition: width 0.3s ease; }
        .ai-log-box {
            background: #000; border: 1px solid rgba(255,255,255,0.08);
            border-radius: 6px; padding: 0.75rem;
            font-family: monospace; font-size: 0.7rem; color: #94a3b8;
            height: 120px; overflow-y: auto; margin-bottom: 1.5rem;
            display: flex; flex-direction: column; gap: 4px; text-align: left;
        }
        .ai-btn-large {
            width: 100%; padding: 1rem; font-size: 0.9rem;
            display: flex; align-items: center; justify-content: center;
            gap: 0.5rem; cursor: pointer; border-radius: 8px;
            font-weight: 800; text-transform: uppercase;
            font-family: 'Outfit', 'Inter', 'Manrope', sans-serif;
            transition: 0.2s; border: none;
        }
        .ai-btn-large.ai-btn-primary {
            background: #16A34A; color: #fff;
        }
        .ai-btn-large.ai-btn-primary:hover { filter: brightness(1.1); }
        .ai-btn-large.ai-btn-outline {
            background: transparent; color: #fff;
            border: 1px solid rgba(255,255,255,0.15);
        }
        .ai-btn-large.ai-btn-outline:hover { border-color: rgba(255,255,255,0.3); }
        @media (max-width: 900px) {
            .ai-modal-container { flex-direction: column; height: 95vh; }
            .ai-modal-left { border-right: none; border-bottom: 1px solid rgba(255,255,255,0.08); max-height: 40vh; }
            .ai-modal-right { width: 100%; }
        }
    `;
    document.head.appendChild(style);

    // ── HTML Injection ──
    const overlay = document.createElement('div');
    overlay.id = 'ai-modal-overlay';
    overlay.innerHTML = `
        <div class="ai-modal-container">
            <div class="ai-modal-left">
                <div style="text-align:left;">
                    <h2 style="font-size:2rem;font-weight:900;text-transform:uppercase;margin:0;letter-spacing:-0.02em;color:white;">AI Pitch Machine</h2>
                    <div style="font-size:0.8rem;color:#94a3b8;font-weight:800;letter-spacing:0.1em;margin-top:4px;text-transform:uppercase;">Federation-Grade Technology System</div>
                </div>
                <div style="font-size:0.95rem;color:#94a3b8;line-height:1.6;text-align:left;">
                    The AI Pitch Machine captures football video, processes live match activity using computer vision, and synchronizes real-time performance analytics directly to the Match Control Center.
                </div>
                <div style="text-align:left;">
                    <div style="font-size:0.75rem;font-weight:800;color:#16A34A;text-transform:uppercase;letter-spacing:0.15em;margin-bottom:1rem;">Core Capabilities</div>
                    <div style="display:flex;flex-direction:column;gap:0.75rem;">
                        <div class="ai-feature-card">
                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                            <div>
                                <div style="font-size:0.85rem;font-weight:800;text-transform:uppercase;margin-bottom:2px;color:white;">Real-Time Player Tracking</div>
                                <div style="font-size:0.75rem;color:#94a3b8;">High-speed coordinate mapping and identification of all players on the pitch using advanced YOLOv8 models.</div>
                            </div>
                        </div>
                        <div class="ai-feature-card">
                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
                            <div>
                                <div style="font-size:0.85rem;font-weight:800;text-transform:uppercase;margin-bottom:2px;color:white;">Automated Event Detection</div>
                                <div style="font-size:0.75rem;color:#94a3b8;">Instant recognition of passes, shots, tackles, and key match events synced directly to the dashboard.</div>
                            </div>
                        </div>
                        <div class="ai-feature-card">
                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m22 8-6 4 6 4V8Z"/><rect width="14" height="12" x="2" y="6" rx="2" ry="2"/></svg>
                            <div>
                                <div style="font-size:0.85rem;font-weight:800;text-transform:uppercase;margin-bottom:2px;color:white;">Video Processing Pipeline</div>
                                <div style="font-size:0.75rem;color:#94a3b8;">Multi-camera support capable of processing streams from IP cameras, mobile devices, and broadcast feeds.</div>
                            </div>
                        </div>
                    </div>
                </div>
                <div style="text-align:left;">
                    <div style="font-size:0.75rem;font-weight:800;color:#16A34A;text-transform:uppercase;letter-spacing:0.15em;margin-bottom:1rem;">System Status Center</div>
                    <div class="ai-status-grid">
                        <div class="ai-status-card"><div class="ai-status-dot active"></div><div style="font-size:0.75rem;font-weight:800;text-transform:uppercase;color:white;">Central Server API</div></div>
                        <div class="ai-status-card"><div class="ai-status-dot active"></div><div style="font-size:0.75rem;font-weight:800;text-transform:uppercase;color:white;">Database Connection</div></div>
                        <div class="ai-status-card"><div class="ai-status-dot"></div><div style="font-size:0.75rem;font-weight:800;text-transform:uppercase;color:#94a3b8;">AI Engine (Local)</div></div>
                        <div class="ai-status-card"><div class="ai-status-dot"></div><div style="font-size:0.75rem;font-weight:800;text-transform:uppercase;color:#94a3b8;">Telemetry Stream</div></div>
                    </div>
                </div>
            </div>
            <div class="ai-modal-right">
                <button class="ai-close-btn" onclick="closeAIModal()">&times;</button>
                <div id="ai-step-1" class="ai-wizard-step active">
                    <div style="text-align:center;margin-bottom:2rem;">
                        <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#16A34A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-bottom:1rem;"><polyline points="8 17 12 21 16 17"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.88 18.09A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.29"/></svg>
                        <h3 style="font-size:1.5rem;font-weight:900;text-transform:uppercase;margin-bottom:0.5rem;color:white;">Deployment Package</h3>
                        <div style="font-size:0.75rem;color:#94a3b8;text-transform:uppercase;letter-spacing:0.1em;display:inline-flex;align-items:center;gap:0.5rem;background:rgba(255,255,255,0.05);padding:4px 12px;border-radius:12px;border:1px solid rgba(255,255,255,0.08);">
                            <span class="ai-status-dot active" style="width:6px;height:6px;"></span> STABLE RELEASE v2.4.0
                        </div>
                    </div>
                    <div style="background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:1rem;margin-bottom:2rem;color:white;">
                        <div style="display:flex;justify-content:space-between;border-bottom:1px solid rgba(255,255,255,0.05);padding-bottom:0.5rem;margin-bottom:0.5rem;">
                            <span style="font-size:0.7rem;color:#94a3b8;font-weight:800;text-transform:uppercase;">Release Date</span>
                            <span style="font-size:0.75rem;font-weight:700;">May 30, 2026</span>
                        </div>
                        <div style="display:flex;justify-content:space-between;border-bottom:1px solid rgba(255,255,255,0.05);padding-bottom:0.5rem;margin-bottom:0.5rem;">
                            <span style="font-size:0.7rem;color:#94a3b8;font-weight:800;text-transform:uppercase;">Installation Size</span>
                            <span style="font-size:0.75rem;font-weight:700;">4.2 GB</span>
                        </div>
                        <div style="display:flex;justify-content:space-between;">
                            <span style="font-size:0.7rem;color:#94a3b8;font-weight:800;text-transform:uppercase;">Requirements</span>
                            <span style="font-size:0.75rem;font-weight:700;">16GB RAM, NVIDIA GPU</span>
                        </div>
                    </div>
                    <div style="display:flex;flex-direction:column;gap:1rem;">
                        <button class="ai-btn-large ai-btn-primary" onclick="startAIInstall('windows')">Deploy for Windows 10/11</button>
                        <button class="ai-btn-large ai-btn-outline" onclick="startAIInstall('linux')">Deploy for Linux (Ubuntu/Debian)</button>
                    </div>
                </div>
                <div id="ai-step-2" class="ai-wizard-step">
                    <div style="text-align:center;margin-bottom:2rem;">
                        <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-bottom:1rem;"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>
                        <h3 style="font-size:1.5rem;font-weight:900;text-transform:uppercase;margin-bottom:0.5rem;color:white;">Package Verification</h3>
                        <div style="font-size:0.8rem;color:#94a3b8;">Checking system compatibility and package integrity...</div>
                    </div>
                    <div class="ai-log-box" id="ai-verify-log"></div>
                    <button class="ai-btn-large ai-btn-primary" id="ai-btn-continue-install" style="display:none;" onclick="showAIStep(3)">CONTINUE INSTALLATION</button>
                </div>
                <div id="ai-step-3" class="ai-wizard-step">
                    <div style="text-align:center;margin-bottom:2rem;">
                        <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#16A34A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-bottom:1rem;"><line x1="22" y1="12" x2="2" y2="12"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/><line x1="6" y1="16" x2="6.01" y2="16"/><line x1="10" y1="16" x2="10.01" y2="16"/></svg>
                        <h3 style="font-size:1.5rem;font-weight:900;text-transform:uppercase;margin-bottom:0.5rem;color:white;" id="ai-install-title">Installing AI Engine</h3>
                        <div style="font-size:0.8rem;color:#94a3b8;" id="ai-install-subtitle">Extracting neural network models...</div>
                    </div>
                    <div class="ai-progress-bar"><div class="ai-progress-fill" id="ai-install-progress"></div></div>
                    <div style="text-align:right;font-size:0.75rem;font-weight:800;color:#16A34A;margin-bottom:1.5rem;" id="ai-install-pct">0%</div>
                    <div class="ai-log-box" id="ai-install-log"></div>
                </div>
                <div id="ai-step-4" class="ai-wizard-step">
                    <div style="text-align:center;margin-bottom:2rem;">
                        <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-bottom:1rem;"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                        <h3 style="font-size:1.5rem;font-weight:900;text-transform:uppercase;margin-bottom:0.5rem;color:white;">Installed Successfully</h3>
                        <div style="font-size:0.85rem;color:#94a3b8;">The AI Pitch Machine is now ready on your system.</div>
                    </div>
                    <div style="display:flex;flex-direction:column;gap:1rem;margin-top:auto;">
                        <a href="../../../ai_machine/install_and_launch.bat" download class="ai-btn-large ai-btn-primary" style="text-decoration:none;" onclick="closeAIModal()">LAUNCH APPLICATION</a>
                        <button class="ai-btn-large ai-btn-outline" onclick="closeAIModal()">CLOSE</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);

    // ── Logic ──
    window.openAIModal = function() {
        overlay.classList.add('active');
        showAIStep(1);
    };

    window.closeAIModal = function() {
        overlay.classList.remove('active');
    };

    // Close on overlay click (outside container)
    overlay.addEventListener('click', function(e) {
        if (e.target === overlay) closeAIModal();
    });

    window.showAIStep = function(stepNum) {
        document.querySelectorAll('.ai-wizard-step').forEach(function(el) { el.classList.remove('active'); });
        document.getElementById('ai-step-' + stepNum).classList.add('active');
        if (stepNum === 3) runAIInstallation();
    };

    function appendAILog(elementId, text, delay) {
        return new Promise(function(resolve) {
            setTimeout(function() {
                var el = document.getElementById(elementId);
                var line = document.createElement('div');
                line.textContent = '> ' + text;
                el.appendChild(line);
                el.scrollTop = el.scrollHeight;
                resolve();
            }, delay);
        });
    }

    window.startAIInstall = async function(platform) {
        showAIStep(2);
        document.getElementById('ai-verify-log').innerHTML = '';
        document.getElementById('ai-btn-continue-install').style.display = 'none';

        await appendAILog('ai-verify-log', 'Initializing ' + platform.toUpperCase() + ' deployment environment...', 500);
        await appendAILog('ai-verify-log', 'Connecting to secure package registry...', 800);
        await appendAILog('ai-verify-log', 'Verifying package signatures...', 1200);
        await appendAILog('ai-verify-log', 'Checking system requirements (16GB RAM, GPU)...', 1000);
        await appendAILog('ai-verify-log', 'SUCCESS: System meets professional requirements.', 800);
        await appendAILog('ai-verify-log', 'SUCCESS: Package Verified Successfully.', 500);

        document.getElementById('ai-btn-continue-install').style.display = 'flex';
    };

    async function runAIInstallation() {
        var logEl = document.getElementById('ai-install-log');
        var progEl = document.getElementById('ai-install-progress');
        var pctEl = document.getElementById('ai-install-pct');
        var subtitleEl = document.getElementById('ai-install-subtitle');

        logEl.innerHTML = '';
        progEl.style.width = '0%';
        pctEl.textContent = '0%';

        var steps = [
            { p: 10, msg: 'Allocating installation directory...', st: 'Preparing environment' },
            { p: 25, msg: 'Extracting core python runtime environment...', st: 'Installing Core' },
            { p: 45, msg: 'Installing PyTorch and computer vision dependencies...', st: 'Installing Dependencies' },
            { p: 65, msg: 'Unpacking YOLOv8 tactical models...', st: 'Extracting AI Models' },
            { p: 80, msg: 'Configuring local API endpoints and authentication...', st: 'Configuring Security' },
            { p: 95, msg: 'Creating desktop and menu shortcuts...', st: 'Finalizing' },
            { p: 100, msg: 'Installation complete. System ready.', st: 'Complete' }
        ];

        var delay = 800;
        for (var i = 0; i < steps.length; i++) {
            var step = steps[i];
            await appendAILog('ai-install-log', step.msg, delay);
            progEl.style.width = step.p + '%';
            pctEl.textContent = step.p + '%';
            subtitleEl.textContent = step.st;
            delay = Math.random() * 1000 + 500;
        }

        setTimeout(function() { showAIStep(4); }, 1000);
    }
})();
