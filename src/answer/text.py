"""Xử lý chữ dùng chung cho phần trả lời (Quân).

Câu hỏi và đoạn luật được so ở mức âm tiết, bỏ dấu và viết thường, để câu gõ không dấu
("dang ky khai sinh") vẫn khớp với văn bản có dấu. Hàm bỏ dấu lấy strip_accents của TV3
(src/retrieval/query.py) cho hai bên chuẩn hoá giống nhau.
"""
from __future__ import annotations

import math
import re
from collections import Counter

from src.retrieval.query import clean_query, has_diacritics, strip_accents

WORD = re.compile(r"\w+", re.UNICODE)

# Hư từ, từ để hỏi: không mang nội dung nên bỏ qua khi chấm điểm dòng và khi tô sáng.
# Câu hỏi có dấu thì lọc trên bản có dấu, vì bỏ dấu thì "đang" trùng "đăng", "đó" trùng "độ".
# Giữ lại "người", "con", "cha", "mẹ" vì người nước ngoài, nhận cha mẹ con là nội dung chính.
STOPWORDS = set("""
thì là có không được cần gì nào đâu bao lâu nhiêu mấy của cho và hay hoặc với ở tại để khi nếu làm
sao thế như những các một tôi em mình bạn ạ nhé vậy ai phải đi mà này đó ra vào lại rồi đã sẽ đang bị
theo về trong từ đến xong mất gồm phần việc muốn xin hỏi giúp ko k
""".split())
# Câu gõ không dấu: không lọc mấy hư từ mà bỏ dấu đi thì trùng chữ hay gặp trong hộ tịch
# ("dang" là đang / đăng ký, "do" là đó / độ, "ma" là mà / mã, "the" là thế / thẻ, "da" là đã / dân, "di" là đi / di trú)
STOPWORDS_PLAIN = {strip_accents(w) for w in STOPWORDS} - {"dang", "do", "ma", "the", "da", "di"}


def syllables(text: str) -> list[str]:
    """Âm tiết dạng bỏ dấu, chữ thường: "Đăng ký khai sinh" → ["dang", "ky", "khai", "sinh"]."""
    return WORD.findall(strip_accents(clean_query(text)))


def content_syllables(text: str) -> list[str]:
    """Âm tiết mang nội dung (bỏ hư từ, từ để hỏi, số), trả về dạng bỏ dấu để so khớp."""
    t = clean_query(text)
    if has_diacritics(t):
        words = [w for w in WORD.findall(t.lower()) if w not in STOPWORDS]
        out = [strip_accents(w) for w in words]
    else:
        out = [w for w in WORD.findall(strip_accents(t)) if w not in STOPWORDS_PLAIN]
    return [w for w in out if not w.isdigit() and len(w) > 1]


class IDF:
    """IDF âm tiết tính trên từng dòng của kho, để "khai sinh" có trọng số cao hơn "uy ban"."""

    def __init__(self, texts: list[str]):
        df = Counter()
        for t in texts:
            df.update(set(syllables(t)))
        self.n = max(len(texts), 1)
        self.df = df

    def __call__(self, s: str) -> float:
        return math.log((self.n + 1) / (self.df.get(s, 0) + 1)) + 1.0
