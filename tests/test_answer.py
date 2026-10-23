"""Test phần trả lời và web (Quân). Không cần model: retrieve() được thay bằng hàm giả."""
from src.answer.answer import AnswerEngine
from src.answer.evaluate_answer import token_f1
from src.answer.intent import (expected_type, find_procedures, has_evidence, is_underspecified,
                               out_of_scope_topic, split_multi_intent)
from src.answer.retriever import Retriever
from src.answer.template import citation, format_answer, highlight_html
from src.app import db

CHUNKS = [
    dict(chunk_id="60.2014.QH13__D16__K1", doc_id="60.2014.QH13", doc_title="Luật Hộ tịch 60/2014/QH13",
         dieu="16", khoan="1", dieu_title="Điều 16. Thủ tục đăng ký khai sinh", muc_ten="ĐĂNG KÝ KHAI SINH",
         display_text="1. Người đi đăng ký khai sinh nộp tờ khai theo mẫu quy định và giấy chứng sinh cho cơ quan đăng ký hộ tịch.",
         url="https://vbpl.vn/x", amended_by=[]),
    dict(chunk_id="60.2014.QH13__D15", doc_id="60.2014.QH13", doc_title="Luật Hộ tịch 60/2014/QH13",
         dieu="15", khoan=None, dieu_title="Điều 15. Trách nhiệm đăng ký khai sinh", muc_ten="ĐĂNG KÝ KHAI SINH",
         display_text="1. Trong thời hạn 60 ngày kể từ ngày sinh con, cha hoặc mẹ có trách nhiệm đăng ký khai sinh cho con.\n"
                      "2. Công chức tư pháp - hộ tịch có trách nhiệm thường xuyên kiểm tra, đôn đốc việc đăng ký khai sinh.",
         url="", amended_by=["07.2025.ND-CP"]),
]
CFG = {"top_k": 5, "evidence_k": 3, "evidence_check": True, "multi_intent": {"split": True},
       "underspecified": {"max_content_syllables": 5}, "similar": {"k": 3}}


def fake_engine(scores):
    """scores: điểm cho 2 chunk theo thứ tự CHUNKS, dùng chung cho mọi câu."""
    def search(q, k):
        pairs = sorted(zip([c["chunk_id"] for c in CHUNKS], scores), key=lambda x: -x[1])
        return pairs[:k]
    return AnswerEngine(CFG, retriever=Retriever("fake", search), chunks=CHUNKS,
                        similar=lambda q, k: [], threshold=0.5)


# ------------------------------------------------------------- intent
def test_split_multi_intent():
    assert split_multi_intent("Kết hôn cần giấy gì và nộp ở đâu?") == ["Kết hôn cần giấy gì", "Kết hôn nộp ở đâu"]
    assert len(split_multi_intent("Khai tử cần giấy tờ gì, ai đi khai và hạn bao nhiêu ngày?")) == 3


def test_no_false_split():
    # "và" giữa hai danh từ, "đầu" (không phải "đâu"), "máy" (không phải "mấy")
    assert len(split_multi_intent("Cha và mẹ đều là người nước ngoài thì khai sinh ở đâu?")) == 1
    assert len(split_multi_intent("Giấy xác nhận độc thân xin từ đầu năm giờ còn dùng được không?")) == 1
    assert len(split_multi_intent("Bằng lái xe máy hết hạn rồi, giờ làm lại thế nào?")) == 1


def test_split_on_question_mark():
    # hai câu hỏi liền nhau ngăn bằng "?"; vế 2 tự nêu việc hộ tịch nên không ghép "Khai sinh" vào
    assert split_multi_intent("Khai sinh cần giấy gì? Kết hôn mất bao lâu?") == ["Khai sinh cần giấy gì",
                                                                                 "Kết hôn mất bao lâu"]
    assert len(split_multi_intent("Khai sinh cần giấy gì?")) == 1


