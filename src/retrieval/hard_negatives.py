"""Đào hard negative cho bi-encoder / cross-encoder (M02, mục 11 hướng dẫn TV1).

Với mỗi câu hỏi TRAIN có nhãn: lấy top-k của BM25 mức từ; chunk nằm trong top-k mà không nằm trong qrels
là hard negative (giống câu hỏi về chữ nhưng không trả lời nó). Bỏ thêm các chunk cùng Điều với chunk đúng,
vì Khoản bên cạnh thường cũng liên quan mà người gán nhãn chưa gán → dễ thành "negative giả".
Chỉ dùng train; validation và test không được đụng tới. Bỏ câu underspecified: câu hỏi mơ hồ thì
chunk nào trong top-k cũng có thể đúng, lấy làm negative sẽ dạy sai mô hình.

Đầu ra: data/processed/train_pairs.csv
    question_id, chunk_id, label (1 = đúng, 0 = hard negative), relevance (qrels, chỉ dòng label 1),
    bm25_rank (hạng BM25 của negative)

Chạy từ gốc repo (sau evaluate, để dùng k1, b đã chọn trên validation):
    python -m src.retrieval.hard_negatives
"""
import csv
import json

import yaml

from src.data.split import ROOT
from src.retrieval.bm25 import BM25
from src.retrieval.evaluate import NO_QRELS, load_data, query_text


def bm25_params(cfg):
    """k1, b của BM25 mức từ đã chọn trên validation; chưa chạy evaluate thì lấy trong config."""
    path = ROOT / "results/retrieval/baseline_results.csv"
    if path.exists():
        for r in csv.DictReader(open(path, encoding="utf-8")):
            if r["model"] == "bm25" and r["token"] == "word" and r["split"] == "validation":
                return json.loads(r["params"])
    return dict(k1=cfg["bm25"]["k1"], b=cfg["bm25"]["b"])


def main():
    cfg = yaml.safe_load(open(ROOT / "configs/retrieval_baseline.yaml", encoding="utf-8"))
    hn = cfg["hard_negatives"]
    chunks, questions, qrels = load_data()
    dieu_of = {c["chunk_id"]: (c["doc_id"], c["dieu"]) for c in chunks}
    params = bm25_params(cfg)
    bm25 = BM25([c["text_seg"] for c in chunks], [c["chunk_id"] for c in chunks], **params)

    rows, short = [], 0
    train = [q for q in questions if q["split"] == "train" and q["type"] not in NO_QRELS | {"underspecified"}]
    for q in train:
        gold = qrels[q["question_id"]]
        gold_dieu = {dieu_of[c] for c in gold}
        for cid, rel in gold.items():
            rows.append(dict(question_id=q["question_id"], chunk_id=cid, label=1, relevance=rel, bm25_rank=""))
        want = hn["neg_per_pos"] * len(gold)
        hits = bm25.search(query_text(q["question"], "word"), k=hn["top_k"])
        negs = [(rank, cid) for rank, (cid, _) in enumerate(hits, start=1)
                if cid not in gold and dieu_of[cid] not in gold_dieu][:want]
        short += len(negs) < want
        rows += [dict(question_id=q["question_id"], chunk_id=cid, label=0, relevance="", bm25_rank=rank)
                 for rank, cid in negs]

    out = ROOT / "data/processed/train_pairs.csv"
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    pos = sum(r["label"] == 1 for r in rows)
    print(f"BM25 từ {params}, top-{hn['top_k']}: {len(train)} câu train, {pos} positive, "
          f"{len(rows) - pos} hard negative (tỉ lệ 1:{(len(rows) - pos) / pos:.1f}); "
          f"{short} câu không đủ {hn['neg_per_pos']} negative/positive → {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
