"""
main.py - Entry point cho Transform pipeline
"""
import sys
import logging
from pathlib import Path

# Đảm bảo có thể import từ src
sys.path.insert(0, str(Path(__file__).parent))

from transform.src.orchestrator.pipeline import run_pipeline

# Thiết lập logging cấu hình (tạm thời, có thể dùng logger của utils)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger(__name__)


def main():
    """
    Hàm chính, xử lý tham số dòng lệnh và gọi pipeline.
    """
    # (Tùy chọn) Có thể dùng argparse để nhận tham số
    # import argparse
    # parser = argparse.ArgumentParser(description="Run Silver Transform Pipeline")
    # parser.add_argument("--bronze-dir", type=Path, default=None, help="Path to Bronze directory")
    # parser.add_argument("--silver-file", type=Path, default=None, help="Path to Silver output file")
    # parser.add_argument("--format", choices=["parquet", "csv"], default="parquet", help="Output format")
    # args = parser.parse_args()

    # Gọi pipeline với tham số mặc định
    exit_code = run_pipeline(
        bronze_dir=None,   # Sẽ dùng mặc định
        silver_file=None,  # Sẽ dùng mặc định
        output_format="parquet"
    )

    if exit_code == 0:
        logger.info("Pipeline finished successfully.")
    else:
        logger.error(f"Pipeline failed with exit code {exit_code}.")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()