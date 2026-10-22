# Kết quả mô hình truy hồi cải tiến (TV3)

Sinh tự động bởi `python -m src.retrieval.evaluate_models`. Model và tham số chọn trên validation (theo NDCG@10, hòa thì MRR); test chỉ chạy với bộ đã chốt trong `configs/retrieval_selected.yaml`.

Số câu: train 91, validation 41, test 88. R@k, MRR, NDCG tính trên câu có nhãn; từ chối đúng tính trên out_of_scope + unsupported, từ chối nhầm trên câu hợp lệ (ngưỡng trên điểm top-1, chọn trên validation như baseline).

Pipeline `retrieve()` dùng: **rerank**: Rerank itdainb/PhoRanker trên top-20 hybrid + tối đa 10 chunk BM25 (blend 0.4).

Môi trường: torch 2.14.1+cpu, transformers 5.19.0, sentence_transformers 6.1.0, underthesea 9.5.0, chunks_sha256 8b646830eb64, qrels_sha256 4a587a27e0ad, dataset v1 (draft), seed 42.

## validation

| Bước | Mô hình | R@1 | R@3 | R@5 | R@10 | R@20 | MRR | NDCG@10 | Ngưỡng | Từ chối đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|---|---|---|---|
| bm25_raw | BM25 âm tiết baseline TV1 (câu không dấu vẫn tìm trên chỉ mục có dấu) | 0.100 | 0.220 | 0.336 | 0.551 | 0.598 | 0.351 | 0.350 | 6.844 | 0.20 | 0.03 |
| bm25 | BM25 âm tiết (k1 1.5, b 0.9) | 0.100 | 0.289 | 0.387 | 0.594 | 0.658 | 0.376 | 0.387 | 6.940 | 0.20 | 0.00 |
| dense | SBERT bkai-foundation-models/vietnamese-bi-encoder | 0.212 | 0.349 | 0.507 | 0.591 | 0.688 | 0.507 | 0.472 | 0.210 | 0.20 | 0.06 |
| hybrid | Hybrid BM25 + SBERT (minmax, alpha 0.8) | 0.244 | 0.395 | 0.524 | 0.643 | 0.734 | 0.557 | 0.526 | 0.853 | 0.20 | 0.03 |
| rerank | Rerank itdainb/PhoRanker trên top-20 hybrid + tối đa 10 chunk BM25 (blend 0.4) | 0.258 | 0.412 | 0.514 | 0.656 | 0.765 | 0.621 | 0.561 | 0.869 | 0.40 | 0.06 |

Theo type (validation, MRR):

| Bước | confusable | direct | multi_intent | paraphrase | underspecified |
|---|---|---|---|---|---|
| bm25_raw | 0.518 (n=7) | 0.528 (n=11) | 0.375 (n=2) | 0.177 (n=13) | 0.048 (n=3) |
| bm25 | 0.543 (n=7) | 0.532 (n=11) | 0.375 (n=2) | 0.233 (n=13) | 0.037 (n=3) |
| dense | 0.341 (n=7) | 0.909 (n=11) | 0.600 (n=2) | 0.336 (n=13) | 0.108 (n=3) |
| hybrid | 0.304 (n=7) | 0.909 (n=11) | 0.625 (n=2) | 0.494 (n=13) | 0.089 (n=3) |
| rerank | 0.414 (n=7) | 0.871 (n=11) | 0.750 (n=2) | 0.557 (n=13) | 0.378 (n=3) |

## Lưới trên validation

Xem `grid_validation.csv`. Model tải lỗi:

- không có

## Câu hỏi tương tự

Kho: train + validation, bỏ out_of_scope / unsupported. min_score chốt: 0.5. Đúng = câu gợi ý top-1 có chung ít nhất 1 chunk liên quan với câu hỏi. Validation bỏ nhóm của chính câu hỏi.

| split | min_score | Có gợi ý | Đúng (P@1) | F1 | Hiện gợi ý cho câu không trả lời được |
|---|---|---|---|---|---|
| validation | 0.5 | 0.81 | 0.34 | 0.48 | 0.40 |
| validation | 0.6 | 0.39 | 0.43 | 0.41 | 0.20 |
| validation | 0.7 | 0.19 | 0.71 | 0.31 | 0.00 |
| validation | 0.8 | 0.06 | 1.00 | 0.11 | 0.00 |
| validation | 0.9 | 0.00 | 0.00 | 0.00 | 0.00 |
