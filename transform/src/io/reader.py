"""
reader.py - Đọc và hợp nhất dữ liệu từ nhiều nguồn (TopCV, ITviec...)
Mỗi nguồn có thư mục riêng trong data/bronze/{source}/
Với mỗi nguồn, đọc các file: jobs_all.json, jobs_detail.json, job_text_final.json (nếu có)
Sau đó chuẩn hóa qua source_normalizer và hợp nhất thành list records.
"""

import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Set

from .source_normalizer import normalize_record

logger = logging.getLogger(__name__)


def normalize_url(url: Optional[str]) -> Optional[str]:
    """
    Chuẩn hóa URL: loại bỏ tham số truy vấn để dùng làm khóa chính.
    Ví dụ: 'https://.../job/123.html?ta_source=...' -> 'https://.../job/123.html'
    """
    if not url:
        return None
    idx = url.find('?')
    if idx == -1:
        return url
    return url[:idx]


def load_json(file_path: Path) -> List[Dict[str, Any]]:
    """
    Tải file JSON, trả về list rỗng nếu file không tồn tại hoặc lỗi định dạng.
    """
    if not file_path.exists():
        logger.debug(f"File not found: {file_path}")
        return []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not isinstance(data, list):
                logger.warning(f"File {file_path} does not contain a list. Skipping.")
                return []
            return data
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {file_path}: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error reading {file_path}: {e}")
        return []


def merge_source_records(
    source_dir: Path,
    source_name: str,
    jobs_all_file: str = "jobs_all.json",
    jobs_detail_file: str = "jobs_detail.json",
    job_text_file: str = "job_text_final.json"
) -> List[Dict[str, Any]]:
    """
    Hợp nhất dữ liệu từ 3 file Bronze của một nguồn cụ thể.
    Trả về danh sách các record đã được chuẩn hóa (normalize_record).
    """
    logger.info(f"Processing source: {source_name}")

    # 1. Đọc 3 file
    path_all = source_dir / jobs_all_file
    path_detail = source_dir / jobs_detail_file
    path_text = source_dir / job_text_file

    list_data = load_json(path_all)
    detail_data = load_json(path_detail)
    text_data = load_json(path_text)

    logger.info(f"  Loaded: list={len(list_data)}, detail={len(detail_data)}, text={len(text_data)}")

    # 2. Tạo tập hợp tất cả normalized_url duy nhất
    all_urls: Set[str] = set()

    for item in list_data:
        url = item.get('url')
        norm = normalize_url(url)
        if norm:
            all_urls.add(norm)

    for item in detail_data:
        norm = item.get('normalized_url')
        if norm:
            all_urls.add(norm)

    for item in text_data:
        norm = item.get('normalized_url')
        if norm:
            all_urls.add(norm)

    logger.info(f"  Total unique URLs for {source_name}: {len(all_urls)}")

    # 3. Khởi tạo dict trung gian (key = normalized_url)
    merged: Dict[str, Dict[str, Any]] = {}
    for url in all_urls:
        merged[url] = {
            'normalized_url': url,
            'url': url,
        }

    # 4. Hàm cập nhật (không ghi đè các trường đã có giá trị khác rỗng)
    def update_record(target: Dict[str, Any], source: Dict[str, Any], skip_empty: bool = True):
        for key, value in source.items():
            if key == 'normalized_url':
                continue
            if skip_empty and (value is None or value == '' or (isinstance(value, str) and not value.strip())):
                continue
            current = target.get(key)
            if current is None or current == '' or (isinstance(current, str) and not current.strip()):
                target[key] = value

    # 5. Đổ dữ liệu từ jobs_all
    for item in list_data:
        norm = normalize_url(item.get('url'))
        if norm and norm in merged:
            item_copy = item.copy()
            item_copy['url'] = item.get('url')
            update_record(merged[norm], item_copy, skip_empty=True)

    # 6. Cập nhật từ jobs_detail (ưu tiên)
    for item in detail_data:
        norm = item.get('normalized_url')
        if norm and norm in merged:
            if 'url' not in item or not item.get('url'):
                item['url'] = norm
            update_record(merged[norm], item, skip_empty=True)

    # 7. Thêm text từ job_text_final
    for item in text_data:
        norm = item.get('normalized_url')
        if norm and norm in merged:
            text_fields = {
                'description': item.get('description', ''),
                'requirements': item.get('requirements', ''),
                'benefits': item.get('benefits', ''),
                'crawled_at': item.get('crawled_at')
            }
            update_record(merged[norm], text_fields, skip_empty=True)

    # 8. Chuyển dict thành list và chuẩn hóa một số trường
    raw_records: List[Dict[str, Any]] = []
    for url, record in merged.items():
        # Nếu không có job_id, thử lấy từ URL
        if 'id' not in record or not record.get('id'):
            match = re.search(r'/(\d+)\.html', url)
            if match:
                record['id'] = match.group(1)

        # Đảm bảo có source (nếu chưa có, gán từ source_name)
        if 'source' not in record or not record.get('source'):
            record['source'] = source_name

        # Đảm bảo title không rỗng
        if not record.get('title') or record['title'].strip() == '':
            record['title'] = f"Job {record.get('id', 'unknown')}"

        raw_records.append(record)

    # 9. Chuẩn hóa từng record qua source_normalizer
    normalized_records = []
    for record in raw_records:
        try:
            normalized = normalize_record(record, source_name)
            normalized_records.append(normalized)
        except Exception as e:
            logger.error(f"Error normalizing record from {source_name}: {e} — record: {record.get('url')}")
            # Vẫn giữ record thô nhưng đánh dấu lỗi? Tốt hơn là bỏ qua để pipeline không crash
            # Tuy nhiên, để an toàn, ta có thể thêm record thô với source đã set
            # Nhưng nếu normalizer lỗi, ta có thể log và bỏ qua record đó.
            # Ở đây tôi chọn bỏ qua (vì normalizer không nên lỗi).
            pass

    logger.info(f"  Source {source_name}: {len(normalized_records)} records after normalization")
    return normalized_records


