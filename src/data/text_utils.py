"""Làm sạch văn bản thủ tục hành chính.

Mỗi rule có tên và được đếm số lần tác động (CleanLog), để báo cáo tiền xử lý
ghi được "rule nào đã sửa bao nhiêu chỗ" thay vì làm sạch kiểu hộp đen.

Nguyên tắc (theo hướng dẫn TV1, mục 5.2):
- Không lowercase, không bỏ dấu, không bỏ stopword ở bước này.
- Giữ nguyên số liệu, ngày tháng, số hiệu văn bản (123/2015/NĐ-CP).
"""
import re
import unicodedata
from collections import Counter

# Dòng rác của giao diện cổng thông tin. Chỉ xóa khi CẢ DÒNG khớp,
# để không lỡ tay xóa nội dung thật có chứa các chữ này.
BOILERPLATE_LINES = {
    "tải về", "tải xuống", "xem chi tiết", "xem thêm", "thu gọn", "in", "in trang",
    "chia sẻ", "đóng", "quay lại", "nộp hồ sơ", "nộp trực tuyến", "đăng nhập",
    "trang chủ", "hướng dẫn", "lượt xem", "mẫu đơn, tờ khai", "không có thông tin",
}

ZERO_WIDTH = re.compile(r"[​‌‍⁠﻿]")
CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
BULLET = re.compile(r"^\s*(?:[•●▪◦·•●▪–—*+]|-(?!\d))\s*")
MULTI_SPACE = re.compile(r"[ \t\u00a0\u2009\u202f]{2,}|[\t\u00a0\u2009\u202f]")   # 2+ khoảng trắng hoặc khoảng trắng lạ
SPACE_BEFORE_PUNCT = re.compile(r"\s+([,.;:!?)])")


class CleanLog:
    """Đếm số lần mỗi rule thay đổi văn bản."""

    def __init__(self):
        self.counts = Counter()

    def hit(self, rule, n=1):
        if n:
            self.counts[rule] += n

    def as_rows(self):
        return [{"rule": r, "hits": n} for r, n in self.counts.most_common()]


def _sub(pattern, repl, text, rule, log):
    new, n = pattern.subn(repl, text)
    if log is not None:
        log.hit(rule, n)
    return new


def normalize_line(line, log=None):
    """Chuẩn hóa một dòng: NFC, ký tự ẩn, khoảng trắng, gạch đầu dòng."""
    nfc = unicodedata.normalize("NFC", line)
    if log is not None and nfc != line:
        log.hit("unicode_nfc")
    s = _sub(ZERO_WIDTH, "", nfc, "zero_width_char", log)
    s = _sub(CONTROL, " ", s, "control_char", log)
    s = _sub(MULTI_SPACE, " ", s, "collapse_space", log).strip()
    s = _sub(SPACE_BEFORE_PUNCT, r"\1", s, "space_before_punct", log)
    if BULLET.match(s):
        s = BULLET.sub("- ", s, count=1)
        if log is not None:
            log.hit("bullet_to_dash")
    return s


def clean_lines(lines, log=None):
    """Làm sạch danh sách dòng: chuẩn hóa, bỏ dòng rỗng, rác và dòng lặp liền kề."""
    out = []
    for raw in lines:
        s = normalize_line(raw, log)
        if not s or s in {"-", "|"}:
            continue
        if s.lower().rstrip(":") in BOILERPLATE_LINES:
            if log is not None:
                log.hit("drop_boilerplate_line")
            continue
        if out and out[-1] == s:
            if log is not None:
                log.hit("drop_repeated_line")
            continue
        out.append(s)
    return out


def clean_text(text, log=None):
    return "\n".join(clean_lines(text.splitlines(), log))


def count_syllables(text):
    """Số âm tiết (tách theo khoảng trắng, bỏ dấu câu đứng riêng)."""
    return len(re.findall(r"\w+", text))
