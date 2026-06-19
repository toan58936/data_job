"""
writer.py - Ghi dữ liệu Silver ra file
"""
import logging
from pathlib import Path
from typing import List, Union, Dict, Any

import pandas as pd

from ..schemas.silver_schema import SilverJob

logger = logging.getLogger(__name__)


def write_silver(
    records: List[Union[SilverJob, Dict[str, Any]]],
    output_path: Path,
    format: str = "parquet"
) -> None:
    """
    Ghi danh sách các bản ghi Silver xuống file.

    Args:
        records: Danh sách các đối tượng SilverJob hoặc dict
        output_path: Đường dẫn đến file output (ví dụ: ./data/silver/jobs_silver.parquet)
        format: Định dạng đầu ra ("parquet" hoặc "csv")

    Raises:
        ValueError: Nếu format không hỗ trợ
        Exception: Nếu ghi file thất bại
    """
    if not records:
        logger.warning("No records to write. Skipping.")
        return

    # Chuyển đổi từ SilverJob objects sang list of dict
    if isinstance(records[0], SilverJob):
        data = [record.to_dict() for record in records]
    else:
        data = records  # Đã là list of dict

    # Tạo DataFrame
    df = pd.DataFrame(data)

    # Đảm bảo thư mục output tồn tại
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Ghi theo định dạng
    if format.lower() == "parquet":
        # Cần cài pyarrow hoặc fastparquet
        df.to_parquet(output_path, index=False, engine='pyarrow')
        logger.info(f"Written {len(df)} records to Parquet: {output_path}")

    elif format.lower() == "csv":
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        logger.info(f"Written {len(df)} records to CSV: {output_path}")

    else:
        raise ValueError(f"Unsupported format: {format}. Use 'parquet' or 'csv'.")


# ===== TEST =====
if __name__ == "__main__":
    # Tạo dữ liệu mẫu để test
    from ..schemas.silver_schema import SilverJob
    from datetime import datetime

    sample = SilverJob(
        job_id="123",
        title="Test Job",
        company="Test Company",
        location_clean="Hà Nội",
        salary_min=10.0,
        salary_max=15.0,
        currency="VND",
        is_negotiable=False,
        exp_min=2,
        exp_max=4,
        skills=["python", "sql"],
        crawled_at=datetime.now()
    )

    # Ghi thử vào thư mục tạm
    temp_dir = Path(__file__).parent.parent.parent.parent / "data" / "silver"
    temp_dir.mkdir(parents=True, exist_ok=True)
    test_path = temp_dir / "test_silver.parquet"

    write_silver([sample], test_path, format="parquet")
    print(f"Test written to {test_path}")