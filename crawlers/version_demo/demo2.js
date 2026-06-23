const { chromium } = require('playwright-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
const fs = require('fs');
const cheerio = require('cheerio');

chromium.use(StealthPlugin());

// ==================== CẤU HÌNH ====================
const CONFIG = {
    // Output chỉ chứa các job đã fix — dùng để verify trước khi merge vào job_text.json
    outputFile: './output/brand_description_fixed.json',
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
    delayBetweenJobs: 8000,
    maxRetries: 2,
    retryDelay: 5000,
};

// ==================== DANH SÁCH JOB BỊ LỖI ====================
// Chỉ xử lý đúng 8 ID này — không đụng đến các job khác
const BAD_JOBS = [
    { id: '905982',  url: 'https://www.topcv.vn/brand/sofitel/tuyen-dung/data-engineer-aws-j905982.html' },
    { id: '2191679', url: 'https://www.topcv.vn/brand/fptis/tuyen-dung/chuyen-vien-thiet-ke-co-so-du-lieu-database-design-j2191679.html' },
    { id: '2185054', url: 'https://www.topcv.vn/brand/vpbank/tuyen-dung/data-engineer-hn-ta165-j2185054.html' },
    { id: '2179631', url: 'https://www.topcv.vn/brand/vpbank/tuyen-dung/senior-data-engineer-finance-division-id437-j2179631.html' },
    { id: '2135980', url: 'https://www.topcv.vn/brand/vpbank/tuyen-dung/data-engineer-ta192-j2135980.html' },
    { id: '2184635', url: 'https://www.topcv.vn/brand/vpbank/tuyen-dung/data-engineer-ha-noi-ta105-j2184635.html' },
    { id: '2143548', url: 'https://www.topcv.vn/brand/techcombank/tuyen-dung/administrator-assistant-to-head-of-data-engineering-j2143548.html' },
    { id: '2177773', url: 'https://www.topcv.vn/brand/smartosc/tuyen-dung/data-engineer-j2177773.html' },
];

// ==================== LOG ====================
function log(msg, level = 'INFO') {
    const ts = new Date().toISOString();
    const line = `[${ts}] [${level}] ${msg}`;
    console.log(line);
    fs.appendFileSync('./output/retry_brand.log', line + '\n');
}

// ==================== KIỂM TRA TRANG HỢP LỆ ====================
function isPageValid(response, finalUrl, originalUrl, html) {
    if (response && response.status() !== 200) {
        log(`HTTP ${response.status()} for ${originalUrl}`, 'WARN');
        return false;
    }
    const norm = url => { const i = url.indexOf('?'); return i === -1 ? url : url.slice(0, i); };
    if (norm(finalUrl) !== norm(originalUrl)) {
        log(`Redirect: ${originalUrl} → ${finalUrl}`, 'WARN');
        return false;
    }
    const headMatch = html.match(/<head[\s\S]*?<\/head>/i);
    const head = headMatch ? headMatch[0].toLowerCase() : '';
    for (const p of ['just a moment', 'cf-challenge', 'challenge-platform', 'id="challenge-form"', 'id="cf-wrapper"']) {
        if (head.includes(p)) { log(`CF challenge: "${p}" for ${originalUrl}`, 'WARN'); return false; }
    }
    const titleM = head.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
    const title = titleM ? titleM[1].toLowerCase() : '';
    for (const t of ['403', '404', 'not found', 'forbidden']) {
        if (title.includes(t)) { log(`Error title "${title}" for ${originalUrl}`, 'WARN'); return false; }
    }
    return true;
}

// ==================== EXTRACT DESCRIPTION — BRAND PAGE ====================
// Brand page (VPBank, Techcombank, Sofitel, SmartOSC, FPT IS) không dùng
// id="mo-ta-cong-viec". Mỗi lớp fallback thử một chiến lược khác nhau.
function extractBrandDescription($, html) {

    // ── Fallback 1: heading chứa "mô tả" (case-insensitive, flexible) ─────────
    // Mở rộng hơn script gốc: thử cả h1/h2/h3/h4, không yêu cầu exact match
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
            if (val.length > 50) { found = val; return false; } // dừng vòng lặp each
        }
    });
    if (found) { log('  ✓ Fallback 1 (heading mô tả)'); return found; }

    // ── Fallback 2: selector class/id phổ biến của brand page TopCV ─────────
    // Các class này xuất hiện trong brand page VPBank, Techcombank, FPT IS
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
            // Loại bỏ phần requirements và benefits đã crawl được (tránh lấy trùng)
            const clone = el.clone();
            clone.find('*').filter((_, n) => {
                const t = $(n).text().toLowerCase();
                return t.startsWith('yêu cầu ứng viên') || t.startsWith('quyền lợi');
            }).remove();
            const val = clone.text().replace(/\s+/g, ' ').trim();
            if (val.length > 50) { log(`  ✓ Fallback 2 (selector: ${sel})`); return val; }
        }
    }

    // ── Fallback 3: lấy text khối lớn đầu tiên trong main content ───────────
    // Brand page đôi khi không có heading — description là đoạn text dài nhất
    // nằm trước phần "Yêu cầu ứng viên"
    const mainContainer = $('main, .container, .job-detail, #content, .content-main').first();
    if (mainContainer.length) {
        // Tách text trước khi gặp "Yêu cầu ứng viên"
        const fullText = mainContainer.text();
        const cutIndex = fullText.search(/yêu cầu ứng viên/i);
        if (cutIndex > 100) {
            // Bỏ phần header (title, company, salary...) — thường ~200 ký tự đầu
            const candidate = fullText.slice(0, cutIndex).trim();
            // Lấy đoạn cuối (gần phần requirements nhất) = nội dung mô tả
            const val = candidate.slice(Math.max(0, candidate.length - 2000))
                .replace(/\s+/g, ' ').trim();
            if (val.length > 100) { log('  ✓ Fallback 3 (text trước yêu cầu)'); return val; }
        }
    }

    // ── Fallback 4: toàn bộ text của trang, bỏ nav/footer/header ────────────
    // Dùng khi không tìm được heading hoặc container rõ ràng
    $('nav, footer, header, script, style, [class*="menu"], [class*="sidebar"]').remove();
    const pageText = $('body').text().replace(/\s+/g, ' ').trim();
    const cutIdx = pageText.search(/yêu cầu ứng viên/i);
    if (cutIdx > 200) {
        // Lấy tối đa 3000 ký tự trước phần requirements
        const val = pageText.slice(Math.max(0, cutIdx - 3000), cutIdx)
            .replace(/\s+/g, ' ').trim();
        if (val.length > 100) { log('  ✓ Fallback 4 (body text trước yêu cầu)'); return val; }
    }

    log('  ✗ Không tìm được description', 'WARN');
    return '';
}

