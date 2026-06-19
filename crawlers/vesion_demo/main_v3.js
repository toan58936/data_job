const { chromium } = require('playwright-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
const fs = require('fs');
const path = require('path');
const cheerio = require('cheerio');

chromium.use(StealthPlugin());

// ==================== CẤU HÌNH ====================
const CONFIG = {
    inputFile: './output/jobs_all.json',           // Danh sách job cần crawl (từ list)
    outputDir: './output',
    outputFile: './output/jobs_detail.json',       // File lưu chi tiết
    checkpointFile: './output/checkpoint_detail.json',
    maxRetries: 2,
    retryDelay: 5000,
    delayBetweenJobs: 7000,
    headless: true,                                 // Ẩn trình duyệt
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

function upsertJobWithDeadlineCheck(newJob, existingJob) {
    // Luôn cập nhật (bạn có thể chỉnh sửa logic nếu muốn)
    return true;
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
        const shouldUpdate = upsertJobWithDeadlineCheck(newJob, existingJobs[existingIndex]);
        if (shouldUpdate) {
            existingJobs[existingIndex] = { ...existingJobs[existingIndex], ...newJob };
            log(`Updated existing job: ${newJob.title} (${newJob.id})`);
        } else {
            log(`Skipped job (no changes): ${newJob.title} (${newJob.id})`);
            return existingJobs.length;
        }
    } else {
        existingJobs.push(newJob);
        log(`Added new job: ${newJob.title} (${newJob.id})`);
    }
    fs.writeFileSync(filePath, JSON.stringify(existingJobs, null, 2));
    return existingJobs.length;
}

function saveCheckpoint(jobIndex, totalJobs, lastUrl) {
    const checkpoint = {
        lastIndex: jobIndex,
        totalJobs: totalJobs,
        lastUrl: lastUrl,
        timestamp: Date.now()
    };
    fs.writeFileSync(CONFIG.checkpointFile, JSON.stringify(checkpoint, null, 2));
    log(`Checkpoint saved: index ${jobIndex}/${totalJobs}, url: ${lastUrl}`);
}

function loadCheckpoint() {
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

// ==================== HÀM CRAWL CHI TIẾT JOB ====================
async function crawlJobDetail(page, jobUrl, retryCount = 0) {
    log(`Crawling detail: ${jobUrl}`);
    try {
        await page.goto(jobUrl, { waitUntil: 'commit', timeout: CONFIG.navigationTimeout });
        await page.waitForSelector('h1, .job-title, .title-detail', { timeout: CONFIG.selectorTimeout });
        await page.waitForTimeout(3000); // Đợi thêm khi headless

        const html = await page.content();
        const $ = cheerio.load(html);

        let idMatch = jobUrl.match(/[-\/](?:j?)(\d+)\.html/);
        if (!idMatch) idMatch = jobUrl.match(/(\d+)\.html/);
        const id = idMatch ? idMatch[1] : null;
        const normalizedUrl = jobUrl.indexOf('?') === -1 ? jobUrl : jobUrl.substring(0, jobUrl.indexOf('?'));

        let title = $('h1, .job-title, .title-detail').first().text().trim();
        const company = $('.company-name, .company, .org').first().text().trim();

        const salary = getValueByLabel($, 'Mức lương');
        const experience = getValueByLabel($, 'Kinh nghiệm');
        let deadlineRaw = getValueByLabel($, 'Hạn nộp');
        if (!deadlineRaw) deadlineRaw = getValueByLabel($, 'Hạn nộp hồ sơ');

        let location = getValueByLabel($, 'Địa điểm');
        if (!location || location === 'Tìm kiếm' || /\{\{.*\}\}/.test(location)) {
            const $locationDiv = $('.job-detail_info-section-content-location, .job-detail-info-location, [class*="location"]').first();
            if ($locationDiv.length) location = $locationDiv.text().trim();
        }
        if (!location || location === 'Tìm kiếm' || /\{\{.*\}\}/.test(location)) {
            const $locationLink = $('a[title*="Hà Nội"]').first();
            if ($locationLink.length) location = $locationLink.text().trim();
        }
        if (!location || location === 'Tìm kiếm' || /\{\{.*\}\}/.test(location)) {
            const $locationHref = $('a[href*="-tai-"][href*="-kl"]').first();
            if ($locationHref.length) location = $locationHref.text().trim();
        }

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

// ==================== KHỞI CHẠY (CẢI TIẾN: CHỈ CRAWL JOB CHƯA CÓ) ====================
(async () => {
    ensureDir(CONFIG.outputDir);
    log('=== START CRAWL ALL JOB DETAILS (UPSERT - SKIP EXISTING) ===');
    log(`Mode: ${CONFIG.headless ? 'Headless (ẩn trình duyệt)' : 'Headed (hiện trình duyệt)'}`);

    if (!fs.existsSync(CONFIG.inputFile)) {
        log(`Input file not found: ${CONFIG.inputFile}`, 'ERROR');
        process.exit(1);
    }
    const allJobsFromList = JSON.parse(fs.readFileSync(CONFIG.inputFile, 'utf8'));
    log(`Total jobs in list: ${allJobsFromList.length}`);

    // Đọc danh sách job đã crawl detail (nếu có)
    let existingDetailMap = new Map(); // key = normalized_url
    if (fs.existsSync(CONFIG.outputFile)) {
        try {
            const existingDetails = JSON.parse(fs.readFileSync(CONFIG.outputFile, 'utf8'));
            for (const job of existingDetails) {
                const normUrl = normalizeUrl(job.url);
                if (normUrl) existingDetailMap.set(normUrl, true);
            }
            log(`Loaded ${existingDetailMap.size} existing detail jobs from ${CONFIG.outputFile}`);
        } catch(e) {
            log(`Failed to parse existing detail file, will treat as empty.`, 'WARN');
        }
    }

    // Lọc ra những job chưa có detail
    const jobsToCrawl = allJobsFromList.filter(job => {
        const normUrl = normalizeUrl(job.url);
        return !existingDetailMap.has(normUrl);
    });
    log(`Jobs already crawled: ${allJobsFromList.length - jobsToCrawl.length}`);
    log(`Jobs to crawl: ${jobsToCrawl.length}`);

    if (jobsToCrawl.length === 0) {
        log('All jobs already have detail. Exiting.');
        process.exit(0);
    }

    // Tạo map original_title cho brand job (từ danh sách gốc)
    const originalTitleMap = new Map();
    for (const job of allJobsFromList) {
        originalTitleMap.set(normalizeUrl(job.url), job.title);
    }

    // Load checkpoint (chỉ áp dụng cho jobsToCrawl)
    const checkpoint = loadCheckpoint();
    let startIndex = 0;
    if (checkpoint && checkpoint.totalJobs === jobsToCrawl.length) {
        startIndex = checkpoint.lastIndex + 1;
        log(`Resume from checkpoint: index ${startIndex}/${jobsToCrawl.length}`);
    } else {
        if (checkpoint) log('Checkpoint ignored because total jobs to crawl changed.', 'WARN');
        log('Starting fresh crawl for new jobs');
        if (fs.existsSync(CONFIG.checkpointFile)) fs.unlinkSync(CONFIG.checkpointFile);
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

    // Ẩn dấu hiệu automation
    await page.addInitScript(() => {
        Object.defineProperty(navigator, 'webdriver', { get: () => false });
    });

    try {
        for (let i = startIndex; i < jobsToCrawl.length; i++) {
            const job = jobsToCrawl[i];
            log(`Progress: ${i+1}/${jobsToCrawl.length} - ${job.title} (${job.company})`);

            const detail = await crawlJobDetail(page, job.url);
            if (detail) {
                // Fix title cho brand job nếu cần
                if (detail.title === detail.company || detail.title.includes('CÔNG TY') || detail.title.includes('TNHH')) {
                    const originalTitle = originalTitleMap.get(normalizeUrl(job.url));
                    if (originalTitle && originalTitle !== detail.title) {
                        log(`Fixing title for job ${detail.id}: "${detail.title}" -> "${originalTitle}"`);
                        detail.title = originalTitle;
                    }
                }
                detail.original_title = job.title;
                upsertJob(detail, CONFIG.outputFile);
            } else {
                log(`Failed to crawl detail for ${job.url}`, 'WARN');
            }

            const delay = CONFIG.delayBetweenJobs + Math.random() * 5000;
            log(`Waiting ${Math.round(delay/1000)} seconds before next job...`);
            await new Promise(resolve => setTimeout(resolve, delay));
            saveCheckpoint(i, jobsToCrawl.length, job.url);
        }
    } finally {
        await browser.close();
        log('Browser closed.');
    }

    if (fs.existsSync(CONFIG.checkpointFile)) fs.unlinkSync(CONFIG.checkpointFile);
    log('=== CRAWL DETAILS FINISHED ===');
})();