"""
reader.py - Đọc và hợp nhất dữ liệu từ 3 file Bronze
"""
import json
import os
import logging
from typing import List, Dict, Any, Optional, Set
from pathlib import Path

# Cấu hình logging (tạm thời, sau này sẽ dùng utils.logger)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


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
        logger.warning(f"File not found: {file_path}")
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


def merge_data(
    bronze_dir: Path,
    jobs_all_file: str = "jobs_all.json",
    jobs_detail_file: str = "jobs_detail.json",
    job_text_file: str = "job_text_final.json"
) -> List[Dict[str, Any]]:
    """
    Hợp nhất dữ liệu từ 3 file Bronze.

    Args:
        bronze_dir: Đường dẫn đến thư mục bronze (ví dụ: Path('data/bronze'))
        jobs_all_file: Tên file danh sách job
        jobs_detail_file: Tên file chi tiết job
        job_text_file: Tên file text job

    Returns:
        List[Dict[str, Any]]: Danh sách các bản ghi đã hợp nhất.
    """
    logger.info("=" * 40)
    logger.info("Starting data merge from Bronze layer")
    logger.info(f"Bronze directory: {bronze_dir}")

    # 1. Đọc 3 file
    path_all = bronze_dir / jobs_all_file
    path_detail = bronze_dir / jobs_detail_file
    path_text = bronze_dir / job_text_file

    list_data = load_json(path_all)
    detail_data = load_json(path_detail)
    text_data = load_json(path_text)

    logger.info(f"Loaded: list={len(list_data)}, detail={len(detail_data)}, text={len(text_data)}")

    # 2. Tạo tập hợp tất cả normalized_url duy nhất
    all_urls: Set[str] = set()

    # jobs_all chưa có normalized_url, cần tạo
    for item in list_data:
        url = item.get('url')
        norm = normalize_url(url)
        if norm:
            all_urls.add(norm)

    # jobs_detail và text đã có normalized_url
    for item in detail_data:
        norm = item.get('normalized_url')
        if norm:
            all_urls.add(norm)

    for item in text_data:
        norm = item.get('normalized_url')
        if norm:
            all_urls.add(norm)

    logger.info(f"Total unique URLs: {len(all_urls)}")

    # 3. Khởi tạo dict trung gian (key = normalized_url)
    merged: Dict[str, Dict[str, Any]] = {}
    for url in all_urls:
        merged[url] = {
            'normalized_url': url,
            # Các trường sẽ được điền dần
            'url': url,  # Dùng normalized_url làm url gốc nếu không có từ detail/list
        }

    # 4. Hàm cập nhật (không ghi đè các trường đã có giá trị khác rỗng)
    def update_record(target: Dict[str, Any], source: Dict[str, Any], skip_empty: bool = True):
        """Cập nhật target từ source. Nếu skip_empty=True, không ghi đè nếu source value rỗng/None."""
        for key, value in source.items():
            if key == 'normalized_url':
                continue  # Không ghi đè khóa chính
            if skip_empty and (value is None or value == '' or (isinstance(value, str) and not value.strip())):
                continue
            # Nếu target chưa có hoặc target empty và source không empty -> ghi đè
            current = target.get(key)
            if current is None or current == '' or (isinstance(current, str) and not current.strip()):
                target[key] = value

    # 5. Đổ dữ liệu từ jobs_all vào
    for item in list_data:
        norm = normalize_url(item.get('url'))
        if norm and norm in merged:
            # Lưu ý: jobs_all có các trường: title, company, location, salary, experience, url
            # Cần thêm url và normalized_url nếu chưa có
            item_copy = item.copy()
            item_copy['url'] = item.get('url')  # đảm bảo có url
            update_record(merged[norm], item_copy, skip_empty=True)

    # 6. Cập nhật/ghi đè từ jobs_detail (ưu tiên detail)
    for item in detail_data:
        norm = item.get('normalized_url')
        if norm and norm in merged:
            # Đảm bảo lấy cả 'url' nếu chưa có
            if 'url' not in item or not item.get('url'):
                item['url'] = norm
            update_record(merged[norm], item, skip_empty=True)

    # 7. Thêm description, requirements, benefits từ job_text_final
    for item in text_data:
        norm = item.get('normalized_url')
        if norm and norm in merged:
            # Chỉ lấy các trường text, không ghi đè các trường khác
            text_fields = {
                'description': item.get('description', ''),
                'requirements': item.get('requirements', ''),
                'benefits': item.get('benefits', ''),
                # Giữ nguyên crawled_at từ text nếu detail chưa có (thường có rồi)
                'crawled_at': item.get('crawled_at')
            }
            update_record(merged[norm], text_fields, skip_empty=True)

    # 8. Chuyển dict thành list và chuẩn hóa một số trường
    result: List[Dict[str, Any]] = []
    for url, record in merged.items():
        # Nếu không có job_id, thử lấy từ URL (dùng trong fallback)
        if 'id' not in record or not record.get('id'):
            # Thử lấy id từ URL (số cuối cùng trước .html)
            import re
            match = re.search(r'/(\d+)\.html', url)
            if match:
                record['id'] = match.group(1)

        # Đảm bảo luôn có source (sẽ được gán trong pipeline, nhưng để mặc định)
        if 'source' not in record or not record.get('source'):
            record['source'] = 'TopCV'

        # Đảm bảo title không bị rỗng (dùng normalized_url fallback)
        if not record.get('title') or record['title'].strip() == '':
            record['title'] = f"Job {record.get('id', 'unknown')}"

        result.append(record)

    logger.info(f"Merge completed: {len(result)} records")
    return result


# ===== TEST =====
if __name__ == "__main__":
    # Chạy thử nếu file này được thực thi trực tiếp
    from pathlib import Path

    # Giả định cấu trúc thư mục: file nằm ở transform/src/io/reader.py
    # Thì bronze_dir = project_root / 'data' / 'bronze'
    project_root = Path(__file__).parent.parent.parent.parent  # lên 4 cấp
    bronze_dir = project_root / 'data' / 'bronze'

    logger.info(f"Project root: {project_root}")
    logger.info(f"Bronze dir: {bronze_dir}")

    if not bronze_dir.exists():
        logger.error(f"Bronze directory not found at {bronze_dir}. Please check path.")
    else:
        merged_data = merge_data(bronze_dir)
        logger.info(f"Sample record: {json.dumps(merged_data[0] if merged_data else {}, indent=2, ensure_ascii=False)[:1000]}...")
        logger.info(f"Total records: {len(merged_data)}")