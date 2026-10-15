"""Gộp điểm của nhiều bộ truy hồi (hybrid BM25 + SBERT). Python thuần, không cần numpy.

Hai cách, chọn trên validation (src/retrieval/evaluate_models.py):
- minmax: đưa điểm từng bộ về [0, 1] trên toàn kho rồi cộng có trọng số
      s(d) = alpha * dense'(d) + (1 - alpha) * bm25'(d)
- rrf (Reciprocal Rank Fusion, Cormack và cộng sự 2009): chỉ dùng thứ hạng, không cần cùng thang điểm
      s(d) = sum_i w_i / (k + rank_i(d))        k = 60 theo bài gốc
"""
from __future__ import annotations


def minmax(scores: list[float]) -> list[float]:
    lo, hi = min(scores), max(scores)
    if hi - lo < 1e-12:
        return [0.0] * len(scores)
    return [(s - lo) / (hi - lo) for s in scores]


def ranks(scores: list[float]) -> list[int]:
    """Thứ hạng 1-based (điểm cao nhất hạng 1); hòa điểm thì giữ thứ tự xuất hiện."""
    order = sorted(range(len(scores)), key=lambda i: -scores[i])
    r = [0] * len(scores)
    for pos, i in enumerate(order, start=1):
        r[i] = pos
    return r


def fuse(score_lists: list[list[float]], weights: list[float], method: str = "minmax",
         rrf_k: int = 60) -> list[float]:
    """score_lists: mỗi phần tử là điểm của MỘT bộ truy hồi trên toàn bộ chunk (cùng thứ tự chunk)."""
    if len(score_lists) != len(weights):
        raise ValueError("số bộ điểm và số trọng số phải bằng nhau")
    n = len(score_lists[0])
    out = [0.0] * n
    for sc, w in zip(score_lists, weights):
        if method == "minmax":
            part = minmax(sc)
        elif method == "rrf":
            part = [1.0 / (rrf_k + r) for r in ranks(sc)]
        else:
            raise ValueError(f"fusion không hỗ trợ: {method}")
        for i, v in enumerate(part):
            out[i] += w * v
    return out


def top_k(ids: list[str], scores: list[float], k: int) -> list[tuple[str, float]]:
    order = sorted(range(len(scores)), key=lambda i: -scores[i])[:k]
    return [(ids[i], float(scores[i])) for i in order]
