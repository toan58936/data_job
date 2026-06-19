.PHONY: crawl transform all clean run

# Chạy riêng crawler (không dùng script)
crawl:
	@echo "=== Crawling data ==="
	cd crawlers && uv run node src/topcv-list-crawler.js
	cd crawlers && uv run node src/topcv-detail-crawler.js
	cd crawlers && uv run node src/topcv-text-crawler.js

# Chạy riêng transform (không dùng script)
transform:
	@echo "=== Transforming data ==="
	uv run python -m transform.src.main

# Chạy toàn bộ pipeline thông qua script PowerShell
run:
	@echo "=== Running full pipeline via PowerShell script ==="
	powershell -ExecutionPolicy Bypass -File run_pipeline.ps1

# Mặc định chạy pipeline đầy đủ
all: run

# Dọn dẹp output
clean:
	@echo "Cleaning output..."
	rm -rf data/silver/*.parquet
	rm -rf data/bronze/checkpoint*.json