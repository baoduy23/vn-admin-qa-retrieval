"""Xếp hạng lại top-n bằng cross-encoder (M5, TV3).

Cross-encoder đọc cả cặp (câu hỏi, chunk) cùng lúc nên chính xác hơn bi-encoder nhưng chậm:
chỉ chạy trên top_n ứng viên (mặc định 20) của bước truy hồi đầu (BM25 / SBERT / hybrid).

Model khai báo trong configs/retrieval.yaml (rerankers), cùng các khóa như dense_models
(name, segment, max_seq_length). PhoBERT phân loại cặp đã fine-tune bằng train_pairs.csv
(src/retrieval/finetune.py --cross) cũng nạp ở đây, name = artifacts/finetuned/<tên>.

blend: 0 = chỉ dùng điểm cross-encoder; > 0 = trộn với điểm bước đầu (đều min-max trên top_n),
       final = blend * first' + (1 - blend) * ce'. Chọn trên validation.
"""
from __future__ import annotations

from functools import lru_cache

from src.retrieval.dense import pick_device
from src.retrieval.fusion import minmax
from src.retrieval.query import model_input


@lru_cache(maxsize=4)
def load_cross_encoder(name: str, max_length: int = 256, device: str = "auto"):
    from sentence_transformers import CrossEncoder              # import muộn: torch nạp lâu
    return CrossEncoder(name, max_length=max_length, device=pick_device(device))


class Reranker:
    def __init__(self, mcfg: dict, chunks_by_id: dict[str, dict], batch_size: int = 16, device: str = "auto"):
        self.cfg = mcfg
        self.chunks = chunks_by_id
        self.batch_size = batch_size
        self.field = "text_seg" if mcfg.get("segment") else "chunk_text"
        self.model = load_cross_encoder(mcfg["name"], mcfg.get("max_seq_length", 256), device)

    def scores(self, question: str, chunk_ids: list[str]) -> list[float]:
        if not chunk_ids:
            return []
        q = model_input(question, self.cfg.get("segment", False))
        pairs = [(q, self.chunks[c][self.field]) for c in chunk_ids]
        out = self.model.predict(pairs, batch_size=self.batch_size, show_progress_bar=False)
        return [float(x) for x in out]

    def rerank(self, question: str, candidates: list[tuple[str, float]], blend: float = 0.0,
               ce_scores: list[float] | None = None) -> list[tuple[str, float]]:
        """candidates: [(chunk_id, điểm bước đầu)] đã sắp. ce_scores: truyền vào nếu đã tính (lưới blend)."""
        ids = [c for c, _ in candidates]
        ce = ce_scores if ce_scores is not None else self.scores(question, ids)
        if blend > 0:
            first = minmax([s for _, s in candidates])
            ce = [blend * f + (1 - blend) * c for f, c in zip(first, minmax(ce))]
        return sorted(zip(ids, ce), key=lambda x: -x[1])
