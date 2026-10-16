"""Nạp sẵn lịch sử mẫu cho buổi demo, để trang Thống kê không trống (Quân).

    python -m src.app.demo_seed            # hỏi lần lượt các câu train + validation, ghi vào artifacts/app.db
    python -m src.app.demo_seed --n 40     # chỉ 40 câu

Chỉ dùng câu train + validation (KHÔNG lấy test), đánh giá ngẫu nhiên có seed để ra số liệu giống nhau.
Muốn xóa: xóa file artifacts/app.db.
"""
from __future__ import annotations

import argparse
import random

from src.answer.answer import get_engine
from src.answer.evaluate_answer import load_questions
from src.app import db


def main(n: int | None = None, seed: int = 42) -> None:
    qs = load_questions({"train", "validation"})
    random.Random(seed).shuffle(qs)
    engine = get_engine()
    for q in qs[:n] if n else qs:
        db.log_query(engine.answer(q["question"]))
    print(db.summary(), "→", db.DB_PATH)
    
    
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=None)
    main(ap.parse_args().n)