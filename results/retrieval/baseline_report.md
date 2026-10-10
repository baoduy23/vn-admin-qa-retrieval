# Kết quả baseline TF-IDF và BM25

Sinh tự động bởi `python -m src.retrieval.evaluate`. Tham số và ngưỡng từ chối chọn trên validation; test chỉ chạy với tham số đã chốt.

Số câu: train 33, validation 16, test 31. R@k, MRR, NDCG tính trên câu có nhãn; từ chối đúng tính trên out_of_scope + unsupported, từ chối nhầm tính trên câu hợp lệ.

Môi trường: scikit-learn 1.9.1, underthesea 9.5.0, chunks_sha256 8b646830eb64, qrels_sha256 661560e6459c, dataset v1 (draft).

## validation

| Mô hình | Token | Tham số | R@1 | R@3 | R@5 | R@10 | MRR | NDCG@10 | Ngưỡng | Từ chối đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TFIDF | âm tiết | `{"ngram_range": [1, 1], "sublinear_tf": true}` | 0.268 | 0.351 | 0.375 | 0.506 | 0.547 | 0.449 | 0.000 | 0.00 | 0.00 |
| BM25 | âm tiết | `{"k1": 2.0, "b": 0.9}` | 0.119 | 0.309 | 0.399 | 0.488 | 0.372 | 0.388 | 0.000 | 0.00 | 0.00 |
| TFIDF | từ | `{"ngram_range": [1, 2], "sublinear_tf": true}` | 0.268 | 0.369 | 0.411 | 0.589 | 0.565 | 0.488 | 0.000 | 0.00 | 0.00 |
| BM25 | từ | `{"k1": 2.0, "b": 0.75}` | 0.119 | 0.351 | 0.458 | 0.476 | 0.383 | 0.386 | 0.000 | 0.00 | 0.00 |

Ngưỡng 0 = trên validation không có ngưỡng nào từ chối được câu ngoài phạm vi mà giữ từ chối nhầm trong giới hạn: điểm top-1 của câu không trả lời được không thấp hơn câu hợp lệ.

Theo type (validation, MRR):

| Mô hình | Token | confusable | direct | multi_intent | paraphrase | underspecified |
|---|---|---|---|---|---|---|
| TFIDF | âm tiết | 1.000 (n=1) | 0.867 (n=5) | 1.000 (n=1) | 0.221 (n=6) | 0.000 (n=1) |
| BM25 | âm tiết | 0.500 (n=1) | 0.569 (n=5) | 1.000 (n=1) | 0.144 (n=6) | 0.000 (n=1) |
| TFIDF | từ | 1.000 (n=1) | 0.720 (n=5) | 1.000 (n=1) | 0.367 (n=6) | 0.111 (n=1) |
| BM25 | từ | 0.500 (n=1) | 0.433 (n=5) | 1.000 (n=1) | 0.283 (n=6) | 0.000 (n=1) |

## test

| Mô hình | Token | Tham số | R@1 | R@3 | R@5 | R@10 | MRR | NDCG@10 | Ngưỡng | Từ chối đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TFIDF | âm tiết | `{"ngram_range": [1, 1], "sublinear_tf": true}` | 0.086 | 0.185 | 0.225 | 0.361 | 0.285 | 0.248 | 0.000 | 0.00 | 0.00 |
| BM25 | âm tiết | `{"k1": 2.0, "b": 0.9}` | 0.086 | 0.173 | 0.213 | 0.333 | 0.297 | 0.238 | 0.000 | 0.00 | 0.00 |
| TFIDF | từ | `{"ngram_range": [1, 2], "sublinear_tf": true}` | 0.077 | 0.191 | 0.269 | 0.349 | 0.284 | 0.256 | 0.000 | 0.00 | 0.00 |
| BM25 | từ | `{"k1": 2.0, "b": 0.75}` | 0.059 | 0.157 | 0.225 | 0.358 | 0.240 | 0.236 | 0.000 | 0.00 | 0.00 |

Ngưỡng 0 = trên validation không có ngưỡng nào từ chối được câu ngoài phạm vi mà giữ từ chối nhầm trong giới hạn: điểm top-1 của câu không trả lời được không thấp hơn câu hợp lệ.

Theo type (test, MRR):

| Mô hình | Token | confusable | direct | multi_intent | paraphrase | underspecified |
|---|---|---|---|---|---|---|
| TFIDF | âm tiết | 0.153 (n=4) | 0.396 (n=8) | 0.667 (n=2) | 0.143 (n=11) | 0.500 (n=2) |
| BM25 | âm tiết | 0.156 (n=4) | 0.429 (n=8) | 0.600 (n=2) | 0.161 (n=11) | 0.500 (n=2) |
| TFIDF | từ | 0.286 (n=4) | 0.494 (n=8) | 0.500 (n=2) | 0.129 (n=11) | 0.083 (n=2) |
| BM25 | từ | 0.146 (n=4) | 0.359 (n=8) | 0.500 (n=2) | 0.152 (n=11) | 0.167 (n=2) |
