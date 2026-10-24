# Kết quả baseline TF-IDF và BM25

Sinh tự động bởi `python -m src.retrieval.evaluate`. Tham số và ngưỡng từ chối chọn trên validation; test chỉ chạy với tham số đã chốt.

Số câu: train 127, validation 57, test 116. R@k, MRR, NDCG tính trên câu có nhãn; từ chối đúng tính trên out_of_scope + unsupported, từ chối nhầm tính trên câu hợp lệ.

Môi trường: scikit-learn 1.9.1, underthesea 9.5.0, chunks_sha256 8b646830eb64, qrels_sha256 4a587a27e0ad, dataset v1 (draft).

## validation

| Mô hình | Token | Tham số | R@1 | R@3 | R@5 | R@10 | MRR | NDCG@10 | Ngưỡng | Từ chối đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TFIDF | âm tiết | `{"ngram_range": [1, 2], "sublinear_tf": true}` | 0.188 | 0.292 | 0.401 | 0.533 | 0.393 | 0.400 | 0.095 | 0.22 | 0.08 |
| BM25 | âm tiết | `{"k1": 1.5, "b": 0.9}` | 0.163 | 0.285 | 0.417 | 0.580 | 0.403 | 0.416 | 6.844 | 0.11 | 0.04 |
| TFIDF | từ | `{"ngram_range": [1, 2], "sublinear_tf": true}` | 0.174 | 0.292 | 0.383 | 0.460 | 0.363 | 0.369 | 0.085 | 0.11 | 0.06 |
| BM25 | từ | `{"k1": 2.0, "b": 0.9}` | 0.153 | 0.313 | 0.393 | 0.470 | 0.367 | 0.373 | 5.063 | 0.11 | 0.06 |

Theo type (validation, MRR):

| Mô hình | Token | confusable | direct | multi_intent | paraphrase | underspecified |
|---|---|---|---|---|---|---|
| TFIDF | âm tiết | 0.432 (n=9) | 0.496 (n=13) | 0.500 (n=4) | 0.324 (n=17) | 0.200 (n=5) |
| BM25 | âm tiết | 0.468 (n=9) | 0.543 (n=13) | 0.438 (n=4) | 0.304 (n=17) | 0.229 (n=5) |
| TFIDF | từ | 0.407 (n=9) | 0.460 (n=13) | 0.500 (n=4) | 0.280 (n=17) | 0.200 (n=5) |
| BM25 | từ | 0.343 (n=9) | 0.515 (n=13) | 0.375 (n=4) | 0.313 (n=17) | 0.200 (n=5) |

## test

| Mô hình | Token | Tham số | R@1 | R@3 | R@5 | R@10 | MRR | NDCG@10 | Ngưỡng | Từ chối đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TFIDF | âm tiết | `{"ngram_range": [1, 2], "sublinear_tf": true}` | 0.138 | 0.326 | 0.385 | 0.505 | 0.464 | 0.428 | 0.095 | 0.15 | 0.10 |
| BM25 | âm tiết | `{"k1": 1.5, "b": 0.9}` | 0.162 | 0.314 | 0.371 | 0.497 | 0.499 | 0.432 | 6.844 | 0.04 | 0.07 |
| TFIDF | từ | `{"ngram_range": [1, 2], "sublinear_tf": true}` | 0.135 | 0.267 | 0.320 | 0.456 | 0.401 | 0.380 | 0.085 | 0.15 | 0.07 |
| BM25 | từ | `{"k1": 2.0, "b": 0.9}` | 0.145 | 0.272 | 0.342 | 0.444 | 0.445 | 0.388 | 5.063 | 0.15 | 0.07 |

Theo type (test, MRR):

| Mô hình | Token | confusable | direct | multi_intent | paraphrase | underspecified |
|---|---|---|---|---|---|---|
| TFIDF | âm tiết | 0.340 (n=18) | 0.639 (n=19) | 0.606 (n=14) | 0.389 (n=26) | 0.370 (n=12) |
| BM25 | âm tiết | 0.379 (n=18) | 0.582 (n=19) | 0.621 (n=14) | 0.434 (n=26) | 0.544 (n=12) |
| TFIDF | từ | 0.281 (n=18) | 0.597 (n=19) | 0.498 (n=14) | 0.358 (n=26) | 0.251 (n=12) |
| BM25 | từ | 0.318 (n=18) | 0.515 (n=19) | 0.603 (n=14) | 0.395 (n=26) | 0.450 (n=12) |
