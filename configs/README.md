# configs/

Mọi tham số nằm ở đây, code chỉ đọc vào. Đổi tham số thì ghi lý do trong PR.

| File | Dùng ở | Nội dung chính |
|---|---|---|
| `preprocessing.yaml` | bước làm sạch + tách đoạn | Chuẩn hoá NFC, không lowercase, không bỏ stopword, công cụ tách từ (underthesea 9.5.0) |
| `chunking.yaml` | bước tách đoạn | `max_tokens: 200` (Điều dài hơn thì tách theo Khoản), format `chunk_id`, bỏ unit bị bãi bỏ, `include`: phần nào của từng văn bản được chunk |
| `retrieval_baseline.yaml` | baseline TF-IDF, BM25, hard negative | `k1`, `b`, n-gram, mức âm tiết / từ, các k khi đánh giá; `refusal.max_wrong_refusal` (giới hạn từ chối nhầm khi chọn ngưỡng); `hard_negatives` (top-k, số negative mỗi positive) |
| `answer.yaml` | `answer()` và web (Quân) | Chọn pipeline (`selected` = của TV3, `bm25` = bản nhẹ; biến môi trường `ANSWER_PIPELINE` ghi đè), số nguồn hiển thị, bật/tắt kiểm tra căn cứ con số, tách câu nhiều ý, ngưỡng câu thiếu thông tin |
| `answer_selected.yaml` | `answer()` (Quân) | **Sinh tự động** bởi `python -m src.answer.evaluate_answer`: ngưỡng từ chối τ và bật/tắt kiểm tra căn cứ cho từng pipeline, chọn trên validation. Không sửa tay |
| `split.yaml` | chia train/val/test | Chia theo `question_group_id`, phân tầng theo `type`, tỉ lệ 40/20/40, seed 42 |

Đổi `chunking.yaml` hoặc `preprocessing.yaml` sau khi đã gán nhãn thì `chunk_id` có thể đổi theo và qrels phải làm lại.
