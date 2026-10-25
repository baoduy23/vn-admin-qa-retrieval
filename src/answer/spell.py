"""Sửa chữ gõ sai trong câu có dấu trước khi truy hồi. Chỉ dùng trong answer() và web, không dùng lúc đánh giá truy hồi.

Vd "thủ tục kết hông với người Đài Loan cần giấy khám sức khóc gì": "hông", "khóc" vẫn là chữ tiếng Việt có thật nên
bảng chữ đúng không bắt được, nhưng kho không có hai chữ này, còn chữ đứng trước thì gần như lúc nào cũng đi với một
chữ rất giống: sau "kết" là "hôn", sau "sức" là "khỏe". PhoRanker đọc "kết hông", "sức khóc" thì chấm Điều 38 Luật Hộ
tịch (đúng đoạn cần trích) dưới τ nên câu bị từ chối.

Cách làm, theo kiểu noisy channel (chương sửa lỗi chính tả), không dùng model:
  - Từ vựng và bảng bigram lấy từ chunk_text của kho và câu hỏi tập train, giống restore.py (không lấy validation /
    test, vì lấy vào là lộ đáp án lúc chọn tham số).
  - Chỉ xét chữ không có trong từ vựng, không viết hoa giữa câu (tên riêng như "Đài Loan"), không có số, không phải
    từ viết tắt (restore.py lo phần đó).
  - Ứng viên là chữ trong từ vựng cách chữ gõ ≤ MAX_DIST: Levenshtein trên phần chữ đã bỏ dấu thanh (vẫn giữ â ê ô ơ
    ư ă đ), cộng TONE_COST nếu khác dấu thanh. "hông" → "hôn" là 1, "khóc" → "khỏe" là 1 + 0.5.
  - Chỉ sửa khi chữ đứng cạnh đoán ra ứng viên rất chắc: P(ứng viên | chữ trước) hoặc P(ứng viên | chữ sau)
    ≥ MIN_PROB. Nhờ vậy "giấy khám" không bị đổi thành "giấy khai": sau "giấy" còn rất nhiều chữ khác (tờ, chứng
    nhận, báo tử...), "khai" chỉ chiếm khoảng 1/10. "sức khỏe" chỉ gặp 1 lần trong kho nhưng sau "sức" không có chữ
    nào khác, nên vẫn sửa được "sức khóc".
  - Thử trên cả 300 câu hỏi của bộ dữ liệu: không câu nào bị đổi chữ, nên số đo validation / test không đổi.
"""
from __future__ import annotations

import json
import unicodedata
from collections import Counter
from functools import lru_cache

from src.data.split import ROOT
from src.data.text_utils import normalize_tone
from src.retrieval.query import clean_query, has_diacritics
from src.retrieval.restore import ABBREV, PUNCT, _train_questions

MAX_DIST = 1.5
TONE_COST = 0.5
MIN_PROB = 0.5
TONES = {"̀", "́", "̃", "̉", "̣"}    # huyền, sắc, ngã, hỏi, nặng


def split_tone(syllable: str) -> tuple[str, str]:
    """("khỏe") → ("khoe", hỏi): phần chữ (giữ â ê ô ơ ư ă đ) và dấu thanh."""
    nfd = unicodedata.normalize("NFD", syllable)
    base = "".join(ch for ch in nfd if ch not in TONES)
    tone = "".join(ch for ch in nfd if ch in TONES)
    return unicodedata.normalize("NFC", base), tone


def levenshtein(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def distance(a: str, b: str) -> float:
    (ba, ta), (bb, tb) = split_tone(a), split_tone(b)
    return levenshtein(ba, bb) + (TONE_COST if ta != tb else 0.0)


class Speller:
    def __init__(self, texts: list[str]):
        self.unigram, self.bigram = Counter(), Counter()
        self.follow, self.precede = Counter(), Counter()     # số lần chữ đứng bên trái / bên phải một cặp
        for t in texts:
            for seg in PUNCT.split(normalize_tone(t or "").lower()):
                ws = seg.split()
                self.unigram.update(ws)
                for a, b in zip(ws, ws[1:]):
                    self.bigram[(a, b)] += 1
                    self.follow[a] += 1
                    self.precede[b] += 1
        self.shapes = [(w, *split_tone(w)) for w in self.unigram if w.isalpha()]

    def candidates(self, word: str) -> list[tuple[str, float]]:
        base, tone = split_tone(word)
        out = []
        for w, b, t in self.shapes:
            if abs(len(b) - len(base)) > MAX_DIST:
                continue
            d = levenshtein(base, b) + (TONE_COST if t != tone else 0.0)
            if d <= MAX_DIST:
                out.append((w, d))
        return out

    def best(self, word: str, left: str | None, right: str | None) -> str | None:
        """Ứng viên mà chữ bên cạnh đoán ra chắc nhất, None nếu không có ứng viên nào đủ chắc."""
        best = None
        for cand, d in self.candidates(word):
            probs = []
            if left and self.bigram[(left, cand)]:
                probs.append(self.bigram[(left, cand)] / self.follow[left])
            if right and self.bigram[(cand, right)]:
                probs.append(self.bigram[(cand, right)] / self.precede[right])
            p = max(probs, default=0.0)
            if p >= MIN_PROB and (best is None or (p, -d) > best[0]):
                best = ((p, -d), cand)
        return best[1] if best else None

    def correct(self, question: str) -> tuple[str, list[tuple[str, str]]]:
        """Trả về (câu đã sửa, [(chữ cũ, chữ mới), ...]). Câu không dấu thì giữ nguyên, restore.py lo phần dấu."""
        q = clean_query(question)
        if not has_diacritics(q):
            return q, []
        out, fixes, first = [], [], True
        for seg in PUNCT.split(q):
            if not seg.strip() or PUNCT.fullmatch(seg):
                out.append(seg)
                continue
            words = seg.split()
            low = [w.lower() for w in words]
            for i, w in enumerate(words):
                if self._skip(w, low[i], first):
                    first = False
                    continue
                first = False
                fix = self.best(low[i], low[i - 1] if i else None, low[i + 1] if i + 1 < len(low) else None)
                if fix:
                    words[i] = fix.capitalize() if w[:1].isupper() else fix
                    low[i] = fix
                    fixes.append((w, words[i]))
            lead, trail = seg[:len(seg) - len(seg.lstrip())], seg[len(seg.rstrip()):]
            out.append(lead + " ".join(words) + trail)
        return "".join(out), fixes

    def _skip(self, word: str, low: str, first: bool) -> bool:
        return (low in self.unigram or len(low) < 2 or not low.isalpha() or low in ABBREV
                or (word[:1].isupper() and not first))


@lru_cache(maxsize=1)
def get_speller() -> Speller:
    with open(ROOT / "data/processed/chunks.jsonl", encoding="utf-8") as f:
        texts = [json.loads(line)["chunk_text"] for line in f if line.strip()]
    return Speller(texts + _train_questions())


def correct_query(question: str) -> tuple[str, list[tuple[str, str]]]:
    return get_speller().correct(question)
