"""Phân công gán nhãn chéo và chọn 20% nhóm cho hai người gán độc lập.

    python -m src.labels.sample_double --questions data/labels/questions.csv \
        --n-members 5 --seed 42 --frac 0.2 --out data/labels/label_assignments.csv

- writer: lấy số TV từ cột annotator (ví dụ "TV2", "TV1-Duy ...").
- labeler_1 (gán chính): TV(w+1), xoay vòng; người viết 5 thì TV1 gán.
- labeler_2 (chỉ nhóm được chọn 20%): TV(w+2), khác người viết và labeler_1.
- Chọn ngẫu nhiên theo nhóm, phân tầng theo loại câu gốc, mỗi loại ít nhất 1 nhóm.
"""
from __future__ import annotations

import argparse
import csv
import random
import re
from collections import defaultdict
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", type=Path, default=Path("data/labels/questions.csv"))
    ap.add_argument("--out", type=Path, default=Path("data/labels/label_assignments.csv"))
    ap.add_argument("--n-members", type=int, default=5)
    ap.add_argument("--frac", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()

    with open(a.questions, encoding="utf-8-sig", newline="") as f:
        rows = sorted(csv.DictReader(f), key=lambda r: r["question_id"])
    groups: dict[str, dict] = {}
    for r in rows:
        gid = r["question_group_id"].strip()
        if gid not in groups:
            m = re.search(r"TV(\d+)", r["annotator"])
            if not m:
                raise SystemExit(f"{r['question_id']}: không đọc được người viết từ annotator={r['annotator']!r}")
            groups[gid] = {"type": r["type"].strip(), "writer": int(m.group(1)), "n": 0}
        groups[gid]["n"] += 1

    rng = random.Random(a.seed)
    by_type = defaultdict(list)
    for gid in sorted(groups):
        by_type[groups[gid]["type"]].append(gid)
    chosen = set()
    for t in sorted(by_type):
        ids = by_type[t][:]
        rng.shuffle(ids)
        chosen.update(ids[: max(1, round(a.frac * len(ids)))])

    nm = a.n_members
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["question_group_id", "group_type", "n_questions", "writer", "labeler_1", "labeler_2"])
        for gid in sorted(groups):
            g = groups[gid]
            l1 = f"TV{g['writer'] % nm + 1}"
            l2 = f"TV{(g['writer'] + 1) % nm + 1}" if gid in chosen else ""
            w.writerow([gid, g["type"], g["n"], f"TV{g['writer']}", l1, l2])
    nq = sum(groups[g]["n"] for g in chosen)
    print(f"{len(chosen)}/{len(groups)} nhóm ({nq} câu) được gán độc lập bởi 2 người -> {a.out}")
    cnt = defaultdict(int)
    for g in chosen:
        cnt[groups[g]["type"]] += 1
    print("theo loại:", dict(sorted(cnt.items())))


if __name__ == "__main__":
    main()
