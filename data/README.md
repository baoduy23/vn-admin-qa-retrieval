# data/

Dữ liệu đi một chiều: `raw → interim → processed`. Thư mục sau luôn sinh lại được từ thư mục trước bằng code trong `src/data/`, nên **không sửa tay** file trong `interim/` và `processed/`.

| Thư mục / file | Nội dung | Ai tạo | Commit? |
|---|---|---|---|
| `raw/source_list.csv` | Danh sách thủ tục cần lấy: `doc_id` (mã thủ tục), `title`, `url`, `issuing_level`, `in_scope`... | TV1, điền tay | Có |
| `raw/html/<doc_id>.html` | Trang gốc đã tải, **bất biến** | `src.data.crawl` | Không (để Drive chung) |
| `raw/raw_manifest.csv` | Mỗi lần tải 1 dòng: url, ngày tải, sha256 | `src.data.crawl` | Có |
| `interim/docs.jsonl` | 1 dòng = 1 thủ tục, đã làm sạch, tách theo mục (`fields.trinh_tu`, `fields.thanh_phan_ho_so`...) | `src.data.parse` | Có |
| `processed/chunks.jsonl` | 1 dòng = 1 đoạn để lập chỉ mục (xem schema bên dưới) | `src.data.chunk` | Có |
| `processed/chunks_meta.json` | Cấu hình + hash của lần chia đoạn | `src.data.chunk` | Có |
| `labels/questions.csv` | Câu hỏi: `question_id, question_group_id, question, type, answer_text, source, annotator` | Cả nhóm viết, TV2 quản | Có |
| `labels/qrels.csv` | Nhãn liên quan: `question_id, chunk_id, relevance` (2 = trả lời trực tiếp, 1 = liên quan một phần) | Gán nhãn chéo, TV2 quản | Có |
| `splits/` | `question_group_id` của train / validation / test | TV2 | Có |

## Schema `processed/chunks.jsonl`

| Trường | Dùng cho |
|---|---|
| `chunk_id` | Khoá chính, dạng `<doc_id>__<field>__<i>`. qrels trỏ vào đây, **đừng đổi format** |
| `doc_id`, `title`, `field`, `field_name` | Biết đoạn thuộc thủ tục nào, mục nào |
| `chunk_text` | `"<Tên thủ tục> \| <Tên mục>: <nội dung>"`, đưa vào mô hình (TF-IDF, BM25 mức âm tiết, SBERT) |
| `text_seg` | `chunk_text` đã tách từ (từ ghép nối bằng `_`), cho BM25 mức từ và PhoBERT |
| `display_text` | Nội dung nguyên văn không tiền tố, để **trích dẫn trên web** |
| `url`, `accessed_at` | Nguồn và ngày lấy, hiện kèm câu trả lời |
| `n_tokens`, `part`, `n_parts` | Thống kê, ghép lại các đoạn bị cắt |

## Quy tắc

- Không sửa `raw/`. Muốn tải lại thì `python -m src.data.crawl --force`, bản cũ được giữ trong `_old/`.
- Đổi cách chia đoạn sau khi đã gán nhãn là phải làm lại qrels. Hỏi TV1 và TV2 trước.
- Không ai mở tập test để chọn tham số hay ngưỡng từ chối.
