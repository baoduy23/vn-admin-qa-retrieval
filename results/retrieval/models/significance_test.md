# Kiểm định chênh lệch giữa các bước truy hồi (test)

Sinh bởi `python -m src.retrieval.significance --split test`. Đọc lại `runs/*_test.csv` đã lưu, không chạy lại mô hình. Paired bootstrap lấy CI95 của chênh lệch trung bình; p là paired randomization (sign-flip) hai phía; p Holm chỉnh cho 5 cặp của cùng một thước đo. B = 10000, seed 42. Hơn / kém = số câu bước sau cao hơn / thấp hơn bước trước.

## MRR

| So sánh | n | Trước | Sau | Chênh lệch | CI95 | Hơn / kém | p | p Holm |
|---|---|---|---|---|---|---|---|---|
| bm25 vs bm25_raw | 89 | 0.506 | 0.600 | +0.094 | [+0.048; +0.147] | 17 / 0 | 0.0001 | 0.0005 |
| dense vs bm25 | 89 | 0.600 | 0.666 | +0.066 | [-0.016; +0.151] | 33 / 20 | 0.1285 | 0.1358 |
| hybrid vs dense | 89 | 0.666 | 0.704 | +0.038 | [-0.001; +0.080] | 16 / 10 | 0.0679 | 0.1358 |
| rerank vs hybrid | 89 | 0.704 | 0.796 | +0.092 | [+0.034; +0.155] | 24 / 8 | 0.0031 | 0.0093 |
| rerank vs bm25_raw | 89 | 0.506 | 0.796 | +0.291 | [+0.198; +0.383] | 45 / 10 | 0.0001 | 0.0005 |

## NDCG@10

| So sánh | n | Trước | Sau | Chênh lệch | CI95 | Hơn / kém | p | p Holm |
|---|---|---|---|---|---|---|---|---|
| bm25 vs bm25_raw | 89 | 0.432 | 0.507 | +0.076 | [+0.036; +0.121] | 18 / 1 | 0.0002 | 0.0008 |
| dense vs bm25 | 89 | 0.507 | 0.588 | +0.081 | [+0.023; +0.141] | 44 / 30 | 0.0100 | 0.0118 |
| hybrid vs dense | 89 | 0.588 | 0.620 | +0.031 | [+0.010; +0.055] | 36 / 13 | 0.0059 | 0.0118 |
| rerank vs hybrid | 89 | 0.620 | 0.691 | +0.071 | [+0.034; +0.109] | 48 / 19 | 0.0006 | 0.0018 |
| rerank vs bm25_raw | 89 | 0.432 | 0.691 | +0.259 | [+0.187; +0.333] | 60 / 16 | 0.0001 | 0.0005 |
