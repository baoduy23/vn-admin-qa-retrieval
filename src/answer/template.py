"""Mẫu câu trả lời trích nguyên văn kèm nguồn (Quân).

    Theo <tên văn bản>, Điều <X> Khoản <Y>: "<trích nguyên văn>"

Câu trả lời KHÔNG sinh chữ mới: phần trích lấy nguyên văn từ display_text của chunk, chỉ chọn
ra dòng (khoản / điểm) khớp câu hỏi nhất. Chữ do hệ thống thêm chỉ là khung "Theo ..., Điều ...".
Nhờ vậy câu trả lời luôn faithful với nguồn, rủi ro còn lại là chọn sai đoạn (đo bằng "đúng nguồn").
"""
from __future__ import annotations

import html
import re

from src.answer.text import IDF, content_syllables, syllables
from src.retrieval.query import strip_accents

KHOAN_LINE = re.compile(r"^\s*(\d+)\.\s")          # "2. Người yêu cầu ..."
DIEM_LINE = re.compile(r"^\s*([a-zđ])\)\s")         # "a) Giấy chứng sinh ..."
MAX_QUOTE_WORDS = 90


def dieu_number(chunk: dict) -> str:
    return str(chunk.get("dieu") or "").strip()


def citation(chunk: dict, quote_lines: list[str] | None = None) -> str:
    """ "Điều 16 Khoản 1", "Điều 9 Khoản 2 Điểm a". Chunk mức Điều mà trích đúng 1 khoản thì ghi
    luôn số khoản đọc từ đầu dòng ("2. ..."), để người dùng mở văn bản gốc tìm nhanh hơn."""
    parts = [f"Điều {dieu_number(chunk)}"] if dieu_number(chunk) else []
    khoan, diem = chunk.get("khoan"), None
    if quote_lines:
        first = quote_lines[0]
        m = KHOAN_LINE.match(first)
        if not khoan and m:
            khoan = m.group(1)
        d = DIEM_LINE.match(first)
        if d:
            diem = d.group(1)
    if khoan:
        parts.append(f"Khoản {khoan}")
    if diem:
        parts.append(f"Điểm {diem}")
    return " ".join(parts)


def _lines(text: str) -> list[str]:
    return [l.strip() for l in (text or "").split("\n") if l.strip()]


def line_score(question_terms: set[str], line: str, idf: IDF) -> float:
    """Tổng IDF các âm tiết nội dung của câu hỏi có mặt trong dòng, chia nhẹ theo độ dài dòng."""
    words = set(syllables(line))
    hit = sum(idf(t) for t in question_terms if t in words)
    return hit / (1 + 0.01 * len(words))


def best_quote(question: str, chunk: dict, idf: IDF, prefer: re.Pattern | None = None,
               line_scorer=None) -> list[str]:
    """Chọn dòng (khoản hoặc điểm) khớp câu hỏi nhất trong display_text, giữ nguyên văn.
    - prefer: mẫu bằng chứng của loại câu hỏi (vd "60 ngày" cho câu hỏi thời hạn). Có dòng nào chứa nó
      thì chỉ chọn trong các dòng đó: hỏi "bao lâu" thì dòng "có giá trị 6 tháng" phải thắng dòng
      "không có giá trị khi sử dụng sai mục đích" dù dòng sau trùng nhiều chữ hơn.
    - Dòng chọn là điểm "a)" → thêm dòng dẫn ở trên ("1. Hồ sơ gồm:") để câu đọc được.
    - Dòng chọn kết thúc bằng ":" → thêm các điểm ngay sau, tới khi đủ MAX_QUOTE_WORDS.
    - line_scorer (src/answer/line_scorer.py): có thì chấm dòng bằng cross-encoder thay cho IDF."""
    lines = _lines(chunk.get("display_text", ""))
    if not lines:
        return []
    terms = set(content_syllables(question))
    if line_scorer is not None and len(lines) > 1:
        scores = line_scorer(question, chunk, lines)
    else:
        scores = [line_score(terms, l, idf) for l in lines]
    pool = [j for j, l in enumerate(lines) if prefer and prefer.search(l.lower())] or range(len(lines))
    i = max(pool, key=lambda j: (scores[j], -j))
    picked = [i]
    if DIEM_LINE.match(lines[i]):
        lead = next((j for j in range(i - 1, -1, -1) if lines[j].endswith(":")), None)
        if lead is not None:
            picked.insert(0, lead)
    if lines[i].endswith(":"):
        j = i + 1
        while j < len(lines) and DIEM_LINE.match(lines[j]):
            picked.append(j)
            j += 1
    out, n = [], 0
    for j in picked:
        w = len(lines[j].split())
        if out and n + w > MAX_QUOTE_WORDS:
            out.append("…")
            break
        out.append(lines[j])
        n += w
    return out


def format_answer(chunk: dict, quote_lines: list[str]) -> str:
    """Theo <tên văn bản>, Điều X Khoản Y: "<trích nguyên văn>" """
    cite = citation(chunk, quote_lines)
    quote = " ".join(quote_lines)
    where = f"{chunk['doc_title']}, {cite}" if cite else chunk["doc_title"]
    return f'Theo {where}: "{quote}"'


def highlight_html(text: str, question: str, quote_lines: list[str] | None = None) -> str:
    """Đoạn trích dạng HTML: âm tiết trùng câu hỏi bọc <mark>, các dòng được chọn làm câu trả lời
    bọc <span class="quote-line">. So khớp trên dạng bỏ dấu nên câu gõ không dấu vẫn tô được."""
    terms = set(content_syllables(question))
    chosen = set(quote_lines or [])

    def mark(line: str) -> str:
        out, last = [], 0
        for m in re.finditer(r"\w+", line):
            out.append(html.escape(line[last:m.start()]))
            w = m.group(0)
            out.append(f"<mark>{html.escape(w)}</mark>" if strip_accents(w) in terms else html.escape(w))
            last = m.end()
        out.append(html.escape(line[last:]))
        return "".join(out)

    rows = []
    for line in _lines(text):
        body = mark(line)
        rows.append(f'<span class="quote-line">{body}</span>' if line in chosen else body)
    return "<br>".join(rows)
