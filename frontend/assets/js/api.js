// Centralized API Service Architecture
// This globally overrides fetch to enforce auth headers and handle 401s
(function() {
    const originalFetch = window.fetch;

    window.fetch = async function(url, options = {}) {
        const token = localStorage.getItem('access_token');
        const headers = {
            ...options.headers,
        };
        
        // Add Authorization if token exists and not explicitly excluded
        if (token && !url.includes('login') && !url.includes('register')) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const config = {
            ...options,
            headers
        };

        try {
            const response = await originalFetch(url, config);

            // Global 401 Unauthorized handling
            if (response.status === 401 && !url.includes('login')) {
                console.warn("Unauthorized API access detected. Terminating session.");
                localStorage.clear();
                window.location.href = '/login.html';
            }

            return response;
        } catch (error) {
            console.error(`Global API Error on ${url}:`, error);
            throw error;
        }
    };
})();

// 🛡️ FRONTEND SAFETY LAYER: Global Image Error Handler (Injected via API module to ensure dashboard coverage)
window.addEventListener('error', function(e) {
    const target = e.target;
    if (target && target.tagName && target.tagName.toLowerCase() === 'img') {
        if (target.dataset.fallbackApplied) return; // Prevent infinite loop
        
        target.dataset.fallbackApplied = "true";
        target.style.objectFit = "contain"; 
        target.style.background = "#1E293B"; 
        target.style.padding = "10px";
        target.style.border = "1px solid rgba(255,255,255,0.05)";
        target.style.borderRadius = "inherit"; 
        
        const isPlayer = target.id.includes('player') || target.className.includes('player') || target.src.includes('player');
        const isAcademy = target.id.includes('academy') || target.className.includes('academy') || target.src.includes('academy');
        const isSchool = target.id.includes('school') || target.className.includes('school') || target.src.includes('school');
        const isClub = target.id.includes('club') || target.className.includes('club') || target.src.includes('club');
        
        if (isPlayer) {
            target.src = 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAiIGhlaWdodD0iMTAwIiB2aWV3Qm94PSIwIDAgMjQgMjQiIGZpbGw9Im5vbmUiIHN0cm9rZT0iIzk0QTNCOCIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxwYXRoIGQ9Ik0yMCAyMXYtMmE0IDQgMCAwIDAtNC00SDhhNCA0IDAgMCAwLTQgNHYyIj48L3BhdGg+PGNpcmNsZSBjeD0iMTIiIGN5PSI3IiByPSI0Ij48L2NpcmNsZT48L3N2Zz4=';
        } else if (isAcademy) {
            target.src = 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAiIGhlaWdodD0iMTAwIiB2aWV3Qm94PSIwIDAgMjQgMjQiIGZpbGw9Im5vbmUiIHN0cm9rZT0iIzk0QTNCOCIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxwYXRoIGQ9Ik0xMiAyTDIgN2wxMCA1IDEwLTUtMTAtNXoiPjwvcGF0aD48cGF0aCBkPSJNMjAxN2wxMCA1IDEwLTUiPjwvcGF0aD48cGF0aCBkPSJNMjAxMmwxMCA1IDEwLTUiPjwvcGF0aD48L3N2Zz4=';
        } else if (isSchool) {
            target.src = 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAiIGhlaWdodD0iMTAwIiB2aWV3Qm94PSIwIDAgMjQgMjQiIGZpbGw9Im5vbmUiIHN0cm9rZT0iIzk0QTNCOCIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxwYXRoIGQ9Ik00IDE5LjVBMi41IDIuNSAwIDAgMSA2LjUgMTdIMjAiPjwvcGF0aD48cGF0aCBkPSJNNi41IDJIMjB2MjBINi41QTIuNSAyLjUgMCAwIDEgNCAxOS41di0xNUEyLjUgMi41IDAgMCAxIDYuNSAyeiI+PC9wYXRoPjwvc3ZnPg==';
        } else {
            target.src = 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAiIGhlaWdodD0iMTAwIiB2aWV3Qm94PSIwIDAgMjQgMjQiIGZpbGw9Im5vbmUiIHN0cm9rZT0iIzk0QTNCOCIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxwYXRoIGQ9Ik0xMiAyMnM4LTQgOC0xMFY1bC04LTMtOCAzdjdjMCA2IDggMTAgOCAxMHoiPjwvcGF0aD48L3N2Zz4=';
        }
    }
}, true);