// ==================== CRAWL 1 JOB ====================
async function crawlOne(page, job, retryCount = 0) {
    log(`Crawling id=${job.id}: ${job.url}`);
    let response = null;
    try {
        response = await page.goto(job.url, { waitUntil: 'commit', timeout: CONFIG.navigationTimeout });
        await page.waitForSelector('h1, .job-title, .title-detail', { timeout: CONFIG.selectorTimeout });
        await page.waitForTimeout(3500); // Brand page load JS chậm hơn

        const html = await page.content();
        const finalUrl = page.url();

        if (!isPageValid(response, finalUrl, job.url, html)) {
            return null;
        }

        const $ = cheerio.load(html);
        const description = extractBrandDescription($, html);

        log(`  description length: ${description.length}`);

        return {
            id: job.id,
            url: job.url,
            normalized_url: job.url.indexOf('?') === -1 ? job.url : job.url.slice(0, job.url.indexOf('?')),
            description,
            fixed_at: new Date().toISOString(),
        };

    } catch (err) {
        log(`Error id=${job.id}: ${err.message}`, 'ERROR');
        if (retryCount < CONFIG.maxRetries) {
            log(`Retry ${retryCount + 1}/${CONFIG.maxRetries} in ${CONFIG.retryDelay / 1000}s...`);
            await new Promise(r => setTimeout(r, CONFIG.retryDelay));
            return crawlOne(page, job, retryCount + 1);
        }
        return null;
    }
}

// ==================== KHỞI CHẠY ====================
(async () => {
    if (!fs.existsSync('./output')) fs.mkdirSync('./output', { recursive: true });

    log('=== RETRY BRAND DESCRIPTION ===');
    log(`Xử lý ${BAD_JOBS.length} job: ${BAD_JOBS.map(j => j.id).join(', ')}`);

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

    const results = [];

    try {
        for (let i = 0; i < BAD_JOBS.length; i++) {
            const job = BAD_JOBS[i];
            log(`\nProgress: ${i + 1}/${BAD_JOBS.length}`);

            const result = await crawlOne(page, job);
            if (result) {
                results.push(result);
                log(`  ✓ OK — description: ${result.description.length} chars`);
            } else {
                // Vẫn ghi record với description rỗng để biết job nào vẫn chưa fix được
                results.push({
                    id: job.id,
                    url: job.url,
                    normalized_url: job.url,
                    description: '',
                    fixed_at: null,
                    status: 'FAILED',
                });
                log(`  ✗ FAILED — ghi record rỗng`, 'WARN');
            }

            // Lưu sau mỗi job — tránh mất data nếu crash
            fs.writeFileSync(CONFIG.outputFile, JSON.stringify(results, null, 2));

            if (i < BAD_JOBS.length - 1) {
                const delay = CONFIG.delayBetweenJobs + Math.random() * 4000;
                log(`Waiting ${Math.round(delay / 1000)}s...`);
                await new Promise(r => setTimeout(r, delay));
            }
        }
    } finally {
        await browser.close();
    }

    // ── Báo cáo kết quả ──────────────────────────────────────────────────────
    const fixed   = results.filter(r => r.description && r.description.length > 0);
    const failed  = results.filter(r => !r.description || r.description.length === 0);

    log('\n=== KẾT QUẢ ===');
    log(`✓ Fixed:  ${fixed.length}/${BAD_JOBS.length}`);
    log(`✗ Failed: ${failed.length}/${BAD_JOBS.length}`);
    for (const r of fixed)  log(`  ✓ id=${r.id} — ${r.description.length} chars`);
    for (const r of failed) log(`  ✗ id=${r.id} — vẫn rỗng`, 'WARN');

    log(`\nOutput: ${CONFIG.outputFile}`);
    log('=== DONE ===');
    log('\nBước tiếp theo:');
    log('  1. Kiểm tra brand_description_fixed.json xem description có đúng không');
    log('  2. Nếu OK → merge vào job_text.json bằng cách update trường description theo id');
})();