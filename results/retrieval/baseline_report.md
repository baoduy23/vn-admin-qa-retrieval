# Kết quả baseline TF-IDF và BM25

Sinh tự động bởi `python -m src.retrieval.evaluate`. Tham số và ngưỡng từ chối chọn trên validation; test chỉ chạy với tham số đã chốt.

Số câu: train 56, validation 28, test 56. R@k, MRR, NDCG tính trên câu có nhãn; từ chối đúng tính trên out_of_scope + unsupported, từ chối nhầm tính trên câu hợp lệ.

Môi trường: scikit-learn 1.9.1, underthesea 9.5.0, chunks_sha256 8b646830eb64, qrels_sha256 661560e6459c, dataset v1 (draft).

## validation

| Mô hình | Token | Tham số | R@1 | R@3 | R@5 | R@10 | MRR | NDCG@10 | Ngưỡng | Từ chối đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TFIDF | âm tiết | `{"ngram_range": [1, 1], "sublinear_tf": true}` | 0.147 | 0.323 | 0.373 | 0.443 | 0.374 | 0.345 | 0.000 | 0.00 | 0.00 |
| BM25 | âm tiết | `{"k1": 1.5, "b": 0.9}` | 0.197 | 0.300 | 0.343 | 0.547 | 0.450 | 0.410 | 0.000 | 0.00 | 0.00 |
| TFIDF | từ | `{"ngram_range": [1, 2], "sublinear_tf": true}` | 0.127 | 0.290 | 0.350 | 0.423 | 0.343 | 0.324 | 0.000 | 0.00 | 0.00 |
| BM25 | từ | `{"k1": 1.5, "b": 0.6}` | 0.157 | 0.200 | 0.270 | 0.490 | 0.362 | 0.350 | 0.000 | 0.00 | 0.00 |

Ngưỡng 0 = trên validation không có ngưỡng nào từ chối được câu ngoài phạm vi mà giữ từ chối nhầm trong giới hạn: điểm top-1 của câu không trả lời được không thấp hơn câu hợp lệ.

Theo type (validation, MRR):

| Mô hình | Token | confusable | direct | multi_intent | paraphrase | underspecified |
|---|---|---|---|---|---|---|
| TFIDF | âm tiết | 0.458 (n=4) | 0.405 (n=7) | 0.667 (n=2) | 0.344 (n=8) | 0.150 (n=4) |
| BM25 | âm tiết | 0.569 (n=4) | 0.506 (n=7) | 0.625 (n=2) | 0.438 (n=8) | 0.167 (n=4) |
| TFIDF | từ | 0.375 (n=4) | 0.338 (n=7) | 0.500 (n=2) | 0.421 (n=8) | 0.083 (n=4) |
| BM25 | từ | 0.300 (n=4) | 0.425 (n=7) | 0.500 (n=2) | 0.447 (n=8) | 0.077 (n=4) |

## test

| Mô hình | Token | Tham số | R@1 | R@3 | R@5 | R@10 | MRR | NDCG@10 | Ngưỡng | Từ chối đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TFIDF | âm tiết | `{"ngram_range": [1, 1], "sublinear_tf": true}` | 0.237 | 0.364 | 0.438 | 0.563 | 0.492 | 0.468 | 0.000 | 0.00 | 0.00 |
| BM25 | âm tiết | `{"k1": 1.5, "b": 0.9}` | 0.194 | 0.373 | 0.480 | 0.554 | 0.481 | 0.447 | 0.000 | 0.00 | 0.00 |
| TFIDF | từ | `{"ngram_range": [1, 2], "sublinear_tf": true}` | 0.196 | 0.301 | 0.375 | 0.466 | 0.395 | 0.383 | 0.000 | 0.00 | 0.00 |
| BM25 | từ | `{"k1": 1.5, "b": 0.6}` | 0.188 | 0.337 | 0.409 | 0.467 | 0.396 | 0.386 | 0.000 | 0.00 | 0.00 |

Ngưỡng 0 = trên validation không có ngưỡng nào từ chối được câu ngoài phạm vi mà giữ từ chối nhầm trong giới hạn: điểm top-1 của câu không trả lời được không thấp hơn câu hợp lệ.

Theo type (test, MRR):

| Mô hình | Token | confusable | direct | multi_intent | paraphrase | underspecified |
|---|---|---|---|---|---|---|
| TFIDF | âm tiết | 0.207 (n=9) | 0.724 (n=15) | 0.679 (n=7) | 0.335 (n=12) | 0.381 (n=3) |
| BM25 | âm tiết | 0.220 (n=9) | 0.650 (n=15) | 0.714 (n=7) | 0.326 (n=12) | 0.500 (n=3) |
| TFIDF | từ | 0.083 (n=9) | 0.590 (n=15) | 0.691 (n=7) | 0.283 (n=12) | 0.111 (n=3) |
| BM25 | từ | 0.115 (n=9) | 0.583 (n=15) | 0.714 (n=7) | 0.260 (n=12) | 0.104 (n=3) |
