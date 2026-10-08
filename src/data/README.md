# src/data/ — xử lý dữ liệu (TV1)

Nguồn là văn bản luật tải tay (vbpl.vn, hoặc toàn văn trên thuvienphapluat.vn khi chỉ có PDF scan), nên không có bước cào web. Danh sách văn bản: `data/raw/source_list.csv`.

| File | Làm gì |
|---|---|
| `text_utils.py` | Chuẩn hoá Unicode NFC, thống nhất kiểu bỏ dấu (`normalize_tone`: hoà→hòa, huỷ→hủy), dọn khoảng trắng và ký tự rác. Kho dữ liệu và câu hỏi người dùng đều phải đi qua hàm này |

Sắp có: script tách luật thành đoạn (1 Điều = 1 đoạn, Điều dài quá 200 từ thì tách theo Khoản), chuyển từ `notebooks/01_doc_luat.ipynb` sang, ghi ra `data/processed/chunks.jsonl`.

Test: `python -m pytest tests/test_text_utils.py`
