"""
config_loader.py - Load và parse config.yaml
"""
import yaml
from pathlib import Path
from typing import Dict, Any

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "config.yaml"


def load_config(config_path: Path = None) -> Dict[str, Any]:
    """Load config từ file YAML."""
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH
    if not config_path.exists():
        # Nếu không có file config, trả về config mặc định (hardcoded)
        return get_default_config()
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def get_default_config() -> Dict[str, Any]:
    """Trả về config mặc định nếu không có file."""
    return {
        "pipeline": {
            "bronze_dir": "data/bronze",
            "silver_dir": "data/silver",
            "gold_dir": "data/gold",
            "output_format": "parquet"
        },
        "gold": {
            "enabled": True,
            "output_dir": "data/gold"
        },
        "quality": {
            "completeness": {
                "warning_threshold": 0.90,
                "error_threshold": 0.70,
                "field_overrides": {
                    "salary_min": 0.15,
                    "salary_max": 0.15,
                    "deadline": 0.50,
                    "normalized_role": 0.55,
                    "skills": 0.75
                }
            },
            "validity": {
                "warning_threshold": 5,
                "error_threshold": 20
            },
            "enabled_stages": ["completeness", "validity", "accuracy", "uniqueness", "timeliness"],
            "report_formats": ["markdown", "json"],
            "report_dir": "data/quality",
            "stop_on_error": False
        },
        "crawler": {
            "roles": ["data-engineer", "data-analyst", "data-scientist", "business-intelligence"]
        }
    }