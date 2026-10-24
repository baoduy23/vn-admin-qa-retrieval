# Đánh giá câu trả lời (Quân, M6)

Sinh tự động bởi `python -m src.answer.evaluate_answer` lúc 2026-10-25T06:18:35. Mọi tham số chọn trên **validation** (57 câu: confusable 9, direct 13, multi_intent 4, out_of_scope 4, paraphrase 17, underspecified 5, unsupported 5). Test chưa chạy trong file này trừ khi có mục *test* ở cuối.

Pipeline `answer()` dùng: **rerank** (theo `configs/retrieval_selected.yaml` của TV3). Kiểm tra căn cứ con số (chọn theo từng pipeline): rerank **bật**, hybrid **bật**, dense **bật**, bm25 **tắt**.

## 1. Ngưỡng từ chối τ và chất lượng câu trả lời (validation)

Từ chối khi điểm top-1 < τ (và, nếu bật, khi câu hỏi đòi con số mà 3 đoạn đầu không có con số đó). Đúng nguồn = đoạn được trích nằm trong qrels; *chặt* = relevance 2. F1 tính theo âm tiết so với `answer_text`, chỉ trên câu hợp lệ được trả lời.

| Pipeline | Kiểm tra căn cứ | τ | Trả lời | Đúng nguồn | Đúng nguồn (chặt) | F1 trích dòng | F1 trích cả đoạn | Từ chối đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|---|---|
| rerank | không | 0.051 | 0.98 | 0.68 | 0.57 | 0.419 | 0.414 | 1.00 | 0.02 |
| rerank | có | 0.051 | 0.92 | 0.68 | 0.57 | 0.426 | 0.413 | 1.00 | 0.08 |
| hybrid | không | 0.946 | 0.96 | 0.52 | 0.43 | 0.395 | 0.375 | 0.44 | 0.04 |
| hybrid | có | 0.000 | 0.94 | 0.51 | 0.42 | 0.391 | 0.368 | 0.56 | 0.06 |
| dense | không | 0.821 | 0.98 | 0.51 | 0.40 | 0.378 | 0.364 | 0.44 | 0.02 |
| dense | có | 0.821 | 0.92 | 0.52 | 0.41 | 0.384 | 0.368 | 0.67 | 0.08 |
| bm25 | không | 0.000 | 1.00 | 0.35 | 0.29 | 0.341 | 0.335 | 0.33 | 0.00 |
| bm25 | có | 0.000 | 0.90 | 0.35 | 0.28 | 0.348 | 0.329 | 0.56 | 0.10 |

Validation chỉ có 9 câu cần từ chối, nên tỉ lệ từ chối đúng nhảy theo bước lớn; đọc kèm `threshold_grid.csv`.

## 2. Câu nhiều ý: tách và không tách

Câu `multi_intent` có nhãn của train + validation, truy hồi trực tiếp bằng **bm25**. Tách: mỗi ý truy hồi riêng, ghép kết quả xen kẽ (ý 1 hạng 1, ý 2 hạng 1, ...). Hai cột cuối đo phần câu trả lời: không tách thì chỉ trích 1 đoạn, tách thì trích 1 đoạn cho mỗi ý.

| Cách làm | n | R@5 | R@10 | NDCG@5 | Số đoạn đúng được trích | Phủ đoạn rel 2 trong câu trả lời |
|---|---|---|---|---|---|---|
| không tách | 20 | 0.448 | 0.621 | 0.479 | 0.70 | 0.258 |
| tách ý | 20 | 0.547 | 0.653 | 0.521 | 0.90 | 0.308 |

Tỉ lệ câu multi_intent được tách: 0.90. Tỉ lệ câu một ý bị tách nhầm: 0.06.

Câu một ý bị tách nhầm:

- Bà nội tôi sinh năm 1948, cả đời chưa có giấy khai sinh, chỉ có căn cước với mấy giấy tờ đất đứng tên, giờ đi làm khai sinh cần gì?
- Chồng tôi quốc tịch Úc, mất ở Đà Nẵng nơi hai vợ chồng đang sống, giờ làm khai tử cho anh ấy ở đâu và nộp gì?
- Nếu tôi chậm đi đăng ký kết hôn thì có bị xử phạt hành chính không và mức phạt cụ thể là bao nhiêu tiền?
- Cho tôi hỏi làm lại cái giấy này thì hết bao nhiêu ngày và nộp ở đâu?
- Giay khai sinh cu cua bo em truoc nam 2016 chi ghi moi nam sinh, gio ko co giay to nao ghi ngay thang sinh va cung ko nho de cam doan thi bo sung ngay thang sinh kieu gi?
- Khi đi xin cấp Giấy xác nhận độc thân thì Ủy ban xã cấp cho mấy bản và có xét điều kiện kết hôn không?
- Theo quy định pháp luật hiện hành thì những người có họ trong phạm vi mấy đời không được phép đăng ký kết hôn với nhau, con cô con cậu ruột đời thứ tư có đăng ký kết hôn được không?
- Họ hàng thân thích trong phạm vi mấy đời thì bị cấm kết hôn, cháu họ đời thứ tư có được phép đăng ký kết hôn với nhau không?
- Chi phí xét nghiệm ADN huyết thống cha con tại trung tâm giám định pháp y để làm chứng cứ đăng ký nhận cha, mẹ, con hiện nay hết bao nhiêu tiền và bao lâu có kết quả xét nghiệm?
- xet nghiem ADN de lam thu tuc nhan cha cho con ton bao nhieu tien va mat may ngay co ket qua giam dinh

## 3. Câu thiếu thông tin

`is_underspecified`: không nhắc việc hộ tịch nào và ≤ 5 âm tiết nội dung. Web vẫn trả lời nhưng hiện gợi ý chọn việc cụ thể. Train + validation:

Precision 0.67, recall 0.18 (đoán 6 câu, nhãn 22 câu).

## test (chạy 1 lần, τ đã chốt)

| Trả lời | Đúng nguồn | Đúng nguồn (chặt) | F1 trích dòng | Từ chối đúng | Từ chối nhầm |
|---|---|---|---|---|---|
| 0.90 | 0.72 | 0.60 | 0.441 | 0.85 | 0.10 |

## Ghi chú

- Faithfulness: câu trả lời chỉ gồm khung mẫu + trích nguyên văn `display_text`, không sinh chữ mới, nên không thể có nội dung ngoài nguồn; lỗi còn lại là chọn sai đoạn, đo bằng cột *Đúng nguồn*.
- F1 so với `answer_text` thấp là bình thường: `answer_text` là câu tóm tắt ngắn do người viết, còn câu trả lời là điều luật nguyên văn dài hơn nhiều. Chỉ số này dùng để so *trích dòng* với *trích cả đoạn*.
- Chấm tay faithfulness và answer relevance (khoảng 50 câu, 2 người) theo phân công của TV2: dùng `validation_answers.csv` hoặc `test_answers.csv`.
