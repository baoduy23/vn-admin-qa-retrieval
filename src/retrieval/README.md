# src/retrieval/: truy hồi và đánh giá (TV1 baseline, TV2 metrics, TV3 mô hình)

## Đã có

| File | Nội dung |
|---|---|
| `bm25.py` | BM25 Okapi tự viết, không cần thư viện. `BM25(docs, ids).search(query, k)` trả `[(chunk_id, score), ...]` |
| `metrics.py` | `recall_at_k`, `reciprocal_rank`, `ndcg_at_k` và `evaluate(run, qrels_all, ks)` trả bảng trung bình |
| `tfidf.py` | TF-IDF + cosine, cùng giao diện với BM25: `TFIDF(docs, ids).search(query, k)` |
| `evaluate.py` | Baseline TF-IDF/BM25 × âm tiết/từ: chọn tham số và ngưỡng từ chối trên validation, `--test` chạy test 1 lần → `results/retrieval/` |
| `hard_negatives.py` | Top-20 BM25 mức từ trên train, bỏ chunk đúng và chunk cùng Điều → `data/processed/train_pairs.csv` (1 positive : ~4 negative) |

```python
import json
from src.retrieval.bm25 import BM25

chunks = [json.loads(l) for l in open("data/processed/chunks.jsonl", encoding="utf-8")]
bm25 = BM25([c["text_seg"] for c in chunks], [c["chunk_id"] for c in chunks])
bm25.search("làm giấy khai sinh cần giấy tờ gì", k=5)
```

BM25 mức từ dùng `text_seg`, mức âm tiết dùng `chunk_text`. Câu hỏi cũng phải tách từ bằng cùng công cụ thì mới khớp.

## Sắp làm

| Việc | Người | Ghi chú |
|---|---|---|
| Script đánh giá chung (gọi `metrics.evaluate`) | TV2 | Mọi mô hình chạy qua cùng 1 script; `evaluate.py` của baseline dùng tạm được, TV2 thay hoặc mở rộng |

## Mô hình cải tiến (TV3)

| File | Nội dung |
|---|---|
| `query.py` | Chuẩn hóa câu hỏi trước khi tokenize hoặc encode (issue #7): `clean_query` (NFC + `normalize_tone` + khoảng trắng), `strip_accents`, `has_diacritics`; `model_input` tách từ bằng đúng `segment()` đã tạo `text_seg` cho model PhoBERT |
| `dense.py` | SBERT bi-encoder: `DenseIndex(model_cfg, chunks).search(q, k)`, cosine; embedding kho lưu ở `artifacts/embeddings/` |
| `fusion.py` | Hybrid: `fuse([dense, bm25], [alpha, 1 - alpha], method="minmax" \| "rrf")`, Python thuần |
| `rerank.py` | Cross-encoder xếp lại top-20: `Reranker(model_cfg, chunks_by_id).rerank(q, candidates, blend)`. Ứng viên = top-20 bước đầu + tối đa `extra_bm25` chunk đầu BM25 bị bỏ sót (`retrieve.rerank_candidates`). `ce_norm`: điểm cross-encoder min-max trong từng câu (cũ) hay giữ xác suất model cho (`raw`, câu lạc đề thì top-1 thấp thật) |
| `restore.py` | Khôi phục dấu cho câu gõ không dấu bằng bảng n-gram của kho + câu hỏi train, chỉ cho bi-encoder / cross-encoder (`restore_diacritics`). BM25 vẫn tìm trên chỉ mục bỏ dấu |
| `retrieve.py` | `retrieve(question, k=10)` dùng chung: đọc `configs/retrieval_selected.yaml`; chưa có thì BM25 âm tiết. Câu gõ không dấu tìm BM25 trên bản bỏ dấu của kho |
| `similar.py` | `similar_questions(q, k=3)`: câu hỏi tương tự trong train + validation (không lấy test), mỗi nhóm 1 câu, cosine bi-encoder (không có model thì Dice âm tiết) |
| `evaluate_models.py` | Chọn model và tham số trên validation (bi-encoder × restore_diacritics, hybrid fusion × alpha, cross-encoder × restore_diacritics × extra_bm25 × blend × ce_norm, ngưỡng câu tương tự; bảng "Công tắc cải tiến" trong báo cáo so bật / tắt) → `configs/retrieval_selected.yaml`; `--test` chạy test 1 lần → `results/retrieval/models/` |
| `finetune.py` | Nếu kịp: `--bi` fine-tune bi-encoder (MNRL + hard negative), `--cross` PhoBERT phân loại cặp, dữ liệu `train_pairs.csv` chỉ phần train → `artifacts/finetuned/` |

Danh sách model ứng viên và lưới tham số ở `configs/retrieval.yaml`. Cài thêm: `pip install sentence-transformers torch`.

```bash
python -m src.retrieval.evaluate_models          # validation: chọn model, ghi configs/retrieval_selected.yaml
python -m src.retrieval.evaluate_models --test   # chạy test 1 lần với bộ đã chốt
```

```python
from src.retrieval.retrieve import retrieve
from src.retrieval.similar import similar_questions
retrieve("dang ky khai sinh can giay to gi", k=5)   # [(chunk_id, score), ...]
similar_questions("làm giấy khai sinh cho con cần gì", k=3)
```

Để `answer()` của TV4 gọi hàm này thì trong `configs/answer.yaml` đổi `function` thành `"src.retrieval.retrieve:retrieve"`.

## Quy ước chung cho mọi mô hình

Mô hình nào cũng có 1 hàm cùng dạng để TV2 đánh giá và TV4 gắn vào web:

```python
def retrieve(question: str, k: int = 10) -> list[tuple[str, float]]:
    """Trả top-k (chunk_id, score), điểm cao = liên quan hơn."""
```

Kết quả ghi vào `results/retrieval/`, kèm tên model, phiên bản thư viện và seed.
