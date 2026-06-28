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
    """Chuẩn hóa URL: loại bỏ tham số truy vấn để dùng làm khóa chính."""
    if not url:
        return None
    idx = url.find('?')
    return url[:idx] if idx != -1 else url


def load_json(file_path: Path) -> List[Dict[str, Any]]:
    """Tải file JSON, trả về list rỗng nếu không tồn tại hoặc lỗi."""
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
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"Error reading {file_path}: {e}")
        return []


def merge_source_records(
    source_dir: Path,
    source_name: str,
    jobs_all_file: str = "jobs_all.json",
    jobs_detail_file: str = "jobs_detail.json",
    job_text_file: str = "job_text_final.json"
) -> List[Dict[str, Any]]:
    """Hợp nhất dữ liệu từ 3 file Bronze của một nguồn cụ thể."""
    logger.info(f"Processing source: {source_name}")

    path_all = source_dir / jobs_all_file
    path_detail = source_dir / jobs_detail_file
    path_text = source_dir / job_text_file

    list_data = load_json(path_all)
    detail_data = load_json(path_detail)
    text_data = load_json(path_text)

    logger.info(f"  Loaded: list={len(list_data)}, detail={len(detail_data)}, text={len(text_data)}")

    all_urls: Set[str] = set()
    for item in list_data:
        norm = normalize_url(item.get('url')) or normalize_url(item.get('job_url'))
        if norm:
            all_urls.add(norm)
    for item in detail_data:
        norm = item.get('normalized_url') or normalize_url(item.get('job_url')) or normalize_url(item.get('url'))
        if norm:
            all_urls.add(norm)
    for item in text_data:
        norm = item.get('normalized_url') or normalize_url(item.get('job_url')) or normalize_url(item.get('url'))
        if norm:
            all_urls.add(norm)

    logger.info(f"  Total unique URLs for {source_name}: {len(all_urls)}")

    merged: Dict[str, Dict[str, Any]] = {url: {'normalized_url': url, 'url': url} for url in all_urls}

    def update_record(target: Dict[str, Any], source: Dict[str, Any], skip_empty: bool = True):
        for key, value in source.items():
            if key == 'normalized_url':
                continue
            if skip_empty and (value is None or value == '' or (isinstance(value, str) and not value.strip())):
                continue
            current = target.get(key)
            if current is None or current == '' or (isinstance(current, str) and not current.strip()):
                target[key] = value

    for item in list_data:
        norm = normalize_url(item.get('url')) or normalize_url(item.get('job_url'))
        if norm and norm in merged:
            item_copy = item.copy()
            item_copy['url'] = item.get('url') or item.get('job_url')
            update_record(merged[norm], item_copy)

    for item in detail_data:
        norm = item.get('normalized_url') or normalize_url(item.get('job_url')) or normalize_url(item.get('url'))
        if norm and norm in merged:
            if 'url' not in item or not item.get('url'):
                item['url'] = norm
            update_record(merged[norm], item)

    for item in text_data:
        norm = item.get('normalized_url') or normalize_url(item.get('job_url')) or normalize_url(item.get('url'))
        if norm and norm in merged:
            text_fields = {
                'description': item.get('description', ''),
                'requirements': item.get('requirements', ''),
                'benefits': item.get('benefits', ''),
                'crawled_at': item.get('crawled_at')
            }
            update_record(merged[norm], text_fields)

    raw_records: List[Dict[str, Any]] = []
    for url, record in merged.items():
        if 'id' not in record or not record.get('id'):
            match = re.search(r'/(\d+)\.html', url)
            if match:
                record['id'] = match.group(1)
        if 'source' not in record or not record.get('source'):
            record['source'] = source_name
        if not record.get('title') or record['title'].strip() == '':
            record['title'] = f"Job {record.get('id', 'unknown')}"
        raw_records.append(record)

    normalized_records = []
    for record in raw_records:
        try:
            normalized = normalize_record(record, source_name)
            normalized_records.append(normalized)
        except Exception as e:
            logger.error(f"Error normalizing record from {source_name}: {e}")
    logger.info(f"  Source {source_name}: {len(normalized_records)} records after normalization")
    return normalized_records


def merge_data(
    bronze_dir: Path,
    source_subdirs: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Hợp nhất dữ liệu từ tất cả các nguồn trong thư mục bronze.
    """
    logger.info("=" * 40)
    logger.info("Starting multi-source data merge from Bronze layer")
    logger.info(f"Bronze directory: {bronze_dir}")

    if not bronze_dir.exists():
        logger.error(f"Bronze directory not found: {bronze_dir}")
        return []

    if source_subdirs is None:
        default_sources = ['topcv', 'itviec']
        source_subdirs = [s for s in default_sources if (bronze_dir / s).exists()]

    if not source_subdirs:
        logger.warning("No source directories found. Returning empty list.")
        return []

    all_records = []
    for source in source_subdirs:
        source_dir = bronze_dir / source
        records = merge_source_records(source_dir, source)
        all_records.extend(records)

    logger.info(f"Total merged records from all sources: {len(all_records)}")
    return all_records