def test_expected_type_and_evidence():
    assert expected_type("Lệ phí cấp bản sao trích lục là bao nhiêu tiền?") == "so_tien"
    assert expected_type("Thời hạn đăng ký khai sinh là bao lâu?") == "thoi_han"
    assert expected_type("Không đi khai tử thì bị phạt không?") == "muc_phat"
    assert expected_type("Cơ quan nào cấp giấy xác nhận phát hiện sai sót?") is None   # "phát" ≠ "phạt"
    assert expected_type("phat hien sai sot trong giay khai sinh thi lam gi") is None   # không dấu: "phat" ≠ mức phạt
    assert expected_type("Người đang chấp hành án phạt tù có đăng ký kết hôn được không?") is None
    assert expected_type("khai sinh tre bi phat bao nhieu") == "muc_phat"
    assert expected_type("Chậm khai tử có bị xử phạt hành chính không?") == "muc_phat"
    assert not has_evidence("muc_phat", ["Cha mẹ bị bắt, tạm giam hoặc đang thi hành án phạt tù."])
    assert has_evidence("muc_phat", ["Phạt tiền từ 200.000 đồng đến 500.000 đồng."])
    assert expected_type("Đăng ký khai sinh cần giấy tờ gì?") is None
    assert has_evidence("thoi_han", ["Trong thời hạn 60 ngày kể từ ngày sinh"])
    assert not has_evidence("so_tien", ["phải nộp lệ phí đăng ký hộ tịch"])
    assert has_evidence(None, [])


def test_underspecified_and_procedures():
    assert is_underspecified("Đăng ký mất bao lâu?")
    assert not is_underspecified("Đăng ký khai sinh mất bao lâu?")
    assert find_procedures("dang ky ket hon voi nguoi nuoc ngoai") == ["Kết hôn"]


# ------------------------------------------------------------- template
def test_citation_reads_khoan_from_quote():
    c = CHUNKS[1]
    assert citation(c, ["2. Công chức tư pháp ..."]) == "Điều 15 Khoản 2"
    assert citation(CHUNKS[0], None) == "Điều 16 Khoản 1"
    assert format_answer(c, ["1. Trong thời hạn 60 ngày"]).startswith('Theo Luật Hộ tịch 60/2014/QH13, Điều 15 Khoản 1: "')


def test_highlight_unaccented_query():
    h = highlight_html("Đăng ký khai sinh <b>", "dang ky khai sinh")
    assert "<mark>Đăng</mark>" in h and "&lt;b&gt;" in h


# ------------------------------------------------------------- answer()
def test_answer_quotes_verbatim():
    r = fake_engine([0.9, 0.8]).answer("Đăng ký khai sinh cần giấy tờ gì?")
    assert not r["refused"]
    quote = r["parts"][0]["quote_lines"][0]
    assert quote in CHUNKS[0]["display_text"]                 # trích nguyên văn, không sinh chữ mới
    assert r["sources"][0]["used_in_answer"] and r["sources"][0]["url"]


def test_answer_prefers_line_with_evidence():
    r = fake_engine([0.1, 0.9]).answer("Thời hạn đăng ký khai sinh là bao lâu?")
    assert r["parts"][0]["quote_lines"][0].startswith("1. Trong thời hạn 60 ngày")
    assert any(n["kind"] == "amended" for n in r["notes"])


def test_refuse_low_score_and_no_evidence():
    r = fake_engine([0.2, 0.1]).answer("Thủ tục xin cấp giấy phép xây dựng nhà ở thế nào?")
    assert r["refused"] and r["reason"] == "low_score"
    assert fake_engine([0.2, 0.1]).answer("Thủ tục tách thửa đất thế nào?")["reason"] == "out_of_scope"
    r = fake_engine([0.9, 0.8]).answer("Lệ phí khai sinh là bao nhiêu tiền?")
    assert r["refused"] and r["reason"] == "no_evidence"
    assert fake_engine([0.9, 0.8]).answer("   ")["reason"] == "empty"


def test_multi_intent_answers_each_part():
    r = fake_engine([0.9, 0.8]).answer("Khai sinh cần giấy gì và hạn bao lâu?")
    assert len(r["parts"]) == 2 and r["answer"].startswith("Câu hỏi gồm 2 ý")


def test_token_f1():
    assert token_f1("trong 60 ngày", "trong 60 ngày") == 1.0
    assert token_f1("abc", "xyz") == 0.0


# ------------------------------------------------------------- SQLite
def test_db_roundtrip(tmp_path):
    path = tmp_path / "app.db"
    r = fake_engine([0.9, 0.8]).answer("Đăng ký khai sinh cần giấy tờ gì?")
    qid = db.log_query(r, path)
    db.save_feedback(qid, 1, "", path)
    db.save_feedback(qid, -1, "trích sai", path)            # bấm lại thì ghi đè
    rows = db.history(path=path)
    assert rows[0]["top_chunk_id"] == "60.2014.QH13__D16__K1" and rows[0]["rating"] == -1
    assert db.summary(path) == {"n": 1, "refused": 0, "up": 0, "down": 1}


