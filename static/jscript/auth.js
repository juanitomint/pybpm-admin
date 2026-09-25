/**
 * Auth check — validates JWT token by calling /api/v1/auth/me endpoint.
 * Redirects to /login if token is expired or invalid.
 */
async function checkAuth() {
    try {
        const response = await fetch(globals.apiUrl + '/api/v1/auth/me', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('bpm_token')}`
            }
        });

        if (response.ok) {
            const user = await response.json();
            // Token valid — set globals.user for client-side use
            window.globals.user = user;
            console.log('Authenticated:', user);
            return true;
        } else {
            // Token expired or invalid — remove it so we don't keep retrying
            console.warn('Auth check failed:', response.status);
            localStorage.removeItem('bpm_token');
            if (window.location.pathname !== '/login') {
                var current = window.location.pathname + window.location.search + window.location.hash;
                window.location.href = '/login?redirect=' + encodeURIComponent(current);
            }
            return false;
        }
    } catch (error) {
        console.error('Auth check error:', error);
        localStorage.removeItem('bpm_token');
        if (window.location.pathname !== '/login') {
            var current = window.location.pathname + window.location.search + window.location.hash;
            window.location.href = '/login?redirect=' + encodeURIComponent(current);
        }
        return false;
    }
}

// Run on DOM ready — checks auth before any UI components load
document.addEventListener('DOMContentLoaded', function() {
    // Defer slightly to ensure globals are fully set
    setTimeout(checkAuth, 0);
});
