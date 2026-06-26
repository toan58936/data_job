const { chromium } = require('playwright-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
const fs = require('fs');
const path = require('path');
const cheerio = require('cheerio');

chromium.use(StealthPlugin());

// ==================== CẤU HÌNH ====================

const CONFIG = {
    inputFile: path.resolve(__dirname, '../../data/bronze/jobs_all.json'),
    outputDir: path.resolve(__dirname, '../../logs/crawler'),
    outputFile: path.resolve(__dirname, '../../data/bronze/jobs_detail.json'),
    checkpointFile: path.resolve(__dirname, '../../data/bronze/checkpoint_detail.json'),
    // ... giữ nguyên
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
    ensureDir(CONFIG.outputDir);
    const logFile = path.join(CONFIG.outputDir, 'crawl_detail.log');
    fs.appendFileSync(logFile, logMsg + '\n');
}

function normalizeUrl(url) {
    if (!url) return null;
    const idx = url.indexOf('?');
    return idx === -1 ? url : url.substring(0, idx);
}

// ==================== HÀM KIỂM TRA TRANG HỢP LỆ ====================
function isPageValid(response, finalUrl, originalUrl, html) {
    // Kiểm tra HTTP status
    if (response && response.status() !== 200) {
        log(`HTTP status ${response.status()} for ${originalUrl}`, 'WARN');
        return false;
    }
    // Kiểm tra redirect (so sánh URL chuẩn hóa)
    if (normalizeUrl(finalUrl) !== normalizeUrl(originalUrl)) {
        log(`Redirect detected: ${originalUrl} -> ${finalUrl}`, 'WARN');
        return false;
    }

    // ── FIX: Chỉ kiểm tra <head> thay vì scan toàn bộ HTML ────────────────
    // Vấn đề cũ: scan lowerHtml.includes('captcha') trên toàn bộ HTML
    // → False positive vì TopCV có thể chứa từ "captcha" trong nội dung job,
    //   script analytics, hoặc footer — không liên quan đến Cloudflare challenge.
    //
    // Cloudflare challenge thật sự luôn nằm trong <title> và <meta> của <head>,
    // KHÔNG bao giờ lẫn vào content thông thường.
    // Các dấu hiệu Cloudflare challenge thực tế:
    //   <title>Just a moment...</title>
    //   <meta name="cf-challenge" ...>
    //   <div id="cf-wrapper"> hoặc id="challenge-form"
    //
    // Cách fix: chỉ extract phần <head> (ngắn, ~2KB) và kiểm tra trong đó,
    // kết hợp với selector CF-specific thay vì text tự do.
    const headMatch = html.match(/<head[\s\S]*?<\/head>/i);
    const headHtml = headMatch ? headMatch[0].toLowerCase() : '';

    // Chỉ check các pattern CỐ ĐỊNH của Cloudflare/bot-wall trong <head>
    const headPatterns = [
        'just a moment',       // Cloudflare: <title>Just a moment...</title>
        'cf-challenge',        // Cloudflare: <meta name="cf-challenge">
        'challenge-platform',  // Cloudflare Turnstile
        'id="challenge-form"', // Cloudflare challenge form
        'id="cf-wrapper"',     // Cloudflare wrapper
    ];
    for (const pattern of headPatterns) {
        if (headHtml.includes(pattern)) {
            log(`Cloudflare challenge detected (pattern: "${pattern}") for ${originalUrl}`, 'WARN');
            return false;
        }
    }

    // Kiểm tra HTTP error page (404/403) qua title — không scan body
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

// ==================== HÀM LẤY GIÁ TRỊ THEO LABEL ====================
function getValueByLabel($, labelText) {
    let $label = $(`strong:contains("${labelText}"), b:contains("${labelText}"), .label:contains("${labelText}"), [class*="label"]:contains("${labelText}"), .basic-information-item__data--label:contains("${labelText}")`).first();
    if ($label.length === 0) {
        $label = $(`*:contains("${labelText}")`).filter(function() {
            return $(this).text().trim() === labelText;
        }).first();
    }
    if ($label.length === 0) return '';

    let $value = $label.next();
    if ($value.length && $value.text().trim()) return $value.text().trim();

    const $parent = $label.closest('.basic-information-item, .info-item, .job-detail-info-item, [class*="item"]');
    if ($parent.length) {
        $value = $parent.find('.basic-information-item__data--value, .value, .info-value, .job-detail_info-section-content-value').first();
        if ($value.length) return $value.text().trim();
        let parentText = $parent.clone().children().remove().end().text().trim();
        if (parentText && parentText !== labelText) return parentText;
    }

    let fullText = $label.text().trim();
    if (fullText.includes(labelText)) {
        let value = fullText.replace(labelText, '').trim();
        if (value) return value;
    }
    return '';
}

// ==================== HÀM CRAWL CHI TIẾT JOB (cải tiến) ====================
async function crawlJobDetail(page, jobUrl, retryCount = 0) {
    log(`Crawling detail: ${jobUrl}`);
    let response = null;
    try {
        response = await page.goto(jobUrl, { waitUntil: 'commit', timeout: CONFIG.navigationTimeout });
        await page.waitForSelector('h1, .job-title, .title-detail', { timeout: CONFIG.selectorTimeout });
        await page.waitForTimeout(3000);

        const html = await page.content();
        const finalUrl = page.url();

        // Kiểm tra tính hợp lệ của trang
        if (!isPageValid(response, finalUrl, jobUrl, html)) {
            log(`Page invalid for ${jobUrl}, skipping`, 'WARN');
            return null;
        }

        const $ = cheerio.load(html);

        let idMatch = jobUrl.match(/[-\/](?:j?)(\d+)\.html/);
        if (!idMatch) idMatch = jobUrl.match(/(\d+)\.html/);
        const id = idMatch ? idMatch[1] : null;
        const normalizedUrl = jobUrl.indexOf('?') === -1 ? jobUrl : jobUrl.substring(0, jobUrl.indexOf('?'));

        let title = $('h1, .job-title, .title-detail').first().text().trim();
        const company = $('.company-name, .company, .org').first().text().trim();

        // Xử lý title bị lỗi (sẽ được fix sau, nhưng vẫn lấy)
        // Lưu ý: không gán luôn original_title ở đây vì chưa có map

        let salary = getValueByLabel($, 'Mức lương');
        // Loại bỏ giá trị sai "thị trường cho vị trí này"
        if (salary && salary.includes('thị trường cho vị trí này')) salary = '';

        const experience = getValueByLabel($, 'Kinh nghiệm');
        let deadlineRaw = getValueByLabel($, 'Hạn nộp');
        if (!deadlineRaw) deadlineRaw = getValueByLabel($, 'Hạn nộp hồ sơ');

        let location = getValueByLabel($, 'Địa điểm');
        // Nếu location bị "Địa điểm" hoặc rỗng, thử fallback nhẹ
        if (!location || location === 'Địa điểm' || location === 'Tìm kiếm' || /\{\{.*\}\}/.test(location)) {
            const $locationDiv = $('.job-detail_info-section-content-location, .job-detail-info-location, [class*="location"]').first();
            if ($locationDiv.length) location = $locationDiv.text().trim();
        }
        if (!location || location === 'Địa điểm' || location === 'Tìm kiếm' || /\{\{.*\}\}/.test(location)) {
            const $locationLink = $('a[title*="Hà Nội"]').first();
            if ($locationLink.length) location = $locationLink.text().trim();
        }
        // Không dùng regex bắt thành phố từ fullText (dễ sai) – để transform layer xử lý sau

        const level = getValueByLabel($, 'Cấp bậc');
        let numberOfHiresRaw = getValueByLabel($, 'Số lượng tuyển');
        const jobType = getValueByLabel($, 'Loại hình làm việc');

        let deadline = null;
        if (deadlineRaw) {
            const dateMatch = deadlineRaw.match(/(\d{2})[\/\-](\d{2})[\/\-](\d{4})/);
            if (dateMatch) {
                deadline = `${dateMatch[3]}-${dateMatch[2]}-${dateMatch[1]}`;
            } else {
                const fullText = $('body').text();
                const globalMatch = fullText.match(/Hạn nộp hồ sơ:\s*(\d{2})\/(\d{2})\/(\d{4})/);
                if (globalMatch) deadline = `${globalMatch[3]}-${globalMatch[2]}-${globalMatch[1]}`;
            }
        }

        let number_of_hires = null;
        const numMatch = numberOfHiresRaw.match(/\d+/);
        if (numMatch) number_of_hires = parseInt(numMatch[0]);

        let working_time = '';
        let location_detail = '';
        $('h2, h3').each((i, el) => {
            const text = $(el).text().toLowerCase().trim();
            if (text === 'thời gian làm việc' || text.includes('thời gian làm việc')) {
                let next = $(el).next();
                let content = [];
                while (next.length && !next.is('h2, h3')) {
                    content.push(next.text().trim());
                    next = next.next();
                }
                working_time = content.join(' ').replace(/\s+/g, ' ').trim();
            } else if (text === 'địa điểm làm việc' || text.includes('địa điểm làm việc')) {
                let next = $(el).next();
                let content = [];
                while (next.length && !next.is('h2, h3')) {
                    content.push(next.text().trim());
                    next = next.next();
                }
                location_detail = content.join(' ').replace(/\s+/g, ' ').trim();
            }
        });

        if (!working_time) {
            working_time = $('.working-time, [class*="working-time"]').first().text().trim();
        }
        if (!location_detail) {
            location_detail = $('.address-detail, [class*="address-detail"], .job-detail-info-section-content').filter(function() {
                return $(this).text().includes('Keangnam') || $(this).text().includes('Geleximco');
            }).first().text().trim();
        }

        // Fallback location nếu vẫn rỗng và có location_detail (ưu tiên lấy từ chi tiết)
        if ((!location || location === 'Địa điểm') && location_detail) {
            // Thử lấy tên thành phố từ location_detail (có thể tách sau)
            const cityMatch = location_detail.match(/(Hà Nội|Hồ Chí Minh|Đà Nẵng|Hải Phòng|Cần Thơ)/);
            if (cityMatch) location = cityMatch[1];
        }

        return {
            id,
            url: jobUrl,
            normalized_url: normalizedUrl,
            title,
            company,
            salary,
            location,
            experience,
            deadline,
            level,
            number_of_hires,
            job_type: jobType,
            working_time,
            location_detail,
            crawled_at: new Date().toISOString()
        };
    } catch (err) {
        log(`Error on ${jobUrl}: ${err.message}`, 'ERROR');
        if (retryCount < CONFIG.maxRetries) {
            log(`Retrying (${retryCount + 1}/${CONFIG.maxRetries}) in ${CONFIG.retryDelay/1000}s...`);
            await new Promise(resolve => setTimeout(resolve, CONFIG.retryDelay));
            return crawlJobDetail(page, jobUrl, retryCount + 1);
        }
        log(`Failed after ${CONFIG.maxRetries} retries.`, 'ERROR');
        return null;
    }
}

// ==================== CHECKPOINT DỰA TRÊN URL (cải tiến) ====================
function saveCheckpointByUrl(lastUrl, pendingUrls) {
    const checkpoint = {
        lastUrl: lastUrl,
        pendingUrls: pendingUrls,
        timestamp: Date.now()
    };
    fs.writeFileSync(CONFIG.checkpointFile, JSON.stringify(checkpoint, null, 2));
    log(`Checkpoint saved: lastUrl = ${lastUrl}, remaining ${pendingUrls.length} jobs`);
}

function loadCheckpointByUrl() {
    if (fs.existsSync(CONFIG.checkpointFile)) {
        try {
            return JSON.parse(fs.readFileSync(CONFIG.checkpointFile, 'utf8'));
        } catch(e) {
            log('Failed to parse checkpoint file', 'WARN');
            return null;
        }
    }
    return null;
}

function upsertJob(newJob, filePath) {
    let existingJobs = [];
    if (fs.existsSync(filePath)) {
        try {
            existingJobs = JSON.parse(fs.readFileSync(filePath, 'utf8'));
        } catch(e) {
            log(`Failed to parse existing file: ${e.message}`, 'WARN');
        }
    }
    const normUrl = normalizeUrl(newJob.url);
    const existingIndex = existingJobs.findIndex(job => normalizeUrl(job.url) === normUrl);
    if (existingIndex !== -1) {
        existingJobs[existingIndex] = { ...existingJobs[existingIndex], ...newJob };
        log(`Updated existing job: ${newJob.title} (${newJob.id})`);
    } else {
        existingJobs.push(newJob);
        log(`Added new job: ${newJob.title} (${newJob.id})`);
    }
    fs.writeFileSync(filePath, JSON.stringify(existingJobs, null, 2));
    return existingJobs.length;
}

// ==================== KHỞI CHẠY (cải tiến checkpoint theo URL) ====================
(async () => {
    ensureDir(CONFIG.outputDir);
    log('=== START CRAWL ALL JOB DETAILS (IMPROVED - VALIDATION + URL CHECKPOINT) ===');
    log(`Mode: ${CONFIG.headless ? 'Headless' : 'Headed'}`);

    if (!fs.existsSync(CONFIG.inputFile)) {
        log(`Input file not found: ${CONFIG.inputFile}`, 'ERROR');
        process.exit(1);
    }
    const allJobsFromList = JSON.parse(fs.readFileSync(CONFIG.inputFile, 'utf8'));
    log(`Total jobs in list: ${allJobsFromList.length}`);

    // Map original_title theo normalized_url
    const originalTitleMap = new Map();
    for (const job of allJobsFromList) {
        originalTitleMap.set(normalizeUrl(job.url), job.title);
    }

    // Đọc danh sách job đã crawl detail
    let existingDetailMap = new Map();
    if (fs.existsSync(CONFIG.outputFile)) {
        try {
            const existingDetails = JSON.parse(fs.readFileSync(CONFIG.outputFile, 'utf8'));
            for (const job of existingDetails) {
                const normUrl = normalizeUrl(job.url);
                if (normUrl) existingDetailMap.set(normUrl, job);
            }
            log(`Loaded ${existingDetailMap.size} existing detail jobs`);
        } catch(e) {
            log(`Failed to parse existing detail file`, 'WARN');
        }
    }

    // Danh sách job cần crawl (chưa có detail) – lưu dưới dạng URL
    let pendingUrls = allJobsFromList
        .filter(job => !existingDetailMap.has(normalizeUrl(job.url)))
        .map(job => normalizeUrl(job.url));
    log(`Jobs already crawled: ${allJobsFromList.length - pendingUrls.length}`);
    log(`Jobs to crawl: ${pendingUrls.length}`);

    if (pendingUrls.length === 0) {
        log('All jobs already have detail. Exiting.');
        process.exit(0);
    }

    // Khôi phục checkpoint
    const checkpoint = loadCheckpointByUrl();
    let remainingUrls = pendingUrls;
    let startUrl = null;

    if (checkpoint && checkpoint.pendingUrls && Array.isArray(checkpoint.pendingUrls)) {
        const checkpointSet = new Set(checkpoint.pendingUrls);
        remainingUrls = pendingUrls.filter(url => checkpointSet.has(url));
        startUrl = checkpoint.lastUrl;
        log(`Resume from checkpoint: lastUrl = ${startUrl}, remaining ${remainingUrls.length} jobs`);
    } else {
        log('Starting fresh crawl');
        if (fs.existsSync(CONFIG.checkpointFile)) fs.unlinkSync(CONFIG.checkpointFile);
    }

    // Tìm index bắt đầu
    let startIndex = 0;
    if (startUrl) {
        const idx = remainingUrls.findIndex(url => url === normalizeUrl(startUrl));
        if (idx !== -1) startIndex = idx + 1;
    }

    // Khởi tạo browser
    const browser = await chromium.launch({
        headless: CONFIG.headless,
        args: CONFIG.launchArgs,
    });
    const context = await browser.newContext({
        userAgent: CONFIG.userAgent,
        viewport: CONFIG.viewport,
        locale: CONFIG.locale,
    });
    const page = await context.newPage();

    await page.addInitScript(() => {
        Object.defineProperty(navigator, 'webdriver', { get: () => false });
    });

    try {
        for (let i = startIndex; i < remainingUrls.length; i++) {
            const targetUrl = remainingUrls[i];
            const originalJob = allJobsFromList.find(job => normalizeUrl(job.url) === targetUrl);
            if (!originalJob) {
                log(`Cannot find original job for URL ${targetUrl}`, 'WARN');
                continue;
            }

            log(`Progress: ${i+1}/${remainingUrls.length} - ${originalJob.title} (${originalJob.company})`);

            const detail = await crawlJobDetail(page, originalJob.url);
            if (detail) {
                // Fix title nếu bị lỗi (Tin tuyển dụng, rỗng, trùng company, domain)
                const fixedTitle = detail.title;
                if (fixedTitle === 'Tin tuyển dụng' || fixedTitle === '' || fixedTitle === detail.company ||
                    fixedTitle.includes('topcv.vn') || fixedTitle.includes('www.topcv.vn')) {
                    const originalTitle = originalTitleMap.get(normalizeUrl(originalJob.url));
                    if (originalTitle && originalTitle !== fixedTitle) {
                        log(`Fixing title for job ${detail.id}: "${fixedTitle}" -> "${originalTitle}"`);
                        detail.title = originalTitle;
                    }
                }
                // Nếu salary vẫn rỗng, giữ nguyên (transform sau)
                detail.original_title = originalJob.title;
                upsertJob(detail, CONFIG.outputFile);
            } else {
                log(`Failed to crawl detail for ${originalJob.url}`, 'WARN');
                // Vẫn giữ URL trong danh sách pending? Không, vì nó đã được xử lý và fail.
                // Tuy nhiên, nếu muốn retry ở lần sau, cần lưu lại URL fail. Ở đây ta sẽ bỏ qua, vì đã retry trong hàm.
                // Nếu fail sau maxRetries, coi như bỏ qua.
            }

            // Cập nhật checkpoint sau mỗi job (lưu danh sách còn lại)
            const remainingAfter = remainingUrls.slice(i + 1);
            saveCheckpointByUrl(originalJob.url, remainingAfter);

            const delay = CONFIG.delayBetweenJobs + Math.random() * 5000;
            log(`Waiting ${Math.round(delay/1000)} seconds before next job...`);
            await new Promise(resolve => setTimeout(resolve, delay));
        }
    } finally {
        await browser.close();
        log('Browser closed.');
    }

    if (fs.existsSync(CONFIG.checkpointFile)) fs.unlinkSync(CONFIG.checkpointFile);
    log('=== CRAWL DETAILS FINISHED ===');
})();