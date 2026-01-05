/**
 * Utility functions for SPA Dashboard
 * DOM helpers, formatters, and common utilities
 */

// === DOM Helper ===

/**
 * Shorthand for querySelector
 * @param {string} sel - CSS selector
 * @returns {Element|null}
 */
export function el(sel) {
    return document.querySelector(sel);
}

// === Debounce & Request Idle ===

/**
 * Simple debounce helper
 * @param {Function} fn - Function to debounce
 * @param {number} ms - Milliseconds to wait
 * @returns {Function}
 */
export function debounce(fn, ms) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), ms);
    };
}

/**
 * Request idle callback with fallback
 * @param {Function} cb - Callback function
 */
export function requestIdle(cb) {
    if ('requestIdleCallback' in window) window.requestIdleCallback(cb);
    else setTimeout(cb, 1);
}

// === URL Helpers ===

/**
 * Build a fresh URL that bypasses caches
 * @param {string} url - Original URL
 * @returns {{fresh: string, clean: string}}
 */
export function withBypass(url) {
    const u = new URL(url, window.location.origin);
    u.searchParams.set('_cb', Date.now());
    return { fresh: u.toString(), clean: url };
}

// === Toast Notifications ===

/**
 * Show toast notification
 * @param {string} message - Message to display
 * @param {string} kind - Type: 'info', 'success', 'error'
 * @param {number} timeout - Duration in ms
 */
export function showToast(message, kind = 'info', timeout = 2600) {
    const toast = document.createElement('div');
    toast.textContent = message;
    toast.style.cssText = `position:fixed;top:16px;right:16px;padding:12px 20px;background:#${kind === 'error' ? 'ef4444' : kind === 'success' ? '10b981' : '3b82f6'
        };color:#fff;border-radius:8px;z-index:9999;box-shadow:0 4px 6px rgba(0,0,0,0.3);`;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), timeout);
}

// === Tab Management ===

/**
 * Set active tab in navigation
 * @param {string} name - Tab name
 */
export function setActiveTab(name) {
    document.querySelectorAll('[data-tab]').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === name);
        btn.setAttribute('aria-selected', btn.dataset.tab === name);
    });
}

// === Date Utilities ===

/**
 * Convert Date to ISO string (YYYY-MM-DD)
 * @param {Date} dt - Date object
 * @returns {string}
 */
export function toISO(dt) {
    return dt.toISOString().split('T')[0];
}

/**
 * Convert preset range to date objects
 * @param {string} range - Range preset (e.g., '7d', '30d')
 * @returns {{from: Date, to: Date}|null}
 */
export function presetToDates(range) {
    const now = new Date();
    const from = new Date(now);
    if (range === '7d') from.setDate(now.getDate() - 7);
    else if (range === '30d') from.setDate(now.getDate() - 30);
    else if (range === '90d') from.setDate(now.getDate() - 90);
    else if (range === '1y') from.setFullYear(now.getFullYear() - 1);
    else if (range === 'mtd') {
        from.setDate(1);
        from.setHours(0, 0, 0, 0);
    } else if (range === 'ytd') {
        from.setMonth(0, 1);
        from.setHours(0, 0, 0, 0);
    } else return null;
    return { from, to: now };
}

// === Number Formatters ===

/**
 * Format number with thousands separator
 * @param {number} n - Number to format
 * @param {number} digits - Decimal places
 * @returns {string}
 */
export function fmt(n, digits = 0) {
    if (n == null || isNaN(n)) return '0';
    return Number(n).toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

/**
 * Format currency (USD)
 * @param {number} n - Amount
 * @returns {string}
 */
export function fmtCurrency(n) {
    if (n == null || isNaN(n)) return '$0.00';
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(n);
}

/**
 * Format large numbers with K/M/B suffix
 * @param {number} n - Number to format
 * @returns {string}
 */
export function fmtShort(n) {
    if (n == null || isNaN(n)) return '0';
    if (n >= 1e9) return (n / 1e9).toFixed(1) + 'B';
    if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
    if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K';
    return String(n);
}
