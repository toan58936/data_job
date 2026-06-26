// crawlers/src/itviec/detail_crawler.js
// Crawl trang chi tiết job ITviec — bản fix 4 bugs:
//
//  BUG-1 FIXED: field 'source' bị overwrite từ "ITviec" thành "json-ld"
//               → đổi sang 'salary_source' để tránh conflict
//
//  BUG-2 FIXED: html-class selector bắt widget "IT Salary Report 2024-2025"
//               → thêm isSalaryTextValid() validate trước khi chấp nhận
//
//  BUG-3 FIXED: html selector bắt text breadcrumb "Home › All IT jobs › ..."
//               → thêm pattern blacklist trong isSalaryTextValid()
//
//  BUG-4 FIXED: experience extraction lấy CSS từ <style> tag
//               → skip style/script/head khi duyệt elements

const { chromium } = require('playwright-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
const fs = require('fs');
const path = require('path');
const cheerio = require('cheerio');

chromium.use(StealthPlugin());

// ==================== XÁC ĐỊNH ROOT DỰ ÁN ====================
const ROOT = path.resolve(__dirname, '../../../');
const BRONZE_ITVIEC_DIR = path.resolve(ROOT, 'data/bronze/itviec');
const LOG_DIR = path.resolve(ROOT, 'logs/crawler/itviec');

// ==================== CẤU HÌNH ====================
const CONFIG = {
    inputFile:      path.resolve(BRONZE_ITVIEC_DIR, 'jobs_all.json'),        // ← ĐÃ SỬA
    outputFile:     path.resolve(BRONZE_ITVIEC_DIR, 'jobs_detail.json'),     // ← ĐÃ SỬA
    checkpointFile: path.resolve(BRONZE_ITVIEC_DIR, 'checkpoint_detail.json'), // ← ĐÃ SỬA
    logDir:         LOG_DIR,                                                 // ← ĐÃ SỬA
    maxRetries:     2,
    retryDelay:     5000,
    delayBetweenJobs: 6000,
    headless: true,
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
    viewport: { width: 1280, height: 800 },
};

// ==================== TIỆN ÍCH ====================
function ensureDir(dir) {
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

function log(message, level = 'INFO') {
    const ts  = new Date().toISOString();
    const msg = `[${ts}] [${level}] [itviec-detail] ${message}`;
    console.log(msg);
    ensureDir(CONFIG.logDir);
    fs.appendFileSync(path.join(CONFIG.logDir, 'itviec_detail.log'), msg + '\n');
}

function normalizeUrl(url) {
    if (!url) return null;
    const idx = url.indexOf('?');
    return idx === -1 ? url : url.substring(0, idx);
}

// ==================== PARSE SALARY STRING ====================
function parseSalaryString(text) {
    if (!text || typeof text !== 'string') return { min: null, max: null, currency: null, unit: null };

    let clean = text.replace(/,/g, '').trim();
    let currency = null;
    let unit     = null;

    if (/usd|\$/i.test(clean))                   currency = 'USD';
    else if (/vnd|₫|đồng|triệu/i.test(clean))  currency = 'VND';

    if (/tháng|month/i.test(clean))              unit = 'MONTH';
    else if (/năm|year/i.test(clean))            unit = 'YEAR';
    else if (/giờ|hour/i.test(clean))            unit = 'HOUR';

    const numericPart = clean.replace(/[^0-9.\-–—\s]/g, ' ').replace(/\s+/g, ' ').trim();
    const numbers = numericPart.match(/\d+(\.\d+)?/g);

    if (!numbers) {
        const isNegotiable = /thoả thuận|negotiable|competitive/i.test(clean);
        return { min: null, max: null, currency, unit, isNegotiable };
    }

    let nums = numbers.map(Number);
    let min = null, max = null;

    if (nums.length === 1) {
        if (/up to|tối đa|max/i.test(clean)) max = nums[0];
        else { min = nums[0]; max = nums[0]; }
    } else if (nums.length >= 2) {
        min = Math.min(nums[0], nums[1]);
        max = Math.max(nums[0], nums[1]);
    }

    if (currency === 'VND') {
        if (min !== null && min > 1000) min = Math.round(min / 1_000_000 * 10) / 10;
        if (max !== null && max > 1000) max = Math.round(max / 1_000_000 * 10) / 10;
    }

    if (min !== null) min = Math.round(min * 10) / 10;
    if (max !== null) max = Math.round(max * 10) / 10;

    return { min, max, currency, unit, isNegotiable: false };
}

// ==================== VALIDATE SALARY TEXT ====================
function isSalaryTextValid(text, min, max) {
    if (!text || typeof text !== 'string') return false;

    const BLACKLIST = [
        /IT Salary Report/i,
        /Salary Report/i,
        /salary survey/i,
        /›/,
        /BreadcrumbList/i,
        /sign in to view/i,
        /you.ll love it/i,
        /you'll love/i,
    ];
    for (const pattern of BLACKLIST) {
        if (pattern.test(text)) return false;
    }

    if (/\b20\d{2}\s*[-–—]\s*(0?[1-9]|1[0-2])\b/.test(text)) return false;

    if (!/\d/.test(text)) return false;

    if (
        min !== null && max !== null &&
        min >= 2020 && max <= 2030 &&
        (max - min) <= 5
    ) return false;

    const looksLikeYear = (v) => v !== null && v >= 2015 && v <= 2035;
    if (looksLikeYear(min) !== looksLikeYear(max) && (looksLikeYear(min) || looksLikeYear(max))) {
        const hasCurrencyHint = /usd|\$|vnd|₫|triệu|million/i.test(text);
        if (!hasCurrencyHint) return false;
    }

    const hasCurrencyHint = /usd|\$|vnd|₫|triệu|million/i.test(text);
    const hasRange = min !== null && max !== null && max > min;
    if (!hasCurrencyHint && !hasRange) return false;

    return true;
}

// ==================== EXTRACT SALARY: JSON-LD ====================
function extractSalaryFromJsonLd($) {
    const scripts = $('script[type="application/ld+json"]');
    for (let i = 0; i < scripts.length; i++) {
        try {
            const data = JSON.parse($(scripts[i]).text());
            const items = Array.isArray(data) ? data : [data];
            for (const item of items) {
                if (item['@type'] !== 'JobPosting' || !item.baseSalary) continue;

                const sal   = item.baseSalary;
                const value = sal.value || sal;
                let minVal  = value.minValue ?? value.min ?? null;
                let maxVal  = value.maxValue ?? value.max ?? null;
                const cur   = value.currency || sal.currency || null;
                const unit  = value.unitText  || null;

                if (typeof minVal === 'string') minVal = parseFloat(minVal);
                if (typeof maxVal === 'string') maxVal = parseFloat(maxVal);
                if (minVal === null && maxVal === null && typeof value === 'number') {
                    minVal = maxVal = value;
                }

                if (minVal === null && maxVal === null) continue;

                let salaryText = '';
                if (minVal !== null && maxVal !== null) salaryText = `${minVal} - ${maxVal}${cur ? ' ' + cur : ''}`;
                else if (minVal !== null)               salaryText = `From ${minVal}${cur ? ' ' + cur : ''}`;
                else                                    salaryText = `Up to ${maxVal}${cur ? ' ' + cur : ''}`;

                return {
                    salary_text:    salaryText.trim(),
                    salary_min:     minVal,
                    salary_max:     maxVal,
                    currency:       cur,
                    unit:           unit,
                    salary_source:  'json-ld',
                    isNegotiable:   false,
                };
            }
        } catch (_) { }
    }
    return null;
}

// ==================== EXTRACT SALARY: HTML FALLBACK ====================
function extractSalaryFromHtml($) {
    const LABEL_SELECTORS = [
        'strong:contains("Mức lương")', 'b:contains("Mức lương")',
        'span:contains("Mức lương")',   'div:contains("Mức lương")',
        'strong:contains("Salary")',    'b:contains("Salary")',
        'span:contains("Salary")',
    ];
    for (const sel of LABEL_SELECTORS) {
        const el = $(sel).first();
        if (!el.length) continue;
        let text = el.parent().text().replace(el.text(), '').trim()
                   || el.next().text().trim();
        if (!text) continue;
        const parsed = parseSalaryString(text);
        if (isSalaryTextValid(text, parsed.min, parsed.max)) {
            return {
                salary_text:   text.substring(0, 100),
                salary_min:    parsed.min,
                salary_max:    parsed.max,
                currency:      parsed.currency,
                unit:          parsed.unit,
                salary_source: 'html-label',
                isNegotiable:  parsed.isNegotiable,
            };
        }
    }

    const CLASS_SELECTORS = [
        '.salary-box', '.job-salary', '.base-salary', '.salary-range',
        '[data-controller*="salary"]',
        '[data-salary]',
    ];
    for (const sel of CLASS_SELECTORS) {
        const el = $(sel).first();
        if (!el.length) continue;
        const text = el.text().trim();
        const parsed = parseSalaryString(text);
        if (isSalaryTextValid(text, parsed.min, parsed.max)) {
            return {
                salary_text:   text.substring(0, 100),
                salary_min:    parsed.min,
                salary_max:    parsed.max,
                currency:      parsed.currency,
                unit:          parsed.unit,
                salary_source: 'html-class',
                isNegotiable:  parsed.isNegotiable,
            };
        }
    }

    const SALARY_PATTERN = /(\$|USD|usd)\s*(\d{2,6})\s*[-–—]\s*(\d{2,6})\s*(USD|usd|\$|triệu|VND|₫)?|(\d{2,6})\s*[-–—]\s*(\d{2,6})\s*(USD|usd|\$|triệu|VND|₫)/g;
    const bodyText = $('body').text();
    let m;
    while ((m = SALARY_PATTERN.exec(bodyText)) !== null) {
        const raw = m[0].trim();
        const parsed = parseSalaryString(raw);
        if (isSalaryTextValid(raw, parsed.min, parsed.max)) {
            return {
                salary_text:   raw,
                salary_min:    parsed.min,
                salary_max:    parsed.max,
                currency:      parsed.currency,
                unit:          parsed.unit,
                salary_source: 'html-pattern',
                isNegotiable:  false,
            };
        }
    }

    return null;
}

// ==================== EXTRACT CONTENT ====================
function extractJobContent($) {
    let description = '', requirements = '', benefits = '';

    const HEADINGS = {
        description:  ['job description', 'mô tả công việc', 'about the role', 'về vị trí',
                        'chi tiết công việc', 'about this role'],
        requirements: ['your skills and experience', 'requirements', 'yêu cầu', 'what you need',
                        'yêu cầu ứng viên', 'qualifications'],
        benefits:     ["why you'll love working here", 'benefits', 'quyền lợi',
                        'what we offer', 'chúng tôi cung cấp', "you'll love"],
    };

    $('h2, h3, h4').each((_, el) => {
        const heading = $(el).text().toLowerCase().trim();
        let field = null;
        for (const [f, keywords] of Object.entries(HEADINGS)) {
            if (keywords.some(kw => heading.includes(kw))) { field = f; break; }
        }
        if (!field) return;

        const parts = [];
        let next = $(el).next();
        while (next.length && !next.is('h2, h3, h4')) {
            parts.push(next.text().trim());
            next = next.next();
        }
        const content = parts.join('\n').replace(/\s{3,}/g, '\n').trim();
        if (field === 'description' && !description)   description   = content;
        if (field === 'requirements' && !requirements) requirements  = content;
        if (field === 'benefits' && !benefits)         benefits      = content;
    });

    if (!description)
        description = $('[class*="description"], .job-description').first()
                        .text().replace(/\s+/g, ' ').trim();

    return { description, requirements, benefits };
}

// ==================== EXTRACT EXPERIENCE ====================
const SKIP_TAGS = new Set(['style', 'script', 'head', 'noscript', 'svg', 'path', 'template']);

function extractExperience($) {
    const EXP_PATTERNS = [
        /(\d+)\s*\+?\s*(?:–|-|to)?\s*(\d+)?\+?\s*years?['’]?\s*(?:of\s+)?(?:[a-zA-Z-]+\s+){0,4}experience/i,
        /(\d+)\s*\+?\s*(?:–|-|to)?\s*(\d+)?\+?\s*years?\s+in\s+[a-zA-Z]/i,
        /more\s+than\s+(\d+)\+?\s*years?/i,
        /(\d+)\s*\+?\s*(?:–|-|to)?\s*(\d+)?\s*(?:years?|yrs?)\s*(?:of\s+)?experience/i,
        /(?:từ\s+|[≥]\s*|>=\s*)?(\d+)\s*(?:–|-|đến)?\s*(\d+)?\s*năm\s*kinh\s*nghiệm/i,
        /(?:minimum|at\s+least|min\.?)\s+(\d+)\s*(?:–|-|to)?\s*(\d+)?\s*years?/i,
        /(\d+)\s*[-–]\s*(\d+)\s*năm/i,
        /[≥]\s*(\d+)\+?\s*(?:years?|năm)|>=\s*(\d+)\+?\s*(?:years?|năm)/i,
    ];

    const requirementsEl = $('[class*="requirement"], [class*="skill"]').first();
    const searchScope = requirementsEl.length ? requirementsEl : $('body');

    let result = '';

    const CONTENT_TAGS = ['p', 'li', 'span', 'div', 'td'];
    searchScope.find(CONTENT_TAGS.join(', ')).each((_, el) => {
        const tagName = (el.tagName || '').toLowerCase();
        if (SKIP_TAGS.has(tagName)) return;
        if ($(el).find('style, script').length) return;

        const text = $(el).text().trim();
        if (text.length > 5000) return;

        for (const pat of EXP_PATTERNS) {
            const m = text.match(pat);
            if (m) {
                const matchStart = m.index ?? text.indexOf(m[0]);
                const contextStart = Math.max(0, matchStart - 20);
                result = text.substring(contextStart, contextStart + 150).trim();
                return false;
            }
        }
    });

    return result;
}

// ==================== CRAWL DETAIL ====================
async function crawlDetail(page, jobUrl, retryCount = 0) {
    log(`Crawling: ${jobUrl}`);
    try {
        const response = await page.goto(jobUrl, {
            waitUntil: 'domcontentloaded',
            timeout: 30000,
        });
        if (!response || response.status() !== 200) {
            log(`HTTP ${response?.status()} for ${jobUrl}`, 'WARN');
            return null;
        }

        await page.waitForTimeout(2000 + Math.random() * 2000);
        const $ = cheerio.load(await page.content());

        let salaryData = extractSalaryFromJsonLd($);
        if (!salaryData) {
            salaryData = extractSalaryFromHtml($);
        }
        if (!salaryData) {
            const bodyText = $('body').text();
            const isNegotiable = /cạnh tranh|competitive|thoả thuận|negotiable/i.test(bodyText);
            salaryData = {
                salary_text:   isNegotiable ? 'Competitive' : '',
                salary_min:    null,
                salary_max:    null,
                currency:      null,
                unit:          null,
                salary_source: isNegotiable ? 'text-competitive' : 'none',
                isNegotiable,
            };
        }

        const { description, requirements, benefits } = extractJobContent($);
        const experience = extractExperience($);

        return {
            salary_text:   salaryData.salary_text,
            salary_min:    salaryData.salary_min,
            salary_max:    salaryData.salary_max,
            currency:      salaryData.currency,
            unit:          salaryData.unit,
            salary_source: salaryData.salary_source,
            isNegotiable:  salaryData.isNegotiable ?? false,
            description,
            requirements,
            benefits,
            experience,
            detail_crawled_at: new Date().toISOString(),
        };

    } catch (err) {
        log(`Error: ${err.message}`, 'ERROR');
        if (retryCount < CONFIG.maxRetries) {
            log(`Retrying (${retryCount + 1}/${CONFIG.maxRetries})...`);
            await new Promise(r => setTimeout(r, CONFIG.retryDelay));
            return crawlDetail(page, jobUrl, retryCount + 1);
        }
        return null;
    }
}

// ==================== MAIN ====================
(async () => {
    ensureDir(CONFIG.logDir);
    ensureDir(BRONZE_ITVIEC_DIR);
    log('=== START ITVIEC DETAIL CRAWLER (fixed) ===');

    const args      = process.argv.slice(2);
    const inputIdx  = args.indexOf('--input');
    const inputPath = inputIdx !== -1 ? args[inputIdx + 1] : CONFIG.inputFile;
    const headless  = !args.includes('--headed');

    if (!fs.existsSync(inputPath)) {
        log(`Input not found: ${inputPath}`, 'ERROR');
        process.exit(1);
    }

    const allJobs = JSON.parse(fs.readFileSync(inputPath, 'utf8'));
    log(`Total jobs: ${allJobs.length}`);

    let existingMap = new Map();
    if (fs.existsSync(CONFIG.outputFile)) {
        try {
            for (const item of JSON.parse(fs.readFileSync(CONFIG.outputFile, 'utf8'))) {
                const norm = normalizeUrl(item.job_url);
                if (norm) existingMap.set(norm, item);
            }
            log(`Loaded ${existingMap.size} existing records`);
        } catch (_) { log('Could not load existing output', 'WARN'); }
    }

    const pending = allJobs.filter(j => !existingMap.has(normalizeUrl(j.job_url)));
    log(`Pending: ${pending.length} jobs`);
    if (pending.length === 0) { log('All done. Exiting.'); process.exit(0); }

    let startIdx = 0;
    if (fs.existsSync(CONFIG.checkpointFile)) {
        try {
            const cp      = JSON.parse(fs.readFileSync(CONFIG.checkpointFile, 'utf8'));
            const lastIdx = pending.findIndex(j => normalizeUrl(j.job_url) === normalizeUrl(cp.lastUrl));
            if (lastIdx !== -1) { startIdx = lastIdx + 1; log(`Resume from index ${startIdx}`); }
        } catch (_) {}
    }

    const browser = await chromium.launch({ headless });
    const context = await browser.newContext({ userAgent: CONFIG.userAgent, viewport: CONFIG.viewport });
    const page    = await context.newPage();
    await page.addInitScript(() => {
        Object.defineProperty(navigator, 'webdriver', { get: () => false });
    });

    let results = Array.from(existingMap.values());
    let salaryFound = 0;

    try {
        for (let i = startIdx; i < pending.length; i++) {
            const job = pending[i];
            log(`[${i + 1}/${pending.length}] ${job.job_title} @ ${job.company_name}`);

            const detail = await crawlDetail(page, job.job_url);
            if (detail) {
                const merged = { ...job, ...detail };
                merged.salary_hidden = (merged.salary_min === null && merged.salary_max === null);

                results.push(merged);
                existingMap.set(normalizeUrl(job.job_url), merged);
                if (merged.salary_min !== null || merged.salary_max !== null) salaryFound++;
            }

            fs.writeFileSync(CONFIG.checkpointFile, JSON.stringify({
                lastUrl: job.job_url, processed: i + 1, total: pending.length,
            }, null, 2));
            if (i % 5 === 0 || i === pending.length - 1) {
                fs.writeFileSync(CONFIG.outputFile, JSON.stringify(results, null, 2));
                log(`Progress saved: ${results.length} records`);
            }

            await new Promise(r => setTimeout(r, CONFIG.delayBetweenJobs + Math.random() * 3000));
        }
    } finally {
        await browser.close();
    }

    fs.writeFileSync(CONFIG.outputFile, JSON.stringify(results, null, 2));
    if (fs.existsSync(CONFIG.checkpointFile)) fs.unlinkSync(CONFIG.checkpointFile);

    log(`=== FINISHED: ${results.length} total, salary found: ${salaryFound}/${pending.length} (${(salaryFound/pending.length*100).toFixed(1)}%) ===`);
})();