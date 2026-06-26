// crawlers/version_demo/list_crawler_itviet2_fixed.js
const axios = require('axios');
const cheerio = require('cheerio');
const fs = require('fs');
const path = require('path');

// ==================== XÁC ĐỊNH ROOT DỰ ÁN ====================
// File này nằm ở crawlers/version_demo/, root là 2 cấp lên: ../../
const PROJECT_ROOT = path.resolve(__dirname, '../../');

// ==================== CẤU HÌNH ====================
const CONFIG = {
    baseUrl: 'https://itviec.com',
    roles: ['data-engineer', 'data-analyst', 'data-scientist', 'business-intelligence'], // Sửa lại đúng slug ITviec
    outputDir: path.resolve(PROJECT_ROOT, 'logs/crawler'),
    rawDir: path.resolve(PROJECT_ROOT, 'data/bronze/itviec'),
    checkpointDir: path.resolve(PROJECT_ROOT, 'data/bronze/itviec'),
    finalOutput: path.resolve(PROJECT_ROOT, 'data/bronze/itviec_jobs_all.json'),
    maxPages: 10,
    maxRetries: 3,
    retryDelay: 5000,
    delayMin: 2500,
    delayMax: 5000,
    delayBetweenRoles: 8000,
    userAgents: [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
    ],
};

// ==================== TIỆN ÍCH ====================
function ensureDir(dir) {
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

function log(role, message, level = 'INFO') {
    const timestamp = new Date().toISOString();
    const logMsg = `[${timestamp}] [${level}] [${role}] ${message}`;
    console.log(logMsg);
    ensureDir(CONFIG.outputDir);
    fs.appendFileSync(path.join(CONFIG.outputDir, `itviec_${role}.log`), logMsg + '\n');
}

function randomUserAgent() {
    return CONFIG.userAgents[Math.floor(Math.random() * CONFIG.userAgents.length)];
}

function randomDelay() {
    const delay = CONFIG.delayMin + Math.random() * (CONFIG.delayMax - CONFIG.delayMin);
    return new Promise(resolve => setTimeout(resolve, delay));
}

function normalizeUrl(url) {
    if (!url) return null;
    const idx = url.indexOf('?');
    return idx === -1 ? url : url.substring(0, idx);
}

// ==================== HTTP FETCH ====================
async function fetchPage(url, role, retryCount = 0) {
    try {
        const response = await axios.get(url, {
            headers: {
                'User-Agent': randomUserAgent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8',
                'Referer': 'https://itviec.com/',
            },
            timeout: 15000,
        });
        return response.data;
    } catch (err) {
        const status = err.response ? err.response.status : 'NO_RESPONSE';
        log(role, `Fetch lỗi (status ${status}): ${err.message} — URL: ${url}`, 'WARN');
        if (retryCount < CONFIG.maxRetries) {
            log(role, `Retry (${retryCount + 1}/${CONFIG.maxRetries}) sau ${CONFIG.retryDelay / 1000}s...`);
            await new Promise(r => setTimeout(r, CONFIG.retryDelay));
            return fetchPage(url, role, retryCount + 1);
        }
        return null;
    }
}

// ==================== PARSE LISTING PAGE ====================
function parseListingPage(html) {
    const $ = cheerio.load(html);
    const jobs = [];
    const cards = $('div.job-card');
    if (cards.length === 0) {
        return { jobs: [], hasNextPage: false, notFound: true };
    }

    cards.each((i, el) => {
        const $card = $(el);
        const slug = $card.attr('data-search--job-selection-job-slug-value') || '';
        const $h3 = $card.find('h3').first();
        const title = $h3.text().trim();
        let detailUrl = $h3.attr('data-url') || '';
        if (!detailUrl && slug) detailUrl = `${CONFIG.baseUrl}/it-jobs/${slug}`;

        const company = $card.find('span.text-hover-underline a').first().text().trim();
        const workModel = $card.find('div.text-rich-grey.flex-shrink-0').first().text().trim();
        const location = $card.find('div.text-rich-grey.text-truncate').first().text().trim();
        const salaryText = $card.find('.salary').first().text().trim();
        const salaryHidden = /sign in/i.test(salaryText) || !salaryText;
        const skills = [];
        $card.find('a[href*="click_source=Skill"]').each((j, s) => {
            const skillText = $(s).text().trim();
            if (skillText) skills.push(skillText);
        });
        const postedText = $card.find('span.small-text').first().text().trim();

        if (!title || !slug) return;

        jobs.push({
            job_id: `itviec_${slug}`,
            source: 'ITviec',
            job_url: detailUrl,
            job_title: title,
            company_name: company,
            location: location,
            work_model: workModel,
            salary_hidden: salaryHidden,
            skills: skills,
            posted_text: postedText,
            collected_at: new Date().toISOString(),
        });
    });

    const hasNextPage = $('div.page.next a[rel="next"]').length > 0;
    return { jobs, hasNextPage, notFound: false };
}

// ==================== LƯU DỮ LIỆU ====================
function saveRawHtml(html, role, page) {
    const today = new Date().toISOString().slice(0, 10);
    const dir = path.join(CONFIG.rawDir, today, role);
    ensureDir(dir);
    fs.writeFileSync(path.join(dir, `listing_page${page}.html`), html, 'utf-8');
}

function appendJobsJsonl(jobs, role) {
    if (jobs.length === 0) return;
    const today = new Date().toISOString().slice(0, 10);
    const dir = path.join(CONFIG.rawDir, today);
    ensureDir(dir);
    const filepath = path.join(dir, `${role}.jsonl`);
    const lines = jobs.map(j => JSON.stringify(j)).join('\n') + '\n';
    fs.appendFileSync(filepath, lines);
    log(role, `Đã lưu ${jobs.length} jobs → ${filepath}`);
}

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

    const urlMap = new Map();
    for (const job of existingJobs) {
        const norm = normalizeUrl(job.job_url);
        if (norm) urlMap.set(norm, job);
    }

    let added = 0;
    for (const job of newJobs) {
        const norm = normalizeUrl(job.job_url);
        if (norm && !urlMap.has(norm)) {
            urlMap.set(norm, job);
            existingJobs.push(job);
            added++;
        }
    }

    fs.writeFileSync(filePath, JSON.stringify(existingJobs, null, 2));
    return { total: existingJobs.length, added };
}

