"""Hàm retrieve() dùng chung của TV3. TV2 dùng để đánh giá, TV4 gọi trong answer() và app.

    from src.retrieval.retrieve import retrieve
    retrieve("đăng ký khai sinh cần giấy tờ gì", k=10)   # [(chunk_id, score), ...], cao = liên quan hơn

Pipeline đọc từ configs/retrieval_selected.yaml, file này do evaluate_models.py ghi ra sau khi chọn trên
validation. Chưa có file (chưa chạy đánh giá, hoặc máy chưa cài sentence-transformers) thì dùng BM25 âm tiết
với tham số tốt nhất của baseline TV1, nên retrieve() lúc nào cũng chạy được.

Các bước:
  bm25    BM25 âm tiết trên chunk_text; câu gõ không dấu tìm trên bản bỏ dấu của kho
  dense   SBERT bi-encoder, cosine (src/retrieval/dense.py)
  hybrid  gộp điểm BM25 + SBERT, minmax có trọng số hoặc RRF (src/retrieval/fusion.py)
  rerank  lấy top_n của first_stage (bm25 / dense / hybrid), cộng thêm tối đa extra_bm25 chunk đứng đầu
          BM25 mà bước đầu bỏ sót (rerank_candidates), rồi xếp lại tất cả bằng cross-encoder
          (ce_norm: minmax / raw, xem rerank.py)
Câu gõ không dấu: BM25 tìm trên chỉ mục bỏ dấu, còn bi-encoder và cross-encoder nhận câu đã khôi phục dấu
nếu restore_diacritics = true trong mục dense / rerank (restore.py).
Câu hỏi nào cũng qua clean_query (NFC + normalize_tone) trước khi tokenize hoặc encode (issue #7).

Để TV4 dùng hàm này thì trong configs/answer.yaml đổi
    function: "src.answer.retriever:baseline_retrieve"   thành   function: "src.retrieval.retrieve:retrieve"
"""
from __future__ import annotations

import json
from functools import lru_cache

import yaml

from src.data.split import ROOT
from src.retrieval.bm25 import BM25
from src.retrieval.fusion import fuse, top_k
from src.retrieval.query import clean_query, has_diacritics, strip_accents

CONFIG = ROOT / "configs/retrieval.yaml"
SELECTED = ROOT / "configs/retrieval_selected.yaml"
CHUNKS = ROOT / "data/processed/chunks.jsonl"
STAGES = ("bm25", "dense", "hybrid", "rerank")


def load_config() -> dict:
    return yaml.safe_load(open(CONFIG, encoding="utf-8"))


def load_spec() -> dict:
    """Pipeline đã chốt trên validation, chưa có thì dùng BM25 (fallback trong configs/retrieval.yaml)."""
    if SELECTED.exists():
        return yaml.safe_load(open(SELECTED, encoding="utf-8"))
    return dict(load_config()["fallback"])


