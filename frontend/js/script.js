/**
 * Sentinel Kiosk — Professional RFID Attendance Interface
 * v3.0 — Enhanced with rich scan feedback, live stats, and audio
 */

class ProfessionalKiosk {
    constructor() {
        this.config = {
            apiBase: window.location.origin,
            apiUrl: '/api/v1/scan',
            resetDelay: 5000,
            debounceTime: 3000,
            statsInterval: 30000,
        };

        this.state = {
            isProcessing: false,
            lastProcessed: {},
            scanBuffer: '',
            lastLocalInputTime: 0,
        };

        this.dom = {
            body: document.body,
            input: document.getElementById('rfidInput'),
            title: document.getElementById('scanTitle'),
            sub: document.getElementById('scanSubtitle'),
            icon: document.getElementById('scanIcon'),
            clock: document.getElementById('clock'),
            date: document.getElementById('date'),
            feed: document.getElementById('feedList'),
            // Live stats
            statPresent: document.getElementById('statPresent'),
            statAbsent: document.getElementById('statAbsent'),
            statLate: document.getElementById('statLate'),
            // Scan result overlay
            overlay: document.getElementById('scanResultOverlay'),
            resultEmoji: document.getElementById('resultEmoji'),
            resultName: document.getElementById('resultName'),
            resultBadge: document.getElementById('resultBadge'),
            resultTime: document.getElementById('resultTime'),
            resultHours: document.getElementById('resultHours'),
            resultLastEvent: document.getElementById('resultLastEvent'),
            resultLastTime: document.getElementById('resultLastTime'),
            lateWarning: document.getElementById('lateWarning'),
            progressFill: document.getElementById('progressFill'),
        };

        this.init();
    }

    init() {
        // Clock
        this.updateTime();
        setInterval(() => this.updateTime(), 1000);

        // Focus management
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
        this.loadLiveStats();

        // Refresh live stats every 30 seconds
        setInterval(() => this.loadLiveStats(), this.config.statsInterval);

        this.safeFocus();
    }

