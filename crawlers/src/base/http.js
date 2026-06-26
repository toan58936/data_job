/**
 * base/http.js
 *
 * HTTP client thuần (axios) dùng cho ITviec list-crawler — KHÔNG launch
 * browser. Đã verify bằng curl thật từ máy người dùng: status 200, HTML
 * đầy đủ job-card, không bị Cloudflare challenge chặn (chỉ có Turnstile
 * script chạy nền, không ảnh hưởng SSR content).
 *
 * KHÔNG dùng module này cho TopCV hoặc ITviec-detail — cả 2 cần JS render
 * (Vue cho TopCV, JSON-LD cần DOM cho ITviec-detail) — xem base/browser.js.
 */

const axios = require('axios');
const { randomUserAgent, DEFAULT_USER_AGENTS } = require('./utils');

const DEFAULT_HEADERS = {
    Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8',
};

/**
 * GET 1 trang HTML với retry tự động, rotate User-Agent mỗi lần gọi.
 *
 * @param {string} url
 * @param {object} options
 * @param {string} options.referer
 * @param {number} options.timeout      - default 15000ms
 * @param {number} options.maxRetries   - default 3
 * @param {number} options.retryDelay   - default 5000ms
 * @param {function} options.log        - log(message, level), default console.log
 * @returns {Promise<string|null>} HTML text, hoặc null nếu fail sau khi hết retry
 */
async function fetchHtml(url, options = {}) {
    const {
        referer = '',
        timeout = 15000,
        maxRetries = 3,
        retryDelay = 5000,
        userAgents = DEFAULT_USER_AGENTS,
        log = console.log,
    } = options;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
        try {
            const response = await axios.get(url, {
                headers: {
                    ...DEFAULT_HEADERS,
                    'User-Agent': randomUserAgent(userAgents),
                    ...(referer ? { Referer: referer } : {}),
                },
                timeout,
            });
            return response.data;
        } catch (err) {
            const status = err.response ? err.response.status : 'NO_RESPONSE';
            log(`Fetch lỗi (status ${status}, attempt ${attempt + 1}/${maxRetries + 1}): ${err.message} — ${url}`, 'WARN');

            if (attempt < maxRetries) {
                await new Promise(r => setTimeout(r, retryDelay));
            } else {
                return null;
            }
        }
    }
    return null;
}

module.exports = {
    fetchHtml,
};
