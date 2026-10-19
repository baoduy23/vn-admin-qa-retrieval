"""Đánh giá và chọn mô hình truy hồi cải tiến (M5, TV3), so với baseline BM25 của TV1.

Quy trình (khóa test, giống src/retrieval/evaluate.py):
  1. Trên validation:
     a. dense: thử từng bi-encoder trong configs/retrieval.yaml, giữ model NDCG@10 cao nhất (hòa: MRR)
     b. hybrid: BM25 + bi-encoder tốt nhất, lưới fusion (minmax / rrf) × alpha
     c. rerank: bước đầu = bước có Recall@20 cao nhất trong bm25 / dense / hybrid; thử từng
        cross-encoder × extra_bm25 × blend trên top_n = 20 (+ tối đa extra_bm25 chunk của BM25)
     d. pipeline cuối = bước NDCG@10 cao nhất; ngưỡng từ chối (điểm top-1) của mỗi bước chọn như TV1
     e. câu hỏi tương tự: chọn min_score trên validation (bỏ nhóm của chính câu hỏi)
     → ghi configs/retrieval_selected.yaml (retrieve() và similar_questions() đọc file này)
  2. Chỉ khi thêm --test: đọc configs/retrieval_selected.yaml, chạy test MỘT lần với tham số đã chốt.

Chạy từ gốc repo:  python -m src.retrieval.evaluate_models          (chỉ validation, chọn tham số)
                   python -m src.retrieval.evaluate_models --test   (validation + test với bộ đã chốt)

Đầu ra: results/retrieval/models/
  models_results.csv     R@k, MRR, NDCG@10, ngưỡng, từ chối đúng/nhầm của bm25 / dense / hybrid / rerank
  models_by_type.csv     tách theo type câu hỏi
  grid_validation.csv    mọi cấu hình đã thử trên validation (kể cả model tải lỗi)
  similar_questions.csv  độ chính xác gợi ý câu hỏi tương tự theo min_score
  runs/<bước>_<split>.csv  top-20 từng câu (cho phân tích lỗi của TV2)
  models_report.md
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import random
import sys
import traceback

import yaml

from src.data.split import ROOT, SPLITS
from src.retrieval.evaluate import NO_QRELS, load_data, pick_threshold, refusal_rates, write_csv
from src.retrieval.fusion import fuse, top_k
from src.retrieval.metrics import evaluate
from src.retrieval.query import clean_query
from src.retrieval.retrieve import SELECTED, STAGES, SparseIndex, load_config, rerank_candidates

OUT = ROOT / "results/retrieval/models"
TOPN = 20


# ---------- 1. Tiện ích ----------
def set_seed(seed):
    random.seed(seed)
    try:
        import numpy as np
        import torch
        np.random.seed(seed)
        torch.manual_seed(seed)
    except ImportError:
        pass


def metrics(run, questions, qrels, ks):
    ranked = {q["question_id"]: [c for c, _ in run[q["question_id"]]] for q in questions}
    return evaluate(ranked, qrels, ks)


def key(m, select_by):
    return (round(m[select_by], 6), round(m["mrr"], 6))


def run_from(scores_of, ids, questions, n=TOPN):
    return {q["question_id"]: top_k(ids, scores_of(q), n) for q in questions}


class ScoreCache:
    """Điểm trên toàn kho của từng câu, tính một lần rồi dùng lại cho cả lưới tham số."""

    def __init__(self, fn):
        self.fn, self.cache = fn, {}

    def __call__(self, q):
        if q["question_id"] not in self.cache:
            self.cache[q["question_id"]] = self.fn(q["question"])
        return self.cache[q["question_id"]]


def rerank_run(reranker, first_run, questions, blend, ce_cache):
    """ce_cache: question_id -> {chunk_id: điểm cross-encoder}, chấm mỗi cặp một lần cho cả lưới."""
    out = {}
    for q in questions:
        cands = first_run[q["question_id"]]
        done = ce_cache.setdefault(q["question_id"], {})
        todo = [c for c, _ in cands if c not in done]
        if todo:
            done.update(zip(todo, reranker.scores(q["question"], todo)))
        out[q["question_id"]] = reranker.rerank(q["question"], cands, blend=blend,
                                                ce_scores=[done[c] for c, _ in cands])
    return out


def candidate_runs(first_scores, bm25_scores, ids, questions, top_n, extra):
    """Ứng viên rerank của từng câu: top_n bước đầu + chunk BM25 bị bỏ sót (xem rerank_candidates)."""
    return {q["question_id"]: rerank_candidates(ids, first_scores(q), bm25_scores(q) if extra else [], top_n, extra)
            for q in questions}


def grid_row(stage, model, params, m, ks, error=""):
    return dict(stage=stage, model=model, params=json.dumps(params, ensure_ascii=False),
                **{f"R@{k}": round(m.get(f"recall@{k}", 0), 4) for k in ks},
                MRR=round(m.get("mrr", 0), 4), **{"NDCG@10": round(m.get("ndcg@10", 0), 4)}, error=error)


def short_error(e):
    return f"{type(e).__name__}: {str(e).strip().splitlines()[0] if str(e).strip() else ''}"[:200]


def model_cfg(m):
    return {k: v for k, v in m.items() if k != "enabled"}


# ---------- 2. Chọn trên validation ----------
def select(cfg, chunks, val, qrels):
    ks, sel = cfg["eval"]["ks"], cfg["eval"]["select_by"]
    ids = [c["chunk_id"] for c in chunks]
    run_cfg = cfg["runtime"]
    grid, runs, spec = [], {}, dict(bm25=cfg["bm25"])

    sparse = ScoreCache(SparseIndex(chunks, **cfg["bm25"]).scores)
    runs["bm25"] = run_from(sparse, ids, val)
    best = {"bm25": key(metrics(runs["bm25"], val, qrels, ks), sel)}
    grid.append(grid_row("bm25", "bm25_syllable", cfg["bm25"], metrics(runs["bm25"], val, qrels, ks), ks))

    # a. bi-encoder
    from src.retrieval.dense import DenseIndex
    dense_best, dense_scores = None, None
    for m in cfg["dense_models"]:
        if not m.get("enabled", True):
            continue
        try:
            idx = DenseIndex(model_cfg(m), chunks, batch_size=run_cfg["batch_size"], device=run_cfg["device"])
        except Exception as e:                                       # tải model lỗi: ghi lại, thử model khác
            traceback.print_exc()
            grid.append(grid_row("dense", m["name"], {}, {}, ks, error=short_error(e)))
            continue
        sc = ScoreCache(idx.scores)
        r = run_from(sc, ids, val)
        mt = metrics(r, val, qrels, ks)
        grid.append(grid_row("dense", m["name"], {}, mt, ks))
        print(f"dense {m['name']}: NDCG@10 {mt['ndcg@10']:.3f} MRR {mt['mrr']:.3f}")
        if dense_best is None or key(mt, sel) > dense_best[0]:
            dense_best, dense_scores, runs["dense"] = (key(mt, sel), model_cfg(m)), sc, r
    if dense_best is None:
        raise SystemExit("Không nạp được bi-encoder nào: xem cột error trong grid_validation.csv")
    best["dense"], spec["dense"] = dense_best

    # b. hybrid
    hb = None
    for method in cfg["hybrid"]["fusion"]:
        for a in cfg["hybrid"]["alpha_grid"]:
            params = dict(fusion=method, alpha=a, rrf_k=cfg["hybrid"]["rrf_k"])
            r = run_from(lambda q: fuse([dense_scores(q), sparse(q)], [a, 1 - a], method, params["rrf_k"]),
                         ids, val)
            mt = metrics(r, val, qrels, ks)
            grid.append(grid_row("hybrid", spec["dense"]["name"], params, mt, ks))
            if hb is None or key(mt, sel) > hb[0]:
                hb, runs["hybrid"] = (key(mt, sel), params), r
    best["hybrid"], spec["hybrid"] = hb

    # c. rerank trên top_n của bước đầu có Recall@20 cao nhất
    rec = {s: metrics(runs[s], val, qrels, ks)[f"recall@{TOPN}"] for s in ("bm25", "dense", "hybrid")}
    first = max(rec, key=lambda s: (rec[s], best[s]))
    spec["first_stage"] = first
    print(f"rerank trên top-{TOPN} của {first} (Recall@{TOPN} {rec[first]:.3f})")
    from src.retrieval.rerank import Reranker
    chunks_by_id = {c["chunk_id"]: c for c in chunks}
    top_n = cfg["rerank"]["top_n"]
    h = spec["hybrid"]
    first_scores = {"bm25": sparse, "dense": dense_scores,
                    "hybrid": lambda q: fuse([dense_scores(q), sparse(q)], [h["alpha"], 1 - h["alpha"]],
                                             h["fusion"], h["rrf_k"])}[first]
    extras = [0] if first == "bm25" else cfg["rerank"].get("extra_bm25_grid", [0])
    pools = {e: candidate_runs(first_scores, sparse, ids, val, top_n, e) for e in extras}
    rb = None
    for m in cfg["rerank"]["models"]:
        if not m.get("enabled", True):
            continue
        try:
            rr = Reranker(model_cfg(m), chunks_by_id, batch_size=run_cfg["batch_size"], device=run_cfg["device"])
        except Exception as e:
            traceback.print_exc()
            grid.append(grid_row("rerank", m["name"], {}, {}, ks, error=short_error(e)))
            continue
        ce_cache = {}
        for extra, pool in pools.items():
            for blend in cfg["rerank"]["blend_grid"]:
                r = rerank_run(rr, pool, val, blend, ce_cache)
                mt = metrics(r, val, qrels, ks)
                params = dict(first_stage=first, top_n=top_n, extra_bm25=extra, blend=blend)
                grid.append(grid_row("rerank", m["name"], params, mt, ks))
                print(f"rerank {m['name']} extra_bm25 {extra} blend {blend}: "
                      f"NDCG@10 {mt['ndcg@10']:.3f} MRR {mt['mrr']:.3f} R@20 {mt['recall@20']:.3f}")
                if rb is None or key(mt, sel) > rb[0]:
                    rb, runs["rerank"] = (key(mt, sel), dict(model_cfg(m), top_n=top_n, extra_bm25=extra,
                                                             blend=blend)), r
    stages = ["bm25", "dense", "hybrid"]
    if rb is not None:
        best["rerank"], spec["rerank"] = rb
        stages.append("rerank")

    # d. pipeline cuối + ngưỡng từ chối của từng bước
    spec["pipeline"] = max(stages, key=lambda s: best[s])
    spec["thresholds"] = {s: round(pick_threshold(runs[s], val, cfg["eval"]["max_wrong_refusal"]), 6)
                          for s in stages}
    return spec, grid


def select_similar(cfg, spec, questions, qrels):
    """min_score của câu hỏi tương tự: chọn trên validation, kho = train + validation trừ nhóm của chính câu."""
    from src.retrieval.similar import SimilarIndex, question_bank
    run = cfg["runtime"]
    idx = SimilarIndex(question_bank(), spec["dense"], run["batch_size"], run["device"])
    rows = similar_table(idx, [q for q in questions if q["split"] == "validation"], qrels,
                         cfg["similar_questions"]["min_score_grid"], "validation")
    # chọn ngưỡng có F1(precision trong các gợi ý đã hiện, tỉ lệ câu có gợi ý) cao nhất; hòa lấy ngưỡng cao hơn
    pick = max(rows, key=lambda r: (r["f1"], r["min_score"]))
    spec["similar"] = dict(dense=True, min_score=pick["min_score"], k=cfg["similar_questions"]["k"])
    return rows


def similar_table(idx, questions, qrels, grid, split):
    """Gợi ý top-1 'đúng' khi câu gợi ý có chung ít nhất 1 chunk liên quan với câu hỏi.
    Câu không trả lời được: gợi ý nào hiện ra cũng là sai (shown_unanswerable)."""
    qrel_of = {qid: {c for c, r in d.items() if r > 0} for qid, d in qrels.items()}
    top1 = {}
    for q in questions:
        res = idx.search(q["question"], k=1, min_score=-1, exclude_groups={q["question_group_id"]})
        top1[q["question_id"]] = res[0] if res else None
    rows = []
    for t in grid:
        ok = shown = n_ans = shown_un = n_un = 0
        for q in questions:
            r = top1[q["question_id"]]
            hit = r is not None and r["score"] >= t
            if q["type"] in NO_QRELS:
                n_un += 1
                shown_un += hit
                continue
            n_ans += 1
            if hit:
                shown += 1
                ok += bool(qrel_of.get(q["question_id"], set()) & qrel_of.get(r["question_id"], set()))
        prec = ok / shown if shown else 0.0
        cov = shown / n_ans if n_ans else 0.0
        rows.append(dict(split=split, min_score=t, n_answerable=n_ans, coverage=round(cov, 4),
                         precision_at_1=round(prec, 4),
                         f1=round(2 * prec * cov / (prec + cov), 4) if prec + cov else 0.0,
                         shown_unanswerable=round(shown_un / n_un, 4) if n_un else 0.0))
    return rows


def write_selected(spec, val_grid_best):
    header = ("# SINH TỰ ĐỘNG bởi python -m src.retrieval.evaluate_models (chọn trên validation), không sửa tay.\n"
              f"# {dt.datetime.now().isoformat(timespec='seconds')}. retrieve() và similar_questions() đọc file này.\n"
              f"# NDCG@10 validation: {val_grid_best}\n")
    SELECTED.write_text(header + yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")


# ---------- 3. Chạy một split với bộ đã chốt ----------
def run_split(spec, cfg, chunks, questions):
    """bước → top-20 từng câu, theo đúng spec (không chọn lại tham số)."""
    from src.retrieval.retrieve import Pipeline
    ids = [c["chunk_id"] for c in chunks]
    stages = [s for s in STAGES if s in spec["thresholds"]]
    full = Pipeline(dict(spec, pipeline=stages[-1]), cfg, chunks, load_all=True)
    cache = {s: ScoreCache(lambda text, s=s: full.stage_scores(text, s)) for s in ("bm25", "dense", "hybrid")}
    runs = {s: run_from(cache[s], ids, questions) for s in ("bm25", "dense", "hybrid")}
    # đúng baseline TV1: chỉ mục có dấu cho mọi câu, để thấy riêng phần lợi của xử lý câu gõ không dấu
    runs = {"bm25_raw": {q["question_id"]: full.sparse.accented.search(clean_query(q["question"]), TOPN)
                         for q in questions}, **runs}
    if "rerank" in stages:
        r = spec["rerank"]
        extra = r.get("extra_bm25", 0) if spec["first_stage"] != "bm25" else 0
        pool = candidate_runs(cache[spec["first_stage"]], cache["bm25"], ids, questions, r["top_n"], extra)
        runs["rerank"] = rerank_run(full.reranker, pool, questions, r.get("blend", 0.0), {})
    return runs


def stage_name(spec, s):
    if s == "bm25_raw":
        return "BM25 âm tiết baseline TV1 (câu không dấu vẫn tìm trên chỉ mục có dấu)"
    if s == "bm25":
        return f"BM25 âm tiết (k1 {spec['bm25']['k1']}, b {spec['bm25']['b']})"
    if s == "dense":
        return f"SBERT {spec['dense']['name']}"
    if s == "hybrid":
        h = spec["hybrid"]
        return f"Hybrid BM25 + SBERT ({h['fusion']}, alpha {h['alpha']})"
    r = spec["rerank"]
    extra = f" + tối đa {r['extra_bm25']} chunk BM25" if r.get("extra_bm25") else ""
    return f"Rerank {r['name']} trên top-{r['top_n']} {spec['first_stage']}{extra} (blend {r['blend']})"


def by_type(run, questions, qrels, ks):
    rows = []
    for t in sorted({q["type"] for q in questions} - NO_QRELS):
        qs = [q for q in questions if q["type"] == t]
        m = metrics(run, qs, qrels, ks)
        rows.append(dict(type=t, n=len(qs), **{k: round(v, 4) for k, v in m.items() if k != "n_questions"}))
    return rows


def save_run(run, name):
    (OUT / "runs").mkdir(parents=True, exist_ok=True)
    with open(OUT / "runs" / f"{name}.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["question_id", "rank", "chunk_id", "score"])
        for qid, res in run.items():
            for i, (cid, s) in enumerate(res, start=1):
                w.writerow([qid, i, cid, round(s, 4)])


def versions():
    out = []
    for mod in ("torch", "transformers", "sentence_transformers", "underthesea"):
        try:
            out.append(f"{mod} {__import__(mod).__version__}")
        except ImportError:
            pass
    m = ROOT / "data/dataset_manifest.json"
    man = json.loads(m.read_text(encoding="utf-8")) if m.exists() else {}
    return (", ".join(out) + f", chunks_sha256 {man.get('chunks_sha256', '?')[:12]}, "
            f"qrels_sha256 {man.get('qrels_sha256', '?')[:12]}, dataset {man.get('dataset_version', '?')} "
            f"({man.get('review_status', '?')})")


# ---------- 4. Báo cáo ----------
def report(results, types, grid, sim_rows, spec, ks, questions):
    n = {s: sum(q["split"] == s for q in questions) for s in SPLITS}
    L = ["# Kết quả mô hình truy hồi cải tiến (TV3)", "",
         "Sinh tự động bởi `python -m src.retrieval.evaluate_models`. Model và tham số chọn trên validation "
         "(theo NDCG@10, hòa thì MRR); test chỉ chạy với bộ đã chốt trong `configs/retrieval_selected.yaml`.", "",
         f"Số câu: train {n['train']}, validation {n['validation']}, test {n['test']}. R@k, MRR, NDCG tính trên "
         "câu có nhãn; từ chối đúng tính trên out_of_scope + unsupported, từ chối nhầm trên câu hợp lệ "
         "(ngưỡng trên điểm top-1, chọn trên validation như baseline).", "",
         f"Pipeline `retrieve()` dùng: **{spec['pipeline']}**: {stage_name(spec, spec['pipeline'])}.", "",
         f"Môi trường: {versions()}, seed {load_config()['runtime']['seed']}.", ""]
    for split in ("validation", "test"):
        rows = [r for r in results if r["split"] == split]
        if not rows:
            continue
        L += [f"## {split}", "", "| Bước | Mô hình | " + " | ".join(f"R@{k}" for k in ks)
              + " | MRR | NDCG@10 | Ngưỡng | Từ chối đúng | Từ chối nhầm |", "|" + "---|" * (len(ks) + 7)]
        for r in rows:
            L.append(f"| {r['stage']} | {r['model']} | " + " | ".join(f"{r[f'R@{k}']:.3f}" for k in ks)
                     + f" | {r['MRR']:.3f} | {r['NDCG@10']:.3f} | {r['threshold']:.3f} | "
                       f"{r['correct_refusal']:.2f} | {r['wrong_refusal']:.2f} |")
        tlist = sorted({t["type"] for t in types if t["split"] == split})
        L += ["", f"Theo type ({split}, MRR):", "", "| Bước | " + " | ".join(tlist) + " |",
              "|" + "---|" * (1 + len(tlist))]
        for s in ("bm25_raw", *STAGES):
            d = {t["type"]: f"{t['mrr']:.3f} (n={t['n']})" for t in types if t["split"] == split and t["stage"] == s}
            if d:
                L.append(f"| {s} | " + " | ".join(d.get(t, "") for t in tlist) + " |")
        L.append("")
    L += ["## Lưới trên validation", "", "Xem `grid_validation.csv`. Model tải lỗi:", ""]
    errs = [g for g in grid if g["error"]]
    L += [f"- {g['model']}: {g['error']}" for g in errs] or ["- không có"]
    L += ["", "## Câu hỏi tương tự", "",
          f"Kho: train + validation, bỏ out_of_scope / unsupported. min_score chốt: {spec['similar']['min_score']}. "
          "Đúng = câu gợi ý top-1 có chung ít nhất 1 chunk liên quan với câu hỏi. Validation bỏ nhóm của chính câu hỏi.", "",
          "| split | min_score | Có gợi ý | Đúng (P@1) | F1 | Hiện gợi ý cho câu không trả lời được |", "|---|---|---|---|---|---|"]
    L += [f"| {r['split']} | {r['min_score']} | {r['coverage']:.2f} | {r['precision_at_1']:.2f} | {r['f1']:.2f} | "
          f"{r['shown_unanswerable']:.2f} |" for r in sim_rows]
    (OUT / "models_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


# ---------- 5. Chạy ----------
def main(with_test=False):
    cfg = load_config()
    set_seed(cfg["runtime"]["seed"])
    ks = cfg["eval"]["ks"]
    chunks, questions, qrels = load_data()
    qs = {s: [q for q in questions if q["split"] == s] for s in SPLITS}
    OUT.mkdir(parents=True, exist_ok=True)

    if with_test:
        if not SELECTED.exists():
            raise SystemExit("Chưa có configs/retrieval_selected.yaml: chạy validation trước (bỏ --test)")
        spec = yaml.safe_load(open(SELECTED, encoding="utf-8"))
        gpath = OUT / "grid_validation.csv"
        grid = list(csv.DictReader(open(gpath, encoding="utf-8"))) if gpath.exists() else []
    else:
        spec, grid = select(cfg, chunks, qs["validation"], qrels)
    sim_rows = select_similar(cfg, spec, questions, qrels) if not with_test else None
    if not with_test:
        write_selected(spec, {s: max((float(g["NDCG@10"]) for g in grid if g["stage"] == s and not g["error"]),
                                     default=None) for s in STAGES})
        write_csv(OUT / "grid_validation.csv", grid)

    results, types, thr = [], [], dict(spec["thresholds"])
    for split in (["validation", "test"] if with_test else ["validation"]):
        sq = qs[split]
        runs = run_split(spec, cfg, chunks, sq)
        if split == "validation":
            thr["bm25_raw"] = pick_threshold(runs["bm25_raw"], sq, cfg["eval"]["max_wrong_refusal"])
        for s, run in runs.items():
            m = metrics(run, sq, qrels, ks)
            correct, wrong = refusal_rates(run, sq, thr[s])
            results.append(dict(stage=s, model=stage_name(spec, s), split=split, n_answerable=m["n_questions"],
                                n_unanswerable=sum(q["type"] in NO_QRELS for q in sq),
                                **{f"R@{k}": round(m[f"recall@{k}"], 4) for k in ks}, MRR=round(m["mrr"], 4),
                                **{"NDCG@10": round(m["ndcg@10"], 4)}, threshold=round(thr[s], 4),
                                correct_refusal=round(correct, 4), wrong_refusal=round(wrong, 4)))
            types += [dict(stage=s, split=split, **r) for r in by_type(run, sq, qrels, ks)]
            save_run(run, f"{s}_{split}")

    if with_test:
        from src.retrieval.similar import SimilarIndex, question_bank
        run = cfg["runtime"]
        idx = SimilarIndex(question_bank(), spec["dense"], run["batch_size"], run["device"])
        sim_rows = [r for r in csv.DictReader(open(OUT / "similar_questions.csv", encoding="utf-8"))
                    if r["split"] == "validation"] if (OUT / "similar_questions.csv").exists() else []
        sim_rows = [dict(r, min_score=float(r["min_score"]), coverage=float(r["coverage"]),
                         precision_at_1=float(r["precision_at_1"]), f1=float(r["f1"]),
                         shown_unanswerable=float(r["shown_unanswerable"])) for r in sim_rows]
        sim_rows += similar_table(idx, qs["test"], qrels, [spec["similar"]["min_score"]], "test")
    write_csv(OUT / "similar_questions.csv", sim_rows)
    write_csv(OUT / "models_results.csv", results)
    write_csv(OUT / "models_by_type.csv", types)
    report(results, types, grid, sim_rows, spec, ks, questions)


if __name__ == "__main__":
    main(with_test="--test" in sys.argv)
