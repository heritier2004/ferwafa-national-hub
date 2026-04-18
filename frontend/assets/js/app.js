/**
 * CORGRI SYSTEM INTELLIGENCE 2.0 - CORE ENGINE
 * Professional Unified Framework
 */

function checkAuth() {
    const token = localStorage.getItem('access_token');
    if (!token && !window.location.pathname.includes('login.html') && !window.location.pathname.includes('index.html')) {
        window.location.href = '../login.html';
    }
}

function logout() {
    localStorage.clear();
    const loginPath = window.location.pathname.includes('pages/') ? '../login.html' : 'login.html';
    window.location.href = loginPath;
}

function goHome() {
    const role = localStorage.getItem('role');
    const REDIRECT_MAP = {
        'SUPER_ADMIN': 'admin.html',
        'FERWAFA': 'ferwafa_dashboard.html',
        'CLUB': 'club_dashboard.html'
    };
    window.location.href = REDIRECT_MAP[role] || 'dashboard.html';
}

function roleGuard() {
    const role = localStorage.getItem('role');
    const path = window.location.pathname;

    const PROTECTION_MAP = {
        'admin.html': 'SUPER_ADMIN',
        'ferwafa_dashboard.html': 'FERWAFA',
        'club_dashboard.html': 'CLUB',
        'school_dashboard.html': 'SCHOOL',
        'academy_dashboard.html': 'ACADEMY'
    };

    const fileName = path.split('/').pop();
    if (PROTECTION_MAP[fileName] && role !== PROTECTION_MAP[fileName]) {
        goHome();
    }
}

// 🗺️ Unified Sidebar Configuration
const SYSTEM_ARCHITECTURE = {
    'SUPER_ADMIN': [
        { name: 'System Overview', id: 'overview', icon: `<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2-2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline>` },
        { name: 'User Management', id: 'onboarding', icon: `<path d="M12 2L2 7l10 5 10-5-10-5z"></path><path d="M2 17l10 5 10-5"></path><path d="M2 12l10 5 10-5"></path>` },
        { name: 'Incident Logs', id: 'errors', icon: `<circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line>` },
        { name: 'Activity History', id: 'logs', icon: `<polyline points="4 17 10 11 4 5"></polyline><line x1="12" y1="19" x2="20" y2="19"></line>` }
    ],
    'FERWAFA': [
        { name: 'Command Board', id: 'overview', icon: `<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2-2H5a2 2 0 0 1-2-2z"></path>` },
        { name: 'National Ledger', id: 'ledger', icon: `<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path>` },
        { name: 'Season Control', id: 'fixtures', icon: `<rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line>` },
        { name: 'Talent Intelligence', id: 'talent', icon: `<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>` },
        { name: 'The Archive Vault', id: 'vault', icon: `<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>` }
    ],
    'CLUB': [
        { name: 'Performance Hub', id: 'overview', icon: `<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>` },
        { name: 'Match Schedules', id: 'fixtures', icon: `<rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line>` },
        { name: 'Player Scouting', id: 'scouting', icon: `<circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line>` }
    ]
};

function initApp() {
    checkAuth();
    roleGuard();
    const role = localStorage.getItem('role') || 'SUPER_ADMIN';
    const sidebarNav = document.getElementById('main-nav');
    
    if (sidebarNav) {
        const config = SYSTEM_ARCHITECTURE[role] || SYSTEM_ARCHITECTURE['CLUB'];
        sidebarNav.innerHTML = config.map((item, index) => `
            <div class="nav-item ${index === 0 ? 'active' : ''}" onclick="switchTab('${item.id}')" data-id="${item.id}">
                <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round">
                    ${item.icon}
                </svg>
                <span>${item.name}</span>
            </div>
        `).join('');
    }

    // Apply User Branding (Photo/Logo)
    const brandingContainers = document.querySelectorAll('.ui-branding-target');
    let userLogo = localStorage.getItem('logo_url');
    
    // 🛡️ Official National Seal Fallback for FERWAFA
    if (!userLogo && role === 'FERWAFA') {
        userLogo = "https://upload.wikimedia.org/wikipedia/en/thumb/7/75/Rwanda_FA.svg/1200px-Rwanda_FA.svg.png";
    }

    if (userLogo && brandingContainers.length > 0) {
        brandingContainers.forEach(container => {
            container.innerHTML = `<img src="${userLogo}" style="width:100%; height:100%; object-fit:cover; border-radius:inherit;">`;
            container.style.overflow = 'hidden';
            container.style.background = 'transparent';
        });
    }

    const roleBadge = document.getElementById('role-badge');
    if (roleBadge) roleBadge.textContent = role.replace('_', ' ');
}

function switchTab(tabId) {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.getAttribute('data-id') === tabId) item.classList.add('active');
    });

    const allPanes = document.querySelectorAll('.tab-pane');
    allPanes.forEach(pane => {
        if (pane.id === tabId) {
            pane.style.display = 'block';
            setTimeout(() => { pane.classList.add('active'); }, 50);
        } else {
            pane.classList.remove('active');
            pane.style.display = 'none';
        }
    });
}

// ⚙️ Global Infrastructure Synchronization
async function syncGlobalInfrastructure() {
    try {
        const res = await fetch('/api/admin/system/settings');
        const settings = await res.json();
        
        settings.forEach(s => {
            if (s.key === 'footer_text') {
                document.querySelectorAll('.app-footer').forEach(f => f.innerHTML = s.value);
            }
            if (s.key === 'system_name') {
                document.querySelectorAll('.global-sys-name').forEach(t => t.textContent = s.value);
            }
            // Check Maintenance Mode
            if (s.key === 'maintenance_mode' && s.value.toLowerCase() === 'true') {
                const role = localStorage.getItem('role');
                if (role !== 'SUPER_ADMIN' && !window.location.pathname.includes('login.html')) {
                    document.body.innerHTML = `
                        <div style="height:100vh; display:flex; flex-direction:column; align-items:center; justify-content:center; background:#05070a; color:#fff; font-family:sans-serif; text-align:center; padding:2rem;">
                            <div style="font-size:4rem; margin-bottom:1rem;">🛠️</div>
                            <h1 style="color:#6366f1;">NATIONAL MAINTENANCE PROTOCOL</h1>
                            <p style="color:#aaa; max-width:500px;">The infrastructure is currently undergoing technical upgrades. <br>Access is restricted to Authorized Administrators only.</p>
                            <button onclick="window.location.href='login.html'" style="margin-top:2rem; background:#6366f1; border:none; color:white; padding:12px 24px; border-radius:8px; cursor:pointer;">ADMIN LOGIN</button>
                        </div>
                    `;
                }
            }
        });
    } catch(e) {}
}

// Global Initialization
document.addEventListener('DOMContentLoaded', () => {
    initApp();
    syncGlobalInfrastructure();
});
