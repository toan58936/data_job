"""
main.py - Entry point cho Transform pipeline
"""
import sys
import logging

from transform.src.orchestrator.pipeline import run_pipeline

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

def main():
    exit_code = run_pipeline(
        bronze_dir=None,
        silver_file=None,
        output_format="parquet"
    )
    if exit_code == 0:
        logger.info("Pipeline finished successfully.")
    else:
        logger.error(f"Pipeline failed with exit code {exit_code}.")
    sys.exit(exit_code)

if __name__ == "__main__":
    main()