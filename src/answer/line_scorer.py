"""Chấm từng dòng (khoản / điểm) bằng cross-encoder để chọn đoạn trích.

Mặc định best_quote() chọn dòng theo tổng IDF các âm tiết trùng câu hỏi, nên hay chọn lệch khoản khi câu hỏi
dùng chữ khác với luật (vd hỏi "cần chuẩn bị những gì" mà khoản đúng lại ghi "nộp tờ khai").
File này dùng lại PhoRanker mà TV3 đã chọn (configs/retrieval_selected.yaml, mục rerank) để chấm cặp
(câu hỏi, tên Điều + dòng). Nếu pipeline rerank đã nạp model rồi thì xài chung, không nạp lần 2 cho đỡ RAM lúc deploy.

    bật trong configs/answer.yaml, mục quote.scorer: rerank | idf
Không nạp được model (chưa cài torch, hoặc pipeline không phải rerank) thì trả None, best_quote quay về IDF.
"""
from __future__ import annotations

from typing import Callable

LineScorer = Callable[[str, dict, list[str]], list[float]]


def _cross_encoder(m: dict):
    """Lấy model cross-encoder của pipeline đang chạy, chưa có thì nạp mới theo cùng cấu hình."""
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
