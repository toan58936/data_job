.PHONY: help install crawl crawl-list crawl-detail crawl-text transform gold quality run dashboard test clean

help:
	@echo "Các lệnh có sẵn:"
	@echo "  make install       - Cài đặt Python + Node dependencies"
	@echo "  make crawl         - Crawl toàn bộ (list + detail + text)"
	@echo "  make crawl-list    - Chỉ crawl danh sách job (tất cả role trong config.yaml)"
	@echo "  make crawl-detail  - Chỉ crawl chi tiết job"
	@echo "  make crawl-text    - Chỉ crawl description/requirements/benefits"
	@echo "  make transform     - Transform Bronze -> Silver -> Gold + Quality"
	@echo "  make gold          - Chỉ build lại Gold layer từ Silver có sẵn"
	@echo "  make quality       - Chỉ chạy Data Quality checks"
	@echo "  make run           - Chạy full pipeline (crawl + transform)"
	@echo "  make dashboard     - Mở Streamlit dashboard"
	@echo "  make test          - Chạy test suite"
	@echo "  make clean         - Xóa checkpoint, log, Silver/Gold output"

# Toàn bộ lệnh đi qua cli.py — đây là entry point chuẩn duy nhất.
# makefile không tự gọi trực tiếp file .js hay module Python lẻ,
# để tránh lệch khi cli.py thay đổi cách điều phối (ví dụ: đổi crawler, đổi role list).

install:
	uv sync
	cd crawlers && npm install
	uv run npx playwright install chromium

crawl:
	uv run python cli.py crawl all

crawl-list:
	uv run python cli.py crawl list

crawl-detail:
	uv run python cli.py crawl detail

crawl-text:
	uv run python cli.py crawl text

transform:
	uv run python cli.py transform

gold:
	uv run python cli.py gold

quality:
	uv run python cli.py quality

run:
	uv run python cli.py run

dashboard:
	uv run streamlit run dashboard/app.py

test:
	uv run pytest transform/tests -v

clean:
	uv run python cli.py clean
