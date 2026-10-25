"""Nối answer() với bước truy hồi (Quân gọi retrieve() của TV3).

    from src.answer.retriever import load_retriever
    r = load_retriever()          # r.name: "rerank" | "hybrid" | "dense" | "bm25"
    r.search("đăng ký khai sinh cần giấy tờ gì", k=5)   # [(chunk_id, score), ...]

- mode "selected" (mặc định trong configs/answer.yaml): gọi retrieve() của TV3 theo configs/retrieval_selected.yaml.
- mode "bm25": BM25 âm tiết của TV1, Python thuần, cho máy không có torch hoặc khi deploy cần nhẹ.
- Nếu nạp "selected" bị lỗi (chưa cài sentence-transformers, không tải được model) thì tự chuyển về bm25 và ghi
  lý do vào r.warning, web sẽ hiện ra cho người dùng biết đang chạy bản baseline.
"""
from __future__ import annotations

import importlib
import os
from dataclasses import dataclass
from typing import Callable

import yaml

from src.data.split import ROOT
from src.retrieval.retrieve import Pipeline, load_chunks, load_config, load_spec

ANSWER_CFG = ROOT / "configs/answer.yaml"


def load_answer_config() -> dict:
    return yaml.safe_load(open(ANSWER_CFG, encoding="utf-8"))


@dataclass
class Retriever:
    name: str                                   # loại pipeline, dùng để chọn ngưỡng τ tương ứng
    search: Callable[[str, int], list]
    warning: str = ""


def baseline_retrieve(chunks: list[dict] | None = None) -> Retriever:
    """BM25 âm tiết với tham số TV1 đã chọn (k1, b trong configs/retrieval.yaml)."""
    p = Pipeline({"pipeline": "bm25", "bm25": load_config()["bm25"]}, chunks=chunks or load_chunks())
    return Retriever("bm25", p.search)


def _import(path: str) -> Callable:
    module, func = path.split(":")
    return getattr(importlib.import_module(module), func)


def load_retriever(cfg: dict | None = None, chunks: list[dict] | None = None) -> Retriever:
    cfg = cfg or load_answer_config()
    mode = os.environ.get("ANSWER_PIPELINE", cfg["retriever"].get("mode", "selected")).strip().lower()
    if mode == "bm25":
        return baseline_retrieve(chunks)
    try:
        fn = _import(cfg["retriever"]["function"])
        fn("khai sinh", 1)                       # gọi thử để nạp model luôn, có lỗi thì bắt ở đây
        return Retriever(load_spec()["pipeline"], fn)
    except Exception as e:                       # ImportError, OSError khi tải model, ...
        r = baseline_retrieve(chunks)
        r.warning = (f"Không nạp được mô hình đã chọn ({type(e).__name__}: {str(e)[:120]}). "
                     "Đang dùng BM25 baseline.")
        return r
