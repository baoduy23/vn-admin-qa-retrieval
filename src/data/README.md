# src/data/ — xử lý dữ liệu (TV1)

Nguồn là văn bản luật tải tay (vbpl.vn, hoặc toàn văn trên thuvienphapluat.vn khi chỉ có PDF scan), nên không có bước cào web. Danh sách văn bản: `data/raw/source_list.csv`.

| File | Làm gì |
|---|---|
| `text_utils.py` | Chuẩn hoá Unicode NFC, thống nhất kiểu bỏ dấu (`normalize_tone`: hoà→hòa, huỷ→hủy), dọn khoảng trắng và ký tự rác. Kho dữ liệu và câu hỏi người dùng đều phải đi qua hàm này |
| `parse_law.py` | Đọc `data/interim/<doc_id>.docx`, tách Chương → Mục → Điều → Khoản → Điểm (bỏ qua đoạn trích trong ngoặc kép của văn bản sửa đổi), kiểm số Điều từng văn bản → `data/processed/units.jsonl` |
| `apply_amendments.py` | Áp `data/raw/amendments.yaml` (sửa, thêm, bãi bỏ, bỏ cụm từ, đổi tên) theo thứ tự ngày hiệu lực → `units_current.jsonl` (bản hợp nhất) + `amendments_log.csv` |
| `chunk.py` | 1 Điều = 1 chunk, dài quá 200 từ thì tách theo Khoản, Khoản vẫn dài thì gom Điểm thành phần `__P1`, `__P2`; thêm tiền tố tên văn bản + Điều; chọn phần nào của văn bản được chunk theo `configs/chunking.yaml` → `chunks.jsonl` |
| `corpus_report.py` | Báo cáo chất lượng kho (số Điều, độ dài, trùng, hiệu lực, phân bố chunk) → `results/data_quality/` |
| `split.py` | Chia câu hỏi train/validation/test theo `question_group_id`, stratify theo type, seed trong `configs/split.yaml` → `data/splits/` |
| `freeze.py` | Kiểm các tiêu chí freeze (mục 9.2 hướng dẫn TV1) rồi ghi `data/dataset_manifest.json`; `--final` để chốt |

Test: `python -m pytest` (`test_text_utils.py`, `test_chunks.py`, `test_labels.py`). Thứ tự chạy: xem README gốc, mục Pipeline dữ liệu.
