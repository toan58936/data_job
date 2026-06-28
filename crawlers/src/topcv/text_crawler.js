const { chromium } = require('playwright-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
const fs = require('fs');
const path = require('path');
const cheerio = require('cheerio');

chromium.use(StealthPlugin());

// ==================== CẤU HÌNH ====================
// Đường dẫn mới cho TopCV
const ROOT = path.resolve(__dirname, '../../../');
const BRONZE_TOPCV_DIR = path.resolve(ROOT, 'data/bronze/topcv');
const LOG_DIR = path.resolve(ROOT, 'logs/crawler/topcv');

const CONFIG = {
    inputFile: path.resolve(BRONZE_TOPCV_DIR, 'jobs_all.json'),           // ← ĐÃ SỬA
    outputFile: path.resolve(BRONZE_TOPCV_DIR, 'job_text_final.json'),    // ← ĐÃ SỬA
    checkpointFile: path.resolve(BRONZE_TOPCV_DIR, 'checkpoint_text.json'), // ← ĐÃ SỬA
    maxRetries: 2,
    retryDelay: 5000,
    delayBetweenJobs: 7000,
    headless: true,
    launchArgs: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-blink-features=AutomationControlled',
        '--disable-dev-shm-usage',
    ],
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
    viewport: { width: 1280, height: 800 },
    locale: 'vi-VN',
    navigationTimeout: 60000,
    selectorTimeout: 20000,
};

// Danh sách ID job brand đã biết bị thiếu description (cần xử lý đặc biệt)
const BRAND_IDS_NEED_FIX = [
    '905982', '2191679', '2185054', '2179631', '2135980', '2184635', '2143548', '2177773'
];

