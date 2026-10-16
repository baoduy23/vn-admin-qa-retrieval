"""Xử lý chữ dùng chung cho phần trả lời (Quân).

So khớp giữa câu hỏi và đoạn luật làm ở mức ÂM TIẾT, dạng bỏ dấu + chữ thường, để câu gõ
không dấu ("dang ky khai sinh") vẫn khớp với văn bản có dấu. Hàm bỏ dấu dùng lại strip_accents
của TV3 (src/retrieval/query.py) để hai bên chuẩn hóa giống hệt nhau.
"""
from __future__ import annotations

import math
import re
from collections import Counter

from src.retrieval.query import clean_query, has_diacritics, strip_accents

WORD = re.compile(r"\w+", re.UNICODE)

# Hư từ và từ để hỏi: không mang nội dung nên bỏ khi chấm điểm dòng và khi tô sáng.
# Lọc trên dạng CÓ DẤU nếu câu hỏi có dấu: bỏ dấu thì "đang" trùng "đăng", "đó" trùng "độ".
# Không bỏ "người", "con", "cha", "mẹ" (người nước ngoài, nhận cha mẹ con là nội dung chính).
STOPWORDS = set("""
thì là có không được cần gì nào đâu bao lâu nhiêu mấy của cho và hay hoặc với ở tại để khi nếu làm
sao thế như những các một tôi em mình bạn ạ nhé vậy ai phải đi mà này đó ra vào lại rồi đã sẽ đang bị
theo về trong từ đến xong mất gồm phần việc muốn xin hỏi giúp ko k
""".split())
# Câu gõ không dấu: giữ lại các hư từ mà bỏ dấu sẽ trùng với chữ nội dung hay gặp trong hộ tịch
# ("dang" = đang / ĐĂNG ký, "do" = đó / độ, "ma" = mà / mã, "the" = thế / thẻ, "da" = đã / dân, "di" = đi / di trú)
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
    """IDF âm tiết tính trên các dòng của kho, để "khai sinh" nặng ký hơn "uy ban"."""

    def __init__(self, texts: list[str]):
        df = Counter()
        for t in texts:
            df.update(set(syllables(t)))
        self.n = max(len(texts), 1)
        self.df = df

    def __call__(self, s: str) -> float:
        return math.log((self.n + 1) / (self.df.get(s, 0) + 1)) + 1.0
