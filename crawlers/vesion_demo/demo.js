const { chromium } = require('playwright-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
const fs = require('fs');
const path = require('path');
const cheerio = require('cheerio');

chromium.use(StealthPlugin());

// ==================== CẤU HÌNH ====================
const CONFIG = {
    inputFile: './output/jobs_all.json',
    outputFile: './output/job_text.json',
    checkpointFile: './output/checkpoint_text.json',
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

// ==================== TIỆN ÍCH ====================
function ensureDir(dir) {
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

function log(message, level = 'INFO') {
    const timestamp = new Date().toISOString();
    const logMsg = `[${timestamp}] [${level}] ${message}`;
    console.log(logMsg);
    ensureDir('./output');
    fs.appendFileSync('./output/crawl_text.log', logMsg + '\n');
}

function normalizeUrl(url) {
    if (!url) return null;
    const idx = url.indexOf('?');
    return idx === -1 ? url : url.substring(0, idx);
}

// ==================== HÀM KIỂM TRA TRANG HỢP LỆ ====================
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

// ==================== HÀM LẤY TEXT THEO HEADING (BRAND) ====================
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

// ==================== HÀM CRAWL TEXT ====================
async function crawlJobText(jobUrl, retryCount = 0) {
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

    let response = null;
    try {
        response = await page.goto(jobUrl, { waitUntil: 'commit', timeout: CONFIG.navigationTimeout });
        await page.waitForSelector('h1, .job-title, .title-detail', { timeout: CONFIG.selectorTimeout });
        await page.waitForTimeout(3000);

        const html = await page.content();
        const finalUrl = page.url();
        await browser.close();

        if (!isPageValid(response, finalUrl, jobUrl, html)) {
            log(`Page invalid for ${jobUrl}, skipping`, 'WARN');
            return null;
        }

        const $ = cheerio.load(html);
        
        // ✅ THÊM DÒNG NÀY: xác định loại trang
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

        // ✅ BỔ SUNG ID VÀO KẾT QUẢ
        return { id, description, requirements, benefits };
    } catch (err) {
        log(`Error on ${jobUrl}: ${err.message}`, 'ERROR');
        await browser.close();
        if (retryCount < CONFIG.maxRetries) {
            log(`Retrying (${retryCount + 1}/${CONFIG.maxRetries}) in ${CONFIG.retryDelay/1000}s...`);
            await new Promise(resolve => setTimeout(resolve, CONFIG.retryDelay));
            return crawlJobText(jobUrl, retryCount + 1);
        }
        log(`Failed after ${CONFIG.maxRetries} retries.`, 'ERROR');
        return null;
    }
}

// ==================== KHỞI CHẠY ====================
(async () => {
    ensureDir('./output');
    log('=== START CRAWL JOB TEXT (description, requirements, benefits) ===');
    log(`Mode: ${CONFIG.headless ? 'Headless' : 'Headed'}`);

    if (!fs.existsSync(CONFIG.inputFile)) {
        log(`Input file not found: ${CONFIG.inputFile}`, 'ERROR');
        process.exit(1);
    }
    const allJobs = JSON.parse(fs.readFileSync(CONFIG.inputFile, 'utf8'));
    log(`Total jobs in list: ${allJobs.length}`);

    // Đọc kết quả đã crawl text (nếu có) để resume
    let existingMap = new Map(); // key = normalized_url, value = object
    if (fs.existsSync(CONFIG.outputFile)) {
        try {
            const existing = JSON.parse(fs.readFileSync(CONFIG.outputFile, 'utf8'));
            for (const item of existing) {
                const norm = normalizeUrl(item.url);
                if (norm) existingMap.set(norm, item);
            }
            log(`Loaded ${existingMap.size} existing text entries`);
        } catch(e) {
            log('Failed to parse existing output, starting fresh', 'WARN');
        }
    }

    // Lọc các job chưa có text
    const jobsToCrawl = allJobs.filter(job => {
        const norm = normalizeUrl(job.url);
        return !existingMap.has(norm);
    });
    log(`Jobs already have text: ${allJobs.length - jobsToCrawl.length}`);
    log(`Jobs to crawl: ${jobsToCrawl.length}`);

    if (jobsToCrawl.length === 0) {
        log('All jobs already have text. Exiting.');
        process.exit(0);
    }

    // Load checkpoint (dạng pending URLs)
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

    // Kết quả sẽ là mảng chứa tất cả các entry (cũ + mới)
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

        log(`Progress: ${i+1}/${pendingUrls.length} - ${originalJob.title}`);
        const textData = await crawlJobText(originalJob.url);
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
            // Cập nhật checkpoint và file tạm sau mỗi job
            const remaining = pendingUrls.slice(i + 1);
            fs.writeFileSync(CONFIG.checkpointFile, JSON.stringify({ lastUrl: originalJob.url, pendingUrls: remaining }, null, 2));
            fs.writeFileSync(CONFIG.outputFile, JSON.stringify(results, null, 2));
        } else {
            log(`Failed to get text for ${originalJob.url}`, 'WARN');
        }

        const delay = CONFIG.delayBetweenJobs + Math.random() * 5000;
        log(`Waiting ${Math.round(delay/1000)} seconds before next job...`);
        await new Promise(resolve => setTimeout(resolve, delay));
    }

    await browser.close();
    if (fs.existsSync(CONFIG.checkpointFile)) fs.unlinkSync(CONFIG.checkpointFile);
    log(`Final saved to ${CONFIG.outputFile} with ${results.length} entries`);
    log('=== FINISHED ===');
})();