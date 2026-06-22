"""
test_fact_skill.py - Kiểm tra hàm build_fact_skills với dữ liệu thật
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

# Thêm đường dẫn gốc vào sys.path để có thể import module
repo_root = Path(r"D:\topcv-data-engineer")
sys.path.insert(0, str(repo_root))

# Import hàm cần test
from transform.src.gold.tables.fact_skills import build_fact_skills

# Đường dẫn file Parquet
silver_file = repo_root / "data" / "silver" / "jobs_silver.parquet"

# 1. Kiểm tra file tồn tại
if not silver_file.exists():
    print(f"❌ File không tồn tại: {silver_file}")
    sys.exit(1)

# 2. Đọc dữ liệu
print("📖 Đang đọc Parquet...")
df = pd.read_parquet(silver_file)
print(f"✅ Đọc được {len(df)} dòng từ Parquet.")

# 3. Kiểm tra cột skills
if 'skills' not in df.columns:
    print("❌ Cột 'skills' không tồn tại trong DataFrame!")
    sys.exit(1)

# 4. Kiểm tra mẫu skills
print("\n🔍 Mẫu skills (3 dòng đầu):")
for i in range(min(3, len(df))):
    val = df['skills'].iloc[i]
    print(f"  Dòng {i+1}: type={type(val)}, value={val}")

# 5. Đếm số job có skills không rỗng
mask = df['skills'].notna() & df['skills'].apply(
    lambda x: isinstance(x, (list, np.ndarray)) and len(x) > 0
)
print(f"\n📊 Số job có skills (không rỗng): {mask.sum()}/{len(df)}")

# 6. Chạy build_fact_skills
print("\n🔄 Đang chạy build_fact_skills...")
result = build_fact_skills(df)

print(f"\n✅ Kết quả: {len(result)} rows")
if not result.empty:
    print("\n📋 Mẫu 5 dòng đầu:")
    print(result.head())
    print("\n📊 Thông tin các cột:")
    print(result.info())
    print("\n📊 Thống kê week:")
    print(result['week'].value_counts().sort_index())
else:
    print("\n⚠️ DataFrame rỗng. Kiểm tra chi tiết:")
    # Kiểm tra từng bước bên trong hàm
    df_copy = df.copy()
    from transform.src.gold.tables.fact_skills import _normalize_skills
    df_copy['skills_normalized'] = df_copy['skills'].apply(_normalize_skills)
    mask2 = df_copy['skills_normalized'].apply(lambda x: len(x) > 0)
    print(f"  - Số job có skills sau normalize: {mask2.sum()}")
    if mask2.sum() == 0:
        # Lấy một vài giá trị để debug
        sample = df['skills'].iloc[0]
        print(f"  - Mẫu giá trị skills: {sample}")
        normalized_sample = _normalize_skills(sample)
        print(f"  - Kết quả normalize: {normalized_sample}")