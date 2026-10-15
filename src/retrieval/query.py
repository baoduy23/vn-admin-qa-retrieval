"""Chuẩn hóa câu hỏi trước khi truy hồi (TV3, issue #7).

Câu hỏi phải qua đúng phép chuẩn hóa đã dùng cho kho: NFC + kiểu bỏ dấu mới (normalize_tone,
hoà → hòa) + bỏ ký tự ẩn, gộp khoảng trắng (normalize_line). Mô hình nhận văn bản đã tách từ
(PhoBERT, bkai, PhoRanker) thì câu hỏi tách từ bằng đúng hàm segment() đã tạo cột text_seg.

Người dùng hay gõ không dấu ("dang ky khai sinh"): has_diacritics() để chọn chỉ mục BM25 bỏ dấu.
"""
from __future__ import annotations

import unicodedata

from src.data.text_utils import normalize_line, normalize_tone


def clean_query(question: str) -> str:
    """NFC, kiểu bỏ dấu mới, bỏ ký tự ẩn, gộp khoảng trắng. Không lowercase (BM25 tự lower)."""
    return normalize_line(question or "")


def strip_accents(text: str) -> str:
    """Bỏ dấu tiếng Việt, đ → d, lower."""
    s = normalize_tone(text).lower().replace("đ", "d")
    s = "".join(ch for ch in unicodedata.normalize("NFD", s) if not unicodedata.combining(ch))
    return unicodedata.normalize("NFC", s)


def has_diacritics(text: str) -> bool:
    """True nếu câu có ít nhất một chữ có dấu hoặc chữ đ."""
    return strip_accents(text) != normalize_tone(text).lower()


def model_input(question: str, segment: bool, prefix: str = "") -> str:
    """Câu hỏi → chuỗi đưa vào bi-encoder / cross-encoder.
    segment=True: tách từ bằng src.data.chunk.segment (cùng công cụ đã tạo text_seg)."""
    q = clean_query(question)
    if segment:
        from src.data.chunk import segment as seg       # import muộn: underthesea nạp lâu
        q = seg(q)
    return prefix + q
