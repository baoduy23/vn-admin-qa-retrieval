"""Khôi phục dấu cho câu gõ không dấu, chỉ để đưa vào bi-encoder / cross-encoder (M5, cải tiến).

Bi-encoder (bkai) và PhoRanker học trên văn bản có dấu, nên hiểu rất kém câu "dang ky khai sinh can giay
to gi": câu không dấu trích đúng nguồn kém hẳn câu có dấu. BM25 không cần bước này vì câu không dấu đã
tìm trên chỉ mục bỏ dấu (retrieve.SparseIndex).

Cách làm, không cần model:
  - Bảng n-gram 1–3 âm tiết lấy từ chunk_text của kho và câu hỏi tập train. Mỗi dạng bỏ dấu ánh xạ về
    dạng có dấu gặp nhiều nhất: "dang ky" → "đăng ký".
  - Duyệt trái sang phải, ưu tiên cụm dài (3 → 2 → 1) vì cụm dài ít nhập nhằng: "toi" đứng một mình có
    thể là "tội" (chữ của luật), còn "toi muon" thì là "tôi muốn" (chữ của câu hỏi).
  - Âm tiết không có trong bảng thì giữ nguyên. Không ghép n-gram qua dấu câu.
  - Chỉ lấy câu hỏi train, không lấy validation / test: bảng này là "dữ liệu huấn luyện", lấy câu
    validation / test vào là lộ đáp án vào bước chọn tham số.
Thêm vài từ viết tắt hay gặp (ko → không, dc → được, j → gì...), áp cho mọi câu khi bật công tắc. Cố ý
không có "tp" (người ta gõ "tp" để chỉ "thành phố") và "bn" (vừa là "bạn" vừa là "bao nhiêu").

Bật / tắt: khóa restore_diacritics trong mục dense / rerank của configs/retrieval_selected.yaml, do
python -m src.retrieval.evaluate_models chọn trên validation (lưới query.restore_diacritics_grid).
"""
from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from functools import lru_cache

from src.data.split import ROOT
from src.data.text_utils import normalize_tone
from src.retrieval.query import clean_query, has_diacritics, strip_accents

MAX_N = 3
PUNCT = re.compile(r"([^\w\s]+)")
ABBREV = {
    "k": "không", "ko": "không", "kg": "không", "khg": "không", "hok": "không", "hk": "không",
    "dc": "được", "đc": "được", "j": "gì", "ntn": "như thế nào", "vs": "với", "cx": "cũng",
    "mk": "mình", "mik": "mình", "r": "rồi",
}


class Restorer:
    def __init__(self, texts: list[str], max_n: int = MAX_N):
        self.max_n = max_n
        counts = [defaultdict(Counter) for _ in range(max_n + 1)]
        for t in texts:
            for seg in PUNCT.split(normalize_tone(t or "").lower()):
                ws = seg.split()
                plain = [strip_accents(w) for w in ws]
                for n in range(1, max_n + 1):
                    for i in range(len(ws) - n + 1):
                        counts[n][" ".join(plain[i:i + n])][" ".join(ws[i:i + n])] += 1
        self.table = [{k: c.most_common(1)[0][0] for k, c in d.items()} for d in counts]

    def restore(self, text: str) -> str:
        """Thêm dấu cho từng cụm tìm được trong bảng, giữ nguyên dấu câu và chữ hoa đầu từ."""
        out = []
        for seg in PUNCT.split(text):
            ws = seg.split()
            if not ws or PUNCT.fullmatch(seg):
                out.append(seg)
                continue
            res, i = [], 0
            while i < len(ws):
                for n in range(min(self.max_n, len(ws) - i), 0, -1):
                    hit = self.table[n].get(" ".join(strip_accents(w) for w in ws[i:i + n]))
                    if hit:
                        res += [_keep_case(o, h) for o, h in zip(ws[i:i + n], hit.split())]
                        i += n
                        break
                else:
                    res.append(ws[i])
                    i += 1
            lead, trail = seg[:len(seg) - len(seg.lstrip())], seg[len(seg.rstrip()):]
            out.append(lead + " ".join(res) + trail)
        return "".join(out)


def _keep_case(orig: str, restored: str) -> str:
    if strip_accents(orig) == restored:          # chữ không có dấu nào để thêm (UBND, 2015): giữ nguyên
        return orig
    if orig.isupper() and len(orig) > 1:
        return restored.upper()
    return restored.capitalize() if orig[:1].isupper() else restored


def expand_abbrev(text: str) -> str:
    return re.sub(r"\w+", lambda m: ABBREV.get(m.group(0).lower(), m.group(0)), text)


def _train_questions() -> list[str]:
    try:
        with open(ROOT / "data/splits/train_qgroups.csv", encoding="utf-8-sig", newline="") as f:
            train = {r["question_group_id"] for r in csv.DictReader(f)}
        with open(ROOT / "data/labels/questions.csv", encoding="utf-8-sig", newline="") as f:
            return [r["question"] for r in csv.DictReader(f)
                    if r["question_group_id"] in train and has_diacritics(r["question"] or "")]
    except FileNotFoundError:
        return []


@lru_cache(maxsize=1)
def get_restorer() -> Restorer:
    with open(ROOT / "data/processed/chunks.jsonl", encoding="utf-8") as f:
        texts = [json.loads(line)["chunk_text"] for line in f if line.strip()]
    return Restorer(texts + _train_questions())


def restore_query(question: str) -> str:
    """clean_query + mở rộng từ viết tắt; câu không có chữ nào có dấu thì khôi phục dấu."""
    q = clean_query(question)
    if not q:
        return q
    accented = has_diacritics(q)
    q = expand_abbrev(q)
    return q if accented else get_restorer().restore(q)
