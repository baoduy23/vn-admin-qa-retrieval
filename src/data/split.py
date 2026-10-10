"""Chia câu hỏi thành train / validation / test THEO NHÓM (D06, mục 9.1 hướng dẫn TV1).

Mọi câu cùng question_group_id nằm chung một tập, để câu diễn đạt lại không rò từ train sang test.
Mỗi nhóm lấy type xuất hiện nhiều nhất làm "type của nhóm", rồi chia riêng từng type theo tỉ lệ
trong configs/split.yaml (stratify), nên tập nào cũng có đủ các loại, kể cả out_of_scope và unsupported.

Đầu vào : data/labels/questions.csv, configs/split.yaml
Đầu ra  : data/splits/{train,validation,test}_qgroups.csv  (chỉ 1 cột question_group_id)

Chạy từ gốc repo:  python -m src.data.split
Chạy lại khi cả nhóm đã viết xong câu hỏi; sau khi freeze thì KHÔNG chạy lại (test bị khóa).
"""
import csv
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SPLITS = ("train", "validation", "test")


def read_questions(path=ROOT / "data/labels/questions.csv"):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def group_types(questions):
    """question_group_id → type chiếm đa số trong nhóm (hòa thì lấy type của câu đầu)."""
    by_group = defaultdict(list)
    for q in questions:
        by_group[q["question_group_id"]].append(q["type"])
    return {g: Counter(ts).most_common(1)[0][0] for g, ts in by_group.items()}


def allocate(n, ratios):
    """Chia n nhóm theo tỉ lệ bằng phương pháp phần dư lớn nhất: 6 nhóm, 40/20/40 → 3/1/2 hoặc 2/1/3."""
    raw = {s: n * ratios[s] for s in SPLITS}
    out = {s: math.floor(v) for s, v in raw.items()}
    for s in sorted(SPLITS, key=lambda s: raw[s] - out[s], reverse=True)[: n - sum(out.values())]:
        out[s] += 1
    return out


def split_groups(gtype, ratios, seed):
    rng = random.Random(seed)
    by_type = defaultdict(list)
    for g, t in sorted(gtype.items()):           # sort trước để kết quả không phụ thuộc thứ tự file
        by_type[t].append(g)
    result = {s: [] for s in SPLITS}
    for t in sorted(by_type):
        groups = by_type[t]
        rng.shuffle(groups)
        k = allocate(len(groups), ratios)
        i = 0
        for s in SPLITS:
            result[s] += groups[i:i + k[s]]
            i += k[s]
    return {s: sorted(gs) for s, gs in result.items()}


def main():
    cfg = yaml.safe_load(open(ROOT / "configs/split.yaml", encoding="utf-8"))
    questions = read_questions()
    gtype = group_types(questions)
    result = split_groups(gtype, cfg["ratios"], cfg["random_seed"])

    out = ROOT / "data/splits"
    out.mkdir(parents=True, exist_ok=True)
    for s, gs in result.items():
        with open(out / f"{s}_qgroups.csv", "w", encoding="utf-8", newline="") as f:
            f.write("question_group_id\n" + "".join(g + "\n" for g in gs))

    # tóm tắt: số nhóm, số câu, số câu theo type của từng tập
    q_split = {g: s for s, gs in result.items() for g in gs}
    print(f"{'type':16}" + "".join(f"{s:>12}" for s in SPLITS))
    for t in sorted({q["type"] for q in questions}):
        cnt = Counter(q_split[q["question_group_id"]] for q in questions if q["type"] == t)
        print(f"{t:16}" + "".join(f"{cnt[s]:>12}" for s in SPLITS))
    cnt = Counter(q_split[q["question_group_id"]] for q in questions)
    print(f"{'TỔNG câu':16}" + "".join(f"{cnt[s]:>12}" for s in SPLITS))
    print(f"{'TỔNG nhóm':16}" + "".join(f"{len(result[s]):>12}" for s in SPLITS))


if __name__ == "__main__":
    main()
