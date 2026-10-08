# configs/

Mọi tham số nằm ở đây, code chỉ đọc vào. Đổi tham số thì ghi lý do trong PR.

| File | Dùng ở | Nội dung chính |
|---|---|---|
| `preprocessing.yaml` | bước làm sạch + tách đoạn | Chuẩn hoá NFC, không lowercase, không bỏ stopword, công cụ tách từ (underthesea) |
| `chunking.yaml` | bước tách đoạn | `max_tokens: 200` (Điều dài hơn thì tách theo Khoản), format `chunk_id`. Một số khoá vẫn theo hướng thủ tục cũ, sửa khi chốt script tách luật |
| `retrieval_baseline.yaml` | baseline TF-IDF, BM25 | `k1`, `b`, n-gram, mức âm tiết / từ, các k khi đánh giá |
| `split.yaml` | chia train/val/test | Chia theo `question_group_id`, phân tầng theo `type`, tỉ lệ 40/20/40, seed 42 |

Đổi `chunking.yaml` hoặc `preprocessing.yaml` sau khi đã gán nhãn thì `chunk_id` có thể đổi theo và qrels phải làm lại.
