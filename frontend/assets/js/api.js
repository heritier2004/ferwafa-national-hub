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
