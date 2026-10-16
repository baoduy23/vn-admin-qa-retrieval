"""Chọn ngưỡng từ chối τ trên validation và đánh giá câu trả lời (Quân, M6).

    python -m src.answer.evaluate_answer              # validation: chọn τ, ghi configs/answer_selected.yaml
    python -m src.answer.evaluate_answer --live selected   # phần câu nhiều ý chạy bằng pipeline TV3 (cần torch)
    python -m src.answer.evaluate_answer --test       # TV2 chạy MỘT lần ở cuối, với τ đã chốt

1. Ngưỡng τ: đọc file kết quả chạy validation của TV3 (results/retrieval/models/runs/<pipeline>_validation.csv,
   top-20 kèm điểm) nên không cần nạp model. Từ chối khi điểm top-1 < τ; chọn τ từ chối đúng nhiều nhất
   (out_of_scope + unsupported) mà từ chối nhầm câu hợp lệ ≤ max_wrong_refusal, hòa lấy τ thấp hơn
   (giống pick_threshold của TV1). Làm 2 lần: chỉ τ, và τ + kiểm tra căn cứ con số (intent.has_evidence).
2. Câu trả lời (validation, τ đã chọn): tỉ lệ trả lời, đúng nguồn (đoạn trích nằm trong qrels), token F1
   so với answer_text, so F1 giữa "trích cả đoạn" và "trích dòng khớp nhất" (template.best_quote).
3. Câu nhiều ý: tách / không tách, đo R@5, R@10, NDCG@5 trên câu multi_intent của train + validation
   (không dùng test), cộng tỉ lệ tách nhầm trên câu một ý. Phần này phải truy hồi lại từng ý nên chạy trực
   tiếp; mặc định BM25 (máy nào cũng chạy được), --live selected để dùng pipeline TV3.
4. Câu thiếu thông tin: precision / recall của intent.is_underspecified trên train + validation.
Kết quả: results/answer/answer_report.md, threshold_grid.csv, <split>_answers.csv.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
from collections import Counter, defaultdict

import yaml

from src.answer.answer import SELECTED, AnswerEngine
from src.answer.intent import is_underspecified, split_multi_intent
from src.answer.retriever import Retriever, baseline_retrieve, load_answer_config, load_retriever
from src.data.split import ROOT, SPLITS
from src.retrieval.metrics import ndcg_at_k, recall_at_k
from src.retrieval.retrieve import load_chunks, load_spec

RUNS = ROOT / "results/retrieval/models/runs"
OUT = ROOT / "results/answer"
NO_ANSWER = {"out_of_scope", "unsupported"}
PIPELINES = ("rerank", "hybrid", "dense", "bm25")


# ------------------------------------------------------------------ dữ liệu
def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_questions(splits) -> list[dict]:
    split_of = {r["question_group_id"]: s for s in SPLITS for r in read_csv(ROOT / f"data/splits/{s}_qgroups.csv")}
    return [dict(q, split=split_of[q["question_group_id"]]) for q in read_csv(ROOT / "data/labels/questions.csv")
            if split_of.get(q["question_group_id"]) in splits]


def load_qrels() -> dict[str, dict[str, int]]:
    out = defaultdict(dict)
    for r in read_csv(ROOT / "data/labels/qrels.csv"):
        out[r["question_id"]][r["chunk_id"]] = int(r["relevance"])
    return dict(out)


def load_run(pipeline: str, split: str) -> dict[str, list[tuple[str, float]]]:
    run = defaultdict(list)
    for r in read_csv(RUNS / f"{pipeline}_{split}.csv"):
        run[r["question_id"]].append((int(r["rank"]), r["chunk_id"], float(r["score"])))
    return {q: [(c, s) for _, c, s in sorted(v)] for q, v in run.items()}


class RunRetriever:
    """Giả retrieve(): trả kết quả có sẵn trong file run theo đúng câu hỏi (không nạp model)."""

    def __init__(self, name, run, questions):
        self.qid_of = {q["question"].strip(): q["question_id"] for q in questions}
        self.r = Retriever(name, self.search)
        self.run = run

    def search(self, question, k):
        return self.run.get(self.qid_of.get(question.strip(), ""), [])[:k]


# ------------------------------------------------------------------ chỉ số
TOKEN = re.compile(r"\w+", re.UNICODE)


def token_f1(pred: str, gold: str) -> float:
    p, g = TOKEN.findall((pred or "").lower()), TOKEN.findall((gold or "").lower())
    common = sum((Counter(p) & Counter(g)).values())
    if not p or not g or not common:
        return 0.0
    prec, rec = common / len(p), common / len(g)
    return 2 * prec * rec / (prec + rec)


def refusal_rates(rows):
    neg = [r for r in rows if r["type"] in NO_ANSWER]
    pos = [r for r in rows if r["type"] not in NO_ANSWER]
    correct = sum(r["refused"] for r in neg) / len(neg) if neg else float("nan")
    wrong = sum(r["refused"] for r in pos) / len(pos) if pos else float("nan")
    return correct, wrong


def run_answers(engine: AnswerEngine, questions, qrels) -> list[dict]:
    rows = []
    for q in questions:
        r = engine.answer(q["question"])
        p = r["parts"][0]
        top = engine.by_id.get(p["chunk_id"]) if p["chunk_id"] else None
        rel = qrels.get(q["question_id"], {})
        quote = " ".join(p["quote_lines"])
        rows.append(dict(
            question_id=q["question_id"], type=q["type"], question=q["question"],
            refused=r["refused"], reason=r["reason"] or "", top_score=round(p["top_score"], 4),
            chunk_id=p["chunk_id"] or "", relevance=rel.get(p["chunk_id"], 0) if p["chunk_id"] else "",
            f1_quote=round(token_f1(quote, q["answer_text"]), 4) if top else "",
            f1_chunk=round(token_f1(top["display_text"], q["answer_text"]), 4) if top else "",
            answer=r["answer"].replace("\n", " "), answer_text=q["answer_text"],
        ))
    return rows


def answer_metrics(rows) -> dict:
    pos = [r for r in rows if r["type"] not in NO_ANSWER]
    answered = [r for r in pos if not r["refused"]]
    correct, wrong = refusal_rates(rows)
    mean = lambda xs: sum(xs) / len(xs) if xs else float("nan")   # noqa: E731
    return {
        "n": len(rows), "n_answerable": len(pos),
        "answered": len(answered) / len(pos) if pos else float("nan"),
        "source_ok": mean([r["relevance"] > 0 for r in answered]),        # đúng nguồn: rel 1 hoặc 2
        "source_strict": mean([r["relevance"] == 2 for r in answered]),   # chỉ rel 2 (trả lời trực tiếp)
        "f1_quote": mean([r["f1_quote"] for r in answered]),
        "f1_chunk": mean([r["f1_chunk"] for r in answered]),
        "correct_refusal": correct, "wrong_refusal": wrong,
    }


# ------------------------------------------------------------------ 1. chọn τ
def pick_threshold(engine, run, questions, max_wrong):
    """Trả (τ tốt nhất, bảng lưới). Ứng viên là trung điểm giữa các điểm top-1 trên validation."""
    tops = sorted({v[0][1] for v in run.values() if v} | {0.0})
    cands = [0.0] + [(a + b) / 2 for a, b in zip(tops, tops[1:])]
    grid, ok = [], []
    for t in cands:
        engine.threshold = t
        correct, wrong = refusal_rates([dict(type=q["type"], refused=engine.answer(q["question"])["refused"])
                                        for q in questions])
        grid.append(dict(threshold=round(t, 6), correct_refusal=round(correct, 4), wrong_refusal=round(wrong, 4)))
        if wrong <= max_wrong:
            ok.append((correct, -t, t))
    return (max(ok)[2] if ok else 0.0), grid


# ------------------------------------------------------------------ 3. câu nhiều ý
def multi_intent_eval(retriever: Retriever, questions, qrels, chunks):
    cfg = load_answer_config()
    rows = []
    for split_on in (False, True):
        cfg_x = dict(cfg, multi_intent={"split": split_on}, evidence_check=False)
        eng = AnswerEngine(cfg_x, retriever=retriever, chunks=chunks, similar=lambda q, k: [], threshold=-1e9)
        qs = [q for q in questions if q["type"] == "multi_intent" and q["question_id"] in qrels]
        r5, r10, n5, cover, quoted_ok = [], [], [], [], []
        for q in qs:
            res = eng.answer(q["question"], k=10)
            ranked = [s["chunk_id"] for s in res["sources"]]
            rel = qrels[q["question_id"]]
            r5.append(recall_at_k(ranked, rel, 5))
            r10.append(recall_at_k(ranked, rel, 10))
            n5.append(ndcg_at_k(ranked, rel, 5))
            # đoạn được TRÍCH trong câu trả lời (1 đoạn / ý): bao nhiêu đoạn đúng, phủ bao nhiêu đoạn rel 2
            quoted = {p["chunk_id"] for p in res["parts"] if p["chunk_id"]}
            gold2 = {c for c, v in rel.items() if v == 2} or {c for c, v in rel.items() if v > 0}
            cover.append(len(quoted & gold2) / len(gold2))
            quoted_ok.append(sum(rel.get(c, 0) > 0 for c in quoted))
        rows.append(dict(mode="tách ý" if split_on else "không tách", n=len(qs),
                         recall5=sum(r5) / len(qs), recall10=sum(r10) / len(qs), ndcg5=sum(n5) / len(qs),
                         cover=sum(cover) / len(qs), quoted_ok=sum(quoted_ok) / len(qs)))
    single = [q for q in questions if q["type"] != "multi_intent"]
    multi = [q for q in questions if q["type"] == "multi_intent"]
    split_rate = dict(
        multi_split=sum(len(split_multi_intent(q["question"])) > 1 for q in multi) / max(len(multi), 1),
        single_split=sum(len(split_multi_intent(q["question"])) > 1 for q in single) / max(len(single), 1),
        false_splits=[q["question"] for q in single if len(split_multi_intent(q["question"])) > 1],
    )
    return rows, split_rate


def underspecified_eval(questions):
    tp = sum(is_underspecified(q["question"]) and q["type"] == "underspecified" for q in questions)
    pred = sum(is_underspecified(q["question"]) for q in questions)
    gold = sum(q["type"] == "underspecified" for q in questions)
    return dict(precision=tp / pred if pred else float("nan"), recall=tp / gold if gold else float("nan"),
                n_pred=pred, n_gold=gold)


# ------------------------------------------------------------------ ghi file
def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def fmt(x, nd=2):
    return "–" if x != x else f"{x:.{nd}f}"   # NaN → –


def main(with_test=False, live="bm25"):
    cfg = load_answer_config()
    max_wrong = cfg["refusal"]["max_wrong_refusal"]
    chunks, qrels = load_chunks(), load_qrels()
    val_q = load_questions({"validation"})
    trval_q = load_questions({"train", "validation"})

    selected = load_spec()["pipeline"]
    pipelines = [p for p in PIPELINES if (RUNS / f"{p}_validation.csv").exists()]
    results, grids, answer_rows = [], [], {}
    for p in pipelines:
        run = load_run(p, "validation")
        rr = RunRetriever(p, run, val_q)
        for ev in (False, True):
            cfg_x = dict(cfg, multi_intent={"split": False}, evidence_check=ev)
            eng = AnswerEngine(cfg_x, retriever=rr.r, chunks=chunks, similar=lambda q, k: [], threshold=0.0)
            eng.evidence_check = ev
            tau, grid = pick_threshold(eng, run, val_q, max_wrong)
            grids += [dict(pipeline=p, evidence_check=ev, **g) for g in grid]
            eng.threshold = tau
            rows = run_answers(eng, val_q, qrels)
            results.append(dict(pipeline=p, evidence_check=ev, threshold=tau, **answer_metrics(rows)))
            answer_rows[(p, ev)] = rows

    # mỗi pipeline: bật kiểm tra căn cứ nếu trên validation nó không làm giảm từ chối đúng và từ chối nhầm
    # vẫn trong trần max_wrong_refusal; không thì tắt và dùng τ của bản "chỉ ngưỡng"
    use_ev, thresholds = {}, {}
    for p in pipelines:
        r = {x["evidence_check"]: x for x in results if x["pipeline"] == p}
        use_ev[p] = bool(r[True]["correct_refusal"] >= r[False]["correct_refusal"]
                         and r[True]["wrong_refusal"] <= max_wrong)
        thresholds[p] = round(r[use_ev[p]]["threshold"], 6)
        if p == selected:
            write_csv(OUT / "validation_answers.csv", answer_rows[(p, use_ev[p])])

    stamp = dt.datetime.now().isoformat(timespec="seconds")
    with open(SELECTED, "w", encoding="utf-8") as f:
        f.write("# SINH TỰ ĐỘNG bởi python -m src.answer.evaluate_answer (chọn trên validation), không sửa tay.\n"
                f"# {stamp}. answer() đọc file này; ngưỡng là điểm top-1 của từng loại pipeline.\n")
        yaml.safe_dump({"thresholds": thresholds, "evidence_check": use_ev, "selected_on": "validation",
                        "max_wrong_refusal": max_wrong}, f, allow_unicode=True, sort_keys=False)
    write_csv(OUT / "threshold_grid.csv", grids)

    # câu nhiều ý + câu thiếu thông tin (train + validation, không test)
    retr = baseline_retrieve(chunks) if live == "bm25" else load_retriever(cfg, chunks)
    mi_rows, split_rate = multi_intent_eval(retr, trval_q, qrels, chunks)
    under = underspecified_eval(trval_q)

    test_rows = None
    if with_test:
        test_q = load_questions({"test"})
        rr = RunRetriever(selected, load_run(selected, "test"), test_q)
        eng = AnswerEngine(dict(cfg, multi_intent={"split": False}), retriever=rr.r, chunks=chunks,
                           similar=lambda q, k: [], threshold=thresholds[selected])
        eng.evidence_check = use_ev[selected]
        rows = run_answers(eng, test_q, qrels)
        write_csv(OUT / "test_answers.csv", rows)
        test_rows = answer_metrics(rows)

    report(results, selected, use_ev, mi_rows, split_rate, under, retr.name, val_q, test_rows, stamp)
    print(f"τ = {thresholds}, evidence_check = {use_ev} → {SELECTED.relative_to(ROOT)}")
    print(f"Báo cáo → {(OUT / 'answer_report.md').relative_to(ROOT)}")


def report(results, selected, use_ev, mi_rows, split_rate, under, live_name, val_q, test_rows, stamp):
    types = Counter(q["type"] for q in val_q)
    L = ["# Đánh giá câu trả lời (Quân, M6)", "",
         f"Sinh tự động bởi `python -m src.answer.evaluate_answer` lúc {stamp}. Mọi tham số chọn trên **validation** "
         f"({len(val_q)} câu: " + ", ".join(f"{t} {n}" for t, n in sorted(types.items())) + "). Test chưa chạy "
         "trong file này trừ khi có mục *test* ở cuối.", "",
         f"Pipeline `answer()` dùng: **{selected}** (theo `configs/retrieval_selected.yaml` của TV3). "
         "Kiểm tra căn cứ con số (chọn theo từng pipeline): " + ", ".join(f"{p} **{'bật' if v else 'tắt'}**" for p, v in use_ev.items()) + ".", "",
         "## 1. Ngưỡng từ chối τ và chất lượng câu trả lời (validation)", "",
         "Từ chối khi điểm top-1 < τ (và, nếu bật, khi câu hỏi đòi con số mà 3 đoạn đầu không có con số đó). "
         "Đúng nguồn = đoạn được trích nằm trong qrels; *chặt* = relevance 2. F1 tính theo âm tiết so với "
         "`answer_text`, chỉ trên câu hợp lệ được trả lời.", "",
         "| Pipeline | Kiểm tra căn cứ | τ | Trả lời | Đúng nguồn | Đúng nguồn (chặt) | F1 trích dòng | F1 trích cả đoạn | Từ chối đúng | Từ chối nhầm |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        L.append(f"| {r['pipeline']} | {'có' if r['evidence_check'] else 'không'} | {r['threshold']:.3f} | "
                 f"{fmt(r['answered'])} | {fmt(r['source_ok'])} | {fmt(r['source_strict'])} | {fmt(r['f1_quote'], 3)} | "
                 f"{fmt(r['f1_chunk'], 3)} | {fmt(r['correct_refusal'])} | {fmt(r['wrong_refusal'])} |")
    L += ["", "Validation chỉ có " + str(types.get("out_of_scope", 0) + types.get("unsupported", 0))
          + " câu cần từ chối, nên tỉ lệ từ chối đúng nhảy theo bước lớn; đọc kèm `threshold_grid.csv`.", "",
          "## 2. Câu nhiều ý: tách và không tách", "",
          f"Câu `multi_intent` có nhãn của train + validation, truy hồi trực tiếp bằng **{live_name}**. "
          "Tách: mỗi ý truy hồi riêng, ghép kết quả xen kẽ (ý 1 hạng 1, ý 2 hạng 1, ...). Hai cột cuối đo phần "
          "câu trả lời: không tách thì chỉ trích 1 đoạn, tách thì trích 1 đoạn cho mỗi ý.", "",
          "| Cách làm | n | R@5 | R@10 | NDCG@5 | Số đoạn đúng được trích | Phủ đoạn rel 2 trong câu trả lời |", "|---|---|---|---|---|---|---|"]
    for r in mi_rows:
        L.append(f"| {r['mode']} | {r['n']} | {r['recall5']:.3f} | {r['recall10']:.3f} | {r['ndcg5']:.3f} | "
                 f"{r['quoted_ok']:.2f} | {r['cover']:.3f} |")
    L += ["", f"Tỉ lệ câu multi_intent được tách: {split_rate['multi_split']:.2f}. "
          f"Tỉ lệ câu một ý bị tách nhầm: {split_rate['single_split']:.2f}."]
    if split_rate["false_splits"]:
        L += ["", "Câu một ý bị tách nhầm:", ""] + [f"- {q}" for q in split_rate["false_splits"][:10]]
    L += ["", "## 3. Câu thiếu thông tin", "",
          "`is_underspecified`: không nhắc việc hộ tịch nào và ≤ 5 âm tiết nội dung. Web vẫn trả lời nhưng hiện "
          "gợi ý chọn việc cụ thể. Train + validation:", "",
          f"Precision {fmt(under['precision'])}, recall {fmt(under['recall'])} "
          f"(đoán {under['n_pred']} câu, nhãn {under['n_gold']} câu).", ""]
    if test_rows:
        L += ["## test (chạy 1 lần, τ đã chốt)", "",
              "| Trả lời | Đúng nguồn | Đúng nguồn (chặt) | F1 trích dòng | Từ chối đúng | Từ chối nhầm |", "|---|---|---|---|---|---|",
              f"| {fmt(test_rows['answered'])} | {fmt(test_rows['source_ok'])} | {fmt(test_rows['source_strict'])} | "
              f"{fmt(test_rows['f1_quote'], 3)} | {fmt(test_rows['correct_refusal'])} | {fmt(test_rows['wrong_refusal'])} |", ""]
    L += ["## Ghi chú", "",
          "- Faithfulness: câu trả lời chỉ gồm khung mẫu + trích nguyên văn `display_text`, không sinh chữ mới, "
          "nên không thể có nội dung ngoài nguồn; lỗi còn lại là chọn sai đoạn, đo bằng cột *Đúng nguồn*.",
          "- F1 so với `answer_text` thấp là bình thường: `answer_text` là câu tóm tắt ngắn do người viết, còn "
          "câu trả lời là điều luật nguyên văn dài hơn nhiều. Chỉ số này dùng để so *trích dòng* với *trích cả đoạn*.",
          "- Chấm tay faithfulness và answer relevance (khoảng 50 câu, 2 người) theo phân công của TV2: dùng "
          "`validation_answers.csv` hoặc `test_answers.csv`."]
    (OUT / "answer_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true", help="chạy test MỘT lần với τ đã chốt (TV2)")
    ap.add_argument("--live", default="bm25", choices=["bm25", "selected"],
                    help="pipeline truy hồi trực tiếp cho phần câu nhiều ý")
    a = ap.parse_args()
    main(with_test=a.test, live=a.live)
