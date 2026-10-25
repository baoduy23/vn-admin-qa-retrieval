"""Fine-tune bằng hard negative của TV1 (data/processed/train_pairs.csv), chỉ dùng câu thuộc train.

    python -m src.retrieval.finetune --bi      bi-encoder, MultipleNegativesRankingLoss có hard negative
                                               → artifacts/finetuned/bi-encoder
    python -m src.retrieval.finetune --cross   PhoBERT phân loại cặp (câu hỏi, chunk) → liên quan / không,
                                               BCE → artifacts/finetuned/cross-encoder

Xong thì bỏ comment khối "artifacts/finetuned/..." trong configs/retrieval.yaml rồi chạy lại
python -m src.retrieval.evaluate_models, model fine-tune sẽ được so trên validation như các model khác.

Tham số nằm trong configs/retrieval.yaml (mục finetune). Dữ liệu ít (43 câu train có cặp, khoảng 590 cặp)
nên đừng mong nhiều, model fine-tune chỉ được dùng nếu thắng trên validation.

MNRL (Henderson et al. 2017): với câu hỏi q_i, positive p_i phải có cosine cao hơn mọi passage khác
trong batch (positive của câu khác và hard negative):
    loss = CE(scale * [cos(q_i, p_1..p_B), cos(q_i, n_1..n_B)], nhãn = i)
Passage nào trong batch mà thật ra cũng là positive của q_i thì bị che, không tính là negative.
"""
from __future__ import annotations

import argparse
import csv
import random
from collections import defaultdict

from src.data.split import ROOT
from src.retrieval.evaluate import load_data
from src.retrieval.query import model_input
from src.retrieval.retrieve import load_config

PAIRS = ROOT / "data/processed/train_pairs.csv"
OUT = ROOT / "artifacts/finetuned"