def load_chunks() -> list[dict]:
    with open(CHUNKS, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def rerank_candidates(ids: list[str], first_scores: list[float], bm25_scores: list[float], top_n: int,
                      extra_bm25: int = 0) -> list[tuple[str, float]]:
    """Ứng viên đưa vào cross-encoder gồm top_n của bước đầu, cộng các chunk trong top extra_bm25 của BM25
    mà bước đầu chưa lấy (điểm đi kèm vẫn là điểm bước đầu để blend tính cho đúng).

    Làm vậy vì hybrid minmax với alpha cao (SBERT nặng ký) hay đẩy mất chunk mà chỉ BM25 bắt được, nhất là
    với câu gõ không dấu: bi-encoder hiểu kém câu không dấu, còn BM25 tìm trên chỉ mục bỏ dấu vẫn ra.
    Chunk nằm ngoài top_n thì cross-encoder không thấy được, rerank cũng không cứu được."""
    cands = top_k(ids, first_scores, top_n)
    if extra_bm25 <= 0:
        return cands
    have = {c for c, _ in cands}
    pos = {c: i for i, c in enumerate(ids)}
    for cid, s in top_k(ids, bm25_scores, extra_bm25):
        if s > 0 and cid not in have:
            cands.append((cid, float(first_scores[pos[cid]])))
            have.add(cid)
    return cands


def candidate_runs(first_scores, bm25_scores, ids, questions, top_n, extra):
    """Ứng viên rerank của từng câu: top_n bước đầu cộng chunk BM25 bị bỏ sót (xem rerank_candidates)."""
    return {q["question_id"]: rerank_candidates(ids, first_scores(q), bm25_scores(q) if extra else [], top_n, extra)
            for q in questions}


def rerank_run(reranker, first_run, questions, blend, ce_cache, ce_norm=None, restore=None):
    """ce_cache: question_id -> {chunk_id: điểm cross-encoder}, mỗi cặp chỉ chấm 1 lần cho cả lưới
    (mỗi giá trị restore cần một cache riêng). ce_norm / restore là None thì theo cấu hình của reranker."""
    out = {}
    for q in questions:
        cands = first_run[q["question_id"]]
        done = ce_cache.setdefault(q["question_id"], {})
        todo = [c for c, _ in cands if c not in done]
        if todo:
            done.update(zip(todo, reranker.scores(q["question"], todo, restore)))
        out[q["question_id"]] = reranker.rerank(q["question"], cands, blend=blend,
                                                ce_scores=[done[c] for c, _ in cands], ce_norm=ce_norm)
    return out


class SparseIndex:
    """BM25 âm tiết với 2 chỉ mục: có dấu (mặc định) và bỏ dấu (cho câu gõ không dấu, cần mới tạo)."""

    def __init__(self, chunks: list[dict], k1: float = 1.5, b: float = 0.9):
        self.texts = [c["chunk_text"] for c in chunks]
        self.ids = [c["chunk_id"] for c in chunks]
        self.k1, self.b = k1, b
        self.accented = BM25(self.texts, self.ids, k1=k1, b=b)
        self._plain = None

    def scores(self, question: str) -> list[float]:
        q = clean_query(question)
        if has_diacritics(q):
            return self.accented.scores(q)
        if self._plain is None:
            self._plain = BM25([strip_accents(t) for t in self.texts], self.ids, k1=self.k1, b=self.b)
        return self._plain.scores(strip_accents(q))


class Pipeline:
    def __init__(self, spec: dict, cfg: dict | None = None, chunks: list[dict] | None = None,
                 load_all: bool = False):
        """load_all=True thì nạp cả bi-encoder dù pipeline không cần (evaluate_models chạy hết các bước)."""
        cfg = cfg or load_config()
        self.spec = spec
        self.chunks = chunks if chunks is not None else load_chunks()
        self.ids = [c["chunk_id"] for c in self.chunks]
        self.kind = spec["pipeline"]
        if self.kind not in STAGES:
            raise ValueError(f"pipeline không hợp lệ: {self.kind}")
        run = cfg.get("runtime", {})
        bs, dev = run.get("batch_size", 16), run.get("device", "auto")
        self.sparse = SparseIndex(self.chunks, **spec.get("bm25", cfg["bm25"]))
        stages = {self.kind, spec.get("first_stage", "")}
        self.dense = None
        if stages & {"dense", "hybrid"} or (load_all and "dense" in spec):
            from src.retrieval.dense import DenseIndex
            self.dense = DenseIndex(spec["dense"], self.chunks, batch_size=bs, device=dev)
        self.reranker = None
        if self.kind == "rerank":
            from src.retrieval.rerank import Reranker
            self.reranker = Reranker(spec["rerank"], {c["chunk_id"]: c for c in self.chunks},
                                     batch_size=bs, device=dev)

    def stage_scores(self, question: str, stage: str) -> list[float]:
        """Điểm của bước bm25 / dense / hybrid trên toàn bộ chunk (cùng thứ tự self.ids)."""
        if stage == "bm25":
            return self.sparse.scores(question)
        if stage == "dense":
            return self.dense.scores(question)
        h = self.spec["hybrid"]
        a = h["alpha"]
        return fuse([self.dense.scores(question), self.sparse.scores(question)], [a, 1 - a],
                    method=h["fusion"], rrf_k=h.get("rrf_k", 60))

    def search(self, question: str, k: int = 10) -> list[tuple[str, float]]:
        if not clean_query(question):
            return []
        if self.kind != "rerank":
            return top_k(self.ids, self.stage_scores(question, self.kind), k)
        r = self.spec["rerank"]
        first = self.spec["first_stage"]
        extra = r.get("extra_bm25", 0) if first != "bm25" else 0
        bm25 = self.sparse.scores(question) if extra else []
        cands = rerank_candidates(self.ids, self.stage_scores(question, first), bm25, max(r["top_n"], k), extra)
        return self.reranker.rerank(question, cands, blend=r.get("blend", 0.0))[:k]


@lru_cache(maxsize=1)
def get_pipeline() -> Pipeline:
    return Pipeline(load_spec())


def retrieve(question: str, k: int = 10) -> list[tuple[str, float]]:
    """Top-k (chunk_id, score) đã xếp hạng, điểm càng cao càng liên quan."""
    return get_pipeline().search(question, k)
