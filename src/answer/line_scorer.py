"""Chấm từng dòng (khoản / điểm) bằng cross-encoder để chọn đoạn trích (M6).

best_quote() mặc định chọn dòng theo tổng IDF âm tiết trùng câu hỏi, nên hay lệch khoản khi câu hỏi
diễn đạt khác chữ trong luật (vd hỏi "cần chuẩn bị những gì" mà khoản đúng ghi "nộp tờ khai").
Ở đây dùng lại đúng PhoRanker TV3 đã chọn (configs/retrieval_selected.yaml, mục rerank) để chấm
cặp (câu hỏi, tên Điều + dòng). Pipeline rerank đã nạp model thì dùng chung model đó, không nạp lần hai
(đỡ RAM khi deploy).

    configs/answer.yaml → quote.scorer: rerank | idf
Không nạp được model (chưa cài torch, pipeline không phải rerank) → trả None, best_quote dùng IDF như cũ.
"""
from __future__ import annotations

from typing import Callable

LineScorer = Callable[[str, dict, list[str]], list[float]]


def _cross_encoder(m: dict):
    """Model cross-encoder của pipeline đang chạy nếu có, không thì nạp mới theo cùng cấu hình."""
    from src.retrieval.retrieve import get_pipeline, load_config
    try:
        rr = get_pipeline().reranker
        if rr is not None and rr.cfg.get("name") == m["name"]:
            return rr.model
    except Exception:
        pass
    from src.retrieval.rerank import load_cross_encoder
    device = load_config().get("runtime", {}).get("device", "auto")
    return load_cross_encoder(m["name"], m.get("max_seq_length", 256), device)


def load_line_scorer(cfg: dict) -> LineScorer | None:
    if cfg.get("quote", {}).get("scorer", "idf") != "rerank":
        return None
    try:
        from src.retrieval.query import model_input
        from src.retrieval.retrieve import load_spec
        m = load_spec().get("rerank")
        if not m:
            return None
        model = _cross_encoder(m)
    except Exception:                              # ImportError, OSError khi tải model, ...
        return None
    seg, restore = m.get("segment", False), m.get("restore_diacritics", False)

    def score(question: str, chunk: dict, lines: list[str]) -> list[float]:
        q = model_input(question, seg, restore=restore)
        head = chunk.get("dieu_title") or ""
        texts = [f"{head} {line}".strip() for line in lines]   # kèm tên Điều để dòng ngắn ("a) ...") có ngữ cảnh
        if seg:
            from src.data.chunk import segment
            texts = [segment(t) for t in texts]
        out = model.predict([(q, t) for t in texts], show_progress_bar=False)
        return [float(x) for x in out]

    return score
