"""Phân tích câu hỏi trước và sau truy hồi (Quân): câu nhiều ý, câu thiếu thông tin, câu dễ bịa.

Toàn bộ là luật (rule) đơn giản trên âm tiết, viết từ định nghĩa 7 loại câu trong guideline gán nhãn,
kiểm tra trên train + validation (không nhìn test):

- split_multi_intent: "Kết hôn cần giấy gì và nộp ở đâu?" → ["Kết hôn cần giấy gì", "Kết hôn nộp ở đâu"].
  Chỉ tách khi MỖI vế đều có từ để hỏi, để không cắt nhầm "cha và mẹ".
- expected_type + has_evidence: câu hỏi đòi một con số cụ thể (tiền, mức phạt, tuổi, thời hạn)
  mà đoạn tìm được không chứa con số loại đó thì từ chối, thay vì trích một đoạn "gần giống".
  Đây là cách chặn câu unsupported như "lệ phí ... bao nhiêu tiền" khi kho không có biểu phí.
- is_underspecified: câu quá ngắn và không nhắc việc hộ tịch nào → vẫn trả lời nhưng gợi ý hỏi rõ hơn.
- out_of_scope_topic: câu hỏi về lĩnh vực khác (hộ chiếu, căn cước, đất đai, thuế, bằng lái...) mà không
  nhắc việc hộ tịch nào → từ chối ngay, không truy hồi. Ngưỡng τ một mình không chặn được vì retrieve()
  luôn trả về đoạn "gần nhất", và với cross-encoder điểm đoạn đó vẫn có thể vượt τ.

So khớp CÓ DẤU khi câu hỏi có dấu, vì bỏ dấu thì nhiều từ trùng nhau: "đầu" và "đâu" cùng thành
"dau", "máy" và "mấy" cùng thành "may", "phát" và "phạt" cùng thành "phat". Câu gõ không dấu thì
đành so trên dạng bỏ dấu (Pattern tự sinh bản bỏ dấu từ mẫu có dấu).
"""
from __future__ import annotations

import re

from src.answer.text import content_syllables
from src.retrieval.query import clean_query, has_diacritics, strip_accents


class Pattern:
    """Regex viết có dấu; tự có thêm bản bỏ dấu cho câu gõ không dấu."""

    def __init__(self, accented: str):
        self.accented = re.compile(accented)
        self.plain = re.compile(strip_accents(accented))

    def search(self, text: str):
        t = clean_query(text)
        return (self.accented.search(t.lower()) if has_diacritics(t)
                else self.plain.search(strip_accents(t)))


# ---------------------------------------------------------------- câu nhiều ý
# "?" giữa câu cũng là ranh giới: "Khai sinh cần giấy gì? Kết hôn mất bao lâu?". Không tách theo "."
# vì số hiệu văn bản ("NĐ 123/2015", "Điều 5.") có dấu chấm. clean_query đã gộp xuống dòng thành dấu cách.
SEPARATOR = re.compile(r"\s*(?:,|;|\?\s+|\s(?:và|va|còn|rồi)\s)\s*", re.IGNORECASE)
QUESTION_WORD = Pattern(r"\b(gì|đâu|bao lâu|bao nhiêu|mấy|thế nào|ra sao|làm sao|ai|nào|khi nào)\b"
                        r"|\bkhông\s*\??$")
# Từ đánh dấu hết phần "chủ đề" ở đầu câu: "Khai sinh cho con | thì nộp ở đâu"
HEAD_STOP = set("thì cần phải nộp làm ở mất trong có được bao gì đâu ai mấy khi là hết từ".split())
HEAD_STOP |= {strip_accents(w) for w in HEAD_STOP}
MAX_PARTS = 3


def _is_question(piece: str) -> bool:
    return bool(QUESTION_WORD.search(piece.strip(" ?.")))


def topic_head(piece: str) -> str:
    """Phần chủ đề ở đầu vế đầu tiên, ghép vào các vế sau bị thiếu chủ ngữ."""
    words = piece.split()
    accented = has_diacritics(piece)
    head = []
    for i, w in enumerate(words):
        key = w.lower().strip(",.?") if accented else strip_accents(w).strip(",.?")
        if i > 0 and key in HEAD_STOP:
            break
        head.append(w)
    return " ".join(head) if 2 <= len(head) < len(words) else ""


def split_multi_intent(question: str) -> list[str]:
    """Tách câu hỏi nhiều ý thành các câu con. Câu một ý trả về [question]."""
    q = clean_query(question).strip()
    pieces = [p.strip(" ?.") for p in SEPARATOR.split(q) if p.strip(" ?.")]
    parts: list[str] = []
    for p in pieces:
        if parts and (not _is_question(p) or not _is_question(parts[-1])):
            parts[-1] = f"{parts[-1]}, {p}"        # một trong hai vế không phải câu hỏi: gộp lại
        else:
            parts.append(p)
    if len(parts) < 2:
        return [q]
    if len(parts) > MAX_PARTS:
        parts = parts[: MAX_PARTS - 1] + [", ".join(parts[MAX_PARTS - 1:])]
    head = topic_head(parts[0])
    out = [parts[0]]
    for p in parts[1:]:
        # vế đã tự nêu việc hộ tịch ("... ? Kết hôn mất bao lâu") thì không ghép chủ đề vế đầu vào
        if head and strip_accents(head) not in strip_accents(p) and not HOTICH_NAMES.search(p):
            p = f"{head} {p}"
        out.append(p)
    return out


