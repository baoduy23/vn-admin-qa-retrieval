"""Kiểm tra questions.csv, qrels.csv và split (chỉ dùng csv/json, chạy được trên CI không cần underthesea).

Chạy: python -m pytest tests/test_labels.py
"""
import csv
import json
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TYPES = {"direct", "paraphrase", "underspecified", "multi_intent", "confusable", "out_of_scope", "unsupported"}
NO_QRELS = {"out_of_scope", "unsupported"}


def read(rel):
    with open(ROOT / rel, encoding="utf-8") as f:
        return list(csv.DictReader(f))


QUESTIONS = read("data/labels/questions.csv")
QRELS = read("data/labels/qrels.csv")
pytestmark = pytest.mark.skipif(not QUESTIONS, reason="chưa có câu hỏi")


def test_question_rows_valid():
    ids = [q["question_id"] for q in QUESTIONS]
    assert len(ids) == len(set(ids)), "question_id trùng"
    for q in QUESTIONS:
        assert q["type"] in TYPES, q
        assert q["source"] in {"human", "generated"}, q
        assert q["question"].strip() and q["question_group_id"].strip() and q["annotator"].strip(), q


def test_qrels_point_to_existing_questions_and_chunks():
    chunks_path = ROOT / "data/processed/chunks.jsonl"
    if not chunks_path.exists():
        pytest.skip("chưa có chunks.jsonl")
    chunk_ids = {json.loads(l)["chunk_id"] for l in open(chunks_path, encoding="utf-8")}
    qids = {q["question_id"] for q in QUESTIONS}
    for r in QRELS:
        assert r["question_id"] in qids, r
        assert r["chunk_id"] in chunk_ids, r
        assert r["relevance"] in {"1", "2"}, r
    assert not [p for p, n in Counter((r["question_id"], r["chunk_id"]) for r in QRELS).items() if n > 1]


def test_answerable_have_qrels_and_refusals_have_none():
    has = Counter(r["question_id"] for r in QRELS)
    for q in QUESTIONS:
        if q["type"] in NO_QRELS:
            assert not has[q["question_id"]], f"{q['question_id']} ({q['type']}) không được có qrels"
        else:
            assert has[q["question_id"]], f"{q['question_id']} ({q['type']}) chưa có qrels"


def test_split_by_group_without_leak():
    paths = {s: ROOT / f"data/splits/{s}_qgroups.csv" for s in ("train", "validation", "test")}
    if not all(p.exists() for p in paths.values()):
        pytest.skip("chưa chạy python -m src.data.split")
    seen = {}
    for s, p in paths.items():
        for r in read(p.relative_to(ROOT)):
            assert r["question_group_id"] not in seen, f"nhóm {r['question_group_id']} ở cả {seen[r['question_group_id']]} và {s}"
            seen[r["question_group_id"]] = s
    assert {q["question_group_id"] for q in QUESTIONS} <= set(seen), "có nhóm chưa được chia (chạy lại split)"