    handleGlobalKeydown(e) {
        if (e.target.tagName === 'INPUT' && e.target !== this.dom.input) return;

        const now = Date.now();
        if (now - this.state.lastLocalInputTime < 500) return;

        if (e.key === 'Enter') {
            if (this.state.scanBuffer.length > 2) {
                const uid = this.state.scanBuffer;
                this.processScan(uid, 'scanner');
            }
            this.state.scanBuffer = '';
        } else if (e.key.length === 1) {
            this.state.scanBuffer += e.key;
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

        const now = Date.now();
        if (this.state.lastProcessed[uid] && (now - this.state.lastProcessed[uid] < this.config.debounceTime)) {
            return;
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

        const isCheckIn = data.event === 'IN';
        const eventLabel = isCheckIn ? 'CHECKED IN' : 'CHECKED OUT';

        // Update main status
        this.setVisuals('state-success', `Welcome, ${data.name}`, `Recorded: ${eventLabel}`);
        this.dom.body.classList.remove('processing');

        // Determine state class
        const stateClass = data.is_late
            ? (isCheckIn ? 'state-late' : 'state-early-out')
            : 'state-success';
        this.dom.body.classList.add(stateClass);

        // If late arrival or early checkout, update subtitle
        if (data.is_late && isCheckIn) {
            this.setVisuals('state-late', `Welcome, ${data.name}`, 'Late Arrival');
        } else if (data.is_late && !isCheckIn) {
            this.setVisuals('state-success', `${data.name}`, 'Early Check Out');
        }

        // Play audio feedback
        this.playTone(data.is_late ? 'late' : 'success');

        // Add to feed
        this.addFeedItem({
            name: data.name,
            event: data.event,
            time: new Date().toISOString(),
            uid: data.uid,
            status: 'success'
        }, true);

        // Reset after delay
        this.resetUI(stateClass);
    }

    handleError(error) {
        this.emitDebug(`Error: ${error.message}`);
        this.setVisuals('state-error', 'Access Denied', error.message || 'Unknown credential');

        this.dom.body.classList.remove('processing');
        this.dom.body.classList.add('state-error');

        this.playTone('error');

        this.resetUI('state-error');
    }

    setVisuals(status, title, subtitle) {
        if (this.dom.title) this.dom.title.textContent = title;
        if (this.dom.sub) this.dom.sub.textContent = subtitle;

        if (this.dom.icon) {
            if (status === 'state-success') {
                this.dom.icon.innerHTML = '<svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>';
            } else if (status === 'state-error') {
                this.dom.icon.innerHTML = '<svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#f43f5e" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
            } else if (status === 'state-processing') {
                this.dom.icon.innerHTML = '<svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>';
            } else if (status === 'state-late') {
                this.dom.icon.innerHTML = '<svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>';
            } else {
                this.dom.icon.innerHTML = '<svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12C2 6.5 6.5 2 12 2a10 10 0 0 1 8 4"/><path d="M5 12a7 7 0 0 1 7-7c2.8 0 5.2 1.6 6.3 4"/><path d="M8.5 12a3.5 3.5 0 0 1 3.5-3.5"/><circle cx="12" cy="12" r="1"/><path d="M12 13v9"/></svg>';
            }
        }
    }

    resetUI(stateClass = 'state-success') {
        setTimeout(() => {
            this.dom.body.classList.remove('processing', 'state-success', 'state-error', 'state-late', 'state-early-out');
            this.setVisuals('idle', 'Ready to Scan', 'Hold your badge near the reader');
            this.state.isProcessing = false;
            if (this.dom.input) this.dom.input.value = '';
            this.safeFocus();
        }, this.config.resetDelay);
    }

    // ── Audio Feedback (Web Audio API — no external files) ──────────
    playTone(type) {
        try {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);

            gain.gain.value = 0.15;

            switch (type) {
                case 'success':
                    osc.frequency.value = 880;
                    osc.type = 'sine';
                    gain.gain.setValueAtTime(0.15, ctx.currentTime);
                    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3);
                    osc.start(ctx.currentTime);
                    osc.stop(ctx.currentTime + 0.3);
                    // Second tone for pleasant "ding ding"
                    const osc2 = ctx.createOscillator();
                    const gain2 = ctx.createGain();
                    osc2.connect(gain2);
                    gain2.connect(ctx.destination);
                    osc2.frequency.value = 1100;
                    osc2.type = 'sine';
                    gain2.gain.setValueAtTime(0.12, ctx.currentTime + 0.15);
                    gain2.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.45);
                    osc2.start(ctx.currentTime + 0.15);
                    osc2.stop(ctx.currentTime + 0.45);
                    break;

                case 'error':
                    osc.frequency.value = 300;
                    osc.type = 'square';
                    gain.gain.setValueAtTime(0.1, ctx.currentTime);
                    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.5);
                    osc.start(ctx.currentTime);
                    osc.stop(ctx.currentTime + 0.5);
                    break;

                case 'late':
                    osc.frequency.value = 660;
                    osc.type = 'triangle';
                    gain.gain.setValueAtTime(0.12, ctx.currentTime);
                    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.2);
                    osc.start(ctx.currentTime);
                    osc.stop(ctx.currentTime + 0.2);
                    // Warning second beep
                    const oscW = ctx.createOscillator();
                    const gainW = ctx.createGain();
                    oscW.connect(gainW);
                    gainW.connect(ctx.destination);
                    oscW.frequency.value = 440;
                    oscW.type = 'triangle';
                    gainW.gain.setValueAtTime(0.12, ctx.currentTime + 0.25);
                    gainW.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.5);
                    oscW.start(ctx.currentTime + 0.25);
                    oscW.stop(ctx.currentTime + 0.5);
                    break;
            }

            // Cleanup
            setTimeout(() => ctx.close(), 1000);
        } catch (e) {
            // AudioContext not available — silently skip
        }
    }

    // ── Live Stats ────────────────────────────────────────────────
    async loadLiveStats() {
        try {
            const res = await fetch(`${this.config.apiBase}/api/v1/attendance/live-stats`, { credentials: 'include' });
            if (res.ok) {
                const stats = await res.json();
                if (this.dom.statPresent) this.dom.statPresent.textContent = stats.present;
                if (this.dom.statAbsent) this.dom.statAbsent.textContent = stats.absent;
                if (this.dom.statLate) this.dom.statLate.textContent = stats.late;
            }
        } catch (e) {
            this.emitDebug(`Live stats failed: ${e.message}`);
        }
    }

    // ── Feed ──────────────────────────────────────────────────────
    addFeedItem(item, confirmed) {
        if (!this.dom.feed) return;

        const div = document.createElement('div');
        div.className = `feed-item ${confirmed ? 'confirmed' : 'pending'}`;

        const dateObj = new Date(item.time);
        const timeStr = isNaN(dateObj.getTime()) ? '--:--' : dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const eventLabel = (item.event || 'Unknown').replace('_', ' ').toUpperCase();

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
