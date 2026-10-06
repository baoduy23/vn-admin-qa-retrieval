"""Retrieval metrics: Recall@k, MRR, NDCG@k.

ranked: list of chunk_id theo thứ tự mô hình trả về.
qrels:  dict chunk_id -> relevance (2 trả lời trực tiếp, 1 liên quan một phần).
"""
import math


def recall_at_k(ranked, qrels, k):
    relevant = {c for c, r in qrels.items() if r > 0}
    if not relevant:
        return 0.0
    return len(set(ranked[:k]) & relevant) / len(relevant)


def reciprocal_rank(ranked, qrels):
    for i, c in enumerate(ranked, start=1):
        if qrels.get(c, 0) > 0:
            return 1.0 / i
    return 0.0


def ndcg_at_k(ranked, qrels, k):
    dcg = sum((2 ** qrels.get(c, 0) - 1) / math.log2(i + 1)
              for i, c in enumerate(ranked[:k], start=1))
    ideal = sorted((r for r in qrels.values() if r > 0), reverse=True)[:k]
    idcg = sum((2 ** r - 1) / math.log2(i + 1) for i, r in enumerate(ideal, start=1))
    return dcg / idcg if idcg > 0 else 0.0


def evaluate(run, qrels_all, ks=(1, 3, 5, 10)):
    """run: question_id -> ranked chunk_ids; qrels_all: question_id -> {chunk_id: rel}.

    Câu hỏi out_of_scope (không có trong qrels_all) bị bỏ qua ở đây;
    tỷ lệ từ chối đúng được tính riêng.
    """
    qids = [q for q in run if q in qrels_all]
    if not qids:
        return {}
    out = {}
    for k in ks:
        out[f"recall@{k}"] = sum(recall_at_k(run[q], qrels_all[q], k) for q in qids) / len(qids)
        out[f"ndcg@{k}"] = sum(ndcg_at_k(run[q], qrels_all[q], k) for q in qids) / len(qids)
    out["mrr"] = sum(reciprocal_rank(run[q], qrels_all[q]) for q in qids) / len(qids)
    out["n_questions"] = len(qids)
    return out
