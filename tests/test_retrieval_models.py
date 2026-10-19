"""Test phần TV3 (src/retrieval/{query,fusion,retrieve,similar}.py).

Chỉ cần pytest + pyyaml như CI: dùng pipeline BM25 và gợi ý câu tương tự kiểu Dice, không nạp model.
"""
import csv

import pytest

from src.data.split import ROOT
from src.retrieval.fusion import fuse, minmax, ranks, top_k
from src.retrieval.query import clean_query, has_diacritics, strip_accents
from src.retrieval.retrieve import Pipeline, load_chunks, load_config, rerank_candidates
from src.retrieval.similar import SimilarIndex, question_bank

BM25_SPEC = {"pipeline": "bm25"}


@pytest.fixture(scope="module")
def chunks():
    return load_chunks()


@pytest.fixture(scope="module")
def bm25(chunks):
    return Pipeline(BM25_SPEC, load_config(), chunks)


# ---------- chuẩn hóa câu hỏi (issue #7) ----------
def test_clean_query_tone_and_nfc():
    import unicodedata
    assert clean_query("thủ tục huỷ  việc nuôi con nuôi ") == "thủ tục hủy việc nuôi con nuôi"
    assert clean_query(unicodedata.normalize("NFD", "khai sinh")) == "khai sinh"


def test_strip_accents_and_detect():
    assert strip_accents("Đăng ký KẾT HÔN") == "dang ky ket hon"
    assert has_diacritics("đăng ký") and not has_diacritics("dang ky ket hon")


# ---------- gộp điểm ----------
def test_minmax_and_ranks():
    assert minmax([1, 3, 2]) == [0.0, 1.0, 0.5]
    assert minmax([2, 2]) == [0.0, 0.0]
    assert ranks([0.1, 0.9, 0.5]) == [3, 1, 2]


def test_fuse_minmax_weights():
    dense, sparse = [0.0, 1.0, 0.5], [10.0, 0.0, 5.0]
    assert fuse([dense, sparse], [1, 0]) == [0.0, 1.0, 0.5]
    assert fuse([dense, sparse], [0, 1]) == [1.0, 0.0, 0.5]


def test_fuse_rrf_prefers_agreement():
    a, b = [3.0, 2.0, 1.0], [1.0, 3.0, 2.0]          # chunk 1: hạng 2 và hạng 1 → cao nhất
    s = fuse([a, b], [0.5, 0.5], method="rrf")
    assert max(range(3), key=lambda i: s[i]) == 1
    with pytest.raises(ValueError):
        fuse([a], [0.5, 0.5])


def test_top_k_order():
    assert top_k(["a", "b", "c"], [0.2, 0.9, 0.5], 2) == [("b", 0.9), ("c", 0.5)]


# ---------- retrieve() ----------
def test_retrieve_interface(bm25, chunks):
    res = bm25.search("Hồ sơ đăng ký khai sinh gồm những giấy tờ gì?", k=5)
    assert len(res) == 5
    ids = {c["chunk_id"] for c in chunks}
    assert all(isinstance(c, str) and c in ids and isinstance(s, float) for c, s in res)
    assert [s for _, s in res] == sorted((s for _, s in res), reverse=True)


def test_retrieve_empty_question(bm25):
    assert bm25.search("   ", k=5) == []


def test_old_tone_style_same_result(bm25):
    # issue #7: "huỷ" (kiểu cũ) và "hủy" (kiểu mới) phải ra cùng kết quả
    assert bm25.search("thủ tục huỷ kết hôn trái pháp luật", 10) == bm25.search("thủ tục hủy kết hôn trái pháp luật", 10)


def test_unaccented_query_finds_same_top(bm25):
    acc = [c for c, _ in bm25.search("đăng ký khai tử", 10)]
    plain = [c for c, _ in bm25.search("dang ky khai tu", 10)]
    assert set(acc[:3]) & set(plain)


def test_rerank_candidates_adds_bm25_misses():
    ids = ["a", "b", "c", "d"]
    first = [0.9, 0.8, 0.1, 0.2]          # bước đầu: top-2 = a, b
    bm25 = [0.0, 5.0, 9.0, 0.0]           # BM25: c đứng đầu nhưng bước đầu bỏ sót
    assert rerank_candidates(ids, first, bm25, 2) == [("a", 0.9), ("b", 0.8)]
    # c được thêm với điểm bước đầu của nó; b đã có; a, d điểm BM25 = 0 nên không thêm
    assert rerank_candidates(ids, first, bm25, 2, extra_bm25=3) == [("a", 0.9), ("b", 0.8), ("c", 0.1)]


def test_rerank_run_scores_each_pair_once():
    from src.retrieval.evaluate_models import rerank_run
    from src.retrieval.rerank import Reranker

    class Fake(Reranker):
        def __init__(self):
            self.calls = []

        def scores(self, question, chunk_ids):
            self.calls.append(list(chunk_ids))
            return [float(len(c)) for c in chunk_ids]     # chunk id dài hơn = điểm cao hơn

    rr, cache, qs = Fake(), {}, [{"question_id": "Q1", "question": "x"}]
    small = rerank_run(rr, {"Q1": [("a", 1.0), ("bb", 0.5)]}, qs, 0.0, cache)
    big = rerank_run(rr, {"Q1": [("a", 1.0), ("bb", 0.5), ("ccc", 0.1)]}, qs, 0.0, cache)
    assert rr.calls == [["a", "bb"], ["ccc"]]            # lần 2 chỉ chấm chunk mới
    assert [c for c, _ in small["Q1"]] == ["bb", "a"] and big["Q1"][0][0] == "ccc"


def test_invalid_pipeline_raises(chunks):
    with pytest.raises(ValueError):
        Pipeline({"pipeline": "abc"}, load_config(), chunks)


# ---------- câu hỏi tương tự ----------
def _split_of():
    out = {}
    for s in ("train", "validation", "test"):
        with open(ROOT / f"data/splits/{s}_qgroups.csv", encoding="utf-8-sig") as f:
            out.update({r["question_group_id"]: s for r in csv.DictReader(f)})
    return out


def test_question_bank_excludes_test_and_unanswerable():
    bank = question_bank()
    split_of = _split_of()
    assert bank
    assert all(split_of[r["question_group_id"]] != "test" for r in bank)
    assert all(r["type"] not in {"out_of_scope", "unsupported"} for r in bank)


def test_similar_questions_lexical():
    idx = SimilarIndex(question_bank(), None)
    q = idx.bank[0]["question"]
    res = idx.search(q, k=3, min_score=0.0)
    assert res and all(r["question"] != q for r in res)                     # không gợi ý lại chính câu đó
    assert len({r["question_id"] for r in res}) == len(res)
    assert all(set(r) == {"question_id", "question", "answer_text", "score"} for r in res)
    groups = {r["question_id"]: r["question_group_id"] for r in idx.bank}
    assert len({groups[r["question_id"]] for r in res}) == len(res)       # mỗi nhóm 1 câu
    assert idx.search(q, k=3, min_score=1.01) == []
