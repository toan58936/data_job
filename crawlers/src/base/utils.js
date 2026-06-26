/**
 * base/utils.js
 *
 * Tiện ích dùng chung cho mọi crawler (TopCV + ITviec).
 * Trích xuất từ logic lặp lại trong list-crawler.js, detail_crawler_itviet4.js,
 * itviec-list-crawler.js — KHÔNG đổi behavior, chỉ gom lại 1 nơi.
 *
 * Quy ước: mọi hàm nhận `source` (vd: 'topcv', 'itviec') làm tham số đầu
 * để log/checkpoint/output tách đúng theo nguồn — tránh lặp lại lỗi file
 * trùng tên giữa 2 nguồn đã từng xảy ra trong quá trình phát triển.
 */

const fs = require('fs');
const path = require('path');

// ==================== FILESYSTEM ====================

function ensureDir(dir) {
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

// ==================== LOGGING ====================

/**
 * Tạo logger riêng cho 1 source + 1 crawler stage (list/detail/text).
 *
 * @param {string} logDir   - Thư mục log gốc, ví dụ path.resolve(ROOT, 'logs/crawler/itviec')
 * @param {string} fileName - Tên file log, ví dụ 'itviec_list.log'
 * @returns {function} log(message, level, tag?) — tag là role/job_id, optional
 */
function makeLogger(logDir, fileName) {
    return function log(message, level = 'INFO', tag = null) {
        const timestamp = new Date().toISOString();
        const tagPart = tag ? ` [${tag}]` : '';
        const logMsg = `[${timestamp}] [${level}]${tagPart} ${message}`;
        console.log(logMsg);
        ensureDir(logDir);
        fs.appendFileSync(path.join(logDir, fileName), logMsg + '\n');
    };
}

// ==================== URL ====================

function normalizeUrl(url) {
    if (!url) return null;
    const idx = url.indexOf('?');
    return idx === -1 ? url : url.substring(0, idx);
}

// ==================== USER AGENTS ====================
// Đặt ở đây (không phải browser.js) để http.js có thể dùng mà KHÔNG cần
// require playwright-extra — http.js phải chạy độc lập, không phụ thuộc
// Playwright được cài hay không.

const DEFAULT_USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
];

function randomUserAgent(pool = DEFAULT_USER_AGENTS) {
    return pool[Math.floor(Math.random() * pool.length)];
}

// ==================== DELAY ====================

function randomDelay(min, max) {
    const delay = min + Math.random() * (max - min);
    return new Promise(resolve => setTimeout(resolve, delay));
}

function randomFrom(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
}

// ==================== UPSERT ====================

/**
 * Upsert một batch job vào file JSON tổng, theo key normalizeUrl(job.job_url)
 * hoặc normalizeUrl(job.url) — tự dò field nào tồn tại.
 *
 * @param {Array<object>} newJobs
 * @param {string} filePath
 * @returns {{ total: number, added: number }}
 */
function upsertJobs(newJobs, filePath) {
    ensureDir(path.dirname(filePath));

    let existingJobs = [];
    if (fs.existsSync(filePath)) {
        try {
            existingJobs = JSON.parse(fs.readFileSync(filePath, 'utf8'));
        } catch (e) {
            existingJobs = [];
        }
    }

    const getUrl = (job) => job.job_url || job.url || null;

    const urlMap = new Map();
    for (const job of existingJobs) {
        const norm = normalizeUrl(getUrl(job));
        if (norm) urlMap.set(norm, job);
    }

    let added = 0;
    for (const job of newJobs) {
        const norm = normalizeUrl(getUrl(job));
        if (norm && !urlMap.has(norm)) {
            urlMap.set(norm, job);
            existingJobs.push(job);
            added++;
        }
    }

    fs.writeFileSync(filePath, JSON.stringify(existingJobs, null, 2));
    return { total: existingJobs.length, added };
}

/**
 * Upsert 1 record duy nhất vào file JSON (dùng cho detail-crawler, ghi mỗi job).
 * Khác upsertJobs ở chỗ: LUÔN merge/overwrite record cũ nếu trùng key
 * (dùng cho việc cập nhật detail sau khi đã có từ listing).
 */
function upsertOne(newRecord, filePath) {
    ensureDir(path.dirname(filePath));

    let existing = [];
    if (fs.existsSync(filePath)) {
        try {
            existing = JSON.parse(fs.readFileSync(filePath, 'utf8'));
        } catch (e) {
            existing = [];
        }
    }

    const getUrl = (r) => r.job_url || r.url || null;
    const normNew = normalizeUrl(getUrl(newRecord));
    const idx = existing.findIndex(r => normalizeUrl(getUrl(r)) === normNew);

    if (idx !== -1) {
        existing[idx] = { ...existing[idx], ...newRecord };
    } else {
        existing.push(newRecord);
    }

    fs.writeFileSync(filePath, JSON.stringify(existing, null, 2));
    return existing.length;
}

// ==================== CHECKPOINT ====================

/**
 * Checkpoint theo index — dùng cho crawler dạng "list job cố định, lặp tuần tự"
 * (detail-crawler, text-crawler).
 */
function saveCheckpointByIndex(checkpointFile, data) {
    ensureDir(path.dirname(checkpointFile));
    fs.writeFileSync(checkpointFile, JSON.stringify({ ...data, timestamp: Date.now() }, null, 2));
}

function loadCheckpoint(checkpointFile) {
    if (!fs.existsSync(checkpointFile)) return null;
    try {
        return JSON.parse(fs.readFileSync(checkpointFile, 'utf8'));
    } catch (e) {
        return null;
    }
}

function clearCheckpoint(checkpointFile) {
    if (fs.existsSync(checkpointFile)) fs.unlinkSync(checkpointFile);
}

/**
 * Checkpoint theo hash danh sách URL — dùng khi list job có thể thay đổi
 * giữa các lần chạy (filter theo "chưa crawl"), để tránh checkpoint dùng
 * count làm key bị lệch khi danh sách filter thay đổi.
 */
function computeUrlListHash(jobList) {
    const crypto = require('crypto');
    const getUrl = (j) => j.job_url || j.url || '';
    const urls = jobList.map(j => normalizeUrl(getUrl(j))).sort().join('|');
    return crypto.createHash('md5').update(urls).digest('hex').slice(0, 8);
}

module.exports = {
    ensureDir,
    makeLogger,
    normalizeUrl,
    randomDelay,
    randomFrom,
    randomUserAgent,
    DEFAULT_USER_AGENTS,
    upsertJobs,
    upsertOne,
    saveCheckpointByIndex,
    loadCheckpoint,
    clearCheckpoint,
    computeUrlListHash,
};
