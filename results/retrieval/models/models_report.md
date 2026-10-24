# Kết quả mô hình truy hồi cải tiến (TV3)

Sinh tự động bởi `python -m src.retrieval.evaluate_models`. Model và tham số chọn trên validation (theo NDCG@10, hòa thì MRR, rồi từ chối đúng nhiều hơn); test chỉ chạy với bộ đã chốt trong `configs/retrieval_selected.yaml`.

Số câu: train 127, validation 57, test 116. R@k, MRR, NDCG tính trên câu có nhãn; từ chối đúng tính trên out_of_scope + unsupported, từ chối nhầm trên câu hợp lệ (ngưỡng trên điểm top-1, chọn trên validation như baseline).

Pipeline `retrieve()` dùng: **rerank**: Rerank itdainb/PhoRanker trên top-20 hybrid + tối đa 5 chunk BM25 (blend 0.0, điểm CE raw, khôi phục dấu).

Môi trường: torch 2.14.1+cpu, transformers 5.19.0, sentence_transformers 6.1.0, underthesea 9.5.0, chunks_sha256 8b646830eb64, qrels_sha256 4a587a27e0ad, dataset v1 (draft), seed 42.

## validation

| Bước | Mô hình | R@1 | R@3 | R@5 | R@10 | R@20 | MRR | NDCG@10 | Ngưỡng | Từ chối đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|---|---|---|---|
| bm25_raw | BM25 âm tiết baseline TV1 (câu không dấu vẫn tìm trên chỉ mục có dấu) | 0.163 | 0.285 | 0.417 | 0.580 | 0.615 | 0.406 | 0.416 | 6.844 | 0.11 | 0.04 |
| bm25 | BM25 âm tiết (k1 1.5, b 0.9) | 0.191 | 0.375 | 0.503 | 0.660 | 0.716 | 0.487 | 0.496 | 6.940 | 0.11 | 0.00 |
| dense | SBERT intfloat/multilingual-e5-base (khôi phục dấu) | 0.314 | 0.442 | 0.556 | 0.671 | 0.742 | 0.617 | 0.582 | 0.831 | 0.33 | 0.02 |
| hybrid | Hybrid BM25 + SBERT (minmax, alpha 0.9) | 0.306 | 0.460 | 0.562 | 0.696 | 0.749 | 0.615 | 0.596 | 0.946 | 0.44 | 0.04 |
| rerank | Rerank itdainb/PhoRanker trên top-20 hybrid + tối đa 5 chunk BM25 (blend 0.0, điểm CE raw, khôi phục dấu) | 0.359 | 0.491 | 0.592 | 0.738 | 0.787 | 0.734 | 0.668 | 0.051 | 1.00 | 0.02 |

Theo type (validation, MRR; co_dau / khong_dau = câu gõ có dấu / không dấu):

| Bước | confusable | direct | multi_intent | paraphrase | underspecified | co_dau | khong_dau |
|---|---|---|---|---|---|---|---|
| bm25_raw | 0.468 (n=9) | 0.543 (n=13) | 0.438 (n=4) | 0.312 (n=17) | 0.229 (n=5) | 0.531 (n=35) | 0.069 (n=13) |
| bm25 | 0.487 (n=9) | 0.546 (n=13) | 0.688 (n=4) | 0.413 (n=17) | 0.422 (n=5) | 0.531 (n=35) | 0.369 (n=13) |
| dense | 0.262 (n=9) | 0.842 (n=13) | 0.500 (n=4) | 0.577 (n=17) | 0.900 (n=5) | 0.633 (n=35) | 0.574 (n=13) |
| hybrid | 0.302 (n=9) | 0.844 (n=13) | 0.625 (n=4) | 0.549 (n=17) | 0.800 (n=5) | 0.614 (n=35) | 0.619 (n=13) |
| rerank | 0.429 (n=9) | 0.929 (n=13) | 0.625 (n=4) | 0.796 (n=17) | 0.656 (n=5) | 0.759 (n=35) | 0.668 (n=13) |

## test

