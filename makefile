.PHONY: crawl transform all clean run

crawl:
	@echo "=== Crawling data ==="
	cd crawlers && uv run node src/topcv-list-crawler.js
	cd crawlers && uv run node src/topcv-detail-crawler.js
	cd crawlers && uv run node src/topcv-text-crawler.js

transform:
	@echo "=== Transforming data ==="
	uv run python -m transform.src.main --format parquet

run:
	@echo "=== Running full pipeline via cli ==="
	uv run python cli.py run

all: run

clean:
	@echo "Cleaning output..."
	rm -rf data/silver/*.parquet
	rm -rf data/bronze/checkpoint*.json