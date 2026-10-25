"""Kiểm tra kho chunks.jsonl (mục 6.2 hướng dẫn TV1). Chỉ đọc file, không cần underthesea."""
import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CHUNKS = ROOT / "data/processed/chunks.jsonl"

pytestmark = pytest.mark.skipif(not CHUNKS.exists(), reason="chưa chạy python -m src.data.chunk")


@pytest.fixture(scope="module")
def chunks():
    return [json.loads(l) for l in open(CHUNKS, encoding="utf-8")]


def test_chunk_id_unique(chunks):
    ids = [c["chunk_id"] for c in chunks]
    assert len(ids) == len(set(ids))


def test_chunk_id_built_from_doc_and_dieu(chunks):
    # ID ghép từ số hiệu + Điều (+ Khoản), không phải số dòng
    for c in chunks:
        assert c["chunk_id"].startswith(f"{c['doc_id']}__D{c['dieu']}") or "__PL" in c["chunk_id"]


def test_no_empty_and_has_all_text_fields(chunks):
    for c in chunks:
        for field in ("chunk_text", "display_text", "text_seg"):
            assert c[field].strip(), f"{c['chunk_id']} thiếu {field}"


def test_length_under_limit(chunks):
    max_tokens = yaml.safe_load(open(ROOT / "configs/chunking.yaml", encoding="utf-8"))["max_tokens"]
    too_long = [c["chunk_id"] for c in chunks if c["n_tokens"] > max_tokens]
    assert not too_long


def test_no_duplicate_text(chunks):
    texts = [c["display_text"] for c in chunks]
    assert len(texts) == len(set(texts))


def test_base_docs_cover_every_dieu(chunks):
    # 4 văn bản gốc chunk toàn bộ: Điều nào còn hiệu lực cũng phải có ít nhất 1 chunk
    expected = {"60.2014.QH13": 77, "123.2015.ND-CP": 48, "04.2020.TT-BTP": 39, "87.2020.ND-CP": 25}
    for doc, n in expected.items():
        assert len({c["dieu"] for c in chunks if c["doc_id"] == doc}) == n, doc


def test_amendments_applied(chunks):
    by_id = {c["chunk_id"]: c for c in chunks}
    # Điều 28a–28c do NĐ 07/2025 thêm vào NĐ 123
    assert any(i.startswith("123.2015.ND-CP__D28a") for i in by_id)
    # khoản 1 Điều 2 NĐ 123 đã bị 18/2026 thay, nên không còn câu về "giai đoạn chuyển tiếp"
    k1 = [c for i, c in by_id.items() if i.startswith("123.2015.ND-CP__D2__K1")]
    assert k1 and all("giai đoạn chuyển tiếp" not in c["display_text"] for c in k1)
    assert all("18.2026.ND-CP" in c["amended_by"] for c in k1)
    # Phụ lục mục I NĐ 120 (thời hạn mới) phải có trong kho
    assert any(i.startswith("120.2025.ND-CP__PL1") for i in by_id)