| Bước | Mô hình | R@1 | R@3 | R@5 | R@10 | R@20 | MRR | NDCG@10 | Ngưỡng | Từ chối đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|---|---|---|---|
| bm25_raw | BM25 âm tiết baseline TV1 (câu không dấu vẫn tìm trên chỉ mục có dấu) | 0.162 | 0.314 | 0.371 | 0.497 | 0.596 | 0.506 | 0.432 | 6.844 | 0.04 | 0.07 |
| bm25 | BM25 âm tiết (k1 1.5, b 0.9) | 0.206 | 0.374 | 0.436 | 0.579 | 0.693 | 0.600 | 0.507 | 6.940 | 0.00 | 0.01 |
| dense | SBERT intfloat/multilingual-e5-base (khôi phục dấu) | 0.239 | 0.447 | 0.547 | 0.657 | 0.755 | 0.666 | 0.588 | 0.831 | 0.19 | 0.01 |
| hybrid | Hybrid BM25 + SBERT (minmax, alpha 0.9) | 0.261 | 0.454 | 0.553 | 0.677 | 0.767 | 0.704 | 0.620 | 0.946 | 0.19 | 0.03 |
| rerank | Rerank itdainb/PhoRanker trên top-20 hybrid + tối đa 5 chunk BM25 (blend 0.0, điểm CE raw, khôi phục dấu) | 0.316 | 0.516 | 0.604 | 0.687 | 0.773 | 0.796 | 0.691 | 0.051 | 0.78 | 0.09 |

Theo type (test, MRR; co_dau / khong_dau = câu gõ có dấu / không dấu):

| Bước | confusable | direct | multi_intent | paraphrase | underspecified | co_dau | khong_dau |
|---|---|---|---|---|---|---|---|
| bm25_raw | 0.384 (n=18) | 0.585 (n=19) | 0.625 (n=14) | 0.445 (n=26) | 0.555 (n=12) | 0.611 (n=65) | 0.220 (n=24) |
| bm25 | 0.469 (n=18) | 0.638 (n=19) | 0.759 (n=14) | 0.533 (n=26) | 0.697 (n=12) | 0.611 (n=65) | 0.570 (n=24) |
| dense | 0.564 (n=18) | 0.733 (n=19) | 0.812 (n=14) | 0.592 (n=26) | 0.704 (n=12) | 0.676 (n=65) | 0.641 (n=24) |
| hybrid | 0.621 (n=18) | 0.730 (n=19) | 0.863 (n=14) | 0.616 (n=26) | 0.794 (n=12) | 0.724 (n=65) | 0.649 (n=24) |
| rerank | 0.751 (n=18) | 0.807 (n=19) | 0.929 (n=14) | 0.772 (n=26) | 0.747 (n=12) | 0.783 (n=65) | 0.833 (n=24) |

## Công tắc cải tiến (validation)

restore_diacritics: câu gõ không dấu được khôi phục dấu trước khi vào bi-encoder / cross-encoder. ce_norm: điểm cross-encoder chuẩn hóa min-max trong từng câu (minmax) hay giữ xác suất model cho (raw). Mỗi dòng là bộ tốt nhất của tổ hợp đó; ngưỡng và từ chối tính trên điểm top-1 như bảng trên.

**dense** (intfloat/multilingual-e5-base):

| restore_diacritics | Tham số khác | NDCG@10 | MRR | R@20 | Ngưỡng | Từ chối đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|
| False | {} | 0.450 | 0.487 | 0.577 | 0.803 | 0.11 | 0.08 |
| True | {} | 0.582 | 0.617 | 0.742 | 0.831 | 0.33 | 0.02 |

**rerank** (itdainb/PhoRanker):

| restore_diacritics | ce_norm | Tham số khác | NDCG@10 | MRR | R@20 | Ngưỡng | Từ chối đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|---|
| False | raw | {"extra_bm25": 5, "blend": 0.4} | 0.624 | 0.697 | 0.764 | 0.401 | 0.56 | 0.08 |
| True | raw | {"extra_bm25": 5, "blend": 0.0} | 0.668 | 0.734 | 0.787 | 0.051 | 1.00 | 0.02 |

## Lưới trên validation

Xem `grid_validation.csv`. Model tải lỗi:

- không có

## Câu hỏi tương tự

Kho: train + validation, bỏ out_of_scope / unsupported. min_score chốt: 0.9. Đúng = câu gợi ý top-1 có chung ít nhất 1 chunk liên quan với câu hỏi. Validation bỏ nhóm của chính câu hỏi.

| split | min_score | Có gợi ý | Đúng (P@1) | F1 | Hiện gợi ý cho câu không trả lời được |
|---|---|---|---|---|---|
| validation | 0.5 | 1.00 | 0.29 | 0.45 | 1.00 |
| validation | 0.6 | 1.00 | 0.29 | 0.45 | 1.00 |
| validation | 0.7 | 1.00 | 0.29 | 0.45 | 1.00 |
| validation | 0.8 | 1.00 | 0.29 | 0.45 | 1.00 |
| validation | 0.9 | 0.71 | 0.38 | 0.50 | 0.56 |
| test | 0.9 | 0.79 | 0.21 | 0.34 | 0.33 |
