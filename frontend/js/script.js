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
        const stateClass = data.is_late ? 'state-late' : 'state-success';
        this.dom.body.classList.add(stateClass);

        // Play audio feedback
        if (data.is_late) {
            this.playTone('late');
        } else {
            this.playTone('success');
        }

        // Show rich scan result overlay
        this.showScanResult(data, isCheckIn, eventLabel);

        // Add to feed
        this.addFeedItem({
            name: data.name,
            event: data.event,
            time: new Date().toISOString(),
            uid: data.uid,
            status: 'success'
        }, true);

        // Refresh live stats
        this.loadLiveStats();

        // Reset after delay
        this.resetUI(stateClass);
    }

    showScanResult(data, isCheckIn, eventLabel) {
        if (!this.dom.overlay) return;

        // Emoji
        if (this.dom.resultEmoji) {
            this.dom.resultEmoji.textContent = data.is_late ? '⚠️' : (isCheckIn ? '✅' : '👋');
        }

        // Name
        if (this.dom.resultName) {
            this.dom.resultName.textContent = `Welcome, ${data.name}!`;
        }

        // Badge
        if (this.dom.resultBadge) {
            this.dom.resultBadge.textContent = eventLabel;
            this.dom.resultBadge.className = `result-badge ${isCheckIn ? 'badge-in' : 'badge-out'}`;
        }

        // Time
        if (this.dom.resultTime) {
            this.dom.resultTime.textContent = new Date().toLocaleTimeString('en-US', {
                hour: '2-digit', minute: '2-digit'
            });
        }

        // Today's hours
        if (this.dom.resultHours) {
            const hours = data.today_hours || 0;
            const h = Math.floor(hours);
            const m = Math.round((hours - h) * 60);
            this.dom.resultHours.textContent = `${h}h ${m}m`;
        }

        // Previous event
        if (this.dom.resultLastEvent) {
            this.dom.resultLastEvent.textContent = data.last_event_type
                ? data.last_event_type.replace('_', ' ')
                : 'First scan';
        }

        // Previous time
        if (this.dom.resultLastTime) {
            if (data.last_event_time) {
                const lastTime = new Date(data.last_event_time);
                this.dom.resultLastTime.textContent = isNaN(lastTime.getTime())
                    ? '—'
                    : lastTime.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
            } else {
                this.dom.resultLastTime.textContent = '—';
            }
        }

        // Late warning
        if (this.dom.lateWarning) {
            this.dom.lateWarning.style.display = data.is_late ? 'block' : 'none';
        }

        // Restart progress bar animation
        if (this.dom.progressFill) {
            this.dom.progressFill.style.animation = 'none';
            this.dom.progressFill.offsetHeight; // force reflow
            this.dom.progressFill.style.animation = 'progressCountdown 5s linear forwards';
        }

        // Show overlay
        this.dom.overlay.classList.add('active');
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
            if (status === 'state-success') this.dom.icon.textContent = '✅';
            else if (status === 'state-error') this.dom.icon.textContent = '❌';
            else if (status === 'state-processing') this.dom.icon.textContent = '🔄';
            else if (status === 'state-late') this.dom.icon.textContent = '⚠️';
            else this.dom.icon.textContent = '📡';
        }
    }

    resetUI(stateClass = 'state-success') {
        setTimeout(() => {
            this.dom.body.classList.remove('processing', 'state-success', 'state-error', 'state-late');
            if (this.dom.overlay) this.dom.overlay.classList.remove('active');
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