# ---------------------------------------------------- loại đáp án và căn cứ
# (tên, mẫu nhận câu hỏi, mẫu bằng chứng phải có trong đoạn trích)
ANSWER_TYPES = [
    ("muc_phat",
     # Không nhận chữ "phạt" đơn lẻ: "án phạt tù" không hỏi mức phạt, và bản bỏ dấu "phat" khớp cả "phát"
     # ("phat hien sai sot" → đòi bằng chứng "phạt" → từ chối oan). Chỉ nhận cụm hỏi mức xử phạt.
     Pattern(r"\b(xử phạt|mức phạt|bị phạt(?!\s+(hiện|tù))|phạt bao nhiêu|phạt tiền|phạt hành chính|chế tài)\b"),
     re.compile(r"\bphạt\b")),
    ("so_tien",
     Pattern(r"\b(lệ phí|phí|tiền)\b.*\b(bao nhiêu|mấy|mức)\b|\b(bao nhiêu|mấy|mức)\b.*\b(lệ phí|phí|tiền)\b"),
     re.compile(r"\d[\d.,]*\s*(đồng|nghìn|ngàn|triệu)\b|miễn lệ phí|miễn thu|không thu lệ phí|không phải nộp lệ phí")),
    ("do_tuoi",
     Pattern(r"\b(bao nhiêu tuổi|mấy tuổi|độ tuổi|đủ tuổi)\b"),
     re.compile(r"\d+\s*tuổi")),
    ("thoi_han",
     Pattern(r"\b(bao lâu|mấy ngày|bao nhiêu ngày|thời hạn|hạn bao nhiêu|trong vòng)\b"),
     re.compile(r"\d+\s*(ngày|tháng|năm|giờ)\b|ngay trong ngày")),
]

TYPE_LABEL = {"muc_phat": "mức xử phạt", "so_tien": "số tiền / lệ phí",
              "do_tuoi": "độ tuổi", "thoi_han": "thời hạn"}


def expected_type(question: str) -> str | None:
    """Loại con số câu hỏi đòi, hoặc None nếu câu không hỏi con số cụ thể."""
    for name, ask, _ in ANSWER_TYPES:
        if ask.search(question):
            return name
    return None


def evidence_pattern(kind: str | None) -> re.Pattern | None:
    return next((ev for name, _, ev in ANSWER_TYPES if name == kind), None)


def has_evidence(kind: str | None, texts: list[str]) -> bool:
    """Ít nhất 1 đoạn trích chứa bằng chứng đúng loại (ví dụ "60 ngày" cho câu hỏi thời hạn).
    Đoạn luật luôn có dấu nên so trên chữ thường có dấu."""
    if kind is None:
        return True
    pattern = next(ev for name, _, ev in ANSWER_TYPES if name == kind)
    return any(pattern.search(clean_query(t).lower()) for t in texts)


# --------------------------------------------------- các việc hộ tịch
# Dùng cho 2 việc: nhận ra câu thiếu thông tin (không nhắc việc nào) và gom chủ đề trong thống kê.
PROCEDURES = [
    ("Khai sinh", r"khai sinh|giấy chứng sinh|trẻ bị bỏ rơi|sinh con|mới đẻ|mới sinh"),
    ("Kết hôn", r"kết hôn|lấy chồng|lấy vợ|vợ chồng"),
    ("Xác nhận tình trạng hôn nhân", r"tình trạng hôn nhân|độc thân"),
    ("Khai tử", r"khai tử|báo tử|qua đời|chết|mất tích"),
    ("Nhận cha, mẹ, con", r"nhận cha|nhận mẹ|nhận con|cha, mẹ, con|cha mẹ con"),
    ("Giám hộ", r"giám hộ"),
    ("Thay đổi, cải chính hộ tịch", r"thay đổi|cải chính|bổ sung thông tin|bổ sung hộ tịch|"
                                    r"xác định lại dân tộc|đổi tên|sửa (tên|thông tin|giấy)"),
    ("Ly hôn, hủy kết hôn", r"ly hôn|hủy việc kết hôn"),
    ("Trích lục, bản sao", r"trích lục|bản sao"),
    ("Đăng ký lại", r"đăng ký lại"),
    ("Hộ tịch điện tử, trực tuyến", r"trực tuyến|online|điện tử|cơ sở dữ liệu"),
]
_PROC = [(name, Pattern(rf"\b(?:{pat})")) for name, pat in PROCEDURES]
PROCEDURE_NAMES = [name for name, _ in PROCEDURES]


