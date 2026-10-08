# data/

Dữ liệu đi một chiều: `raw → interim → processed`. Thư mục sau luôn sinh lại được từ thư mục trước bằng code trong `src/data/`, nên **không sửa tay** file trong `interim/` và `processed/`.

| Thư mục / file | Nội dung | Ai tạo | Commit? |
|---|---|---|---|
| `raw/` | File luật gốc tải từ vbpl.vn (`.doc`, `.PDF`), **bất biến** | TV1, tải tay | Có (file nhỏ) |
| `raw/source_list.csv` | Danh sách văn bản đã tải: số hiệu, tên, url, ngày tải | TV1, điền tay | Có |
| `interim/` | Bản `.docx` đọc được bằng code | TV1 | Có |
| `processed/chunks.jsonl` | 1 dòng = 1 đoạn để lập chỉ mục (1 Điều, hoặc 1 Khoản nếu Điều dài) | Script tách luật (đang làm trong notebook) | Có |
| `labels/questions.csv` | Câu hỏi: `question_id, question_group_id, question, type, answer_text, source, annotator` | Cả nhóm viết, TV2 quản | Có |
| `labels/qrels.csv` | Nhãn liên quan: `question_id, chunk_id, relevance` (2 = trả lời trực tiếp, 1 = liên quan một phần) | Gán nhãn chéo, TV2 quản | Có |
| `splits/` | `question_group_id` của train / validation / test | TV2 | Có |

## Schema `processed/chunks.jsonl`

Chốt khi chuyển notebook tách luật thành script. Tối thiểu cần: `chunk_id` (ổn định, qrels trỏ vào đây), `text` (đưa vào mô hình), `display_text` (trích dẫn trên web), nguồn (số hiệu văn bản, Điều, Khoản).

## Quy tắc

- Không sửa `raw/`. Tải bản mới thì lưu thành file mới và ghi vào `source_list.csv`.
- Đổi cách chia đoạn sau khi đã gán nhãn là phải làm lại qrels. Hỏi TV1 và TV2 trước.
- Không ai mở tập test để chọn tham số hay ngưỡng từ chối.
