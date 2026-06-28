/**
 * base/browser.js
 *
 * Khởi tạo Playwright + stealth dùng chung cho:
 *   - TopCV (list, detail, text) — Vue render cần JS, không thể dùng axios
 *   - ITviec detail-crawler — JSON-LD + HTML cần render trước khi cheerio đọc
 *
 * KHÔNG dùng cho ITviec list-crawler — xem base/http.js. ITviec listing page
 * là SSR đầy đủ (đã verify bằng curl thật, status 200, job-card có sẵn trong
 * HTML gốc), launch browser cho tầng đó chỉ tốn RAM không cần thiết.
 */

const { chromium } = require('playwright-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
const { randomUserAgent, DEFAULT_USER_AGENTS } = require('./utils');

chromium.use(StealthPlugin());

const DEFAULT_LAUNCH_ARGS = [
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-blink-features=AutomationControlled',
    '--disable-dev-shm-usage',
];

/**
 * Khởi tạo browser + context dùng 1 lần cho toàn batch (không mở/đóng mỗi job).
 *
 * @param {object} options
 * @param {boolean} options.headless        - default true
 * @param {string}  options.userAgent       - cố định 1 UA cho cả context (mặc định lấy random 1 lần)
 * @param {{width:number,height:number}} options.viewport
 * @param {string}  options.locale          - default 'vi-VN'
 * @returns {Promise<{browser, context}>}
 */
async function createBrowserContext(options = {}) {
    const {
        headless = true,
        userAgent = randomUserAgent(),
        viewport = { width: 1280, height: 800 },
        locale = 'vi-VN',
        launchArgs = DEFAULT_LAUNCH_ARGS,
    } = options;

    const browser = await chromium.launch({ headless, args: launchArgs });
    const context = await browser.newContext({ userAgent, viewport, locale });

    // Ẩn dấu hiệu automation — quan trọng nhất khi headless: true, vì
    // navigator.webdriver=true là tín hiệu đầu tiên site dùng để detect bot.
    await context.addInitScript(() => {
        Object.defineProperty(navigator, 'webdriver', { get: () => false });
    });

    return { browser, context };
}

/**
 * Mở 1 page mới trong context có sẵn — dùng khi cần nhiều page độc lập
 * trong cùng 1 browser (ví dụ: crawl nhiều role tuần tự, mỗi role 1 page
 * riêng để lỗi 1 role không làm hỏng state của role khác, nhưng không phải
 * khởi tạo lại browser — xem list-crawler-multi.js).
 */
async function newPageWithStealth(context) {
    const page = await context.newPage();
    await page.addInitScript(() => {
        Object.defineProperty(navigator, 'webdriver', { get: () => false });
    });
    return page;
}

/**
 * goto với retry built-in — dùng waitUntil: 'domcontentloaded' theo mặc định
 * (nhẹ hơn 'networkidle', đủ cho phần lớn trang). Trả về Playwright Response
 * object để caller tự check status.
 */
async function gotoWithRetry(page, url, options = {}) {
    const {
        waitUntil = 'domcontentloaded',
        timeout = 30000,
        maxRetries = 2,
        retryDelay = 5000,
        log = console.log,
    } = options;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
        try {
            const response = await page.goto(url, { waitUntil, timeout });
            return response;
        } catch (err) {
            log(`goto lỗi (attempt ${attempt + 1}/${maxRetries + 1}): ${err.message} — ${url}`, 'WARN');
            if (attempt < maxRetries) {
                await new Promise(r => setTimeout(r, retryDelay));
            } else {
                throw err;
            }
        }
    }
}

module.exports = {
    createBrowserContext,
    newPageWithStealth,
    gotoWithRetry,
    // Re-export để code cũ import từ browser.js (nếu có) vẫn chạy được
    randomUserAgent,
    DEFAULT_USER_AGENTS,
    DEFAULT_LAUNCH_ARGS,
};
