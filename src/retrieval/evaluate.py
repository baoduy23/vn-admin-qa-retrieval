"""Chạy baseline TF-IDF và BM25, mức âm tiết và mức từ (M01, mục 10 hướng dẫn TV1).

Làm theo đúng quy định khoá test ở mục 9.1:
  1. Lập chỉ mục trên toàn bộ chunks (baseline không học gì từ câu hỏi).
  2. Trên validation: thử lưới tham số (TF-IDF n-gram, BM25 k1 × b), lấy bộ có NDCG@10 cao nhất,
     rồi chọn ngưỡng từ chối theo điểm top-1 (dưới ngưỡng thì từ chối), sao cho từ chối nhầm
     câu hợp lệ không quá refusal.max_wrong_refusal.
  3. Phải thêm --test thì mới chạy test, chỉ chạy 1 lần với tham số và ngưỡng đã chốt.

Đầu vào : data/processed/chunks.jsonl, data/labels/{questions,qrels}.csv, data/splits/*_qgroups.csv,
          configs/retrieval_baseline.yaml
Đầu ra  : results/retrieval/baseline_results.csv   (bảng 10.3: R@k, MRR, NDCG@10, từ chối đúng/nhầm)
          results/retrieval/baseline_by_type.csv   (tách theo type, cho phần phân tích bắt buộc)
          results/retrieval/grid_validation.csv    (mọi bộ tham số đã thử trên validation)
          results/retrieval/runs/<model>_<token>_<split>.csv  (top-10 từng câu, cho phân tích lỗi)
          results/retrieval/baseline_report.md

Chạy từ gốc repo:  python -m src.retrieval.evaluate          (chỉ validation)
                   python -m src.retrieval.evaluate --test   (validation + test)
"""
import csv
import itertools
import json
import sys
from collections import defaultdict

import yaml

from src.data.split import ROOT, SPLITS
from src.data.text_utils import normalize_tone
from src.retrieval.bm25 import BM25
from src.retrieval.metrics import evaluate
from src.retrieval.tfidf import TFIDF

OUT = ROOT / "results/retrieval"
NO_QRELS = {"out_of_scope", "unsupported"}
TOP = 10
FIELD = {"syllable": "chunk_text", "word": "text_seg"}       # mức token nào thì dùng cột văn bản nào của chunk
TOKEN_VI = {"syllable": "âm tiết", "word": "từ"}


