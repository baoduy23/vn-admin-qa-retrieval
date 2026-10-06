# Hướng dẫn D01–D03: từ trang Dịch vụ công đến chunks.jsonl + báo cáo

Dành cho TV1. Làm lần lượt từ bước 0 đến bước 7. Mỗi bước là một script chạy lại được bao nhiêu lần cũng ra cùng kết quả, đầu ra của bước trước là đầu vào của bước sau.

```
source_list.csv ──crawl──► raw/html/*.html + raw_manifest.csv      (D01, bất biến)
                 ──parse──► interim/docs.jsonl + cleaning_log.csv   (D02 trích xuất + làm sạch)
                 ──chunk──► processed/chunks.jsonl + chunks_meta.json (D03)
                 ──eda────► results/data_quality/corpus_report.md + figures/  (báo cáo)
```

## 0. Cài đặt (Windows, PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium     # tải trình duyệt headless cho crawler (~150 MB)
python -m pytest -q                        # phải pass hết trước khi làm tiếp
```

Mọi lệnh bên dưới chạy ở **thư mục gốc repo**, dạng `python -m src.data.<tên>`.

## 1. Điền `data/raw/source_list.csv`

Mỗi thủ tục một dòng. Lấy từ Cổng DVC: tra cứu thủ tục → lọc **Lĩnh vực: Hộ tịch**, **Cấp thực hiện: Cấp Xã** → mở từng thủ tục → copy URL trên thanh địa chỉ và **Mã thủ tục** trên trang.

```csv
doc_id,title,source_type,url,issuing_level,legal_basis,accessed_at,in_scope
1.001193,Đăng ký khai sinh,dichvucong,https://dichvucong.gov.vn/p/home/dvc-tthc-thu-tuc-hanh-chinh-chi-tiet.html?ma_thu_tuc=...,Cấp Xã,,,yes
```

- `doc_id` = mã thủ tục trên trang (dạng `1.001193`). Không đặt kiểu `ts01`, vì parser sẽ đối chiếu mã trên trang với `doc_id` để bắt lỗi copy nhầm URL.
- `url`: copy y nguyên từ trình duyệt.
- `accessed_at` để trống, crawler tự ghi vào manifest.
- Thủ tục muốn tạm bỏ thì để `in_scope = no`, đừng xóa dòng.

## 2. Thử trên 1 thủ tục trước (quan trọng)

Parser không bám vào class CSS của trang mà cắt theo **nhãn mục** ("Trình tự thực hiện:", "Thành phần hồ sơ:", ...). Danh sách nhãn nằm ở `FIELD_LABELS` trong `src/data/parse.py`. Nhãn được viết theo bố cục Cổng DVC, nhưng chưa được kiểm tra trên trang thật, nên thử 1 thủ tục trước:

```powershell
python -m src.data.crawl --only 1.001193 --headed     # thấy trình duyệt mở trang là đúng
python -m src.data.parse --only 1.001193 --show       # in JSON ra màn hình, không ghi file
```

Soi JSON in ra:
- `fields` có đủ `trinh_tu`, `thanh_phan_ho_so`, `thoi_han`, `le_phi`, `co_quan`, `can_cu_phap_ly` chưa?
- Thiếu mục nào thì mở `data/raw/html/1.001193.html` bằng trình duyệt, xem nhãn trên trang viết chính xác thế nào (ví dụ "Thời hạn giải quyết" hay "Thời gian giải quyết"), rồi thêm vào list tương ứng trong `FIELD_LABELS`.
- Mục nào dính rác (chữ menu, "Tải về", chân trang) thì thêm dòng đó vào `BOILERPLATE_LINES` (`src/data/text_utils.py`) hoặc nhãn bắt đầu vùng rác vào `STOP_LABELS`.
- Trên Cổng DVC, thời hạn và phí nằm chung bảng "Cách thức thực hiện". Parser tự tách bảng này ra 3 mục `cach_thuc`, `thoi_han`, `le_phi` để không có 2 đoạn trùng thông tin.

Sửa xong thì chạy lại `parse --only ... --show` tới khi ổn. Không cần crawl lại, vì HTML đã nằm sẵn trong `data/raw/html/`.

## 3. Crawl toàn bộ (D01)

```powershell
python -m src.data.crawl
```

- Chỉ tải thủ tục chưa có file. Bị đứt giữa chừng thì chạy lại lệnh y vậy, nó chạy tiếp từ chỗ dở.
- Nghỉ ngẫu nhiên 3–6 giây giữa 2 trang. Đừng giảm xuống, cổng nhà nước chặn IP rất nhanh.
- Trang nào không thấy nhãn "Trình tự thực hiện" thì bị cất vào `data/raw/html/_failed/` để m mở ra xem (thường là trang lỗi, trang chờ, captcha).
- `--force` để tải lại: bản cũ được chuyển sang `_old/` chứ không bị ghi đè, manifest thêm một dòng sha256 mới.

**Nếu bị chặn / timeout liên tục:** thử `--headed --delay 8 15`. Vẫn không được thì lưu tay: mở từng trang, Ctrl+S, chọn "Webpage, Complete" hoặc "HTML only", lưu thành `data/raw/html/<doc_id>.html`, rồi:

```powershell
python -m src.data.crawl --register-manual    # tính sha256 và ghi vào raw_manifest.csv
```

Vài chục thủ tục lưu tay mất tầm 30 phút. Parser xử lý file lưu tay giống y file crawl.

**Kiểm tra:** mở `raw_manifest.csv`, mọi dòng có `sha256`, `accessed_at`. Mở tay 5 file ngẫu nhiên xem đúng thủ tục không.

## 4. Trích xuất + làm sạch (D02)

```powershell
python -m src.data.parse
```

Ra 3 file:
- `data/interim/docs.jsonl`: mỗi dòng một thủ tục, các mục nằm trong `fields`.
- `results/data_quality/cleaning_log.csv`: rule làm sạch nào sửa bao nhiêu chỗ.
- `results/data_quality/parse_issues.csv`: thiếu mục bắt buộc, mã trên trang khác `doc_id`, trang không trích được gì. **Phải về 0 hoặc giải thích được từng dòng.**

Làm sạch chỉ gồm: Unicode NFC, xóa ký tự ẩn, gộp khoảng trắng, chuẩn gạch đầu dòng, bỏ dòng rác giao diện, bỏ dòng lặp liền nhau. **Không** lowercase, bỏ dấu hay bỏ stopword ở đây, vì mấy cái đó là lựa chọn của từng mô hình (BM25 có thể lowercase, PhoBERT thì không).

## 5. Chia đoạn (D03)

```powershell
python -m src.data.chunk
```

- Mỗi mục là 1 chunk. Mục dài hơn `max_tokens` trong `configs/chunking.yaml` (200 từ sau tách từ) thì cắt theo dòng/câu, chồng lấn 1 câu.
- 200 chứ không phải 256: PhoBERT giới hạn 256 **subword**, 1 từ thường ra hơn 1 subword, và lúc ghép cặp (câu hỏi, đoạn) cho cross-encoder thì câu hỏi cũng chiếm chỗ.
- `chunk_text` = `"<tên thủ tục> | <tên mục>: <nội dung>"`. Không có tiền tố thì đoạn "Ủy ban nhân dân cấp xã" của 20 thủ tục giống hệt nhau, mô hình không biết đoạn nào của thủ tục nào.
- Script tự kiểm tra: chunk_id không trùng, không chunk rỗng, thủ tục nào cũng có chunk, không chunk nào vượt ngưỡng. Không đạt thì thoát với mã lỗi 1.
- `chunks_meta.json` ghi sha256 của docs và chunks, phiên bản underthesea. Chạy lại mà sha256 đổi trong khi input không đổi nghĩa là pipeline không tái lập được: phải tìm nguyên nhân.

**Sau khi TV2 bắt đầu gán nhãn thì không đổi `chunking.yaml` nữa**, vì đổi là chunk_id đổi, nhãn mất hết.

## 6. Báo cáo + biểu đồ

```powershell
python -m src.data.eda
```

| File | Dùng để |
|---|---|
| `corpus_report.md` | Báo cáo tiền xử lý: tổng quan, bảng kiểm tra chất lượng, thống kê từng mục, chunk, cặp gần giống, 10 chunk mẫu |
| `figures/01_field_coverage.png` | % thủ tục có từng mục. Cột cam = mục bắt buộc bị thiếu |
| `figures/02_field_length.png` | Độ dài từng mục, phát hiện mục trích lỗi (quá ngắn/quá dài bất thường) |
| `figures/03_chunk_length.png` | Phân bố độ dài chunk so với ngưỡng |
| `figures/04_chunks_per_doc.png` | Thủ tục nào sinh nhiều chunk (thường là thủ tục phức tạp) |
| `figures/05_doc_similarity.png` | Heatmap cosine TF-IDF giữa các thủ tục |
| `figures/06_top_terms.png` | Từ phổ biến sau tách từ |
| `figures/07_cleaning.png` | Rule làm sạch đã tác động bao nhiêu, số ký tự trước/sau |
| `near_duplicate_docs.csv` | Cặp thủ tục giống nhau ≥ 0,8. Đưa TV2 để viết câu hỏi loại "tài liệu gần trùng" |
| `duplicate_chunk_texts.csv` | Nội dung đoạn y hệt nhau giữa các thủ tục |
| `issue_samples.csv` | Gom mọi vấn đề cần tra lại |

Đọc báo cáo xong thì viết mục 9 "Nhận xét của TV1" (vấn đề gặp, cách xử lý). Phần này bê thẳng vào báo cáo nhóm được.

## 7. Commit gì

| Commit | Không commit (để Drive chung, ghi link trong README) |
|---|---|
| `source_list.csv`, `raw_manifest.csv` | `data/raw/html/` (đã nằm trong .gitignore) |
| `docs.jsonl`, `chunks.jsonl`, `chunks_meta.json` | |
| `results/data_quality/` (báo cáo + hình) | |
| Mọi sửa đổi trong `src/data/`, `configs/` | |

Nhánh gợi ý: `feature/D01-crawl`, `feature/D02-parse-clean`, `feature/D03-chunking`.

## Chạy thử không cần mạng

`tests/fixtures/make_fake_pages.py` sinh 6 trang **giả** có bố cục giống Cổng DVC. `python -m pytest` dùng chúng để test parse và chunk. Báo cáo chạy trên dữ liệu giả tự in dòng cảnh báo ở đầu, đừng lẫn với báo cáo thật.

## Góc DE: mấy nguyên tắc trong pipeline này

- **Raw bất biến:** không bao giờ sửa file trong `data/raw/html`. Parse sai thì sửa parser rồi chạy lại, không sửa dữ liệu nguồn.
- **Lineage:** `raw_sha256` trong docs.jsonl → `docs_sha256`, `chunks_sha256` trong chunks_meta.json. Nhìn 1 chunk là truy được nó từ file HTML nào, tải lúc nào.
- **Idempotent:** chạy lại bước nào cũng ra cùng output. Crawl thì resume được.
- **Data quality có log:** rule làm sạch nào cũng được đếm, check nào cũng có trạng thái Đạt/Chưa đạt. Đây đúng là thứ người ta hỏi khi phỏng vấn DE.
- **Config tách khỏi code:** ngưỡng chunk, tool tách từ nằm trong `configs/`, đổi không cần sửa code.
