# src/data/ — pipeline dữ liệu (TV1)

Chạy từ thư mục gốc của repo, theo đúng thứ tự:

| Bước | Lệnh | Đọc | Ghi ra |
|---|---|---|---|
| D01 Tải trang | `python -m src.data.crawl` | `data/raw/source_list.csv` | `data/raw/html/*.html`, `data/raw/raw_manifest.csv` |
| D02 Trích xuất + làm sạch | `python -m src.data.parse` | HTML ở trên | `data/interim/docs.jsonl`, log trong `results/data_quality/` |
| D03 Chia đoạn | `python -m src.data.chunk` | `docs.jsonl`, `configs/chunking.yaml`, `configs/preprocessing.yaml` | `data/processed/chunks.jsonl`, `chunks_meta.json` |
| EDA | `python -m src.data.eda` | `docs.jsonl`, `chunks.jsonl` | `results/data_quality/corpus_report.md` + biểu đồ |

Thử 1 thủ tục trước khi chạy hết:

```bash
python -m src.data.crawl --only 1.001193 --headed
python -m src.data.parse --only 1.001193 --show
```

## Các file

| File | Làm gì |
|---|---|
| `crawl.py` | Mở trang bằng Playwright (trang Dịch vụ công render bằng JavaScript), lưu HTML, ghi sha256. Chạy lại chỉ tải trang chưa có. `--force` tải lại, `--register-manual` đăng ký file tự lưu bằng Ctrl+S |
| `parse.py` | Cắt trang theo nhãn mục ("Trình tự thực hiện:", "Thành phần hồ sơ:"...), không phụ thuộc CSS. Sửa nhãn trong `FIELD_LABELS` nếu trang đổi chữ |
| `text_utils.py` | Chuẩn hoá Unicode NFC, khoảng trắng, ký tự rác; đếm số thay đổi theo từng luật |
| `chunk.py` | 1 mục = 1 đoạn, dài quá `max_tokens` thì cắt tiếp có chồng lấn; thêm tiền tố tên thủ tục; tách từ bằng underthesea |
| `eda.py` | Báo cáo chất lượng kho: độ phủ mục, độ dài, thủ tục gần giống nhau, đoạn trùng |

Hướng dẫn chi tiết từng bước (cài đặt trên Windows, lỗi hay gặp): [docs/huong-dan-cao-du-lieu.md](../../docs/huong-dan-cao-du-lieu.md). Schema các file đầu ra: [data/README.md](../../data/README.md).

Test: `python -m pytest tests/test_data_pipeline.py` (chạy trên trang giả trong `tests/fixtures/`, không cần mạng).
