"""Câu hỏi tương tự (TV3): tìm trong bộ câu hỏi đã gán nhãn, không lấy câu thuộc tập test.

    from src.retrieval.similar import similar_questions
    similar_questions("làm giấy khai sinh cho con cần gì", k=3)
    # [{question_id, question, answer_text, score}, ...]   (cùng dạng với src/answer/similar.py của TV4)

- Kho câu hỏi là train + validation, bỏ out_of_scope / unsupported (không có câu trả lời để gợi ý)
  và bỏ nhóm thuộc test, để gợi ý không làm lộ đáp án test lúc đánh giá.
- Mỗi nhóm câu hỏi (question_group_id) chỉ lấy 1 câu, khỏi hiện 3 cách hỏi của cùng một ý.
- Pipeline đã chốt (configs/retrieval_selected.yaml) có bi-encoder thì so cosine giữa câu hỏi với câu hỏi,
  không có thì so tỉ lệ âm tiết chung (Dice, trên bản bỏ dấu).
- min_score là ngưỡng tối thiểu để tính là tương tự, mặc định lấy trong configs/retrieval_selected.yaml
  (chọn trên validation), chưa có thì lấy configs/retrieval.yaml.
"""
from __future__ import annotations

import csv
import re
from functools import lru_cache

from src.data.split import ROOT, SPLITS
from src.retrieval.query import clean_query, model_input, strip_accents
from src.retrieval.retrieve import load_config, load_spec

NO_ANSWER = {"out_of_scope", "unsupported"}


def _read(rel: str) -> list[dict]:
    with open(ROOT / rel, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def question_bank(exclude_splits=("test",)) -> list[dict]:
    """Các câu trả lời được thuộc những split không bị loại. Nhóm không nằm trong file split nào cũng bị loại
    (chưa biết thuộc tập nào thì coi như có thể là test)."""
    split_of = {r["question_group_id"]: s for s in SPLITS for r in _read(f"data/splits/{s}_qgroups.csv")}
    out = []
    for r in _read("data/labels/questions.csv"):
        s = split_of.get(r["question_group_id"])
        if s is None or s in exclude_splits or r.get("type") in NO_ANSWER or not (r.get("question") or "").strip():
            continue
        out.append(dict(r, split=s))
    return out


def dice(a: str, b: str) -> float:
    x = set(re.findall(r"\w+", strip_accents(a)))
    y = set(re.findall(r"\w+", strip_accents(b)))
    return 2 * len(x & y) / (len(x) + len(y)) if x and y else 0.0


class SimilarIndex:
    def __init__(self, bank: list[dict], mcfg: dict | None = None, batch_size: int = 16, device: str = "auto"):
        self.bank = bank
        self.mcfg = mcfg
        self.model = None
        if mcfg and bank:
            from src.retrieval.dense import load_bi_encoder
            self.model = load_bi_encoder(mcfg["name"], mcfg.get("max_seq_length", 256), device)
            self.batch_size = batch_size
            self.emb = self._encode([r["question"] for r in bank])

    def _encode(self, texts: list[str]):
        # so câu hỏi với câu hỏi nên cả hai bên dùng query_prefix
        xs = [model_input(t, self.mcfg.get("segment", False), self.mcfg.get("query_prefix", ""),
                          self.mcfg.get("restore_diacritics", False)) for t in texts]
        return self.model.encode(xs, batch_size=self.batch_size, normalize_embeddings=True,
                                 convert_to_numpy=True, show_progress_bar=False)

    def scores(self, question: str) -> list[float]:
        if self.model is not None:
            return (self.emb @ self._encode([question])[0]).tolist()
        return [dice(question, r["question"]) for r in self.bank]

    def search(self, question: str, k: int = 3, min_score: float = 0.0, exclude_groups=()) -> list[dict]:
        if not self.bank or not clean_query(question):
            return []
        sc = self.scores(question)
        norm_q = strip_accents(clean_query(question)).strip(" ?")
        out, seen = [], set(exclude_groups)
        for i in sorted(range(len(sc)), key=lambda i: -sc[i]):
            r = self.bank[i]
            if sc[i] < min_score:
                break
            if r["question_group_id"] in seen or strip_accents(r["question"]).strip(" ?") == norm_q:
                continue
            seen.add(r["question_group_id"])
            out.append(dict(question_id=r["question_id"], question=r["question"],
                            answer_text=r.get("answer_text", ""), score=round(float(sc[i]), 3)))
            if len(out) == k:
                break
        return out


def default_min_score(spec: dict, cfg: dict, dense: bool) -> float:
    s = spec.get("similar", {}).get("min_score")
    if s is not None and spec.get("similar", {}).get("dense", False) == dense:
        return s
    c = cfg["similar_questions"]
    return c["min_score_dense"] if dense else c["min_score_lexical"]


@lru_cache(maxsize=1)
def get_index() -> SimilarIndex:
    spec, cfg = load_spec(), load_config()
    run = cfg.get("runtime", {})
    return SimilarIndex(question_bank(), spec.get("dense"), run.get("batch_size", 16), run.get("device", "auto"))


def similar_questions(question: str, k: int = 3, min_score: float | None = None, exclude_groups=()) -> list[dict]:
    idx = get_index()
    if min_score is None:
        min_score = default_min_score(load_spec(), load_config(), idx.model is not None)
    return idx.search(question, k=k, min_score=min_score, exclude_groups=exclude_groups)
