/**
 * Authentication Helper for RFID Attendance System
 * Handles Login State, Admin Guards, and Auto-Logout.
 *
 * SECURITY:
 * - Tokens are HttpOnly Cookies managed by the browser.
 * - No access_token in localStorage (XSS Protection).
 * - Admin pages verify role via server-side /auth/me call.
 * - Page content is hidden until auth is verified (no flash).
 */

// Resolve API base once — works with Nginx proxy, direct uvicorn, or file://
const _AUTH_API_BASE = (function () {
    if (typeof window !== 'undefined' && window.location && window.location.protocol !== 'file:') {
        return window.location.origin;
    }
    return 'http://127.0.0.1:8000';
})();

const AUTH = {
    LOGGED_IN_KEY: 'is_logged_in',
    USER_ROLE_KEY: 'user_role',
    API_BASE: _AUTH_API_BASE,

    /** UI-state check (fast, client-only) */
    isLoggedIn() {
        return !!localStorage.getItem(this.LOGGED_IN_KEY);
    },

    /** Get cached role */
    getRole() {
        return localStorage.getItem(this.USER_ROLE_KEY) || '';
    },

    /** Save UI state after successful login */
    login(profile) {
        localStorage.setItem(this.LOGGED_IN_KEY, 'true');
        if (profile && profile.role) {
            localStorage.setItem(this.USER_ROLE_KEY, profile.role);
        }
    },

    /** Clear state and call logout endpoint to clear cookies */
    async logout(redirectUrl = 'index.html') {
        try {
            await fetch(`${this.API_BASE}/api/v1/auth/logout`, {
                method: 'POST',
                credentials: 'include'
            });
        } catch (e) {
            console.error('Logout failed', e);
        }
        localStorage.clear();
        sessionStorage.clear();
        window.location.href = redirectUrl;
    },

    /** Inactivity timeout for admin pages (15 minutes) */
    initInactivityTimeout(minutes = 15) {
        let timer;
        const reset = () => {
            clearTimeout(timer);
            timer = setTimeout(() => {
                alert('Session expired due to inactivity.');
                this.logout();
            }, minutes * 60 * 1000);
        };
        ['load', 'mousemove', 'keypress', 'click', 'scroll', 'touchstart'].forEach(evt => {
            document.addEventListener(evt, reset, { passive: true });
        });
        reset(); // Start the timer
    },

    /** Fetch wrapper that auto-redirects on 401 */
    async fetch(url, options = {}) {
        if (!options.headers) options.headers = {};
        if (!options.headers['Content-Type'] && !(options.body instanceof FormData)) {
            options.headers['Content-Type'] = 'application/json';
        }
        options.credentials = 'include';  // Always send cookies
        const response = await fetch(url, options);
        if (response.status === 401) {
            console.warn('401 Unauthorized — redirecting to login');
            localStorage.removeItem(this.LOGGED_IN_KEY);
            localStorage.removeItem(this.USER_ROLE_KEY);
            const redirect = encodeURIComponent(window.location.href);
            window.location.href = `login.html?redirect=${redirect}`;
            return response;
        }
        return response;
    },

    /**
     * SERVER-SIDE auth guard for protected pages.
     * Calls /auth/me to verify the cookie is valid.
     * If it fails, redirects to login.html.
     * Returns the user profile on success.
     */
    async requireAuth() {
        // Quick client-side pre-check (avoids network call for obviously unauthenticated users)
        if (!this.isLoggedIn()) {
            const redirect = encodeURIComponent(window.location.href);
            window.location.href = `login.html?redirect=${redirect}`;
            return null;
        }
        try {
            const res = await fetch(`${this.API_BASE}/api/v1/auth/me`, {
                credentials: 'include'
            });
            if (!res.ok) throw new Error('Not authenticated');
            const user = await res.json();
            // Update cached state
            localStorage.setItem(this.LOGGED_IN_KEY, 'true');
            if (user.role) localStorage.setItem(this.USER_ROLE_KEY, user.role);
            return user;
        } catch (e) {
            localStorage.removeItem(this.LOGGED_IN_KEY);
            localStorage.removeItem(this.USER_ROLE_KEY);
            const redirect = encodeURIComponent(window.location.href);
            window.location.href = `login.html?redirect=${redirect}`;
            return null;
        }
    },

    /**
     * SERVER-SIDE admin guard for admin pages.
     * Calls /auth/me, checks role === 'admin'.
     * Hides page content until verified.
     * Redirects to login.html if not authenticated,
     * or to index.html if authenticated but not admin.
     * Returns the user profile on success.
     */
    async requireAdmin() {
        // Immediately hide page content to prevent flash
        document.documentElement.style.visibility = 'hidden';

        // Quick client-side pre-check
        if (!this.isLoggedIn()) {
            window.location.href = 'login.html';
            return null;
        }
        try {
            const res = await fetch(`${this.API_BASE}/api/v1/auth/me`, {
                credentials: 'include'
            });
            if (!res.ok) throw new Error('Not authenticated');
            const user = await res.json();
            localStorage.setItem(this.LOGGED_IN_KEY, 'true');
            if (user.role) localStorage.setItem(this.USER_ROLE_KEY, user.role);
            if (user.role !== 'admin') {
                // Authenticated but not admin — send back to kiosk
                alert('Access Denied: Admin privileges required.');
                window.location.href = 'index.html';
                return null;
            }
            // Auth succeeded — reveal the page
            document.documentElement.style.visibility = 'visible';
            return user;
        } catch (e) {
            localStorage.removeItem(this.LOGGED_IN_KEY);
            localStorage.removeItem(this.USER_ROLE_KEY);
            window.location.href = 'login.html';
            return null;
        }
    },

    /** Check if current user is admin (client-side cache, fast) */
    isAdmin() {
        return this.getRole() === 'admin';
    }
};

window.AUTH = AUTH;
