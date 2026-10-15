# Kết quả baseline TF-IDF và BM25

Sinh tự động bởi `python -m src.retrieval.evaluate`. Tham số và ngưỡng từ chối chọn trên validation; test chỉ chạy với tham số đã chốt.

Số câu: train 64, validation 32, test 64. R@k, MRR, NDCG tính trên câu có nhãn; từ chối đúng tính trên out_of_scope + unsupported, từ chối nhầm tính trên câu hợp lệ.

Môi trường: scikit-learn 1.9.1, underthesea 9.5.0, chunks_sha256 8b646830eb64, qrels_sha256 4a587a27e0ad, dataset v1 (draft).

## validation

| Mô hình | Token | Tham số | R@1 | R@3 | R@5 | R@10 | MRR | NDCG@10 | Ngưỡng | Từ chối đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TFIDF | âm tiết | `{"ngram_range": [1, 1], "sublinear_tf": true}` | 0.096 | 0.281 | 0.364 | 0.494 | 0.320 | 0.310 | 0.173 | 0.40 | 0.07 |
| BM25 | âm tiết | `{"k1": 1.5, "b": 0.9}` | 0.086 | 0.210 | 0.333 | 0.525 | 0.281 | 0.310 | 6.844 | 0.20 | 0.04 |
| TFIDF | từ | `{"ngram_range": [1, 1], "sublinear_tf": true}` | 0.105 | 0.216 | 0.284 | 0.395 | 0.237 | 0.263 | 0.000 | 0.00 | 0.00 |
| BM25 | từ | `{"k1": 1.8, "b": 0.9}` | 0.049 | 0.228 | 0.284 | 0.377 | 0.210 | 0.246 | 0.000 | 0.00 | 0.00 |

Ngưỡng 0 = trên validation không có ngưỡng nào từ chối được câu ngoài phạm vi mà giữ từ chối nhầm trong giới hạn: điểm top-1 của câu không trả lời được không thấp hơn câu hợp lệ.

Theo type (validation, MRR):

| Mô hình | Token | confusable | direct | multi_intent | paraphrase | underspecified |
|---|---|---|---|---|---|---|
| TFIDF | âm tiết | 0.567 (n=5) | 0.314 (n=7) | 0.417 (n=2) | 0.278 (n=10) | 0.000 (n=3) |
| BM25 | âm tiết | 0.326 (n=5) | 0.455 (n=7) | 0.375 (n=2) | 0.188 (n=10) | 0.048 (n=3) |
| TFIDF | từ | 0.100 (n=5) | 0.462 (n=7) | 0.500 (n=2) | 0.167 (n=10) | 0.000 (n=3) |
| BM25 | từ | 0.100 (n=5) | 0.385 (n=7) | 0.250 (n=2) | 0.199 (n=10) | 0.000 (n=3) |

## test

| Mô hình | Token | Tham số | R@1 | R@3 | R@5 | R@10 | MRR | NDCG@10 | Ngưỡng | Từ chối đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TFIDF | âm tiết | `{"ngram_range": [1, 1], "sublinear_tf": true}` | 0.185 | 0.303 | 0.348 | 0.463 | 0.413 | 0.374 | 0.173 | 0.31 | 0.10 |
| BM25 | âm tiết | `{"k1": 1.5, "b": 0.9}` | 0.159 | 0.301 | 0.365 | 0.474 | 0.389 | 0.364 | 6.844 | 0.08 | 0.08 |
| TFIDF | từ | `{"ngram_range": [1, 1], "sublinear_tf": true}` | 0.131 | 0.286 | 0.315 | 0.392 | 0.332 | 0.308 | 0.000 | 0.00 | 0.00 |
| BM25 | từ | `{"k1": 1.8, "b": 0.9}` | 0.121 | 0.278 | 0.326 | 0.385 | 0.322 | 0.304 | 0.000 | 0.00 | 0.00 |

Ngưỡng 0 = trên validation không có ngưỡng nào từ chối được câu ngoài phạm vi mà giữ từ chối nhầm trong giới hạn: điểm top-1 của câu không trả lời được không thấp hơn câu hợp lệ.

Theo type (test, MRR):

| Mô hình | Token | confusable | direct | multi_intent | paraphrase | underspecified |
|---|---|---|---|---|---|---|
| TFIDF | âm tiết | 0.283 (n=11) | 0.603 (n=13) | 0.583 (n=7) | 0.316 (n=15) | 0.262 (n=5) |
| BM25 | âm tiết | 0.248 (n=11) | 0.466 (n=13) | 0.600 (n=7) | 0.344 (n=15) | 0.340 (n=5) |
| TFIDF | từ | 0.176 (n=11) | 0.455 (n=13) | 0.571 (n=7) | 0.288 (n=15) | 0.153 (n=5) |
| BM25 | từ | 0.187 (n=11) | 0.378 (n=13) | 0.548 (n=7) | 0.277 (n=15) | 0.292 (n=5) |
