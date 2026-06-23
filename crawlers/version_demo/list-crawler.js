const { chromium } = require('playwright-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
const fs = require('fs');
const path = require('path');
const cheerio = require('cheerio');

chromium.use(StealthPlugin());

// ==================== ĐỌC THAM SỐ CLI ====================
const args = process.argv.slice(2);
const roleIndex = args.indexOf('--role');
const ROLE = roleIndex !== -1 ? args[roleIndex + 1] : 'data-engineer';

// Nếu role không hợp lệ, báo lỗi và exit
const VALID_ROLES = [
    'data-engineer',
    'data-analyst',
    'data-scientist',
    'business-intelligence',
    'machine-learning',
    'ai-engineer',
    'analytics-engineer'
];
if (!VALID_ROLES.includes(ROLE)) {
    console.error(`❌ Invalid role: ${ROLE}. Allowed: ${VALID_ROLES.join(', ')}`);
    process.exit(1);
}

// ==================== CẤU HÌNH ====================
const CONFIG = {
    // URL động theo role
    baseUrl: `https://www.topcv.vn/tim-viec-lam-${ROLE}?type_keyword=1&sba=1`,
    outputDir: path.resolve(__dirname, '../../logs/crawler'),
    // Checkpoint riêng cho từng role
    checkpointFile: path.resolve(__dirname, `../../data/bronze/checkpoint_${ROLE}.json`),
    finalOutput: path.resolve(__dirname, '../../data/bronze/jobs_all.json'),
    maxRetries: 3,
    retryDelay: 5000,
    waitBetweenPages: 2000,
    headless: true,
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
    viewport: { width: 1280, height: 800 },
    locale: 'vi-VN',
    possibleSelectors: ['.job-item', '.recruit-item', '.media-job', 'div[class*="job"]', 'div[class*="recruit"]']
};

// ==================== TIỆN ÍCH ====================
function ensureDir(dir) {
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

function log(message, level = 'INFO') {
    const timestamp = new Date().toISOString();
    const logMsg = `[${timestamp}] [${level}] [${ROLE}] ${message}`;
    console.log(logMsg);
    // Log riêng cho từng role
    const logFile = path.join(CONFIG.outputDir, `crawl_${ROLE}.log`);
    fs.appendFileSync(logFile, logMsg + '\n');
}

function normalizeUrl(url) {
    if (!url) return null;
    const questionIndex = url.indexOf('?');
    return questionIndex === -1 ? url : url.substring(0, questionIndex);
}

function upsertJobs(newJobs, filePath) {
    let existingJobs = [];
    if (fs.existsSync(filePath)) {
        try {
            existingJobs = JSON.parse(fs.readFileSync(filePath, 'utf8'));
            log(`Loaded ${existingJobs.length} existing jobs from ${filePath}`);
        } catch(e) {
            log(`Failed to parse existing file, starting fresh`, 'WARN');
        }
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
    
    fs.writeFileSync(filePath, JSON.stringify(existingJobs, null, 2));
    return { total: existingJobs.length, added: addedCount };
}

function saveCheckpoint(pageNum, totalPages, jobsSoFar) {
    const checkpoint = {
        role: ROLE,
        lastPage: pageNum,
        totalPages: totalPages,
        jobsCount: jobsSoFar.length,
        timestamp: Date.now()
    };
    fs.writeFileSync(CONFIG.checkpointFile, JSON.stringify(checkpoint, null, 2));
    log(`Checkpoint saved: page ${pageNum}/${totalPages}, jobs: ${jobsSoFar.length}`);
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

async function getTotalPages(page, url) {
    log(`Detecting total pages from ${url}`);
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
    log(`Detected total pages: ${totalPages}`);
    return totalPages;
}

async function crawlPage(page, pageNum, retryCount = 0) {
    const url = pageNum === 1 ? CONFIG.baseUrl : `${CONFIG.baseUrl}&page=${pageNum}`;
    log(`Crawling page ${pageNum}: ${url}`);
    
    try {
        await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
        
        let found = false;
        for (const sel of CONFIG.possibleSelectors) {
            try {
                await page.waitForSelector(sel, { timeout: 8000 });
                found = true;
                break;
            } catch(e) {}
        }
        if (!found) log(`Warning: No known selector found on page ${pageNum}`, 'WARN');
        
        await page.waitForTimeout(3000);
        
        // Cuộn trang
        await page.evaluate(async () => {
            await new Promise((resolve) => {
                let totalHeight = 0;
                const distance = 400;
                const timer = setInterval(() => {
                    const scrollHeight = document.body.scrollHeight;
                    window.scrollBy(0, distance);
                    totalHeight += distance;
                    if (totalHeight >= scrollHeight) {
                        clearInterval(timer);
                        resolve();
                    }
                }, 200);
            });
        });
        await page.waitForTimeout(2000);
        
        const html = await page.content();
        const $ = cheerio.load(html);
        
        let jobSelector = null;
        for (const sel of CONFIG.possibleSelectors) {
            if ($(sel).length > 0) {
                jobSelector = sel;
                break;
            }
        }
        if (!jobSelector) {
            log(`No job cards found on page ${pageNum}`, 'WARN');
            return [];
        }
        
        const jobs = [];
        $(jobSelector).each((i, el) => {
            let title = $(el).find('h3 a, .job-title a, .title a').first().text().trim();
            if (!title) title = $(el).find('a[title]').attr('title') || '';
            if (!title) return;
            
            // Lọc job có chứa từ khóa "data" để đảm bảo đúng ngành
            // (có thể bỏ nếu role đã đủ chính xác)
            if (!title.toLowerCase().includes('data')) return;
            
            const company = $(el).find('.company-name, .company, .org').first().text().trim();
            const location = $(el).find('.location, .address, .city').first().text().trim();
            const salary = $(el).find('.salary, .price, .money').first().text().trim();
            const experience = $(el).find('.experience, .exp, .year').first().text().trim();
            let url = $(el).find('h3 a, .job-title a').first().attr('href');
            if (url && !url.startsWith('http')) url = 'https://www.topcv.vn' + url;
            
            jobs.push({ title, company, location, salary, experience, url });
        });
        
        log(`Page ${pageNum}: found ${jobs.length} jobs`);
        return jobs;
        
    } catch (err) {
        log(`Error on page ${pageNum}: ${err.message}`, 'ERROR');
        if (retryCount < CONFIG.maxRetries) {
            log(`Retrying page ${pageNum} (attempt ${retryCount+1}/${CONFIG.maxRetries})...`);
            await page.waitForTimeout(CONFIG.retryDelay);
            return crawlPage(page, pageNum, retryCount+1);
        }
        return [];
    }
}

// ==================== KHỞI CHẠY ====================
(async () => {
    ensureDir(CONFIG.outputDir);
    log(`=== START CRAWL JOB LIST FOR ROLE: ${ROLE} ===`);
    
    const checkpoint = loadCheckpoint();
    let startPage = 1;
    let allJobsThisRun = [];
    let totalPages = 0;
    
    const browser = await chromium.launch({ headless: CONFIG.headless });
    const context = await browser.newContext({
        userAgent: CONFIG.userAgent,
        viewport: CONFIG.viewport,
        locale: CONFIG.locale,
    });
    const page = await context.newPage();
    
    try {
        totalPages = await getTotalPages(page, CONFIG.baseUrl);
        
        if (checkpoint && checkpoint.totalPages === totalPages && checkpoint.role === ROLE) {
            startPage = checkpoint.lastPage + 1;
            log(`Resume from checkpoint: starting page ${startPage}`);
        } else {
            if (checkpoint) log('Checkpoint ignored because total pages changed or role mismatch.', 'WARN');
            log(`Starting fresh crawl from page 1 for role ${ROLE}`);
        }
        
        for (let pageNum = startPage; pageNum <= totalPages; pageNum++) {
            const jobs = await crawlPage(page, pageNum);
            allJobsThisRun.push(...jobs);
            saveCheckpoint(pageNum, totalPages, allJobsThisRun);
            await page.waitForTimeout(CONFIG.waitBetweenPages);
        }
        
        // Deduplicate trong cùng đợt crawl
        const uniqueThisRun = [];
        const urlSet = new Set();
        for (const job of allJobsThisRun) {
            const normUrl = normalizeUrl(job.url);
            if (normUrl && !urlSet.has(normUrl)) {
                urlSet.add(normUrl);
                uniqueThisRun.push(job);
            }
        }
        log(`This run: raw ${allJobsThisRun.length} jobs, unique ${uniqueThisRun.length}`);
        
        // Upsert vào file tổng
        const { total, added } = upsertJobs(uniqueThisRun, CONFIG.finalOutput);
        log(`Upsert completed: ${added} new jobs added for role ${ROLE}, total ${total} jobs in database.`);
        
        // Xóa checkpoint nếu thành công
        if (fs.existsSync(CONFIG.checkpointFile)) fs.unlinkSync(CONFIG.checkpointFile);
        
    } catch (err) {
        log(`Fatal error: ${err.message}`, 'ERROR');
    } finally {
        await browser.close();
        log('Browser closed.');
        log(`=== CRAWL FINISHED FOR ROLE: ${ROLE} ===`);
    }
})();