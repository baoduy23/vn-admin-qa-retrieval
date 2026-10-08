import sys
from pathlib import Path

from src.data.chunk import build_chunks, check, pack
from src.data.parse import parse_doc, split_sections
from src.data.text_utils import CleanLog, clean_lines, normalize_tone

sys.path.insert(0, str(Path(__file__).parent / "fixtures"))
import make_fake_pages  # noqa: E402

CFG = {"max_tokens": 200, "overlap_sentences": 1, "add_context_prefix": True,
       "chunk_id_format": "{doc_id}__{field}__{index}"}


def ident(s):
    return s


def _docs(tmp_path):
    ids, titles = make_fake_pages.main(tmp_path)
    docs = []
    for i in ids:
        doc, issues = parse_doc(i, (tmp_path / f"{i}.html").read_text(encoding="utf-8"),
                                {"title": titles[i], "url": f"http://x/{i}"}, {"accessed_at": "2026-10-06"}, CleanLog())
        assert issues == []
        docs.append(doc)
    return docs


def test_parse_splits_fields_and_cach_thuc_table(tmp_path):
    doc = next(d for d in _docs(tmp_path) if d["doc_id"] == "1.001193")
    f = doc["fields"]
    assert doc["title"] == "Đăng ký khai sinh" and doc["ma_thu_tuc_tren_trang"] == "1.001193"
    assert f["thoi_han"].startswith("Trực tiếp: Ngay trong ngày")
    assert "0 Đồng" in f["le_phi"] and "Đồng" not in f["cach_thuc"]
    assert f["thanh_phan_ho_so"].splitlines()[0] == "- Tờ khai đăng ký khai sinh theo mẫu (Bản chính: 1, Bản sao: 0)"
    assert f["can_cu_phap_ly"].startswith("- 60/2014/QH13: Luật Hộ tịch")
    assert "Bản quyền" not in " ".join(f.values()) and "Tải về" not in " ".join(f.values())


def test_label_needs_colon_or_own_line():
    _, fields = split_sections(["Phí, lệ phí:", "Lệ phí đăng ký là 8.000 đồng", "Thời hạn giải quyết cho trường hợp này"])
    assert fields == {"le_phi": ["Lệ phí đăng ký là 8.000 đồng", "Thời hạn giải quyết cho trường hợp này"]}


def test_clean_lines_logs_rules():
    log = CleanLog()
    out = clean_lines(["•  Tờ khai  ;", "Tải về", "a", "a", ""], log)
    assert out == ["- Tờ khai;", "a"]
    assert log.counts["drop_boilerplate_line"] == 1 and log.counts["drop_repeated_line"] == 1


def test_pack_respects_budget_with_overlap():
    units = [f"câu số {i} có năm từ" for i in range(10)]   # 5 token mỗi câu
    chunks = pack(units, ident, max_tokens=17, prefix_tokens=2, overlap=1)
    assert len(chunks) > 1
    assert all(len(c.split()) <= 15 for c in chunks)
    assert chunks[1].splitlines()[0] == chunks[0].splitlines()[-1]   # chồng lấn 1 câu


def test_chunks_stable_and_valid(tmp_path):
    docs = _docs(tmp_path)
    a, b = build_chunks(docs, ident, CFG), build_chunks(list(reversed(docs)), ident, CFG)
    assert [c["chunk_id"] for c in a] == [c["chunk_id"] for c in b]
    assert check(a, docs, 200) == []
    c = next(c for c in a if c["chunk_id"] == "1.001193__le_phi__0")
    assert c["chunk_text"].startswith("Đăng ký khai sinh | Phí, lệ phí: ")
    assert not c["display_text"].startswith("Đăng ký khai sinh")


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


