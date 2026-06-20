"""
main.py - Entry point cho Transform pipeline
"""
import sys
import logging
import argparse
from pathlib import Path

# Đảm bảo có thể import từ src
sys.path.insert(0, str(Path(__file__).parent))

from transform.src.orchestrator.pipeline import run_pipeline

# Thiết lập logging
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
    parser = argparse.ArgumentParser(description="Run Silver Transform Pipeline")
    parser.add_argument(
        "--format",
        choices=["parquet", "csv"],
        default="parquet",
        help="Output format (parquet or csv)"
    )
    parser.add_argument(
        "--bronze-dir",
        type=Path,
        default=None,
        help="Path to Bronze directory"
    )
    parser.add_argument(
        "--silver-file",
        type=Path,
        default=None,
        help="Path to Silver output file"
    )
    args = parser.parse_args()

    # Gọi pipeline với tham số từ CLI
    exit_code = run_pipeline(
        bronze_dir=args.bronze_dir,
        silver_file=args.silver_file,
        output_format=args.format
    )

    if exit_code == 0:
        logger.info("Pipeline finished successfully.")
    else:
        logger.error(f"Pipeline failed with exit code {exit_code}.")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()