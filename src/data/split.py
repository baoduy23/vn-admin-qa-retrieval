"""Chia câu hỏi thành train / validation / test theo nhóm câu hỏi, phân tầng theo loại câu.

    python -m src.data.split            (seed, tỉ lệ lấy trong configs/split.yaml)

- Chia theo question_group_id, nên các cách hỏi khác nhau của cùng một ý luôn nằm chung một tập.
- Loại của nhóm lấy theo type của câu gốc (câu có question_id nhỏ nhất trong nhóm).
- Mỗi loại chia khoảng 40/20/40, sau đó hoán đổi nhóm cùng loại để số câu mỗi tập gần
  120/60/120 (hoặc 40%/20%/40% tổng số câu nếu không phải 300 câu).
- Ghi train_qgroups.csv, validation_qgroups.csv, test_qgroups.csv vào data/splits/.
Chạy lại với cùng dữ liệu và seed thì ra đúng kết quả cũ.
"""
from __future__ import annotations

import argparse
import csv
import random
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]  # gốc repo; freeze.py, evaluate.py, hard_negatives.py import từ đây
SPLITS = ("train", "validation", "test")
CFG = yaml.safe_load(open(ROOT / "configs/split.yaml", encoding="utf-8"))
RATIOS = tuple(CFG["ratios"][s] for s in SPLITS)


def load_groups(path: Path) -> dict[str, dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = sorted(csv.DictReader(f), key=lambda r: r["question_id"])
    groups: dict[str, dict] = {}
    for r in rows:
        g = groups.setdefault(r["question_group_id"].strip(), {"type": r["type"].strip(), "n": 0})
        g["n"] += 1  # type lấy từ câu đầu tiên, tức câu gốc
    return groups


def alloc(n: int) -> list[int]:
    raw = [n * r for r in RATIOS]
    base = [int(x) for x in raw]
    for i in sorted(range(3), key=lambda i: -(raw[i] - base[i]))[: n - sum(base)]:
        base[i] += 1
    if n >= 3:  # validation và test mỗi loại có ít nhất 1 nhóm
        for i in (1, 2):
            if base[i] == 0:
                base[i], base[0] = 1, base[0] - 1
    return base


def split_groups(groups: dict[str, dict], seed: int) -> dict[str, int]:
    rng = random.Random(seed)
    by_type = defaultdict(list)
    for gid in sorted(groups):
        by_type[groups[gid]["type"]].append(gid)
    assign: dict[str, int] = {}
    for t in sorted(by_type):
        ids = by_type[t][:]
        rng.shuffle(ids)
        a, start = alloc(len(ids)), 0
        for s, k in enumerate(a):
            for gid in ids[start:start + k]:
                assign[gid] = s
            start += k
    total = sum(g["n"] for g in groups.values())
    t_split = [round(total * RATIOS[0]), round(total * RATIOS[1])]
    t_split.append(total - sum(t_split))
    size = [0, 0, 0]
    for gid, s in assign.items():
        size[s] += groups[gid]["n"]
    cost = lambda sz: sum(abs(sz[i] - t_split[i]) for i in range(3))
    improved = True
    while improved:  # hoán đổi nhóm cùng loại giữa hai tập để sát chỉ tiêu số câu
        improved = False
        for t in sorted(by_type):
            ids = by_type[t]
            for i, g1 in enumerate(ids):
                for g2 in ids[i + 1:]:
                    s1, s2 = assign[g1], assign[g2]
                    if s1 == s2:
                        continue
                    d = groups[g2]["n"] - groups[g1]["n"]
                    new = size[:]
                    new[s1] += d
                    new[s2] -= d
                    if cost(new) < cost(size):
                        assign[g1], assign[g2], size = s2, s1, new
                        improved = True
    return assign


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", type=Path, default=ROOT / "data/labels/questions.csv")
    ap.add_argument("--out", type=Path, default=ROOT / "data/splits")
    ap.add_argument("--seed", type=int, default=CFG["random_seed"])
    a = ap.parse_args()

    groups = load_groups(a.questions)
    assign = split_groups(groups, a.seed)
    a.out.mkdir(parents=True, exist_ok=True)
    for s, name in enumerate(SPLITS):
        with open(a.out / f"{name}_qgroups.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["question_group_id", "group_type", "n_questions"])
            for gid in sorted(g for g, v in assign.items() if v == s):
                w.writerow([gid, groups[gid]["type"], groups[gid]["n"]])

    types = sorted({g["type"] for g in groups.values()})
    print(f"{len(groups)} nhóm, {sum(g['n'] for g in groups.values())} câu, seed {a.seed}\n")
    print(f"{'type':<16}" + "".join(f"{n:>22}" for n in SPLITS))
    print(f"{'':<16}" + "".join(f"{'nhóm/câu':>22}" for _ in SPLITS))
    for t in types:
        cells = []
        for s in range(3):
            gs = [g for g, v in assign.items() if v == s and groups[g]["type"] == t]
            cells.append(f"{len(gs)}/{sum(groups[g]['n'] for g in gs)}")
        print(f"{t:<16}" + "".join(f"{c:>22}" for c in cells))
    tot = [(sum(1 for v in assign.values() if v == s),
            sum(groups[g]["n"] for g, v in assign.items() if v == s)) for s in range(3)]
    print(f"{'TỔNG':<16}" + "".join(f"{f'{g}/{q}':>22}" for g, q in tot))
    for t in types:
        for s in (1, 2):
            if not any(v == s and groups[g]["type"] == t for g, v in assign.items()):
                print(f"CẢNH BÁO: loại {t} không có nhóm nào trong {SPLITS[s]}")


if __name__ == "__main__":
    main()
