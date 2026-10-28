"""Đo thời gian phản hồi giống như web, trên câu hỏi train hoặc validation (không cho chạy test).

    python -m src.answer.latency                       (57 câu validation, pipeline đã chốt)
    python -m src.answer.latency --repeat 3            (mỗi câu đo 3 lần, lấy từng lần)
    ANSWER_PIPELINE=bm25 python -m src.answer.latency  (bản BM25 khi máy không có torch)

Đo 3 thứ, đều tính bằng ms, trên CPU của máy đang chạy:
  1. Nạp: dựng AnswerEngine (nạp chunk, bi-encoder, cross-encoder, bộ chọn dòng), chỉ xảy ra 1 lần lúc mở web.
  2. Câu đầu tiên sau khi nạp (còn khởi động thư viện), ghi riêng vì chậm hơn hẳn các câu sau.
  3. Từng bước truy hồi (BM25, dense, hybrid, rerank) và cả hàm answer() như web gọi (main.py run_query):
     answer() gồm lọc câu, truy hồi, kiểm tra căn cứ, chọn dòng trích, câu hỏi tương tự.
Từng bước chỉ đo khi pipeline đã chốt là rerank và nạp được model; bản BM25 thì chỉ có bm25 và answer.

Chỉ đo thời gian, không chấm đúng sai, nên không ghi gì vào kết quả đánh giá.
Đầu ra: results/answer/latency_<split>.csv (từng câu, từng bước) và latency_report.md
"""
from __future__ import annotations

import argparse
import csv
import os
import platform
import time
from statistics import mean, median

from src.data.split import ROOT
from src.retrieval.fusion import top_k

OUT = ROOT / "results/answer"
STAGES = ("bm25", "dense", "hybrid", "rerank", "answer")


# 1. Câu hỏi và môi trường
def load_questions(split: str) -> list[dict]:
    split_of = {}
    for s in ("train", "validation", "test"):
        with open(ROOT / f"data/splits/{s}_qgroups.csv", encoding="utf-8") as f:
            split_of |= {r["question_group_id"]: s for r in csv.DictReader(f)}
    with open(ROOT / "data/labels/questions.csv", encoding="utf-8") as f:
        return [q for q in csv.DictReader(f) if split_of.get(q["question_group_id"]) == split]


def machine() -> str:
    """CPU, số luồng, RAM, Python, torch (nếu có). Thiếu psutil thì bỏ phần RAM."""
    cpu = platform.processor() or platform.machine()
    if platform.system() == "Linux":
        try:
            with open("/proc/cpuinfo", encoding="utf-8") as f:
                cpu = next(l.split(":", 1)[1].strip() for l in f if l.startswith("model name"))
        except (OSError, StopIteration):
            pass
    parts = [f"{platform.system()} {platform.release()}", cpu, f"{os.cpu_count()} luồng"]
    try:
        import psutil
        parts.append(f"RAM {psutil.virtual_memory().total / 2**30:.1f} GB")
    except ImportError:
        pass
    parts.append(f"Python {platform.python_version()}")
    try:
        import torch
        parts.append(f"torch {torch.__version__}, {torch.get_num_threads()} luồng torch")
    except ImportError:
        pass
    return ", ".join(parts)


# 2. Đo
def timed(fn, *args) -> float:
    t = time.perf_counter()
    fn(*args)
    return (time.perf_counter() - t) * 1000


def stage_fns(engine) -> dict:
    """Hàm gọi từng bước truy hồi. Dùng lại pipeline mà answer() đang dùng nên không nạp model lần hai."""
    fns = {"answer": engine.answer}
    if engine.retriever.name != "rerank" or engine.retriever.warning:
        fns["bm25"] = lambda q: engine.retriever.search(q, 10)
        return fns
    from src.retrieval.retrieve import get_pipeline
    p = get_pipeline()
    for s in ("bm25", "dense", "hybrid"):
        fns[s] = lambda q, s=s: top_k(p.ids, p.stage_scores(q, s), 10)
    fns["rerank"] = lambda q: p.search(q, 10)
    return fns


def run(split: str, repeat: int) -> tuple[dict, list[dict], str]:
    from src.answer.answer import AnswerEngine
    questions = load_questions(split)
    t = time.perf_counter()
    engine = AnswerEngine()
    load_ms = (time.perf_counter() - t) * 1000
    fns = stage_fns(engine)
    first = {s: timed(fn, questions[0]["question"]) for s, fn in fns.items()}
    rows = []
    for i in range(repeat):
        for q in questions:
            for s in STAGES:
                if s in fns:
                    rows.append(dict(split=split, question_id=q["question_id"], type=q["type"], repeat=i + 1,
                                     stage=s, ms=round(timed(fns[s], q["question"]), 1)))
    info = dict(load_ms=load_ms, first=first, pipeline=engine.retriever.name, warning=engine.retriever.warning,
                n=len(questions))
    return info, rows, machine()


# 3. Ghi kết quả
def pct(xs: list[float], p: float) -> float:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p * (len(xs) - 1))))]


def write(info: dict, rows: list[dict], env: str, split: str, repeat: int) -> None:
    with open(OUT / f"latency_{split}.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    L = ["# Thời gian phản hồi", "",
         f"Sinh bởi `python -m src.answer.latency --split {split} --repeat {repeat}`. {info['n']} câu {split}, "
         f"mỗi câu đo {repeat} lần, sau 1 câu khởi động. Pipeline: **{info['pipeline']}**."
         + (f" Cảnh báo: {info['warning']}" if info["warning"] else ""), "",
         f"Máy: {env}.", "",
         f"Nạp hệ thống (dựng AnswerEngine, gồm nạp model): **{info['load_ms'] / 1000:.1f} s**. "
         "Web chỉ nạp 1 lần lúc mở, các lượt hỏi sau dùng lại.", "",
         "| Bước | Câu đầu (ms) | Trung bình (ms) | Trung vị (ms) | p95 (ms) | Lớn nhất (ms) |",
         "|---|---|---|---|---|---|"]
    names = {"bm25": "BM25 (top-10)", "dense": "Dense e5 (top-10)", "hybrid": "Hybrid (top-10)",
             "rerank": "Hybrid + rerank (top-10)", "answer": "answer() như web"}
    for s in STAGES:
        xs = [r["ms"] for r in rows if r["stage"] == s]
        if xs:
            L.append(f"| {names[s]} | {info['first'][s]:.0f} | {mean(xs):.0f} | {median(xs):.0f} | "
                     f"{pct(xs, 0.95):.0f} | {max(xs):.0f} |")
    if "rerank" in info["first"]:
        L += ["", "Mỗi bước đo riêng từ đầu (rerank đã gồm thời gian BM25 + dense + hybrid để lấy ứng viên). "
              "answer() còn gồm lọc câu, chọn dòng trích bằng PhoRanker và câu hỏi tương tự, nên chậm hơn rerank."]
    L.append("")
    path = OUT / "latency_report.md"
    path.write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="validation", choices=["train", "validation"],
                    help="không cho chọn test: test chỉ được chạy 1 lần")
    ap.add_argument("--repeat", type=int, default=1)
    a = ap.parse_args()
    info, rows, env = run(a.split, a.repeat)
    write(info, rows, env, a.split, a.repeat)


if __name__ == "__main__":
    main()
