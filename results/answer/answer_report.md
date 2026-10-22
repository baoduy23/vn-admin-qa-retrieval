# Đánh giá câu trả lời (Quân, M6)

Sinh tự động bởi `python -m src.answer.evaluate_answer` lúc 2026-10-23T00:17:51. Mọi tham số chọn trên **validation** (41 câu: confusable 7, direct 11, multi_intent 2, out_of_scope 2, paraphrase 13, underspecified 3, unsupported 3). Test chưa chạy trong file này trừ khi có mục *test* ở cuối.

Pipeline `answer()` dùng: **rerank** (theo `configs/retrieval_selected.yaml` của TV3). Kiểm tra căn cứ con số (chọn theo từng pipeline): rerank **bật**, hybrid **bật**, dense **bật**, bm25 **bật**.

## 1. Ngưỡng từ chối τ và chất lượng câu trả lời (validation)

Từ chối khi điểm top-1 < τ (và, nếu bật, khi câu hỏi đòi con số mà 3 đoạn đầu không có con số đó). Đúng nguồn = đoạn được trích nằm trong qrels; *chặt* = relevance 2. F1 tính theo âm tiết so với `answer_text`, chỉ trên câu hợp lệ được trả lời.

| Pipeline | Kiểm tra căn cứ | τ | Trả lời | Đúng nguồn | Đúng nguồn (chặt) | F1 trích dòng | F1 trích cả đoạn | Từ chối đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|---|---|
| rerank | không | 0.869 | 0.94 | 0.53 | 0.44 | 0.368 | 0.350 | 0.60 | 0.06 |
| rerank | có | 0.869 | 0.94 | 0.53 | 0.44 | 0.368 | 0.350 | 0.80 | 0.06 |
| hybrid | không | 0.000 | 1.00 | 0.42 | 0.36 | 0.357 | 0.330 | 0.40 | 0.00 |
| hybrid | có | 0.000 | 0.97 | 0.43 | 0.37 | 0.362 | 0.334 | 0.60 | 0.03 |
| dense | không | 0.000 | 1.00 | 0.39 | 0.31 | 0.324 | 0.306 | 0.40 | 0.00 |
| dense | có | 0.000 | 0.97 | 0.40 | 0.31 | 0.327 | 0.309 | 0.60 | 0.03 |
| bm25 | không | 0.000 | 1.00 | 0.22 | 0.17 | 0.298 | 0.273 | 0.40 | 0.00 |
| bm25 | có | 0.000 | 0.92 | 0.24 | 0.18 | 0.301 | 0.277 | 0.40 | 0.08 |

Validation chỉ có 5 câu cần từ chối, nên tỉ lệ từ chối đúng nhảy theo bước lớn; đọc kèm `threshold_grid.csv`.

## 2. Câu nhiều ý: tách và không tách

Câu `multi_intent` có nhãn của train + validation, truy hồi trực tiếp bằng **bm25**. Tách: mỗi ý truy hồi riêng, ghép kết quả xen kẽ (ý 1 hạng 1, ý 2 hạng 1, ...). Hai cột cuối đo phần câu trả lời: không tách thì chỉ trích 1 đoạn, tách thì trích 1 đoạn cho mỗi ý.

| Cách làm | n | R@5 | R@10 | NDCG@5 | Số đoạn đúng được trích | Phủ đoạn rel 2 trong câu trả lời |
|---|---|---|---|---|---|---|
| không tách | 12 | 0.428 | 0.625 | 0.417 | 0.58 | 0.194 |
| tách ý | 12 | 0.572 | 0.658 | 0.523 | 0.83 | 0.278 |

Tỉ lệ câu multi_intent được tách: 0.83. Tỉ lệ câu một ý bị tách nhầm: 0.03.

Câu một ý bị tách nhầm:

- Bà nội tôi sinh năm 1948, cả đời chưa có giấy khai sinh, chỉ có căn cước với mấy giấy tờ đất đứng tên, giờ đi làm khai sinh cần gì?
- Chồng tôi quốc tịch Úc, mất ở Đà Nẵng nơi hai vợ chồng đang sống, giờ làm khai tử cho anh ấy ở đâu và nộp gì?
- Nếu tôi chậm đi đăng ký kết hôn thì có bị xử phạt hành chính không và mức phạt cụ thể là bao nhiêu tiền?
- Cho tôi hỏi làm lại cái giấy này thì hết bao nhiêu ngày và nộp ở đâu?

## 3. Câu thiếu thông tin

`is_underspecified`: không nhắc việc hộ tịch nào và ≤ 5 âm tiết nội dung. Web vẫn trả lời nhưng hiện gợi ý chọn việc cụ thể. Train + validation:

Precision 0.67, recall 0.29 (đoán 6 câu, nhãn 14 câu).

## Ghi chú

- Faithfulness: câu trả lời chỉ gồm khung mẫu + trích nguyên văn `display_text`, không sinh chữ mới, nên không thể có nội dung ngoài nguồn; lỗi còn lại là chọn sai đoạn, đo bằng cột *Đúng nguồn*.
- F1 so với `answer_text` thấp là bình thường: `answer_text` là câu tóm tắt ngắn do người viết, còn câu trả lời là điều luật nguyên văn dài hơn nhiều. Chỉ số này dùng để so *trích dòng* với *trích cả đoạn*.
- Chấm tay faithfulness và answer relevance (khoảng 50 câu, 2 người) theo phân công của TV2: dùng `validation_answers.csv` hoặc `test_answers.csv`.
