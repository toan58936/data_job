#.\run_pipeline.ps1
Write-Host "===== BẮT ĐẦU PIPELINE =====" -ForegroundColor Cyan

# 1. Crawler
Write-Host "`n[1/2] Đang chạy crawler..." -ForegroundColor Yellow
cd crawlers
uv run node src/topcv-list-crawler.js
if ($LASTEXITCODE -ne 0) {
    Write-Host "Crawler list lỗi! Dừng pipeline." -ForegroundColor Red
    exit 1
}
uv run node src/topcv-detail-crawler.js
if ($LASTEXITCODE -ne 0) {
    Write-Host "Crawler detail lỗi!" -ForegroundColor Red
    exit 1
}
uv run node src/topcv-text-crawler.js
if ($LASTEXITCODE -ne 0) {
    Write-Host "Crawler text lỗi!" -ForegroundColor Red
    exit 1
}
cd ..

# 2. Transform
Write-Host "`n[2/2] Đang chạy transform..." -ForegroundColor Yellow
uv run python -m transform.src.main
if ($LASTEXITCODE -ne 0) {
    Write-Host "Transform lỗi!" -ForegroundColor Red
    exit 1
}

Write-Host "`n===== PIPELINE HOÀN TẤT =====" -ForegroundColor Green