
/**
 * Professional Kiosk Logic
 * Handles RFID scanning, UI states, and API communication.
 * Refactored to use AUTH helper and /api/v1 endpoints.
 */

const API_BASE = window.location.origin && window.location.protocol !== 'file:'
    ? window.location.origin
    : 'http://127.0.0.1:8000';

class ProfessionalKiosk {
    constructor() {
        this.config = {
            apiBase: API_BASE,
            apiUrl: '/api/v1/employees/scan',
            resetDelay: 3000,
            debounceTime: 1200
        };

        // mode controls
        this.currentMode = 'attendance';
        this.breakState = 'start';

        this.state = { isProcessing: false, lastScan: 0, scanBuffer: '', lastLocalInputTime: 0, lastProcessed: {} };

        this.dom = {
            body: document.body,
            input: document.getElementById('rfidInput'),
            clock: document.getElementById('clock'),
            date: document.getElementById('date'),
            feed: document.getElementById('feedList'),
            title: document.getElementById('scanTitle'),
            sub: document.getElementById('scanSubtitle'),
            icon: document.getElementById('scanIcon'),
            visualizer: document.getElementById('visualizer')
        };

        this.init();
    }

    init() {
        // Prevent browser from restoring previous scroll position on reload
        if ('scrollRestoration' in history) history.scrollRestoration = 'manual';

        this.updateTime();
        setInterval(() => this.updateTime(), 1000);

        // Focus Trap and initial load
        document.addEventListener('click', () => this.safeFocus());
        if (this.dom.input) this.dom.input.addEventListener('blur', () => setTimeout(() => this.safeFocus(), 50));

        // Input Handler
        if (this.dom.input) {
            this.dom.input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    const uid = this.dom.input.value.trim();
                    this.dom.input.value = '';
                    this.state.lastLocalInputTime = Date.now();
                    this.state.scanBuffer = '';
                    if (uid) this.processScan(uid, 'input');
                }
            });
        }

        // Global key buffer for hardware scanners
        document.addEventListener('keydown', this.handleGlobalKeydown.bind(this));

        // Initial data load
        this.loadToday();

        this.safeFocus();
    }

    handleGlobalKeydown(e) {
        // Ignore if focus is on an input (like debug tools)
        if (e.target.tagName === 'INPUT' && e.target !== this.dom.input) return;

        const now = Date.now();
        // If regular typing recently occurred, assume manual entry
        if (now - this.state.lastLocalInputTime < 500) return;

        if (e.key === 'Enter') {
            if (this.state.scanBuffer.length > 2) {
                const uid = this.state.scanBuffer;
                this.processScan(uid, 'scanner');
            }
            this.state.scanBuffer = '';
        } else if (e.key.length === 1) {
            this.state.scanBuffer += e.key;
            // Clear buffer if too long or timeout
            if (this.state.scanBuffer.length > 64) this.state.scanBuffer = '';
            if (!this._bufferTimeout) {
                this._bufferTimeout = setTimeout(() => {
                    this.state.scanBuffer = '';
                    this._bufferTimeout = null;
                }, 200);
            }
        }
    }

    async processScan(uid, source) {
        if (this.state.isProcessing) return;

        // Dedup: ignore same UID within debounceTime
        const now = Date.now();
        if (this.state.lastProcessed[uid] && (now - this.state.lastProcessed[uid] < this.config.debounceTime)) {
            return; // ignore
        }

        this.state.isProcessing = true;
        this.emitDebug(`Processing scan: ${uid} via ${source}`);

        // Visual State: Processing
        this.setVisuals('state-processing', 'Processing...', 'Verifying credentials');
        this.dom.body.classList.add('processing');

        try {
            const payload = { uid: uid };
            const response = await fetch(this.config.apiBase + this.config.apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Access Denied');
            }

            this.state.lastProcessed[uid] = Date.now();
            this.handleSuccess(data);

        } catch (error) {
            this.handleError(error);
        }
    }

    handleSuccess(data) {
        this.emitDebug(`Success: ${data.event} for ${data.name}`);

        const eventLabel = data.event.replace('_', ' ');
        this.setVisuals('state-success', `Welcome, ${data.name}`, `Recorded: ${eventLabel}`);

        this.dom.body.classList.remove('processing');
        this.dom.body.classList.add('state-success'); // Using 'state-success' to match CSS selector .state-success

        // Add to feed
        this.addFeedItem({
            name: data.name,
            event: data.event,
            time: new Date().toISOString(),
            uid: data.uid,
            status: 'success'
        }, true);

        this.resetUI();
    }

    handleError(error) {
        this.emitDebug(`Error: ${error.message}`);
        this.setVisuals('state-error', 'Access Denied', error.message || 'Unknown credential');

        this.dom.body.classList.remove('processing');
        this.dom.body.classList.add('state-error');

        this.resetUI();
    }

    setVisuals(status, title, subtitle) {
        if (this.dom.title) this.dom.title.textContent = title;
        if (this.dom.sub) this.dom.sub.textContent = subtitle;

        if (this.dom.icon) {
            if (status === 'state-success') this.dom.icon.textContent = '✅';
            else if (status === 'state-error') this.dom.icon.textContent = '❌';
            else if (status === 'state-processing') this.dom.icon.textContent = '🔄';
            else this.dom.icon.textContent = '📡';
        }
    }

    resetUI() {
        setTimeout(() => {
            this.dom.body.classList.remove('processing', 'state-success', 'state-error');
            this.setVisuals('idle', 'Ready to Scan', 'Hold your badge near the reader');
            this.state.isProcessing = false;
            if (this.dom.input) this.dom.input.value = '';
            this.safeFocus();
        }, this.config.resetDelay);
    }

    addFeedItem(item, confirmed) {
        if (!this.dom.feed) return;

        const div = document.createElement('div');
        div.className = `feed-item ${confirmed ? 'confirmed' : 'pending'}`;

        const dateObj = new Date(item.time);
        const timeStr = isNaN(dateObj.getTime()) ? '--:--' : dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const eventLabel = (item.event || 'Unknown').replace('_', ' ').toUpperCase();

        // Initials (safe — derived from name characters)
        const initials = (item.name || 'U').split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();

        // Build DOM safely (no innerHTML with user data — prevents XSS)
        const avatar = document.createElement('div');
        avatar.className = 'avatar';
        avatar.textContent = initials;

        const feedName = document.createElement('div');
        feedName.className = 'feed-name';
        feedName.textContent = item.name || 'Unknown User';

        const timeBadge = document.createElement('span');
        timeBadge.className = 'time-badge';
        timeBadge.textContent = timeStr;

        const eventSpan = document.createElement('span');
        eventSpan.textContent = eventLabel;

        const feedMeta = document.createElement('div');
        feedMeta.className = 'feed-meta';
        feedMeta.appendChild(timeBadge);
        feedMeta.appendChild(eventSpan);

        const feedInfo = document.createElement('div');
        feedInfo.className = 'feed-info';
        feedInfo.appendChild(feedName);
        feedInfo.appendChild(feedMeta);

        const feedStatus = document.createElement('div');
        feedStatus.className = 'feed-status';
        feedStatus.style.color = confirmed ? 'var(--success-accent)' : 'var(--text-muted)';
        feedStatus.textContent = confirmed ? '●' : '○';

        div.appendChild(avatar);
        div.appendChild(feedInfo);
        div.appendChild(feedStatus);

        // Insert at top
        if (this.dom.feed.firstChild) {
            this.dom.feed.insertBefore(div, this.dom.feed.firstChild);
        } else {
            this.dom.feed.appendChild(div);
        }

        // Limit feed size
        while (this.dom.feed.children.length > 15) {
            this.dom.feed.removeChild(this.dom.feed.lastChild);
        }
    }

    async loadToday() {
        try {
            const res = await fetch(`${this.config.apiBase}/api/v1/attendance/today`, { credentials: 'include' });
            if (res.ok) {
                const data = await res.json();
                if (this.dom.feed) this.dom.feed.innerHTML = '';

                // Reverse to show newest at top (API usually returns newest first, so we invert?)
                // Actually the API returns newest first.
                // If I prepend, I want to prepend the OLDEST first so the NEWEST ends up at the TOP?
                // No, if list is [New, Old], and I prepend New... List: [New]
                // Prepend Old... List: [Old, New] -> Top is Old. User sees Oldest.
                // So I want to prepend in REVERSE order (Oldest -> Newest).
                const reversed = [...data].reverse();
                reversed.forEach(r => {
                    this.addFeedItem({
                        name: r.name,
                        event: r.event_type,
                        time: r.timestamp,
                        uid: r.rfid_uid,
                        status: 'success'
                    }, true);
                });
            }
        } catch (e) {
            this.emitDebug(`Failed to load history: ${e.message}`);
        }
    }

    emitDebug(msg) {
        console.debug(`[Kiosk] ${msg}`);
    }

    updateTime() {
        const now = new Date();
        if (this.dom.clock) this.dom.clock.textContent = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
        if (this.dom.date) this.dom.date.textContent = now.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
    }

    safeFocus() {
        try { if (this.dom.input) this.dom.input.focus({ preventScroll: true }); }
        catch (e) { }
    }
}

const app = new ProfessionalKiosk();