# ------------------------------------------------------------- chọn khoản bằng cross-encoder
def test_line_scorer_overrides_idf():
    def fake(question, chunk, lines):              # giả PhoRanker: thích dòng thứ 2
        return [0.0, 1.0][: len(lines)]
    eng = AnswerEngine(CFG, retriever=Retriever("fake", lambda q, k: [(CHUNKS[1]["chunk_id"], 0.9)]),
                       chunks=CHUNKS, similar=lambda q, k: [], threshold=0.5, line_scorer=fake)
    r = eng.answer("Trách nhiệm đăng ký khai sinh cho con của cha mẹ?")
    assert r["parts"][0]["quote_lines"][0].startswith("2. Công chức")
    assert fake_engine([0.1, 0.9]).line_scorer is None      # truyền retriever giả → không nạp model


# ------------------------------------------------------------- câu ngoài phạm vi
def test_out_of_scope_topic():
    assert out_of_scope_topic("Làm hộ chiếu mất bao lâu?") == "hộ chiếu, xuất nhập cảnh"
    assert out_of_scope_topic("bang lai xe het han doi o dau") == "giao thông"          # gõ không dấu
    assert out_of_scope_topic("Ly hôn thì tài sản chung chia thế nào?")                  # nhắc ly hôn vẫn chặn
    # có nhắc việc hộ tịch → để truy hồi xử lý, không chặn
    assert out_of_scope_topic("Làm khai sinh cho con có cần căn cước của cha mẹ không?") is None
    assert out_of_scope_topic("Tôi đang tạm trú ở Bình Dương thì làm khai sinh cho con ở đó được không?") is None
    assert out_of_scope_topic("Đăng ký khai sinh cần giấy tờ gì?") is None
    # "chết" chỉ là từ đời thường, không phải tên thủ tục: câu hỏi sang tên sổ đỏ vẫn bị chặn
    assert out_of_scope_topic("Bố chết thì sổ đỏ sang tên thế nào?") == "đất đai, nhà ở"
    assert out_of_scope_topic("Bố chết thì làm khai tử ở đâu?") is None


def test_out_of_scope_refused_before_retrieval():
    called = []
    eng = AnswerEngine(CFG, retriever=Retriever("fake", lambda q, k: called.append(q) or [(CHUNKS[0]["chunk_id"], 0.99)]),
                       chunks=CHUNKS, similar=lambda q, k: [], threshold=0.5)
    r = eng.answer("Làm hộ chiếu mất bao lâu?")
    assert r["refused"] and r["reason"] == "out_of_scope" and r["parts"] == [] and called == []
    assert "hộ chiếu" in r["answer"]
    off = AnswerEngine(dict(CFG, out_of_scope_filter=False), retriever=eng.retriever, chunks=CHUNKS,
                       similar=lambda q, k: [], threshold=0.5)
    assert not off.answer("Làm hộ chiếu ở đâu?")["refused"]                             # tắt lọc: như cũ


def test_out_of_scope_part_of_multi_intent():
    # cả câu có "khai tử" nên qua lọc cả câu; ý 2 hỏi sổ đỏ phải bị từ chối riêng, ý 1 vẫn được trả lời
    r = fake_engine([0.9, 0.8]).answer("Khai tử cho bố cần giấy gì? Sổ đỏ sang tên thế nào?")
    assert len(r["parts"]) == 2 and not r["refused"]
    p1, p2 = r["parts"]
    assert not p1["refused"]
    assert p2["refused"] and p2["reason"] == "out_of_scope" and p2["top_chunks"] == []
    assert p2["question"] == "Sổ đỏ sang tên thế nào"                     # không kèm chủ đề ghép từ ý 1
    assert "đất đai" in r["answer"]


def test_no_overlap_refused_before_retrieval():
    # điểm rerank là minmax: câu vô nghĩa vẫn có top-1 = 0.99 > τ, phải chặn trước khi truy hồi
    called = []
    eng = AnswerEngine(CFG, retriever=Retriever("fake", lambda q, k: called.append(q) or [(CHUNKS[0]["chunk_id"], 0.99)]),
                       chunks=CHUNKS, similar=lambda q, k: [], threshold=0.5)
    for q in ("hello world", "hello word", "asdf qwer"):
        r = eng.answer(q)
        assert r["refused"] and r["reason"] == "no_overlap" and r["parts"] == [], q
    assert called == []
    assert not eng.answer("dang ky khai sinh can giay gi")["refused"]                  # không dấu vẫn khớp kho
    off = AnswerEngine(dict(CFG, no_overlap_filter=False), retriever=eng.retriever, chunks=CHUNKS,
                       similar=lambda q, k: [], threshold=0.5)
    assert not off.answer("hello world")["refused"]                                    # tắt lọc: như cũ
