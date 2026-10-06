# src/retrieval/ — truy hồi và đánh giá (TV1 baseline, TV2 metrics, TV3 mô hình)

## Đã có

| File | Nội dung |
|---|---|
| `bm25.py` | BM25 Okapi tự viết, không cần thư viện. `BM25(docs, ids).search(query, k)` trả `[(chunk_id, score), ...]` |
| `metrics.py` | `recall_at_k`, `reciprocal_rank`, `ndcg_at_k` và `evaluate(run, qrels_all, ks)` trả bảng trung bình |

```python
import json
from src.retrieval.bm25 import BM25

chunks = [json.loads(l) for l in open("data/processed/chunks.jsonl", encoding="utf-8")]
bm25 = BM25([c["text_seg"] for c in chunks], [c["chunk_id"] for c in chunks])
bm25.search("làm giấy khai sinh cần giấy tờ gì", k=5)
```

`text_seg` cho BM25 mức từ, `chunk_text` cho mức âm tiết. Câu hỏi cũng phải tách từ cùng công cụ thì mới khớp.

## Sắp làm

| Việc | Người | Ghi chú |
|---|---|---|
| TF-IDF, chạy BM25 trên validation, hard negative top-20 | TV1 | Tham số trong `configs/retrieval_baseline.yaml` |
| Script đánh giá chung (gọi `metrics.evaluate`) | TV2 | Mọi mô hình chạy qua cùng 1 script |
| SBERT, hybrid, rerank cross-encoder / PhoBERT | TV3 | Cài thêm các dòng đang comment trong `requirements.txt` |

## Quy ước chung cho mọi mô hình

Mỗi mô hình có 1 hàm cùng dạng để TV2 đánh giá và TV4 ráp vào web:

```python
def retrieve(question: str, k: int = 10) -> list[tuple[str, float]]:
    """Trả top-k (chunk_id, score), điểm cao = liên quan hơn."""
```

Kết quả ghi vào `results/retrieval/` kèm tên model, phiên bản thư viện và seed.
