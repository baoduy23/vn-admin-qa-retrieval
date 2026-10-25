"""Xếp hạng lại top-n bằng cross-encoder (TV3).

Cross-encoder đọc nguyên cặp (câu hỏi, chunk) một lượt nên chính xác hơn bi-encoder nhưng chậm, vì vậy
chỉ chạy trên top_n ứng viên (mặc định 20) của bước truy hồi đầu (BM25 / SBERT / hybrid).

Model khai báo trong configs/retrieval.yaml (mục rerankers), cùng các khoá như dense_models
(name, segment, max_seq_length). PhoBERT phân loại cặp fine-tune bằng train_pairs.csv
(src/retrieval/finetune.py --cross) cũng nạp ở đây, với name là artifacts/finetuned/<tên>.

blend: 0 là chỉ dùng điểm cross-encoder, > 0 là trộn với điểm bước đầu (min-max trên top_n),
       final = blend * first' + (1 - blend) * ce'. Chọn trên validation.
ce_norm: cách đưa điểm cross-encoder vào công thức trên (chọn trên validation, lưới rerank.ce_norm_grid):
  minmax  ce' là min-max trong các ứng viên của câu đó. Chunk tốt nhất lúc nào cũng được 1.0 kể cả khi chẳng
          chunk nào liên quan, nên câu nào điểm top-1 cũng cao, τ chỉ mang tính tương đối.
  raw     ce' là xác suất liên quan do model cho (sigmoid, 0..1), không chuẩn hoá theo câu. Câu lạc đề thì
          ứng viên nào cũng thấp, top-1 thấp theo, nên τ trên điểm top-1 lọc câu cần từ chối tốt hơn.
restore_diacritics: true thì câu gõ không dấu được khôi phục dấu trước khi đưa vào model (restore.py).
"""
from __future__ import annotations

import math
from functools import lru_cache

from src.retrieval.fusion import minmax
from src.retrieval.query import model_input


@lru_cache(maxsize=4)
def load_cross_encoder(name: str, max_length: int = 256, device: str = "auto"):
    from sentence_transformers import CrossEncoder              # import muộn: torch nạp lâu
    from src.retrieval.dense import pick_device                 # import muộn: dense.py cần numpy
    return CrossEncoder(name, max_length=max_length, device=pick_device(device))


class Reranker:
    def __init__(self, mcfg: dict, chunks_by_id: dict[str, dict], batch_size: int = 16, device: str = "auto"):
        self.cfg = mcfg
        self.chunks = chunks_by_id
        self.batch_size = batch_size
        self.field = "text_seg" if mcfg.get("segment") else "chunk_text"
        self.model = load_cross_encoder(mcfg["name"], mcfg.get("max_seq_length", 256), device)

    def scores(self, question: str, chunk_ids: list[str], restore: bool | None = None) -> list[float]:
        """Điểm model.predict. restore=None thì theo cfg, evaluate_models truyền True / False để thử cả hai."""
        if not chunk_ids:
            return []
        restore = self.cfg.get("restore_diacritics", False) if restore is None else restore
        q = model_input(question, self.cfg.get("segment", False), restore=restore)
        pairs = [(q, self.chunks[c][self.field]) for c in chunk_ids]
        out = self.model.predict(pairs, batch_size=self.batch_size, show_progress_bar=False)
        return [float(x) for x in out]

    def probs(self, ce: list[float]) -> list[float]:
        """Đổi điểm thô thành xác suất 0..1. Model 1 nhãn (PhoRanker) đã được sentence-transformers áp sigmoid
        thì giữ nguyên, model trả logit (activation Identity) thì áp sigmoid ở đây, để blend luôn trộn hai thang 0..1."""
        act = getattr(self.model, "activation_fn", None) or getattr(self.model, "default_activation_function", None)
        if type(act).__name__ == "Sigmoid":
            return list(ce)
        return [1 / (1 + math.exp(-x)) if x >= 0 else math.exp(x) / (1 + math.exp(x)) for x in ce]

    def rerank(self, question: str, candidates: list[tuple[str, float]], blend: float = 0.0,
               ce_scores: list[float] | None = None, ce_norm: str | None = None) -> list[tuple[str, float]]:
        """candidates: [(chunk_id, điểm bước đầu)] đã sắp xếp. ce_scores: truyền vào nếu đã tính rồi (lưới blend).
        ce_norm=None thì theo cfg (mặc định minmax, như hồi chưa có công tắc này)."""
        ids = [c for c, _ in candidates]
        ce = ce_scores if ce_scores is not None else self.scores(question, ids)
        ce_norm = ce_norm or self.cfg.get("ce_norm", "minmax")
        if ce_norm == "raw":
            ce = self.probs(ce)
        elif ce_norm != "minmax":
            raise ValueError(f"ce_norm không hợp lệ: {ce_norm}")
        if blend > 0:
            first = minmax([s for _, s in candidates])
            ce = [blend * f + (1 - blend) * c for f, c in zip(first, ce if ce_norm == "raw" else minmax(ce))]
        return sorted(zip(ids, ce), key=lambda x: -x[1])
