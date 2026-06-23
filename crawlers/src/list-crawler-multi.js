const { chromium } = require('playwright-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
const fs = require('fs');
const path = require('path');
const cheerio = require('cheerio');

chromium.use(StealthPlugin());

// ==================== ĐỌC THAM SỐ CLI ====================
// Nhận --roles với danh sách role phân cách bằng dấu phẩy
// Ví dụ: --roles data-engineer,data-analyst,data-scientist
// Không có kiểm tra VALID_ROLES ở đây — CLI đã đảm nhận.
const args = process.argv.slice(2);
const rolesIndex = args.indexOf('--roles');
const ROLES_ARG = rolesIndex !== -1 ? args[rolesIndex + 1] : 'data-engineer';

// Nếu không có --roles, mặc định chỉ crawl data-engineer (standalone)
const ROLES = ROLES_ARG ? ROLES_ARG.split(',').map(r => r.trim()) : ['data-engineer'];

// ==================== CẤU HÌNH ====================
const BASE_CONFIG = {
    outputDir: path.resolve(__dirname, '../../logs/crawler'),
    finalOutput: path.resolve(__dirname, '../../data/bronze/jobs_all.json'),
    maxRetries: 3,
    retryDelay: 5000,
    waitBetweenPages: 2000,
    waitBetweenRoles: 5000,
    headless: true,
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
    viewport: { width: 1280, height: 800 },
    locale: 'vi-VN',
    possibleSelectors: ['.job-item', '.recruit-item', '.media-job', 'div[class*="job"]', 'div[class*="recruit"]']
};

function buildRoleConfig(role) {
    return {
        ...BASE_CONFIG,
        role,
        baseUrl: `https://www.topcv.vn/tim-viec-lam-${role}?type_keyword=1&sba=1`,
        checkpointFile: path.resolve(__dirname, `../../data/bronze/checkpoint_${role}.json`),
    };
}

// ==================== TIỆN ÍCH ====================
function ensureDir(dir) {
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

function log(role, message, level = 'INFO') {
    const timestamp = new Date().toISOString();
    const logMsg = `[${timestamp}] [${level}] [${role}] ${message}`;
    console.log(logMsg);
    const logFile = path.join(BASE_CONFIG.outputDir, `crawl_${role}.log`);
    try { fs.appendFileSync(logFile, logMsg + '\n'); } catch (e) {}
}

function normalizeUrl(url) {
    if (!url) return null;
    const idx = url.indexOf('?');
    return idx === -1 ? url : url.substring(0, idx);
}

function upsertJobs(newJobs, filePath, role) {
    let existingJobs = [];
    if (fs.existsSync(filePath)) {
        try { existingJobs = JSON.parse(fs.readFileSync(filePath, 'utf8')); }
        catch(e) { log(role, 'Failed to parse existing file, starting fresh', 'WARN'); }
    }
    const urlMap = new Map();
    for (const job of existingJobs) {
        const normUrl = normalizeUrl(job.url);
        if (normUrl) urlMap.set(normUrl, job);
    }
    let addedCount = 0;
    for (const newJob of newJobs) {
        const normUrl = normalizeUrl(newJob.url);
        if (normUrl && !urlMap.has(normUrl)) {
            urlMap.set(normUrl, newJob);
            existingJobs.push(newJob);
            addedCount++;
        }
    }
    try {
        fs.writeFileSync(filePath, JSON.stringify(existingJobs, null, 2));
    } catch (e) {
        log(role, `Failed to write ${filePath}: ${e.message}`, 'ERROR');
        return { total: existingJobs.length, added: addedCount, error: e.message };
    }
    return { total: existingJobs.length, added: addedCount };
}

function saveCheckpoint(cfg, pageNum, totalPages, jobsSoFar) {
    const checkpoint = {
        role: cfg.role,
        lastPage: pageNum,
        totalPages: totalPages,
        jobsCount: jobsSoFar.length,
        timestamp: Date.now()
    };
    try {
        fs.writeFileSync(cfg.checkpointFile, JSON.stringify(checkpoint, null, 2));
        log(cfg.role, `Checkpoint saved: page ${pageNum}/${totalPages}, jobs: ${jobsSoFar.length}`);
    } catch (e) { log(cfg.role, `Failed to save checkpoint: ${e.message}`, 'ERROR'); }
}

function loadCheckpoint(cfg) {
    if (fs.existsSync(cfg.checkpointFile)) {
        try { return JSON.parse(fs.readFileSync(cfg.checkpointFile, 'utf8')); }
        catch(e) { log(cfg.role, 'Failed to parse checkpoint file', 'WARN'); }
    }
    return null;
}

async function getTotalPages(cfg, page, url) {
    log(cfg.role, `Detecting total pages from ${url}`);
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(3000);
    const html = await page.content();
    const $ = cheerio.load(html);
    let totalPages = 1;
    const paginationText = $('.pagination, .page-numbers, .pages').text();
    const match = paginationText.match(/(\d+)\s*$/);
    if (match) totalPages = parseInt(match[1]);
    else {
        const numbers = [];
        $('.pagination a, .page-numbers a').each((i, el) => {
            const num = parseInt($(el).text());
            if (!isNaN(num)) numbers.push(num);
        });
        if (numbers.length) totalPages = Math.max(...numbers);
    }
    log(cfg.role, `Detected total pages: ${totalPages}`);
    return totalPages;
}

async function crawlPage(cfg, page, pageNum, retryCount = 0) {
    const url = pageNum === 1 ? cfg.baseUrl : `${cfg.baseUrl}&page=${pageNum}`;
    log(cfg.role, `Crawling page ${pageNum}: ${url}`);
    try {
        await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
        let found = false;
        for (const sel of cfg.possibleSelectors) {
            try { await page.waitForSelector(sel, { timeout: 8000 }); found = true; break; } catch(e) {}
        }
        if (!found) log(cfg.role, `No known selector on page ${pageNum}`, 'WARN');
        await page.waitForTimeout(3000);
        await page.evaluate(async () => {
            await new Promise((resolve) => {
                let totalHeight = 0, distance = 400;
                const timer = setInterval(() => {
                    const scrollHeight = document.body.scrollHeight;
                    window.scrollBy(0, distance);
                    totalHeight += distance;
                    if (totalHeight >= scrollHeight) { clearInterval(timer); resolve(); }
                }, 200);
            });
        });
        await page.waitForTimeout(2000);
        const html = await page.content();
        const $ = cheerio.load(html);
        let jobSelector = null;
        for (const sel of cfg.possibleSelectors) {
            if ($(sel).length > 0) { jobSelector = sel; break; }
        }
        if (!jobSelector) {
            log(cfg.role, `No job cards found on page ${pageNum}`, 'WARN');
            return [];
        }
        const jobs = [];
        $(jobSelector).each((i, el) => {
            let title = $(el).find('h3 a, .job-title a, .title a').first().text().trim();
            if (!title) title = $(el).find('a[title]').attr('title') || '';
            if (!title) return;
            if (!title.toLowerCase().includes('data')) return;
            const company = $(el).find('.company-name, .company, .org').first().text().trim();
            const location = $(el).find('.location, .address, .city').first().text().trim();
            const salary = $(el).find('.salary, .price, .money').first().text().trim();
            const experience = $(el).find('.experience, .exp, .year').first().text().trim();
            let url = $(el).find('h3 a, .job-title a').first().attr('href');
            if (url && !url.startsWith('http')) url = 'https://www.topcv.vn' + url;
            jobs.push({ title, company, location, salary, experience, url });
        });
        log(cfg.role, `Page ${pageNum}: found ${jobs.length} jobs`);
        return jobs;
    } catch (err) {
        log(cfg.role, `Error on page ${pageNum}: ${err.message}`, 'ERROR');
        if (retryCount < cfg.maxRetries) {
            log(cfg.role, `Retrying page ${pageNum} (attempt ${retryCount+1}/${cfg.maxRetries})...`);
            await page.waitForTimeout(cfg.retryDelay);
            return crawlPage(cfg, page, pageNum, retryCount+1);
        }
        return [];
    }
}

async function crawlRole(context, role) {
    const cfg = buildRoleConfig(role);
    ensureDir(BASE_CONFIG.outputDir);
    log(role, `=== START CRAWL JOB LIST FOR ROLE: ${role} ===`);
    const page = await context.newPage();
    let allJobsThisRun = [];
    try {
        const checkpoint = loadCheckpoint(cfg);
        let startPage = 1;
        const totalPages = await getTotalPages(cfg, page, cfg.baseUrl);
        if (checkpoint && checkpoint.totalPages === totalPages && checkpoint.role === role) {
            startPage = checkpoint.lastPage + 1;
            log(role, `Resume from checkpoint: starting page ${startPage}`);
        } else {
            if (checkpoint) log(role, 'Checkpoint ignored', 'WARN');
            log(role, `Fresh crawl from page 1 for role ${role}`);
        }
        for (let pageNum = startPage; pageNum <= totalPages; pageNum++) {
            const jobs = await crawlPage(cfg, page, pageNum);
            allJobsThisRun.push(...jobs);
            saveCheckpoint(cfg, pageNum, totalPages, allJobsThisRun);
            await page.waitForTimeout(cfg.waitBetweenPages);
        }
        const uniqueThisRun = [];
        const urlSet = new Set();
        for (const job of allJobsThisRun) {
            const normUrl = normalizeUrl(job.url);
            if (normUrl && !urlSet.has(normUrl)) {
                urlSet.add(normUrl);
                uniqueThisRun.push(job);
            }
        }
        log(role, `Raw: ${allJobsThisRun.length}, Unique: ${uniqueThisRun.length}`);
        const result = upsertJobs(uniqueThisRun, BASE_CONFIG.finalOutput, role);
        if (result.error) {
            log(role, `Upsert failed: ${result.error}`, 'ERROR');
            return { role, status: 'failed', error: result.error };
        }
        log(role, `Upsert: +${result.added} new jobs (total ${result.total})`);
        if (fs.existsSync(cfg.checkpointFile)) fs.unlinkSync(cfg.checkpointFile);
        return { role, status: 'success', added: result.added, total: result.total };
    } catch (err) {
        log(role, `Fatal error: ${err.message}`, 'ERROR');
        return { role, status: 'failed', error: err.message };
    } finally {
        await page.close();
        log(role, `Page closed for role: ${role}`);
        log(role, `=== CRAWL FINISHED FOR ROLE: ${role} ===`);
    }
}

(async () => {
    console.log(`=== START MULTI-ROLE CRAWL: ${ROLES.join(', ')} ===`);
    const browser = await chromium.launch({ headless: BASE_CONFIG.headless });
    const context = await browser.newContext({
        userAgent: BASE_CONFIG.userAgent,
        viewport: BASE_CONFIG.viewport,
        locale: BASE_CONFIG.locale,
    });
    const results = [];
    try {
        for (let i = 0; i < ROLES.length; i++) {
            const role = ROLES[i];
            console.log(`\n[${i+1}/${ROLES.length}] Crawling role: ${role}...`);
            const result = await crawlRole(context, role);
            results.push(result);
            if (i < ROLES.length - 1) {
                await new Promise(r => setTimeout(r, BASE_CONFIG.waitBetweenRoles));
            }
        }
    } finally {
        await browser.close();
        console.log('\nBrowser closed.');
    }
    const succeeded = results.filter(r => r.status === 'success');
    const failed = results.filter(r => r.status === 'failed');
    console.log('\n=== SUMMARY ===');
    for (const r of succeeded) console.log(`  ✓ ${r.role}: +${r.added} new jobs (total ${r.total})`);
    for (const r of failed) console.log(`  ✗ ${r.role}: FAILED — ${r.error}`);
    console.log(`\nSucceeded: ${succeeded.length}/${ROLES.length}, Failed: ${failed.length}/${ROLES.length}`);
    console.log('=== MULTI-ROLE CRAWL FINISHED ===');
    process.exit(failed.length > 0 ? 1 : 0);
})();