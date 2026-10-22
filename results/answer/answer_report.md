# Đánh giá câu trả lời (Quân, M6)

Sinh tự động bởi `python -m src.answer.evaluate_answer` lúc 2026-10-19T10:20:38. Mọi tham số chọn trên **validation** (32 câu: confusable 5, direct 7, multi_intent 2, out_of_scope 2, paraphrase 10, underspecified 3, unsupported 3). Test chưa chạy trong file này trừ khi có mục *test* ở cuối.

Pipeline `answer()` dùng: **rerank** (theo `configs/retrieval_selected.yaml` của TV3). Kiểm tra căn cứ con số (chọn theo từng pipeline): rerank **bật**, hybrid **bật**, dense **bật**, bm25 **tắt**.

## 1. Ngưỡng từ chối τ và chất lượng câu trả lời (validation)

Từ chối khi điểm top-1 < τ (và, nếu bật, khi câu hỏi đòi con số mà 3 đoạn đầu không có con số đó). Đúng nguồn = đoạn được trích nằm trong qrels; *chặt* = relevance 2. F1 tính theo âm tiết so với `answer_text`, chỉ trên câu hợp lệ được trả lời.

| Pipeline | Kiểm tra căn cứ | τ | Trả lời | Đúng nguồn | Đúng nguồn (chặt) | F1 trích dòng | F1 trích cả đoạn | Từ chối đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|---|---|
| rerank | không | 0.709 | 0.96 | 0.46 | 0.42 | 0.336 | 0.305 | 0.60 | 0.04 |
| rerank | có | 0.709 | 0.96 | 0.46 | 0.42 | 0.336 | 0.305 | 0.80 | 0.04 |
| hybrid | không | 0.000 | 1.00 | 0.37 | 0.37 | 0.339 | 0.295 | 0.40 | 0.00 |
| hybrid | có | 0.000 | 0.96 | 0.38 | 0.38 | 0.344 | 0.299 | 0.60 | 0.04 |
| dense | không | 0.000 | 1.00 | 0.30 | 0.30 | 0.304 | 0.272 | 0.40 | 0.00 |
| dense | có | 0.000 | 0.96 | 0.31 | 0.31 | 0.308 | 0.274 | 0.60 | 0.04 |
| bm25 | không | 0.000 | 1.00 | 0.15 | 0.15 | 0.271 | 0.235 | 0.40 | 0.00 |
| bm25 | có | 0.000 | 0.89 | 0.17 | 0.17 | 0.272 | 0.236 | 0.40 | 0.11 |

Validation chỉ có 5 câu cần từ chối, nên tỉ lệ từ chối đúng nhảy theo bước lớn; đọc kèm `threshold_grid.csv`.

## 2. Câu nhiều ý: tách và không tách

Câu `multi_intent` có nhãn của train + validation, truy hồi trực tiếp bằng **bm25**. Tách: mỗi ý truy hồi riêng, ghép kết quả xen kẽ (ý 1 hạng 1, ý 2 hạng 1, ...). Hai cột cuối đo phần câu trả lời: không tách thì chỉ trích 1 đoạn, tách thì trích 1 đoạn cho mỗi ý.

| Cách làm | n | R@5 | R@10 | NDCG@5 | Số đoạn đúng được trích | Phủ đoạn rel 2 trong câu trả lời |
|---|---|---|---|---|---|---|
| không tách | 9 | 0.570 | 0.733 | 0.556 | 0.78 | 0.259 |
| tách ý | 9 | 0.644 | 0.678 | 0.559 | 0.78 | 0.259 |

Tỉ lệ câu multi_intent được tách: 0.78. Tỉ lệ câu một ý bị tách nhầm: 0.00.

## 3. Câu thiếu thông tin

`is_underspecified`: không nhắc việc hộ tịch nào và ≤ 5 âm tiết nội dung. Web vẫn trả lời nhưng hiện gợi ý chọn việc cụ thể. Train + validation:

Precision 0.60, recall 0.27 (đoán 5 câu, nhãn 11 câu).

## Ghi chú

- Faithfulness: câu trả lời chỉ gồm khung mẫu + trích nguyên văn `display_text`, không sinh chữ mới, nên không thể có nội dung ngoài nguồn; lỗi còn lại là chọn sai đoạn, đo bằng cột *Đúng nguồn*.
- F1 so với `answer_text` thấp là bình thường: `answer_text` là câu tóm tắt ngắn do người viết, còn câu trả lời là điều luật nguyên văn dài hơn nhiều. Chỉ số này dùng để so *trích dòng* với *trích cả đoạn*.
- Chấm tay faithfulness và answer relevance (khoảng 50 câu, 2 người) theo phân công của TV2: dùng `validation_answers.csv` hoặc `test_answers.csv`.
