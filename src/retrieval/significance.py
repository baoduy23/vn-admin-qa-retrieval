"""Kiểm định chênh lệch giữa các bước truy hồi, đọc lại file run đã lưu, không chạy lại mô hình.

    python -m src.retrieval.significance              (mặc định: các run test đã lưu ngày 24/10)
    python -m src.retrieval.significance --split validation

Đọc results/retrieval/models/runs/<bước>_<split>.csv (do evaluate_models ghi) và data/labels/qrels.csv,
tính RR và NDCG@10 từng câu có nhãn, rồi so từng cặp bước trên cùng một tập câu:
  - paired bootstrap: lấy mẫu lại có hoàn lại các câu, lấy khoảng 2,5%–97,5% của chênh lệch trung bình (CI95)
  - paired randomization (sign-flip): đổi dấu ngẫu nhiên chênh lệch từng câu, p hai phía = (số lần
    |trung bình| ≥ |quan sát| + 1) / (B + 1)
  - p chỉnh Holm cho nhiều cặp so sánh cùng lúc
Chỉ đọc file, không gọi model, nên chạy với split test vẫn không phải là chạy lại test.

Đầu ra: results/retrieval/models/significance_<split>.csv và significance_<split>.md
"""
from __future__ import annotations

import argparse
import csv
import random
from collections import defaultdict
from statistics import mean

from src.data.split import ROOT, SPLITS
from src.retrieval.metrics import ndcg_at_k, reciprocal_rank

RUNS = ROOT / "results/retrieval/models/runs"
OUT = ROOT / "results/retrieval/models"
# các cặp (bước sau, bước trước) như Bảng 6 của báo cáo: từng bước cải tiến, rồi bước cuối so với baseline
PAIRS = [("bm25", "bm25_raw"), ("dense", "bm25"), ("hybrid", "dense"), ("rerank", "hybrid"), ("rerank", "bm25_raw")]
METRICS = {"MRR": lambda ranked, rel: reciprocal_rank(ranked, rel),
           "NDCG@10": lambda ranked, rel: ndcg_at_k(ranked, rel, 10)}


# 1. Đọc dữ liệu
def read_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_qrels() -> dict[str, dict[str, int]]:
    qrels = defaultdict(dict)
    for r in read_csv(ROOT / "data/labels/qrels.csv"):
        qrels[r["question_id"]][r["chunk_id"]] = int(r["relevance"])
    return dict(qrels)


def load_run(stage: str, split: str) -> dict[str, list[str]]:
    """question_id -> danh sách chunk_id theo hạng."""
    rows = defaultdict(list)
    for r in read_csv(RUNS / f"{stage}_{split}.csv"):
        rows[r["question_id"]].append((int(r["rank"]), r["chunk_id"]))
    return {q: [c for _, c in sorted(v)] for q, v in rows.items()}


def per_query(run: dict[str, list[str]], qrels: dict, metric: str) -> dict[str, float]:
    """Điểm từng câu có nhãn; câu out_of_scope / unsupported không có qrels nên bỏ qua."""
    return {q: METRICS[metric](ranked, qrels[q]) for q, ranked in run.items() if q in qrels}


# 2. Kiểm định
def paired_bootstrap(diffs: list[float], n_boot: int, rng: random.Random) -> tuple[float, float]:
    n = len(diffs)
    means = sorted(mean(rng.choices(diffs, k=n)) for _ in range(n_boot))
    return means[int(0.025 * n_boot)], means[int(0.975 * n_boot) - 1]


def sign_flip_p(diffs: list[float], n_perm: int, rng: random.Random) -> float:
    obs = abs(mean(diffs))
    hits = sum(abs(mean(d if rng.random() < 0.5 else -d for d in diffs)) >= obs - 1e-12 for _ in range(n_perm))
    return (hits + 1) / (n_perm + 1)


def holm(pvals: list[float]) -> list[float]:
    """Chỉnh Holm–Bonferroni, giữ thứ tự đầu vào."""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adj, running = [0.0] * m, 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvals[i]))
        adj[i] = running
    return adj


def compare(split: str, n_boot: int = 10000, seed: int = 42) -> list[dict]:
    qrels = load_qrels()
    runs = {s: load_run(s, split) for s in {s for p in PAIRS for s in p}}
    rows = []
    for metric in METRICS:
        scores = {s: per_query(r, qrels, metric) for s, r in runs.items()}
        part = []
        for new, old in PAIRS:
            qs = sorted(set(scores[new]) & set(scores[old]))
            diffs = [scores[new][q] - scores[old][q] for q in qs]
            rng = random.Random(seed)          # mỗi cặp cùng một seed để chạy lại ra đúng số cũ
            lo, hi = paired_bootstrap(diffs, n_boot, rng)
            part.append(dict(split=split, metric=metric, new=new, old=old, n=len(qs),
                             old_mean=mean(scores[old][q] for q in qs), new_mean=mean(scores[new][q] for q in qs),
                             diff=mean(diffs), ci_low=lo, ci_high=hi,
                             better=sum(d > 0 for d in diffs), worse=sum(d < 0 for d in diffs),
                             p=sign_flip_p(diffs, n_boot, rng)))
        for r, a in zip(part, holm([r["p"] for r in part])):
            r["p_holm"] = a
        rows += part
    return rows


# 3. Ghi kết quả
def write(rows: list[dict], split: str, n_boot: int, seed: int) -> None:
    keys = ["split", "metric", "new", "old", "n", "old_mean", "new_mean", "diff", "ci_low", "ci_high",
            "better", "worse", "p", "p_holm"]
    with open(OUT / f"significance_{split}.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows({k: round(v, 4) if isinstance(v, float) else v for k, v in r.items()} for r in rows)
    L = [f"# Kiểm định chênh lệch giữa các bước truy hồi ({split})", "",
         f"Sinh bởi `python -m src.retrieval.significance --split {split}`. Đọc lại `runs/*_{split}.csv` đã lưu, "
         "không chạy lại mô hình. Paired bootstrap lấy CI95 của chênh lệch trung bình; p là paired randomization "
         f"(sign-flip) hai phía; p Holm chỉnh cho {len(PAIRS)} cặp của cùng một thước đo. "
         f"B = {n_boot}, seed {seed}. Hơn / kém = số câu bước sau cao hơn / thấp hơn bước trước.", ""]
    for metric in METRICS:
        L += [f"## {metric}", "", "| So sánh | n | Trước | Sau | Chênh lệch | CI95 | Hơn / kém | p | p Holm |",
              "|---|---|---|---|---|---|---|---|---|"]
        for r in (r for r in rows if r["metric"] == metric):
            L.append(f"| {r['new']} vs {r['old']} | {r['n']} | {r['old_mean']:.3f} | {r['new_mean']:.3f} | "
                     f"{r['diff']:+.3f} | [{r['ci_low']:+.3f}; {r['ci_high']:+.3f}] | {r['better']} / {r['worse']} | "
                     f"{r['p']:.4f} | {r['p_holm']:.4f} |")
        L.append("")
    (OUT / f"significance_{split}.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test", choices=SPLITS)
    ap.add_argument("--n-boot", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    write(compare(a.split, a.n_boot, a.seed), a.split, a.n_boot, a.seed)


if __name__ == "__main__":
    main()
