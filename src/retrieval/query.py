"""Chuẩn hóa câu hỏi trước khi truy hồi (TV3, issue #7).

Câu hỏi phải chuẩn hoá giống hệt kho: NFC, kiểu bỏ dấu mới (normalize_tone, hoà thành hòa), bỏ ký tự ẩn,
gộp khoảng trắng (normalize_line). Model nào nhận văn bản đã tách từ (PhoBERT, bkai, PhoRanker) thì câu hỏi
cũng tách bằng đúng hàm segment() đã dùng để tạo cột text_seg.

Người dùng hay gõ không dấu ("dang ky khai sinh"), nên has_diacritics() dùng để chọn chỉ mục BM25 bỏ dấu.
Với bi-encoder / cross-encoder thì model_input(..., restore=True) khôi phục dấu trước (src/retrieval/restore.py).
"""
from __future__ import annotations

import unicodedata

from src.data.text_utils import normalize_line, normalize_tone


def clean_query(question: str) -> str:
    """NFC, kiểu bỏ dấu mới, bỏ ký tự ẩn, gộp khoảng trắng. Không lowercase (BM25 tự lower)."""
    return normalize_line(question or "")


def strip_accents(text: str) -> str:
    """Bỏ dấu tiếng Việt, đổi đ thành d, viết thường."""
    s = normalize_tone(text).lower().replace("đ", "d")
    s = "".join(ch for ch in unicodedata.normalize("NFD", s) if not unicodedata.combining(ch))
    return unicodedata.normalize("NFC", s)


def has_diacritics(text: str) -> bool:
    """True nếu câu có ít nhất một chữ có dấu hoặc chữ đ."""
    return strip_accents(text) != normalize_tone(text).lower()


def model_input(question: str, segment: bool, prefix: str = "", restore: bool = False) -> str:
    """Biến câu hỏi thành chuỗi đưa vào bi-encoder / cross-encoder.
    segment=True thì tách từ bằng src.data.chunk.segment (cùng hàm đã tạo text_seg).
    restore=True thì mở rộng từ viết tắt, câu không dấu thì khôi phục dấu (src/retrieval/restore.py)."""
    if restore:
        from src.retrieval.restore import restore_query    # import muộn: dựng bảng n-gram từ kho
        q = restore_query(question)
    else:
        q = clean_query(question)
    if segment:
        from src.data.chunk import segment as seg       # import muộn: underthesea nạp lâu
        q = seg(q)
    return prefix + q