# 1. Đọc dữ liệu
def read_csv(rel):
    with open(ROOT / rel, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_data():
    chunks = [json.loads(l) for l in open(ROOT / "data/processed/chunks.jsonl", encoding="utf-8")]
    split_of = {r["question_group_id"]: s for s in SPLITS for r in read_csv(f"data/splits/{s}_qgroups.csv")}
    questions = read_csv("data/labels/questions.csv")
    for q in questions:
        q["split"] = split_of.get(q["question_group_id"])
    qrels = defaultdict(dict)
    for r in read_csv("data/labels/qrels.csv"):
        qrels[r["question_id"]][r["chunk_id"]] = int(r["relevance"])
    return chunks, questions, dict(qrels)


def query_text(question, level):
    """Câu hỏi phải chuẩn hoá và tách từ bằng đúng cách đã làm với chunk."""
    if level == "word":
        from src.data.chunk import segment            # import muộn: underthesea nạp lâu
        return segment(normalize_tone(question))
    return question


# 2. Mô hình và lưới tham số
def param_grid(cfg):
    """Lưới thử trên validation: TF-IDF n-gram (1,1)/(1,2); BM25 k1 1.2–2.0 × b quanh 0.75."""
    for ng in ([1, 1], cfg["tfidf"]["ngram_range"]):
        yield "tfidf", dict(ngram_range=tuple(ng), sublinear_tf=cfg["tfidf"]["sublinear_tf"])
    for k1, b in itertools.product([1.2, 1.5, 1.8, 2.0], [0.6, 0.75, 0.9]):
        yield "bm25", dict(k1=k1, b=b)


def build(model, params, docs, ids):
    return TFIDF(docs, ids, **params) if model == "tfidf" else BM25(docs, ids, **params)


def run(retriever, questions, level):
    """Trả về {question_id: top-10 [(chunk_id, score)]}."""
    return {q["question_id"]: retriever.search(query_text(q["question"], level), k=TOP) for q in questions}


# 3. Chỉ số
def ranking_metrics(results, questions, qrels, ks):
    """R@k, MRR, NDCG@k trên các câu có nhãn (bỏ out_of_scope, unsupported)."""
    ranked = {q["question_id"]: [c for c, _ in results[q["question_id"]]] for q in questions}
    return evaluate(ranked, qrels, ks)


def refusal_rates(results, questions, threshold):
    """Điểm top-1 < ngưỡng thì từ chối. Trả về (tỉ lệ từ chối đúng câu không trả lời được,
    tỉ lệ từ chối nhầm câu hợp lệ)."""
    refuse = {q["question_id"]: (results[q["question_id"]][0][1] if results[q["question_id"]] else 0) < threshold
              for q in questions}
    neg = [q["question_id"] for q in questions if q["type"] in NO_QRELS]
    pos = [q["question_id"] for q in questions if q["type"] not in NO_QRELS]
    correct = sum(refuse[q] for q in neg) / len(neg) if neg else float("nan")
    wrong = sum(refuse[q] for q in pos) / len(pos) if pos else float("nan")
    return correct, wrong


def pick_threshold(results, questions, max_wrong):
    """Chọn ngưỡng từ chối đúng nhiều nhất mà từ chối nhầm câu hợp lệ không quá max_wrong (trên validation),
    hoà thì lấy ngưỡng thấp hơn. Nếu không giới hạn từ chối nhầm thì ngưỡng bị kéo lên rất cao
    (từ chối gần hết), vì validation chỉ có vài câu out_of_scope / unsupported."""
    if not any(q["type"] in NO_QRELS for q in questions):
        return 0.0
    tops = sorted({r[0][1] for r in results.values() if r} | {0.0})
    cands = [0.0] + [(a + b) / 2 for a, b in zip(tops, tops[1:])]
    ok = []
    for t in cands:
        correct, wrong = refusal_rates(results, questions, t)
        if wrong <= max_wrong:
            ok.append((correct, -t, t))
    return max(ok)[2]


def by_type(results, questions, qrels, ks):
    rows = []
    for t in sorted({q["type"] for q in questions} - NO_QRELS):
        qs = [q for q in questions if q["type"] == t]
        m = ranking_metrics(results, qs, qrels, ks)
        rows.append(dict(type=t, n=len(qs), **{k: round(v, 4) for k, v in m.items() if k != "n_questions"}))
    return rows


def save_run(results, name):
    (OUT / "runs").mkdir(parents=True, exist_ok=True)
    with open(OUT / "runs" / f"{name}.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["question_id", "rank", "chunk_id", "score"])
        for qid, res in results.items():
            for i, (cid, s) in enumerate(res, start=1):
                w.writerow([qid, i, cid, round(s, 4)])


def write_csv(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


# 4. Chạy
def main(with_test=False):
    cfg = yaml.safe_load(open(ROOT / "configs/retrieval_baseline.yaml", encoding="utf-8"))
    ks = cfg["eval"]["ks"]
    chunks, questions, qrels = load_data()
    ids = [c["chunk_id"] for c in chunks]
    qs = {s: [q for q in questions if q["split"] == s] for s in SPLITS}
    OUT.mkdir(parents=True, exist_ok=True)

    grid, results, types = [], [], []
    for level in cfg["token_level"]:
        docs = [c[FIELD[level]] for c in chunks]
        val_q = qs["validation"]
        best = {}                                          # model: (ndcg, mrr, params, run)
        for model, params in param_grid(cfg):
            res = run(build(model, params, docs, ids), val_q, level)
            m = ranking_metrics(res, val_q, qrels, ks)
            grid.append(dict(model=model, token=level, params=json.dumps(params), **{k: round(m[k], 4) for k in
                                                                                     (f"ndcg@{ks[-1]}", "mrr", "recall@5")}))
            key = (m[f"ndcg@{ks[-1]}"], m["mrr"])
            if model not in best or key > best[model][:2]:
                best[model] = (*key, params, res)

        for model, (_, _, params, val_res) in best.items():
            thr = pick_threshold(val_res, val_q, cfg["refusal"]["max_wrong_refusal"])
            splits = [("validation", val_res)]
            if with_test:
                splits.append(("test", run(build(model, params, docs, ids), qs["test"], level)))
            for split, res in splits:
                sq = qs[split]
                m = ranking_metrics(res, sq, qrels, ks)
                correct, wrong = refusal_rates(res, sq, thr)
                results.append(dict(model=model, token=level, params=json.dumps(params), split=split,
                                    n_answerable=m["n_questions"],
                                    n_unanswerable=sum(q["type"] in NO_QRELS for q in sq),
                                    **{f"R@{k}": round(m[f"recall@{k}"], 4) for k in ks},
                                    MRR=round(m["mrr"], 4), **{f"NDCG@{ks[-1]}": round(m[f"ndcg@{ks[-1]}"], 4)},
                                    threshold=round(thr, 4), correct_refusal=round(correct, 4),
                                    wrong_refusal=round(wrong, 4)))
                types += [dict(model=model, token=level, split=split, **r) for r in by_type(res, sq, qrels, ks)]
                save_run(res, f"{model}_{level}_{split}")

    write_csv(OUT / "grid_validation.csv", grid)
    write_csv(OUT / "baseline_results.csv", results)
    write_csv(OUT / "baseline_by_type.csv", types)
    report(results, types, ks, questions)


def versions():
    """Phiên bản thư viện và mã băm dữ liệu, ghi kèm mỗi kết quả theo results/README.md."""
    import sklearn
    import underthesea
    m = ROOT / "data/dataset_manifest.json"
    man = json.loads(m.read_text(encoding="utf-8")) if m.exists() else {}
    return (f"scikit-learn {sklearn.__version__}, underthesea {underthesea.__version__}, "
            f"chunks_sha256 {man.get('chunks_sha256', '?')[:12]}, qrels_sha256 {man.get('qrels_sha256', '?')[:12]}, "
            f"dataset {man.get('dataset_version', '?')} ({man.get('review_status', 'chưa freeze')})")


def report(results, types, ks, questions):
    n = {s: sum(q["split"] == s for q in questions) for s in SPLITS}
    lines = ["# Kết quả baseline TF-IDF và BM25", "",
             "Sinh tự động bởi `python -m src.retrieval.evaluate`. Tham số và ngưỡng từ chối chọn trên validation; "
             "test chỉ chạy với tham số đã chốt.", "",
             f"Số câu: train {n['train']}, validation {n['validation']}, test {n['test']}. "
             "R@k, MRR, NDCG tính trên câu có nhãn; từ chối đúng tính trên out_of_scope + unsupported, "
             "từ chối nhầm tính trên câu hợp lệ.", "",
             f"Môi trường: {versions()}.", ""]
    for split in ("validation", "test"):
        rows = [r for r in results if r["split"] == split]
        if not rows:
            continue
        lines += [f"## {split}", "",
                  "| Mô hình | Token | Tham số | " + " | ".join(f"R@{k}" for k in ks) +
                  f" | MRR | NDCG@{ks[-1]} | Ngưỡng | Từ chối đúng | Từ chối nhầm |",
                  "|" + "---|" * (len(ks) + 8)]
        for r in rows:
            lines.append(f"| {r['model'].upper()} | {TOKEN_VI[r['token']]} | `{r['params']}` | "
                         + " | ".join(f"{r[f'R@{k}']:.3f}" for k in ks)
                         + f" | {r['MRR']:.3f} | {r[f'NDCG@{ks[-1]}']:.3f} | {r['threshold']:.3f}"
                         f" | {r['correct_refusal']:.2f} | {r['wrong_refusal']:.2f} |")
        if any(r["threshold"] == 0 for r in rows):
            lines += ["", "Ngưỡng 0 = trên validation không có ngưỡng nào từ chối được câu ngoài phạm vi mà "
                      "giữ từ chối nhầm trong giới hạn: điểm top-1 của câu không trả lời được không thấp hơn câu hợp lệ."]
        lines += ["", f"Theo type ({split}, MRR):", "",
                  "| Mô hình | Token | " + " | ".join(sorted({t['type'] for t in types})) + " |",
                  "|" + "---|" * (2 + len({t['type'] for t in types}))]
        for (model, token), grp in itertools.groupby([t for t in types if t["split"] == split],
                                                     key=lambda t: (t["model"], t["token"])):
            d = {t["type"]: f"{t['mrr']:.3f} (n={t['n']})" for t in grp}
            lines.append(f"| {model.upper()} | {TOKEN_VI[token]} | "
                         + " | ".join(d.get(t, "") for t in sorted({t['type'] for t in types})) + " |")
        lines.append("")
    (OUT / "baseline_report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main(with_test="--test" in sys.argv)
