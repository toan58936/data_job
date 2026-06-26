// crawlers/version_demo/list_crawler_itviet_fixed.js
const { chromium } = require('playwright-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');

chromium.use(StealthPlugin());

// === Đọc tham số dòng lệnh ===
const args = process.argv.slice(2);
const roleIndex = args.indexOf('--role');
const role = roleIndex !== -1 ? args[roleIndex + 1] : 'data-engineer';
const headless = !args.includes('--headed');

// === Hàm trích xuất dữ liệu job từ DOM ===
function extractJobsFromPage() {
  const cards = document.querySelectorAll('div.job-card');
  return Array.from(cards).map(card => {
    // ---- Title ----
    const titleEl = card.querySelector('h3 a');
    let title = titleEl?.textContent?.trim() || '';
    if (!title) {
      const h3 = card.querySelector('h3');
      if (h3) title = h3.textContent.trim();
    }

    // ---- Link ----
    let link = titleEl?.href || '';
    if (!link) {
      const h3 = card.querySelector('h3');
      if (h3) link = h3.getAttribute('data-url') || '';
    }

    // ---- Company ----
    const companyEl = card.querySelector('span.ims-2.small-text.text-hover-underline a');
    const company = companyEl?.textContent?.trim() || '';

    // ---- Location ----
    const locationEls = card.querySelectorAll('div.text-rich-grey.text-truncate');
    const location = locationEls.length > 0 ? locationEls[locationEls.length - 1]?.textContent?.trim() : '';

    // ---- Salary ----
    const salaryEl = card.querySelector('div.salary a') || card.querySelector('div.salary');
    const salary = salaryEl?.textContent?.trim() || '';

    // ---- Skills ----
    const skillEls = card.querySelectorAll('div.imt-4.imb-3.d-flex.igap-1 a.itag');
    const skills = Array.from(skillEls).map(el => el.textContent.trim());

    // ---- Posted time ----
    const postedEl = card.querySelector('span.small-text.text-dark-grey');
    const posted = postedEl?.textContent?.trim() || '';

    // ---- Working model ----
    const wmEl = card.querySelector('div.text-rich-grey.flex-shrink-0');
    const workingModel = wmEl?.textContent?.trim() || '';

    return { title, company, location, salary, skills, posted, workingModel, link };
  });
}

// === Hàm chính ===
(async () => {
  const browser = await chromium.launch({ headless });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
    viewport: { width: 1280, height: 800 },
    locale: 'vi-VN',
  });
  const page = await context.newPage();

  console.log(`🕷️  Crawling ITviec for role: ${role}`);
  const baseUrl = `https://itviec.com/it-jobs/${role}`;
  await page.goto(baseUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });

  let allJobs = [];
  let currentPage = 1;
  let hasNext = true;

  while (hasNext) {
    try {
      await page.waitForSelector('div.job-card', { timeout: 5000 });
      console.log(`✅ Page loaded, job cards found.`);
    } catch (e) {
      console.warn('⚠️  No job cards found on page', currentPage);
      break;
    }

    const jobs = await page.evaluate(extractJobsFromPage);
    allJobs = allJobs.concat(jobs);
    console.log(`📄 Page ${currentPage}: ${jobs.length} jobs`);

    const nextLink = await page.$('a[rel="next"]');
    if (!nextLink) {
      hasNext = false;
      break;
    }

    try {
      await page.click('a[rel="next"]', { force: true, timeout: 10000 });
      await page.waitForLoadState('domcontentloaded', { timeout: 30000 });
      await page.waitForTimeout(2000);
      currentPage++;
    } catch (err) {
      console.warn(`⚠️  Click failed on page ${currentPage}, using fallback URL...`);
      const currentUrl = page.url();
      let nextPageUrl;
      if (currentUrl.includes('page=')) {
        nextPageUrl = currentUrl.replace(/(page=)(\d+)/, (match, p1, p2) => p1 + (parseInt(p2) + 1));
      } else {
        nextPageUrl = currentUrl.includes('?') ? currentUrl + '&page=' + (currentPage + 1) : currentUrl + '?page=' + (currentPage + 1);
      }
      console.log(`🔄 Navigating to ${nextPageUrl}`);
      await page.goto(nextPageUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
      await page.waitForSelector('div.job-card', { timeout: 5000 });
      await page.waitForTimeout(2000);
      currentPage++;
    }
  }

  console.log(`\n✅ Total jobs crawled: ${allJobs.length}`);
  console.log(JSON.stringify(allJobs, null, 2));

  await browser.close();
})();