// ==================== TIỆN ÍCH ====================
function ensureDir(dir) {
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

function log(message, level = 'INFO') {
    const timestamp = new Date().toISOString();
    const logMsg = `[${timestamp}] [${level}] ${message}`;
    console.log(logMsg);
    ensureDir(LOG_DIR);
    const logFile = path.join(LOG_DIR, 'crawl_text.log');
    fs.appendFileSync(logFile, logMsg + '\n');
}

function normalizeUrl(url) {
    if (!url) return null;
    const idx = url.indexOf('?');
    return idx === -1 ? url : url.substring(0, idx);
}

// ==================== KIỂM TRA TRANG HỢP LỆ (giữ nguyên) ====================
function isPageValid(response, finalUrl, originalUrl, html) {
    if (response && response.status() !== 200) {
        log(`HTTP status ${response.status()} for ${originalUrl}`, 'WARN');
        return false;
    }
    if (normalizeUrl(finalUrl) !== normalizeUrl(originalUrl)) {
        log(`Redirect detected: ${originalUrl} -> ${finalUrl}`, 'WARN');
        return false;
    }

    const headMatch = html.match(/<head[\s\S]*?<\/head>/i);
    const headHtml = headMatch ? headMatch[0].toLowerCase() : '';
    const headPatterns = [
        'just a moment', 'cf-challenge', 'challenge-platform',
        'id="challenge-form"', 'id="cf-wrapper"'
    ];
    for (const pattern of headPatterns) {
        if (headHtml.includes(pattern)) {
            log(`Cloudflare challenge detected (pattern: "${pattern}") for ${originalUrl}`, 'WARN');
            return false;
        }
    }

    const titleMatch = headHtml.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
    const pageTitle = titleMatch ? titleMatch[1].toLowerCase() : '';
    const errorTitles = ['403', '404', 'not found', 'forbidden', 'access denied'];
    for (const t of errorTitles) {
        if (pageTitle.includes(t)) {
            log(`Error title detected: "${pageTitle}" for ${originalUrl}`, 'WARN');
            return false;
        }
    }
    return true;
}

// ==================== LẤY TEXT THEO HEADING (CHO BRAND) ====================
function extractByHeadings($, contentSelector, headingKeyword) {
    const $content = $(contentSelector).length ? $(contentSelector) : $('main, .job-detail, .container');
    let result = '';
    $content.find('h2, h3').each((i, el) => {
        const text = $(el).text().toLowerCase().trim();
        if (text.includes(headingKeyword)) {
            let next = $(el).next();
            let content = [];
            while (next.length && !next.is('h2, h3')) {
                content.push(next.text().trim());
                next = next.next();
            }
            result = content.join('\n').replace(/\s+/g, ' ').trim();
            return false;
        }
    });
    return result;
}

// ==================== FALLBACK ĐẶC BIỆT CHO BRAND BỊ THIẾU DESCRIPTION ====================
function extractBrandDescription($, html) {
    let found = '';
    $('h1, h2, h3, h4').each((_, el) => {
        const text = $(el).text().toLowerCase().trim();
        if (text.includes('mô tả') || text.includes('mo ta') || text.includes('job description')) {
            let next = $(el).next();
            const parts = [];
            while (next.length && !next.is('h1,h2,h3,h4')) {
                parts.push(next.text().trim());
                next = next.next();
            }
            const val = parts.join('\n').replace(/\s+/g, ' ').trim();
            if (val.length > 50) { found = val; return false; }
        }
    });
    if (found) return found;

    const brandSelectors = [
        '#box-job-information-detail',
        '.job-description-content',
        '.job-detail__description',
        '[class*="description"]',
        '[class*="job-content"]',
        '[class*="detail-content"]',
        '.tab-content',
        '.brand-job-detail',
    ];
    for (const sel of brandSelectors) {
        const el = $(sel).first();
        if (el.length) {
            const clone = el.clone();
            clone.find('*').filter((_, n) => {
                const t = $(n).text().toLowerCase();
                return t.startsWith('yêu cầu ứng viên') || t.startsWith('quyền lợi');
            }).remove();
            const val = clone.text().replace(/\s+/g, ' ').trim();
            if (val.length > 50) return val;
        }
    }

    const mainContainer = $('main, .container, .job-detail, #content, .content-main').first();
    if (mainContainer.length) {
        const fullText = mainContainer.text();
        const cutIndex = fullText.search(/yêu cầu ứng viên/i);
        if (cutIndex > 100) {
            const candidate = fullText.slice(0, cutIndex).trim();
            const val = candidate.slice(Math.max(0, candidate.length - 2000)).replace(/\s+/g, ' ').trim();
            if (val.length > 100) return val;
        }
    }

    $('nav, footer, header, script, style, [class*="menu"], [class*="sidebar"]').remove();
    const pageText = $('body').text().replace(/\s+/g, ' ').trim();
    const cutIdx = pageText.search(/yêu cầu ứng viên/i);
    if (cutIdx > 200) {
        const val = pageText.slice(Math.max(0, cutIdx - 3000), cutIdx).replace(/\s+/g, ' ').trim();
        if (val.length > 100) return val;
    }

    return '';
}

// ==================== CRAWL JOB TEXT (THƯỜNG) ====================
async function crawlJobText(page, jobUrl, retryCount = 0) {
    log(`Crawling: ${jobUrl}`);
    let response = null;
    try {
        response = await page.goto(jobUrl, { waitUntil: 'commit', timeout: CONFIG.navigationTimeout });
        await page.waitForSelector('h1, .job-title, .title-detail', { timeout: CONFIG.selectorTimeout });
        await page.waitForTimeout(3000);

        const html = await page.content();
        const finalUrl = page.url();

        if (!isPageValid(response, finalUrl, jobUrl, html)) {
            log(`Page invalid for ${jobUrl}, skipping`, 'WARN');
            return null;
        }

        const $ = cheerio.load(html);
        const isStandard = $('#mo-ta-cong-viec, .requirement, .benefit').length > 0;

        let idMatch = jobUrl.match(/[-\/](?:j?)(\d+)\.html/);
        if (!idMatch) idMatch = jobUrl.match(/(\d+)\.html/);
        const id = idMatch ? idMatch[1] : null;

        let description = '', requirements = '', benefits = '';

        if (isStandard) {
            description = $('#mo-ta-cong-viec, .job-description').first().text().trim();
            requirements = $('.requirement').first().text().trim();
            benefits = $('.benefit').first().text().trim();
        } else {
            const contentSelector = '#box-job-information-detail, .job-detail, main, .container';
            description = extractByHeadings($, contentSelector, 'mô tả công việc');
            requirements = extractByHeadings($, contentSelector, 'yêu cầu ứng viên');
            benefits = extractByHeadings($, contentSelector, 'quyền lợi');
        }

        description = description.replace(/\s+/g, ' ').trim();
        requirements = requirements.replace(/\s+/g, ' ').trim();
        benefits = benefits.replace(/\s+/g, ' ').trim();

        if (id && BRAND_IDS_NEED_FIX.includes(id) && !description) {
            log(`Brand ${id} has empty description, trying advanced fallback...`, 'INFO');
            description = extractBrandDescription($, html);
            if (description) {
                log(`  -> Retrieved ${description.length} chars via advanced fallback`);
            } else {
                log(`  -> Still empty after advanced fallback`, 'WARN');
            }
        }

        return { id, description, requirements, benefits };
    } catch (err) {
        log(`Error on ${jobUrl}: ${err.message}`, 'ERROR');
        if (retryCount < CONFIG.maxRetries) {
            log(`Retrying (${retryCount + 1}/${CONFIG.maxRetries}) in ${CONFIG.retryDelay/1000}s...`);
            await new Promise(resolve => setTimeout(resolve, CONFIG.retryDelay));
            return crawlJobText(page, jobUrl, retryCount + 1);
        }
        log(`Failed after ${CONFIG.maxRetries} retries.`, 'ERROR');
        return null;
    }
}

// ==================== KHỞI CHẠY (VỚI CHECKPOINT) ====================
(async () => {
    ensureDir(LOG_DIR);
    ensureDir(BRONZE_TOPCV_DIR);
    log('=== START CRAWL JOB TEXT (FINAL VERSION) ===');
    log(`Mode: ${CONFIG.headless ? 'Headless' : 'Headed'}`);

    if (!fs.existsSync(CONFIG.inputFile)) {
        log(`Input file not found: ${CONFIG.inputFile}`, 'ERROR');
        process.exit(1);
    }
    const allJobs = JSON.parse(fs.readFileSync(CONFIG.inputFile, 'utf8'));
    log(`Total jobs in list: ${allJobs.length}`);

    let existingMap = new Map();
    if (fs.existsSync(CONFIG.outputFile)) {
        try {
            const existing = JSON.parse(fs.readFileSync(CONFIG.outputFile, 'utf8'));
            for (const item of existing) {
                const norm = normalizeUrl(item.url);
                if (norm) existingMap.set(norm, item);
            }
            log(`Loaded ${existingMap.size} existing entries from ${CONFIG.outputFile}`);
        } catch(e) {
            log('Failed to parse existing output, starting fresh', 'WARN');
        }
    }

    const jobsToCrawl = allJobs.filter(job => {
        const norm = normalizeUrl(job.url);
        return !existingMap.has(norm);
    });
    log(`Jobs already crawled: ${allJobs.length - jobsToCrawl.length}`);
    log(`Jobs to crawl: ${jobsToCrawl.length}`);

    if (jobsToCrawl.length === 0) {
        log('All jobs already crawled. Exiting.');
        process.exit(0);
    }

    let pendingUrls = jobsToCrawl.map(job => normalizeUrl(job.url));
    let startIndex = 0;
    if (fs.existsSync(CONFIG.checkpointFile)) {
        try {
            const cp = JSON.parse(fs.readFileSync(CONFIG.checkpointFile, 'utf8'));
            if (cp.pendingUrls && Array.isArray(cp.pendingUrls)) {
                const cpSet = new Set(cp.pendingUrls);
                pendingUrls = pendingUrls.filter(url => cpSet.has(url));
                const lastUrl = cp.lastUrl;
                const idx = pendingUrls.findIndex(url => url === normalizeUrl(lastUrl));
                if (idx !== -1) startIndex = idx + 1;
                log(`Resume from checkpoint: lastUrl=${lastUrl}, remaining=${pendingUrls.length}`);
            }
        } catch(e) {
            log('Failed to parse checkpoint', 'WARN');
        }
    }

    const browser = await chromium.launch({ headless: CONFIG.headless, args: CONFIG.launchArgs });
    const context = await browser.newContext({
        userAgent: CONFIG.userAgent,
        viewport: CONFIG.viewport,
        locale: CONFIG.locale,
    });
    const page = await context.newPage();
    await page.addInitScript(() => {
        Object.defineProperty(navigator, 'webdriver', { get: () => false });
    });

    let results = [];
    if (fs.existsSync(CONFIG.outputFile)) {
        try {
            const old = JSON.parse(fs.readFileSync(CONFIG.outputFile, 'utf8'));
            results.push(...old);
        } catch(e) {}
    }

    for (let i = startIndex; i < pendingUrls.length; i++) {
        const targetUrl = pendingUrls[i];
        const originalJob = allJobs.find(job => normalizeUrl(job.url) === targetUrl);
        if (!originalJob) {
            log(`Cannot find job for URL ${targetUrl}`, 'WARN');
            continue;
        }

        log(`Progress: ${i+1}/${pendingUrls.length} - ${originalJob.title} (${originalJob.company || 'unknown'})`);
        const textData = await crawlJobText(page, originalJob.url);
        if (textData) {
            results.push({
                id: textData.id,
                url: originalJob.url,
                normalized_url: normalizeUrl(originalJob.url),
                title: originalJob.title,
                description: textData.description,
                requirements: textData.requirements,
                benefits: textData.benefits,
                crawled_at: new Date().toISOString()
            });
        } else {
            log(`Failed to get text for ${originalJob.url}`, 'WARN');
        }

        const remaining = pendingUrls.slice(i + 1);
        fs.writeFileSync(CONFIG.checkpointFile, JSON.stringify({ lastUrl: originalJob.url, pendingUrls: remaining }, null, 2));
        fs.writeFileSync(CONFIG.outputFile, JSON.stringify(results, null, 2));

        const delay = CONFIG.delayBetweenJobs + Math.random() * 5000;
        log(`Waiting ${Math.round(delay/1000)} seconds before next job...`);
        await new Promise(resolve => setTimeout(resolve, delay));
    }

    await browser.close();
    if (fs.existsSync(CONFIG.checkpointFile)) fs.unlinkSync(CONFIG.checkpointFile);
    log(`Final saved to ${CONFIG.outputFile} with ${results.length} entries`);
    log('=== FINISHED ===');
})();