def load_pairs():
    """Trả về ({question_id: câu hỏi}, {question_id: [chunk_id positive]}, {question_id: [chunk_id negative]}, chunks)."""
    chunks, questions, _ = load_data()
    train_q = {q["question_id"]: q["question"] for q in questions if q["split"] == "train"}
    pos, neg = defaultdict(list), defaultdict(list)
    with open(PAIRS, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["question_id"] not in train_q:                      # chỉ lấy train để không rò rỉ dữ liệu
                continue
            (pos if r["label"] == "1" else neg)[r["question_id"]].append(r["chunk_id"])
    return train_q, dict(pos), dict(neg), {c["chunk_id"]: c for c in chunks}


def seed_all(seed):
    import numpy as np
    import torch
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def scheduler(opt, n_steps, warmup_ratio):
    from transformers import get_linear_schedule_with_warmup
    return get_linear_schedule_with_warmup(opt, int(n_steps * warmup_ratio), n_steps)


def train_bi(cfg):
    import torch
    import torch.nn.functional as F
    from sentence_transformers import SentenceTransformer

    from src.retrieval.dense import pick_device
    ft = cfg["finetune"]
    base = next((m for m in cfg["dense_models"] if m["name"] == ft["bi_base"]), {"segment": True})
    seg, field = base.get("segment", False), "text_seg" if base.get("segment") else "chunk_text"
    qp, pp = base.get("query_prefix", ""), base.get("passage_prefix", "")
    train_q, pos, neg, chunks = load_pairs()

    # mỗi (câu hỏi, positive) thành 1 bộ ba, hard negative xoay vòng
    triples = []
    for qid, ps in pos.items():
        ns = neg.get(qid) or []
        for i, p in enumerate(ps):
            if ns:
                triples.append((qid, p, ns[i % len(ns)]))
    print(f"bi-encoder: {len(triples)} bộ ba từ {len(pos)} câu train")

    device = pick_device(cfg["runtime"]["device"])
    model = SentenceTransformer(ft["bi_base"], device=device)
    model.max_seq_length = base.get("max_seq_length", 256)
    opt = torch.optim.AdamW(model.parameters(), lr=ft["lr"])
    bs = ft["batch_size"]
    n_steps = ft["epochs"] * ((len(triples) + bs - 1) // bs)
    sch = scheduler(opt, n_steps, ft["warmup_ratio"])

    def embed(texts):
        prep = getattr(model, "preprocess", None) or model.tokenize     # sentence-transformers >= 6 đổi tên
        feats = {k: (v.to(device) if hasattr(v, "to") else v) for k, v in prep(texts).items()}
        return F.normalize(model(feats)["sentence_embedding"], dim=-1)

    model.train()
    for ep in range(ft["epochs"]):
        random.shuffle(triples)
        total = 0.0
        for s in range(0, len(triples), bs):
            batch = triples[s:s + bs]
            q = embed([model_input(train_q[qid], seg, qp) for qid, _, _ in batch])
            cids = [p for _, p, _ in batch] + [n for _, _, n in batch]
            d = embed([pp + chunks[c][field] for c in cids])
            logits = 20.0 * q @ d.T                                   # scale 20 như mặc định của MNRL
            mask = torch.tensor([[j != i and cids[j] in pos[batch[i][0]] for j in range(len(cids))]
                                 for i in range(len(batch))], device=device)
            logits = logits.masked_fill(mask, float("-inf"))
            loss = F.cross_entropy(logits, torch.arange(len(batch), device=device))
            loss.backward()
            opt.step()
            sch.step()
            opt.zero_grad()
            total += loss.item() * len(batch)
        print(f"epoch {ep + 1}: loss {total / len(triples):.4f}")
    out = OUT / "bi-encoder"
    model.save(str(out))
    print(f"đã lưu {out}")


def train_cross(cfg):
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    from src.retrieval.dense import pick_device
    ft = cfg["finetune"]
    seg = True                                                       # PhoBERT: đầu vào tách từ
    train_q, pos, neg, chunks = load_pairs()
    pairs = [(qid, c, 1.0) for qid, cs in pos.items() for c in cs] + \
            [(qid, c, 0.0) for qid, cs in neg.items() for c in cs]
    print(f"cross-encoder: {len(pairs)} cặp ({sum(p[2] for p in pairs):.0f} positive) từ {len(pos)} câu train")

    device = pick_device(cfg["runtime"]["device"])
    tok = AutoTokenizer.from_pretrained(ft["cross_base"])
    model = AutoModelForSequenceClassification.from_pretrained(ft["cross_base"], num_labels=1).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=ft["lr"])
    bs = ft["batch_size"]
    n_steps = ft["epochs"] * ((len(pairs) + bs - 1) // bs)
    sch = scheduler(opt, n_steps, ft["warmup_ratio"])
    n_pos = sum(p[2] for p in pairs)
    loss_fn = torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor((len(pairs) - n_pos) / max(n_pos, 1), device=device))

    model.train()
    for ep in range(ft["epochs"]):
        random.shuffle(pairs)
        total = 0.0
        for s in range(0, len(pairs), bs):
            batch = pairs[s:s + bs]
            enc = tok([model_input(train_q[q], seg) for q, _, _ in batch], [chunks[c]["text_seg"] for _, c, _ in batch],
                      truncation=True, max_length=256, padding=True, return_tensors="pt").to(device)
            logits = model(**enc).logits.squeeze(-1)
            loss = loss_fn(logits, torch.tensor([y for _, _, y in batch], device=device))
            loss.backward()
            opt.step()
            sch.step()
            opt.zero_grad()
            total += loss.item() * len(batch)
        print(f"epoch {ep + 1}: loss {total / len(pairs):.4f}")
    out = OUT / "cross-encoder"
    model.save_pretrained(out)
    tok.save_pretrained(out)
    print(f"đã lưu {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bi", action="store_true")
    ap.add_argument("--cross", action="store_true")
    a = ap.parse_args()
    if not (a.bi or a.cross):
        ap.error("chọn --bi và/hoặc --cross")
    cfg = load_config()
    seed_all(cfg["finetune"]["seed"])
    if a.bi:
        train_bi(cfg)
    if a.cross:
        train_cross(cfg)
