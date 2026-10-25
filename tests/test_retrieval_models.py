"""Test phần TV3 (src/retrieval/{query,fusion,retrieve,similar}.py).

Chỉ cần pytest + pyyaml như CI: dùng pipeline BM25 và gợi ý câu tương tự kiểu Dice, không nạp model.
"""
import csv

import pytest

from src.data.split import ROOT
from src.retrieval.fusion import fuse, minmax, ranks, top_k
from src.retrieval.query import clean_query, has_diacritics, strip_accents
from src.retrieval.retrieve import Pipeline, load_chunks, load_config, rerank_candidates, rerank_run
from src.retrieval.similar import SimilarIndex, question_bank

BM25_SPEC = {"pipeline": "bm25"}


@pytest.fixture(scope="module")
def chunks():
    return load_chunks()


@pytest.fixture(scope="module")
def bm25(chunks):
    return Pipeline(BM25_SPEC, load_config(), chunks)


# chuẩn hóa câu hỏi (issue #7)
def test_clean_query_tone_and_nfc():
    import unicodedata
    assert clean_query("thủ tục huỷ  việc nuôi con nuôi ") == "thủ tục hủy việc nuôi con nuôi"
    assert clean_query(unicodedata.normalize("NFD", "khai sinh")) == "khai sinh"


def test_strip_accents_and_detect():
    assert strip_accents("Đăng ký KẾT HÔN") == "dang ky ket hon"
    assert has_diacritics("đăng ký") and not has_diacritics("dang ky ket hon")


# gộp điểm
def test_minmax_and_ranks():
    assert minmax([1, 3, 2]) == [0.0, 1.0, 0.5]
    assert minmax([2, 2]) == [0.0, 0.0]
    assert ranks([0.1, 0.9, 0.5]) == [3, 1, 2]


def test_fuse_minmax_weights():
    dense, sparse = [0.0, 1.0, 0.5], [10.0, 0.0, 5.0]
    assert fuse([dense, sparse], [1, 0]) == [0.0, 1.0, 0.5]
    assert fuse([dense, sparse], [0, 1]) == [1.0, 0.0, 0.5]


def test_fuse_rrf_prefers_agreement():
    a, b = [3.0, 2.0, 1.0], [1.0, 3.0, 2.0]          # chunk 1 có hạng 2 và hạng 1 nên cao nhất
    s = fuse([a, b], [0.5, 0.5], method="rrf")
    assert max(range(3), key=lambda i: s[i]) == 1
    with pytest.raises(ValueError):
        fuse([a], [0.5, 0.5])


def test_top_k_order():
    assert top_k(["a", "b", "c"], [0.2, 0.9, 0.5], 2) == [("b", 0.9), ("c", 0.5)]


# retrieve()
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
    # c được thêm với điểm bước đầu của nó, b có sẵn rồi, a và d điểm BM25 = 0 nên không thêm
    assert rerank_candidates(ids, first, bm25, 2, extra_bm25=3) == [("a", 0.9), ("b", 0.8), ("c", 0.1)]


def test_rerank_run_scores_each_pair_once():
    class Fake:
        """Reranker giả (không import rerank.py vì file đó cần numpy / torch), chỉ có scores và rerank."""
        def __init__(self):
            self.calls = []

        def rerank(self, question, candidates, blend=0.0, ce_scores=None, ce_norm=None):
            return sorted(zip([c for c, _ in candidates], ce_scores), key=lambda x: -x[1])

        def scores(self, question, chunk_ids, restore=None):
            self.calls.append(list(chunk_ids))
            return [float(len(c)) for c in chunk_ids]     # chunk id dài hơn thì điểm cao hơn

    rr, cache, qs = Fake(), {}, [{"question_id": "Q1", "question": "x"}]
    small = rerank_run(rr, {"Q1": [("a", 1.0), ("bb", 0.5)]}, qs, 0.0, cache)
    big = rerank_run(rr, {"Q1": [("a", 1.0), ("bb", 0.5), ("ccc", 0.1)]}, qs, 0.0, cache)
    assert rr.calls == [["a", "bb"], ["ccc"]]            # lần 2 chỉ chấm chunk mới
    assert [c for c, _ in small["Q1"]] == ["bb", "a"] and big["Q1"][0][0] == "ccc"


