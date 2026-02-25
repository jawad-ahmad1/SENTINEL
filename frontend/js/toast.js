/**
 * Toast Notification System — Global drop-in for all Sentinel pages.
 * Replaces all alert() calls with non-blocking, styled notifications.
 *
 * Usage:
 *   showToast('Settings saved!', 'success');
 *   showToast('Failed to load data', 'error');
 *   showToast('Processing...', 'info', 5000);
 */

(function () {
    'use strict';

    // Inject toast container + styles once
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.setAttribute('role', 'status');
    container.setAttribute('aria-live', 'polite');

    const style = document.createElement('style');
    style.textContent = `
        #toast-container {
            position: fixed;
            bottom: 24px;
            right: 24px;
            display: flex;
            flex-direction: column-reverse;
            gap: 10px;
            z-index: 99999;
            pointer-events: none;
        }
        .sentinel-toast {
            pointer-events: auto;
            padding: 14px 24px;
            border-radius: 10px;
            color: #fff;
            font-family: 'Plus Jakarta Sans', sans-serif;
            font-weight: 600;
            font-size: 0.88rem;
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255,255,255,0.1);
            transform: translateX(120%);
            opacity: 0;
            transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
            max-width: 380px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.4);
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .sentinel-toast.show {
            transform: translateX(0);
            opacity: 1;
        }
        .sentinel-toast.toast-success {
            background: linear-gradient(135deg, rgba(16,185,129,0.9), rgba(5,150,105,0.9));
        }
        .sentinel-toast.toast-error {
            background: linear-gradient(135deg, rgba(244,63,94,0.9), rgba(225,29,72,0.9));
        }
        .sentinel-toast.toast-info {
            background: linear-gradient(135deg, rgba(99,102,241,0.9), rgba(79,70,229,0.9));
        }
        .sentinel-toast.toast-warning {
            background: linear-gradient(135deg, rgba(245,158,11,0.9), rgba(217,119,6,0.9));
        }
        .toast-icon { font-size: 1.15rem; flex-shrink: 0; }
    `;

    document.head.appendChild(style);
    document.body.appendChild(container);

    const ICONS = {
        success: '\u2705',
        error: '\u274c',
        info: '\u2139\ufe0f',
        warning: '\u26a0\ufe0f'
    };

    /**
     * Show a toast notification.
     * @param {string} message - Text to display
     * @param {'success'|'error'|'info'|'warning'} type - Toast style
     * @param {number} duration - Auto-dismiss time in ms (default 3500)
     */
    window.showToast = function (message, type = 'success', duration = 3500) {
        const toast = document.createElement('div');
        toast.className = `sentinel-toast toast-${type}`;
        toast.innerHTML = `<span class="toast-icon">${ICONS[type] || ''}</span><span>${message}</span>`;
        container.appendChild(toast);

        // Trigger animation
        requestAnimationFrame(() => {
            requestAnimationFrame(() => toast.classList.add('show'));
        });

        // Auto-dismiss
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 350);
        }, duration);
    };
})();
