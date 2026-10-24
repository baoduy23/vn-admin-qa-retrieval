"""SBERT bi-encoder (M5, TV3): mã hóa câu hỏi và chunk thành vector, xếp hạng bằng cosine.

Mỗi model khai báo trong configs/retrieval.yaml (dense_models):
  name            tên trên Hugging Face hoặc đường dẫn model đã fine-tune (artifacts/finetuned/...)
  segment         true nếu model học trên văn bản đã tách từ (PhoBERT: "đăng_ký khai_sinh").
                  Khi đó chunk dùng cột text_seg, câu hỏi tách từ bằng cùng hàm segment() (issue #7)
  query_prefix /  tiền tố model yêu cầu, vd multilingual-e5: "query: " / "passage: "
  passage_prefix
  max_seq_length  PhoBERT tối đa 256 token; chunk của kho tối đa 200 từ nên gần như không bị cắt
  restore_diacritics  true: câu hỏi gõ không dấu được khôi phục dấu trước khi mã hóa (chọn trên validation)

Embedding của kho lưu ở artifacts/embeddings/<model>__<hash>.npy (không commit). Hash tính trên
tên model + toàn bộ văn bản đưa vào, nên đổi chunks.jsonl hay đổi model thì tự mã hóa lại.
"""
from __future__ import annotations

import hashlib
import re
from functools import lru_cache

import numpy as np

from src.data.split import ROOT
from src.retrieval.fusion import top_k
from src.retrieval.query import model_input

ART = ROOT / "artifacts"


def pick_device(device: str = "auto") -> str:
    if device != "auto":
        return device
    import torch
    return "cuda" if torch.cuda.is_available() else "cpu"


def slug(name: str) -> str:
    return re.sub(r"[^\w.-]+", "_", name).strip("_")


@lru_cache(maxsize=4)
def load_bi_encoder(name: str, max_seq_length: int = 256, device: str = "auto"):
    from sentence_transformers import SentenceTransformer       # import muộn: torch nạp lâu
    model = SentenceTransformer(name, device=pick_device(device))
    model.max_seq_length = max_seq_length
    return model


def passage_texts(chunks: list[dict], mcfg: dict) -> list[str]:
    field = "text_seg" if mcfg.get("segment") else "chunk_text"
    return [mcfg.get("passage_prefix", "") + c[field] for c in chunks]


class DenseIndex:
    def __init__(self, mcfg: dict, chunks: list[dict], batch_size: int = 16, device: str = "auto"):
        self.cfg = mcfg
        self.ids = [c["chunk_id"] for c in chunks]
        self.batch_size = batch_size
        self.model = load_bi_encoder(mcfg["name"], mcfg.get("max_seq_length", 256), device)
        self.emb = self._encode_cached(passage_texts(chunks, mcfg))

    def encode(self, texts: list[str]) -> np.ndarray:
        """Vector đã chuẩn hóa L2 → tích vô hướng = cosine."""
        return self.model.encode(texts, batch_size=self.batch_size, normalize_embeddings=True,
                                 convert_to_numpy=True, show_progress_bar=False).astype(np.float32)

    def _encode_cached(self, texts: list[str]) -> np.ndarray:
        h = hashlib.sha256((self.cfg["name"] + str(self.cfg.get("max_seq_length", 256)) + "\n"
                            + "\n".join(texts)).encode("utf-8")).hexdigest()[:12]
        path = ART / "embeddings" / f"{slug(self.cfg['name'])}__{h}.npy"
        if path.exists():
            return np.load(path)
        emb = self.encode(texts)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.save(path, emb)
        return emb

    def query_vector(self, question: str, restore: bool | None = None) -> np.ndarray:
        """restore=None: theo cfg (restore_diacritics); evaluate_models truyền True / False để thử cả hai."""
        restore = self.cfg.get("restore_diacritics", False) if restore is None else restore
        q = model_input(question, self.cfg.get("segment", False), self.cfg.get("query_prefix", ""), restore)
        return self.encode([q])[0]

    def scores(self, question: str, restore: bool | None = None) -> list[float]:
        """Cosine giữa câu hỏi và từng chunk, cùng thứ tự với self.ids."""
        return (self.emb @ self.query_vector(question, restore)).tolist()

    def search(self, question: str, k: int = 10) -> list[tuple[str, float]]:
        return top_k(self.ids, self.scores(question), k)
