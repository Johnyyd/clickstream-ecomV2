/**
 * Cache Management System for SPA Dashboard
 * Handles HTTP cache, localStorage, and snapshot persistence
 */

// === HTTP Cache ===
export const httpCache = new Map();
export const cacheKey = (url) => url;

// === LocalStorage Persistence ===
const LS_NS = 'spa_cache_v1:';
const SNAP_NS = 'spa_snap_v1:';

export function lsKey(url) { return LS_NS + url; }

export function lsGet(url) {
    try {
        const s = localStorage.getItem(lsKey(url));
        return s ? JSON.parse(s) : null;
    } catch { return null; }
}

export function lsSet(url, data) {
    try {
        localStorage.setItem(lsKey(url), JSON.stringify({ data, ts: Date.now() }));
    } catch { }
}

export function lsData(payload) {
    return payload && typeof payload === 'object' ? (payload.data ?? payload) : payload;
}

export function lsDel(url) {
    try { localStorage.removeItem(lsKey(url)); } catch { }
}

// === Filter Signature ===
export function filterSig(state) {
    const { range, from, to, segment, channel } = state?.filters || {};
    return `r=${range || ''}|f=${from || ''}|t=${to || ''}|s=${segment || ''}|c=${channel || ''}`;
}

// === Snapshot Management ===
export function snapKey(tab, state) {
    return SNAP_NS + tab + '|' + filterSig(state);
}

export function snapSet(tab, payload, state) {
    try {
        const key = snapKey(tab, state);
        const data = { ts: Date.now(), payload };
        localStorage.setItem(key, JSON.stringify(data));
        console.debug(`[Cache] snapSet('${tab}') - Saved to ${key}`, {
            hasData: hasAnyData(payload),
            payloadKeys: Object.keys(payload || {})
        });
    } catch (e) {
        console.error(`[Cache] snapSet('${tab}') failed:`, e);
    }
}

export function snapGet(tab, state) {
    try {
        const s = localStorage.getItem(snapKey(tab, state));
        return s ? JSON.parse(s).payload : null;
    } catch { return null; }
}

export function snapRaw(tab, state) {
    try {
        const s = localStorage.getItem(snapKey(tab, state));
        return s ? JSON.parse(s) : null;
    } catch { return null; }
}

export function snapAgeMs(tab, state) {
    try {
        const r = snapRaw(tab, state);
        return r && typeof r.ts === 'number' ? (Date.now() - r.ts) : Infinity;
    } catch { return Infinity; }
}

// === Snapshot Clear Functions ===
export function clearSnapshotForTabCurrentFilter(tab, state) {
    try {
        localStorage.removeItem(snapKey(tab, state));
    } catch { }
    if (tab === 'journey') {
        try { delete window.__jnSankeyHash; } catch { }
    }
}

export function clearSnapshotsForTab(tab) {
    try {
        const prefix = SNAP_NS + tab + '|';
        for (let i = localStorage.length - 1; i >= 0; i--) {
            const k = localStorage.key(i);
            if (k && k.startsWith(prefix)) {
                try { localStorage.removeItem(k); } catch { }
            }
        }
    } catch { }
}

export function clearSnapshotsForCurrentFilters(state) {
    try {
        const suffix = '|' + filterSig(state);
        for (let i = localStorage.length - 1; i >= 0; i--) {
            const k = localStorage.key(i);
            if (!k) continue;
            if (k.startsWith(SNAP_NS) && k.endsWith(suffix)) {
                try { localStorage.removeItem(k); } catch { }
            }
        }
    } catch { }
}

// === Data Validation ===
export function hasAnyData(obj) {
    try {
        if (obj == null) return false;
        if (Array.isArray(obj)) return obj.length > 0;
        if (typeof obj !== 'object') return true;
        const keys = Object.keys(obj);
        if (keys.length === 0) return false;
        for (const k of keys) {
            const v = obj[k];
            if (Array.isArray(v)) {
                if (v.length > 0) return true;
                continue;
            }
            if (v && typeof v === 'object') {
                if (Object.keys(v).length > 0 && hasAnyData(v)) return true;
                continue;
            }
            if (v != null) return true;
        }
    } catch { }
    return false;
}

export function snapMaybe(tab, payload, state) {
    if (hasAnyData(payload)) snapSet(tab, payload, state);
}

export function snapUpdate(tab, payload, state) {
    if (!hasAnyData(payload)) {
        console.debug(`[Cache] snapUpdate('${tab}') - Skipped (no data)`);
        return;
    }
    try {
        const prev = snapGet(tab, state);
        const same = prev && JSON.stringify(prev) === JSON.stringify(payload);
        if (!same) {
            snapSet(tab, payload, state);
            console.debug(`[Cache] snapUpdate('${tab}') - Updated (data changed)`);
        } else {
            console.debug(`[Cache] snapUpdate('${tab}') - Skipped (data unchanged)`);
        }
    } catch {
        snapSet(tab, payload, state);
        console.debug(`[Cache] snapUpdate('${tab}') - Saved (error comparing)`);
    }
}

// === Legacy Migration ===
function snapGetLegacyRaw(tab) {
    try {
        const s = localStorage.getItem(SNAP_NS + tab);
        return s ? JSON.parse(s) : null;
    } catch { return null; }
}

export function migrateOldSnapshots(state) {
    try {
        const prefix = SNAP_NS;
        for (let i = 0; i < localStorage.length; i++) {
            const k = localStorage.key(i);
            if (!k || !k.startsWith(prefix)) continue;
            if (k.includes('|')) continue; // Already migrated
            const tab = k.slice(prefix.length);
            const raw = snapGetLegacyRaw(tab);
            const payload = raw && raw.payload;
            if (hasAnyData(payload)) {
                try {
                    localStorage.setItem(snapKey(tab, state), JSON.stringify({ ts: Date.now(), payload }));
                } catch { }
            }
        }
    } catch { }
}

// === TTL-aware Cache Getter ===
export async function getWithTTL(url, ttlMs = 600000) {
    const key = cacheKey(url);
    if (httpCache.has(key)) return httpCache.get(key);

    const persisted = lsGet(key);
    if (persisted && typeof persisted === 'object' && typeof persisted.ts === 'number') {
        if (Date.now() - persisted.ts <= ttlMs) {
            const data = lsData(persisted);
            httpCache.set(key, data);
            return data;
        }
        lsDel(key); // Expired
    }

    const token = localStorage.getItem('token') || localStorage.getItem('access_token') || '';
    const res = await fetch(url, {
        headers: {
            'Accept': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        }
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = await res.json();
    httpCache.set(key, json);
    lsSet(key, json);
    return json;
}
