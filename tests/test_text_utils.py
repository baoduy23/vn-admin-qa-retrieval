from src.data.text_utils import CleanLog, clean_lines, normalize_tone


def test_clean_lines_logs_rules():
    log = CleanLog()
    out = clean_lines(["•  Tờ khai  ;", "Tải về", "a", "a", ""], log)
    assert out == ["- Tờ khai;", "a"]
    assert log.counts["drop_boilerplate_line"] == 1 and log.counts["drop_repeated_line"] == 1


def test_normalize_tone():
    #5 từ đầu đổi, các từ còn lại giữ nguyên
    # hoàn/khoản: có phụ âm cuối | hoặc, HOẶC: dấu nặng + dấu trăng (bug đã gặp)
    # quý, QUỶ: sau q | hòa: đã là kiểu mới
    log = CleanLog()
    vao = "Hoà thuận, huỷ, khoẻ, UỶ BAN, tuỳ; hoàn, khoản, hoặc, HOẶC, quý, QUỶ, hòa"
    ra = "Hòa thuận, hủy, khỏe, ỦY BAN, tùy; hoàn, khoản, hoặc, HOẶC, quý, QUỶ, hòa"
    assert normalize_tone(vao, log) == ra
    assert log.counts["tone_mark_style"] == 5
    assert normalize_tone(ra) == ra


def test_bm25_matches_both_tone_styles():
    # Kho viết kiểu MỚI, câu hỏi gõ kiểu CŨ. Câu hỏi CHỈ có đúng 1 từ khác kiểu dấu,
    # để không còn từ nào khác "cứu" kết quả: nếu tokenize không chuẩn hóa thì điểm = 0.
    from src.retrieval.bm25 import BM25, tokenize
    assert tokenize("Hu\u1ef7 KẾT HÔN") == tokenize("hủy kết hôn")    # "Huỷ" kiểu cũ
    bm = BM25(["thủ tục hủy kết hôn", "đăng ký khai sinh"], ["a", "b"])
    assert bm.scores("hu\u1ef7")[0] > 0       # "huỷ" phải khớp "hủy" trong đoạn a