def merge_data(
    bronze_dir: Path,
    source_subdirs: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Hợp nhất dữ liệu từ tất cả các nguồn trong thư mục bronze.
    
    Args:
        bronze_dir: Đường dẫn đến thư mục bronze gốc (ví dụ: Path('data/bronze'))
        source_subdirs: Danh sách tên thư mục con cần đọc (mặc định: ['topcv', 'itviec'])
    
    Returns:
        List[Dict[str, Any]]: Danh sách các bản ghi đã chuẩn hóa (Bronze Contract).
    """
    logger.info("=" * 40)
    logger.info("Starting multi-source data merge from Bronze layer")
    logger.info(f"Bronze directory: {bronze_dir}")

    if not bronze_dir.exists():
        logger.error(f"Bronze directory not found: {bronze_dir}")
        return []

    # Xác định danh sách thư mục con cần đọc
    if source_subdirs is None:
        # Mặc định: topcv và itviec (nếu tồn tại)
        default_sources = ['topcv', 'itviec']
        source_subdirs = [s for s in default_sources if (bronze_dir / s).exists()]
    else:
        # Chỉ lấy những thư mục tồn tại
        source_subdirs = [s for s in source_subdirs if (bronze_dir / s).exists()]

    if not source_subdirs:
        logger.warning("No source directories found in bronze directory. Returning empty list.")
        return []

    all_records = []
    for source in source_subdirs:
        source_dir = bronze_dir / source
        records = merge_source_records(source_dir, source)
        all_records.extend(records)

    logger.info(f"Total merged records from all sources: {len(all_records)}")
    return all_records


# ===== TEST =====
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent.parent.parent
    bronze_dir = project_root / 'data' / 'bronze'

    if not bronze_dir.exists():
        logger.error(f"Bronze directory not found at {bronze_dir}")
    else:
        merged_data = merge_data(bronze_dir)
        logger.info(f"Sample record: {json.dumps(merged_data[0] if merged_data else {}, indent=2, ensure_ascii=False)[:1000]}...")
        logger.info(f"Total records: {len(merged_data)}")