# điểm cross-encoder: minmax / raw
def _fake_reranker(scores_by_chunk, activation="Sigmoid", **cfg):
    """Reranker thật nhưng model giả, không nạp sentence-transformers, chỉ test phần trộn điểm."""
    from src.retrieval.rerank import Reranker

    class Act:
        pass
    Act.__name__ = activation

    class Model:
        activation_fn = Act()

        def predict(self, pairs, **kw):
            return [scores_by_chunk[t] for _, t in pairs]

    rr = Reranker.__new__(Reranker)
    rr.cfg, rr.model, rr.batch_size, rr.field = cfg, Model(), 16, "chunk_text"
    rr.chunks = {c: {"chunk_text": c} for c in scores_by_chunk}
    return rr


def test_ce_norm_raw_keeps_low_scores_low():
    # câu lạc đề: cross-encoder cho mọi ứng viên rất thấp
    rr = _fake_reranker({"a": 0.03, "b": 0.01})
    cands = [("a", 0.9), ("b", 0.2)]
    mm = rr.rerank("x", cands, blend=0.4)                       # mặc định minmax: top-1 vẫn = 1.0
    raw = rr.rerank("x", cands, blend=0.4, ce_norm="raw")
    assert mm[0] == ("a", pytest.approx(1.0))
    assert raw[0][0] == "a" and raw[0][1] == pytest.approx(0.4 * 1.0 + 0.6 * 0.03)
    assert _fake_reranker({"a": 0.03}, ce_norm="raw").rerank("x", [("a", 1.0)])[0][1] == pytest.approx(0.03)
    with pytest.raises(ValueError):
        rr.rerank("x", cands, ce_norm="abc")


def test_ce_norm_raw_applies_sigmoid_to_logits():
    rr = _fake_reranker({"a": 0.0, "b": -800.0}, activation="Identity")   # model trả logit
    out = dict(rr.rerank("x", [("a", 1.0), ("b", 1.0)], ce_norm="raw"))
    assert out["a"] == pytest.approx(0.5) and 0 <= out["b"] < 1e-6


def test_reranker_restores_unaccented_question():
    seen = []
    rr = _fake_reranker({"a": 0.5}, restore_diacritics=True)
    rr.model.predict = lambda pairs, **kw: seen.extend(q for q, _ in pairs) or [0.5] * len(pairs)
    rr.scores("dang ky khai sinh", ["a"])
    rr.scores("dang ky khai sinh", ["a"], restore=False)
    assert seen == ["đăng ký khai sinh", "dang ky khai sinh"]


# khôi phục dấu
def test_restorer_prefers_longer_ngrams_and_keeps_case():
    from src.retrieval.restore import Restorer
    r = Restorer(["Người phạm tội.", "Tội phạm.", "Tôi muốn đăng ký khai sinh."])
    assert r.restore("toi") == "tội"                             # một mình: dạng gặp nhiều nhất trong bảng
    assert r.restore("Toi muon dang ky") == "Tôi muốn đăng ký"   # có ngữ cảnh: cụm 2–3 âm tiết thắng
    assert r.restore("UBND xa, dang ky?") == "UBND xa, đăng ký?"  # chữ lạ giữ nguyên, giữ dấu câu


def test_restore_query_only_for_unaccented():
    from src.retrieval.restore import restore_query
    assert restore_query("dang ky khai sinh can giay to gi") == "đăng ký khai sinh cần giấy tờ gì"
    assert restore_query("khai sinh ko can giay j") == "khai sinh không cần giấy gì"
    assert restore_query("Đăng ký ket hon") == "Đăng ký ket hon"          # đã có dấu: chỉ mở rộng viết tắt
    assert restore_query("UBND tp Thủ Đức") == "UBND tp Thủ Đức"          # "tp" không bị đổi thành "tư pháp"
    assert restore_query("   ") == ""


def test_restorer_uses_train_questions_only():
    from src.retrieval.restore import _train_questions
    split_of = _split_of()
    with open(ROOT / "data/labels/questions.csv", encoding="utf-8-sig") as f:
        q_split = {r["question"]: split_of.get(r["question_group_id"]) for r in csv.DictReader(f)}
    qs = _train_questions()
    assert qs and all(q_split[q] == "train" for q in qs)


def test_invalid_pipeline_raises(chunks):
    with pytest.raises(ValueError):
        Pipeline({"pipeline": "abc"}, load_config(), chunks)


# câu hỏi tương tự
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