// ==================== CHECKPOINT ====================
function checkpointPath(role) {
    return path.join(CONFIG.checkpointDir, `checkpoint_${role}.json`);
}

function saveCheckpoint(role, pageNum, jobsSoFar) {
    const checkpoint = { role, lastPage: pageNum, jobsCount: jobsSoFar.length, timestamp: Date.now() };
    ensureDir(CONFIG.checkpointDir);
    fs.writeFileSync(checkpointPath(role), JSON.stringify(checkpoint, null, 2));
}

function loadCheckpoint(role) {
    const p = checkpointPath(role);
    if (!fs.existsSync(p)) return null;
    try {
        return JSON.parse(fs.readFileSync(p, 'utf8'));
    } catch (e) {
        return null;
    }
}

function clearCheckpoint(role) {
    const p = checkpointPath(role);
    if (fs.existsSync(p)) fs.unlinkSync(p);
}

// ==================== CRAWL 1 ROLE ====================
async function crawlRole(role) {
    log(role, `=== START CRAWL LISTING FOR ROLE: ${role} ===`);

    const checkpoint = loadCheckpoint(role);
    let startPage = 1;
    if (checkpoint) {
        startPage = checkpoint.lastPage + 1;
        log(role, `Resume từ checkpoint: page ${startPage}`);
    }

    const allJobsThisRun = [];
    const seenIds = new Set();

    for (let pageNum = startPage; pageNum <= CONFIG.maxPages; pageNum++) {
        const url = pageNum === 1
            ? `${CONFIG.baseUrl}/it-jobs/${role}`
            : `${CONFIG.baseUrl}/it-jobs/${role}?page=${pageNum}`;

        log(role, `Listing page ${pageNum}: ${url}`);

        const html = await fetchPage(url, role);
        if (!html) {
            log(role, `Không fetch được trang ${pageNum}, dừng role này`, 'WARN');
            break;
        }

        saveRawHtml(html, role, pageNum);

        const { jobs: pageJobs, hasNextPage, notFound } = parseListingPage(html);

        if (notFound) {
            log(role, `Trang ${pageNum} không có job-card, dừng role '${role}'`, 'WARN');
            break;
        }

        const newJobs = pageJobs.filter(j => !seenIds.has(j.job_id));
        newJobs.forEach(j => seenIds.add(j.job_id));

        log(role, `Trang ${pageNum}: ${pageJobs.length} jobs (${newJobs.length} mới)`);
        allJobsThisRun.push(...newJobs);

        if (newJobs.length > 0) appendJobsJsonl(newJobs, role);

        saveCheckpoint(role, pageNum, allJobsThisRun);

        if (!hasNextPage) {
            log(role, `Hết trang cho role '${role}'`);
            break;
        }

        await randomDelay();
    }

    const { total, added } = upsertJobs(allJobsThisRun, CONFIG.finalOutput);
    log(role, `Upsert: +${added} job mới, tổng ${total} job trong ${CONFIG.finalOutput}`);

    clearCheckpoint(role);
    log(role, `=== CRAWL FINISHED FOR ROLE: ${role} ===\n`);

    return { role, jobsFound: allJobsThisRun.length, added, total };
}

// ==================== KHỞI CHẠY ====================
(async () => {
    const args = process.argv.slice(2);
    const rolesIndex = args.indexOf('--roles');
    const rolesArg = rolesIndex !== -1 ? args[rolesIndex + 1] : 'all';
    const roles = rolesArg === 'all' ? CONFIG.roles : rolesArg.split(',').map(r => r.trim());

    console.log(`=== ITVIEC LISTING CRAWLER — roles: ${roles.join(', ')} ===`);
    ensureDir(CONFIG.outputDir);
    ensureDir(CONFIG.rawDir);
    ensureDir(CONFIG.checkpointDir);
    ensureDir(path.dirname(CONFIG.finalOutput));

    const results = [];
    for (let i = 0; i < roles.length; i++) {
        const role = roles[i];
        console.log(`\n[${i + 1}/${roles.length}] Role: ${role}`);
        const result = await crawlRole(role);
        results.push(result);

        if (i < roles.length - 1) {
            await new Promise(r => setTimeout(r, CONFIG.delayBetweenRoles));
        }
    }

    console.log('\n=== SUMMARY ===');
    let totalAdded = 0;
    for (const r of results) {
        console.log(`  ${r.role}: found ${r.jobsFound}, +${r.added} new (total ${r.total})`);
        totalAdded += r.added;
    }
    console.log(`\nTổng job mới: ${totalAdded}`);
    console.log('=== ITVIEC LISTING CRAWL FINISHED ===');
})();