def find_procedures(text: str) -> list[str]:
    return [name for name, pat in _PROC if pat.search(text or "")]


def chunk_topic(chunk: dict) -> str:
    """Chủ đề của một đoạn luật cho thống kê: theo tên Mục, rồi tên Điều; không khớp → "Quy định chung"."""
    for field in ("muc_ten", "dieu_title"):
        hits = find_procedures(chunk.get(field) or "")
        if hits:
            return hits[0]
    if chunk.get("doc_id", "").startswith("87.2020"):
        return "Hộ tịch điện tử, trực tuyến"
    return "Quy định chung"


def is_underspecified(question: str, max_content: int = 5) -> bool:
    """Câu ngắn và không nhắc việc hộ tịch cụ thể nào: "Đăng ký mất bao lâu?"."""
    return not find_procedures(question) and len(content_syllables(question)) <= max_content


# --------------------------------------------------- câu ngoài phạm vi
# (tên lĩnh vực, mẫu). Chỉ từ chối khi câu KHÔNG nhắc việc hộ tịch nào (HOTICH_NAMES không khớp), để
# "làm khai sinh có cần căn cước không" hay "tạm trú ở Bình Dương làm khai sinh được không" vẫn được trả lời.
# Viết từ định nghĩa out_of_scope trong guideline gán nhãn và câu train + validation, không nhìn test.
OUT_OF_SCOPE = [
    ("hộ chiếu, xuất nhập cảnh", r"hộ chiếu|visa|thị thực|xuất cảnh|nhập cảnh"),
    ("căn cước, định danh", r"căn cước|cccd|cmnd|chứng minh nhân dân|định danh điện tử|vneid"),
    ("cư trú", r"đăng ký thường trú|đăng ký tạm trú|khai báo tạm trú|nhập hộ khẩu|tách hộ khẩu|chuyển hộ khẩu"),
    ("đất đai, nhà ở", r"đất đai|thửa đất|sử dụng đất|sổ đỏ|sổ hồng|nhà đất|mua nhà|bán nhà"),
    ("thuế", r"thuế"),
    ("giao thông", r"bằng lái|giấy phép lái xe|đăng ký xe|đăng kiểm|xe máy|ô tô"),
    ("quốc tịch", r"quốc tịch"),
    ("bảo hiểm, lao động", r"bảo hiểm xã hội|bhxh|lương hưu|hợp đồng lao động|thất nghiệp"),
    ("doanh nghiệp, kinh doanh", r"thành lập công ty|doanh nghiệp|đăng ký kinh doanh|hộ kinh doanh|"
                                 r"giấy phép kinh doanh|an toàn thực phẩm"),
]
# Có mẫu này thì từ chối dù câu có nhắc việc hộ tịch: phần đó thuộc luật khác hoặc ngoài kho.
# "Ly hôn thì tài sản chung chia thế nào?" nhắc ly hôn nhưng hỏi chia tài sản (Luật Hôn nhân và gia đình, tòa án).
OUT_OF_SCOPE_ALWAYS = [
    ("chia tài sản, cấp dưỡng khi ly hôn", r"tài sản chung|chia tài sản|cấp dưỡng|quyền nuôi con"),
    ("Luật Hộ tịch mới (hiệu lực 2027, chưa có trong kho)",
     r"luật hộ tịch (mới|năm 2026|năm 2027|2026|2027)|03/2026/qh16"),
]
_OOS = [(name, Pattern(rf"\b(?:{pat})")) for name, pat in OUT_OF_SCOPE]
_OOS_ALWAYS = [(name, Pattern(rf"\b(?:{pat})")) for name, pat in OUT_OF_SCOPE_ALWAYS]


# Tên việc hộ tịch "chắc chắn" dùng để tha cho câu có từ ngoài phạm vi. Không dùng cả PROCEDURES vì trong đó có
# từ đời thường ("chết", "vợ chồng", "thay đổi", "online"): "bố chết thì sổ đỏ sang tên thế nào" khớp "chết"
# → Khai tử → lọt lọc đất đai, dù câu hỏi chuyện sang tên đất.
HOTICH_NAMES = Pattern(r"\b(?:khai sinh|giấy chứng sinh|kết hôn|khai tử|báo tử|hộ tịch|tình trạng hôn nhân|"
                       r"nhận cha|nhận mẹ|nhận con|giám hộ|cải chính|trích lục|đăng ký lại|ly hôn|"
                       r"thay đổi họ|đổi tên|xác định lại dân tộc)")


def out_of_scope_topic(question: str) -> str | None:
    """Tên lĩnh vực ngoài hộ tịch mà câu hỏi nói tới, hoặc None nếu câu (có thể) thuộc phạm vi."""
    for name, pat in _OOS_ALWAYS:
        if pat.search(question):
            return name
    if HOTICH_NAMES.search(question):
        return None
    return next((name for name, pat in _OOS if pat.search(question)), None)
