import math

from src.retrieval.bm25 import BM25
from src.retrieval.metrics import evaluate, ndcg_at_k, recall_at_k, reciprocal_rank


def test_recall_and_mrr():
    ranked = ["a", "b", "c"]
    qrels = {"b": 2, "d": 1}
    assert recall_at_k(ranked, qrels, 3) == 0.5
    assert reciprocal_rank(ranked, qrels) == 0.5


def test_ndcg_perfect_is_one():
    assert math.isclose(ndcg_at_k(["a", "b"], {"a": 2, "b": 1}, 2), 1.0)


def test_evaluate_skips_out_of_scope():
    res = evaluate({"q1": ["a"], "q_oos": ["a"]}, {"q1": {"a": 2}}, ks=(1,))
    assert res["n_questions"] == 1 and res["recall@1"] == 1.0


def test_bm25_ranks_matching_chunk_first():
    docs = ["Đăng ký khai sinh. Thành phần hồ sơ: tờ khai, giấy chứng sinh",
            "Đăng ký kết hôn. Thời hạn: ngay trong ngày",
            "Đăng ký khai tử. Cơ quan thực hiện: UBND cấp xã"]
    bm = BM25(docs, ["ks", "kh", "kt"])
    assert bm.search("khai sinh cần giấy chứng sinh không", k=1)[0][0] == "ks"
