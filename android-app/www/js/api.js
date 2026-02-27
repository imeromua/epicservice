/**
 * www/js/api.js
 * HTTP-клієнт для спілкування з EpicService API.
 * Підтримує офлайн-режим та кешування.
 */
const EpicAPI = (function () {
    'use strict';

    const SERVER = window.APP_CONFIG?.serverUrl || 'https://anubis-ua.pp.ua';
    const CACHE_PREFIX = 'epic_cache_';
    const CACHE_TTL = 5 * 60 * 1000; // 5 хвилин

    async function _request(method, path, body, token) {
        const url = `${SERVER}${path}`;
        const headers = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const options = { method, headers };
        if (body) options.body = JSON.stringify(body);

        const resp = await fetch(url, options);
        const data = await resp.json();

        if (!resp.ok) {
            const msg = data?.detail || data?.message || `HTTP ${resp.status}`;
            throw new Error(msg);
        }
        return data;
    }

    async function get(path, token) {
        return _request('GET', path, null, token);
    }

    async function post(path, body, token) {
        return _request('POST', path, body, token);
    }

    async function put(path, body, token) {
        return _request('PUT', path, body, token);
    }

    async function del(path, token) {
        return _request('DELETE', path, null, token);
    }

    // --- Кешування для офлайн-режиму ---
    function cacheSet(key, data) {
        try {
            localStorage.setItem(CACHE_PREFIX + key, JSON.stringify({
                data,
                ts: Date.now()
            }));
        } catch { /* ігноруємо помилки сховища */ }
    }

    function cacheGet(key) {
        try {
            const raw = localStorage.getItem(CACHE_PREFIX + key);
            if (!raw) return null;
            const { data, ts } = JSON.parse(raw);
            if (Date.now() - ts > CACHE_TTL) return null;
            return data;
        } catch { return null; }
    }

    function cacheClear(key) {
        localStorage.removeItem(CACHE_PREFIX + key);
    }

    // --- GET з кешуванням ---
    async function getWithCache(path, token, cacheKey) {
        try {
            const data = await get(path, token);
            if (cacheKey) cacheSet(cacheKey, data);
            return { data, fromCache: false };
        } catch {
            if (cacheKey) {
                const cached = cacheGet(cacheKey);
                if (cached) return { data: cached, fromCache: true };
            }
            throw new Error('Немає з\'єднання та кешованих даних');
        }
    }

    // --- Перевірка мережі ---
    function isOnline() { return navigator.onLine; }

    return { get, post, put, del, cacheSet, cacheGet, cacheClear, getWithCache, isOnline };
})();
