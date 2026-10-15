"""Hàm retrieve() dùng chung (M5, TV3): TV2 đánh giá, TV4 ráp vào answer() và app.

    from src.retrieval.retrieve import retrieve
    retrieve("đăng ký khai sinh cần giấy tờ gì", k=10)   # [(chunk_id, score), ...], cao = liên quan hơn

Pipeline đọc từ configs/retrieval_selected.yaml, file do evaluate_models.py ghi sau khi chọn trên
validation. Chưa có file đó (chưa chạy đánh giá, máy chưa cài sentence-transformers) thì dùng
BM25 âm tiết, tham số tốt nhất của baseline TV1, nên retrieve() luôn chạy được.

Các bước (pipeline):
  bm25    BM25 âm tiết trên chunk_text; câu gõ không dấu tìm trên bản bỏ dấu của kho
  dense   SBERT bi-encoder, cosine (src/retrieval/dense.py)
  hybrid  gộp điểm BM25 + SBERT, minmax có trọng số hoặc RRF (src/retrieval/fusion.py)
  rerank  lấy top_n của first_stage (bm25 / dense / hybrid) rồi xếp lại bằng cross-encoder
Mọi câu hỏi đều qua clean_query (NFC + normalize_tone) trước khi tokenize hoặc encode (issue #7).

TV4 ráp vào: trong configs/answer.yaml đổi
    function: "src.answer.retriever:baseline_retrieve"   →   function: "src.retrieval.retrieve:retrieve"
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
    """Pipeline đã chốt trên validation; chưa có thì BM25 (fallback trong configs/retrieval.yaml)."""
    if SELECTED.exists():
        return yaml.safe_load(open(SELECTED, encoding="utf-8"))
    return dict(load_config()["fallback"])


def load_chunks() -> list[dict]:
    with open(CHUNKS, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


class SparseIndex:
    """BM25 âm tiết. Hai chỉ mục: có dấu (mặc định) và bỏ dấu (cho câu gõ không dấu, tạo khi cần)."""

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
        """load_all=True: nạp cả bi-encoder dù pipeline không cần (evaluate_models chạy mọi bước)."""
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
        """Điểm trên toàn bộ chunk (cùng thứ tự self.ids) của bước bm25 / dense / hybrid."""
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
        cands = top_k(self.ids, self.stage_scores(question, self.spec["first_stage"]), max(r["top_n"], k))
        return self.reranker.rerank(question, cands, blend=r.get("blend", 0.0))[:k]


@lru_cache(maxsize=1)
def get_pipeline() -> Pipeline:
    return Pipeline(load_spec())


def retrieve(question: str, k: int = 10) -> list[tuple[str, float]]:
    """Top-k (chunk_id, score) đã xếp hạng, điểm cao = liên quan hơn."""
    return get_pipeline().search(question, k)
