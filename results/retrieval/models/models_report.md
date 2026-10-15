# Kết quả mô hình truy hồi cải tiến (TV3)

Sinh tự động bởi `python -m src.retrieval.evaluate_models`. Model và tham số chọn trên validation (theo NDCG@10, hòa thì MRR); test chỉ chạy với bộ đã chốt trong `configs/retrieval_selected.yaml`.

Số câu: train 64, validation 32, test 64. R@k, MRR, NDCG tính trên câu có nhãn; từ chối đúng tính trên out_of_scope + unsupported, từ chối nhầm trên câu hợp lệ (ngưỡng trên điểm top-1, chọn trên validation như baseline).

Pipeline `retrieve()` dùng: **rerank**: Rerank itdainb/PhoRanker trên top-20 hybrid (blend 0.4).

Môi trường: torch 2.14.1+cpu, transformers 5.19.0, sentence_transformers 6.1.0, underthesea 9.5.0, chunks_sha256 8b646830eb64, qrels_sha256 4a587a27e0ad, dataset v1 (draft), seed 42.

## validation

| Bước | Mô hình | R@1 | R@3 | R@5 | R@10 | R@20 | MRR | NDCG@10 | Ngưỡng | Từ chối đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|---|---|---|---|
| bm25_raw | BM25 âm tiết baseline TV1 (câu không dấu vẫn tìm trên chỉ mục có dấu) | 0.086 | 0.210 | 0.333 | 0.525 | 0.580 | 0.286 | 0.310 | 6.844 | 0.20 | 0.04 |
| bm25 | BM25 âm tiết (k1 1.5, b 0.9) | 0.086 | 0.302 | 0.401 | 0.562 | 0.648 | 0.319 | 0.350 | 6.940 | 0.20 | 0.00 |
| dense | SBERT bkai-foundation-models/vietnamese-bi-encoder | 0.216 | 0.340 | 0.500 | 0.583 | 0.697 | 0.424 | 0.450 | 0.220 | 0.20 | 0.07 |
| hybrid | Hybrid BM25 + SBERT (minmax, alpha 0.8) | 0.272 | 0.407 | 0.518 | 0.652 | 0.759 | 0.518 | 0.525 | 0.853 | 0.20 | 0.04 |
| rerank | Rerank itdainb/PhoRanker trên top-20 hybrid (blend 0.4) | 0.278 | 0.417 | 0.485 | 0.652 | 0.759 | 0.575 | 0.544 | 0.709 | 0.40 | 0.04 |

Theo type (validation, MRR):

| Bước | confusable | direct | multi_intent | paraphrase | underspecified |
|---|---|---|---|---|---|
| bm25_raw | 0.326 (n=5) | 0.455 (n=7) | 0.375 (n=2) | 0.201 (n=10) | 0.048 (n=3) |
| bm25 | 0.360 (n=5) | 0.455 (n=7) | 0.375 (n=2) | 0.276 (n=10) | 0.037 (n=3) |
| dense | 0.077 (n=5) | 1.000 (n=7) | 0.600 (n=2) | 0.253 (n=10) | 0.108 (n=3) |
| hybrid | 0.125 (n=5) | 1.000 (n=7) | 0.625 (n=2) | 0.484 (n=10) | 0.089 (n=3) |
| rerank | 0.168 (n=5) | 0.878 (n=7) | 0.750 (n=2) | 0.594 (n=10) | 0.367 (n=3) |

## test

| Bước | Mô hình | R@1 | R@3 | R@5 | R@10 | R@20 | MRR | NDCG@10 | Ngưỡng | Từ chối đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|---|---|---|---|
| bm25_raw | BM25 âm tiết baseline TV1 (câu không dấu vẫn tìm trên chỉ mục có dấu) | 0.159 | 0.301 | 0.365 | 0.474 | 0.551 | 0.394 | 0.364 | 6.844 | 0.08 | 0.08 |
| bm25 | BM25 âm tiết (k1 1.5, b 0.9) | 0.188 | 0.358 | 0.423 | 0.565 | 0.655 | 0.460 | 0.427 | 6.940 | 0.00 | 0.02 |
| dense | SBERT bkai-foundation-models/vietnamese-bi-encoder | 0.256 | 0.455 | 0.507 | 0.568 | 0.658 | 0.594 | 0.519 | 0.220 | 0.23 | 0.04 |
| hybrid | Hybrid BM25 + SBERT (minmax, alpha 0.8) | 0.285 | 0.452 | 0.545 | 0.642 | 0.742 | 0.625 | 0.562 | 0.853 | 0.15 | 0.04 |
| rerank | Rerank itdainb/PhoRanker trên top-20 hybrid (blend 0.4) | 0.301 | 0.496 | 0.588 | 0.666 | 0.742 | 0.672 | 0.595 | 0.709 | 0.23 | 0.10 |

Theo type (test, MRR):

| Bước | confusable | direct | multi_intent | paraphrase | underspecified |
|---|---|---|---|---|---|
| bm25_raw | 0.248 (n=11) | 0.470 (n=13) | 0.600 (n=7) | 0.352 (n=15) | 0.352 (n=5) |
| bm25 | 0.336 (n=11) | 0.470 (n=13) | 0.790 (n=7) | 0.418 (n=15) | 0.372 (n=5) |
| dense | 0.591 (n=11) | 0.736 (n=13) | 0.667 (n=7) | 0.491 (n=15) | 0.435 (n=5) |
| hybrid | 0.568 (n=11) | 0.735 (n=13) | 0.762 (n=7) | 0.566 (n=15) | 0.453 (n=5) |
| rerank | 0.558 (n=11) | 0.731 (n=13) | 0.806 (n=7) | 0.719 (n=15) | 0.445 (n=5) |

## Lưới trên validation

Xem `grid_validation.csv`. Model tải lỗi:

- không có

## Câu hỏi tương tự

Kho: train + validation, bỏ out_of_scope / unsupported. min_score chốt: 0.7. Đúng = câu gợi ý top-1 có chung ít nhất 1 chunk liên quan với câu hỏi. Validation bỏ nhóm của chính câu hỏi.

| split | min_score | Có gợi ý | Đúng (P@1) | F1 | Hiện gợi ý cho câu không trả lời được |
|---|---|---|---|---|---|
| validation | 0.5 | 0.70 | 0.47 | 0.57 | 0.40 |
| validation | 0.6 | 0.44 | 0.50 | 0.47 | 0.20 |
| validation | 0.7 | 0.26 | 0.71 | 0.38 | 0.00 |
| validation | 0.8 | 0.07 | 1.00 | 0.14 | 0.00 |
| validation | 0.9 | 0.00 | 0.00 | 0.00 | 0.00 |
| test | 0.7 | 0.08 | 0.25 | 0.12 | 0.00 |
