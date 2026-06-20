"""
skills.py - Trích xuất kỹ năng (có lọc stopwords và nhiễu)
"""

import re
from typing import List, Optional

# Import stopwords và danh sách từ khóa từ config
from ..utils.config import SKILL_KEYWORDS, STOPWORDS_VI, DOMAIN_KEYWORDS, COMPANY_NAMES_TO_FILTER


def _make_pattern(keyword: str) -> str:
    """
    Tạo regex pattern cho một keyword, xử lý đúng cả 2 trường hợp:

    1. Keyword thông thường ('python', 'spark', 'ml'):
       Dùng lookaround (?<![a-zA-Z0-9]) ... (?![a-zA-Z0-9]) thay vì \b.
       Lý do: \b không hoạt động với keyword chứa ký tự đặc biệt như
       c++ hay c# (vì + và # là non-word char, \b bị hiểu sai boundary).
       Lookaround không phụ thuộc vào loại ký tự nên stable hơn.

    2. Keyword nhiều từ ('power bi', 'machine learning', 'rest api'):
       Split theo space, escape từng phần, nối bằng \\s+ để bắt được
       cả "Power  BI" hay "machine  learning" (nhiều space).
    """
    if " " in keyword:
        parts = keyword.split(" ")
        inner = r'\s+'.join(re.escape(p) for p in parts)
        return r'(?<![a-zA-Z0-9])' + inner + r'(?![a-zA-Z0-9])'
    else:
        return r'(?<![a-zA-Z0-9])' + re.escape(keyword) + r'(?![a-zA-Z0-9])'


def extract_skills(
    title: Optional[str],
    description: Optional[str],
    requirements: Optional[str],
    skill_keywords: List[str]
) -> List[str]:
    """
    Trích xuất danh sách kỹ năng từ title, description, requirements.

    Các cải tiến:
    - Sử dụng stopwords tiếng Việt để loại bỏ nhiễu.
    - Chỉ giữ lại các token có chữ hoa hoặc số hoặc nằm trong skill_keywords.
    - Loại bỏ các kỹ năng trùng với DOMAIN_KEYWORDS.
    - Loại bỏ các tên công ty.
    """
    # 1. Gộp văn bản
    texts = []
    if title:
        texts.append(title)
    if description:
        texts.append(description)
    if requirements:
        texts.append(requirements)

    if not texts:
        return []

    full_text = " ".join(texts).lower()

    # 2. Tách từ và cụm từ (unigrams, bigrams, trigrams)
    # Token pattern: chỉ giữ từ có chữ cái, số, dấu gạch nối
    token_pattern = re.compile(r'[a-z0-9]+(?:[-_][a-z0-9]+)*')
    tokens = token_pattern.findall(full_text)

    # 3. Lọc token: bỏ stopwords tiếng Việt, tên công ty, và token quá ngắn
    filtered_tokens = []
    for t in tokens:
        if len(t) < 3:  # Bỏ token quá ngắn
            continue
        if t in STOPWORDS_VI:  # Bỏ stopwords tiếng Việt
            continue
        if t in COMPANY_NAMES_TO_FILTER:  # Bỏ tên công ty
            continue
        # Ưu tiên token có chữ hoa (tên riêng) hoặc số
        # Ở đây ta đã lower hết, nên kiểm tra token có thể là kỹ năng thực tế
        # bằng cách kiểm tra token có nằm trong SKILL_KEYWORDS không
        if t in skill_keywords:
            filtered_tokens.append(t)
        else:
            # Nếu không nằm trong skill_keywords, kiểm tra có phải từ tiếng Anh không
            # Giữ lại nếu token có chữ hoa hoặc số (đã lower hết nên không phân biệt)
            # Ta giữ lại token nếu độ dài >= 4 và không bị loại bỏ ở trên
            if len(t) >= 4:
                filtered_tokens.append(t)

    # 4. Trích xuất kỹ năng bằng regex với các từ khóa
    # Đây là cách truyền thống, nhưng ta sẽ ưu tiên dùng filtered_tokens để giảm nhiễu
    found_skills = set()

    # Cách 1: Dùng filtered_tokens để tìm kiếm trực tiếp trong các từ khóa
    # Kiểm tra từng token có nằm trong skill_keywords không
    for token in filtered_tokens:
        if token in skill_keywords:
            found_skills.add(token)

    # Cách 2: Dùng regex để bắt các cụm từ nhiều từ (bigrams, trigrams)
    # Tạo danh sách các cụm từ từ full_text
    words = full_text.split()
    # Bigrams
    for i in range(len(words) - 1):
        gram = ' '.join(words[i:i+2])
        if gram in skill_keywords:
            # Kiểm tra xem gram có chứa stopwords hoặc tên công ty không
            parts = gram.split()
            if not any(p in STOPWORDS_VI or p in COMPANY_NAMES_TO_FILTER for p in parts):
                found_skills.add(gram)
    # Trigrams
    for i in range(len(words) - 2):
        gram = ' '.join(words[i:i+3])
        if gram in skill_keywords:
            parts = gram.split()
            if not any(p in STOPWORDS_VI or p in COMPANY_NAMES_TO_FILTER for p in parts):
                found_skills.add(gram)

    # 5. Loại bỏ các kỹ năng trùng với DOMAIN_KEYWORDS (để tránh nhiễu)
    domain_set = set(DOMAIN_KEYWORDS)
    found_skills = found_skills - domain_set

    # 6. Sắp xếp kết quả
    return sorted(list(found_skills))