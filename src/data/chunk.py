"""D03: chia đoạn, data/interim/docs.jsonl → data/processed/chunks.jsonl.

- Mỗi mục của một thủ tục là một đoạn. Mục dài hơn max_tokens (đếm theo từ
  sau tách từ) thì cắt tiếp theo dòng/câu, chồng lấn overlap_sentences đơn vị.
- chunk_text = "<Tên thủ tục> | <Tên mục>: <nội dung>" (dùng cho mô hình).
- display_text = nội dung nguyên văn (dùng để trích dẫn trên web).
- text_seg = chunk_text đã tách từ (BM25 mức từ, PhoBERT).
- chunk_id = <doc_id>__<field>__<i>: ổn định nếu nội dung không đổi.

Chạy:
    python -m src.data.chunk
"""
import argparse
import functools
import hashlib
import json
import re
from pathlib import Path

import yaml

from src.data.parse import FIELD_LABELS, FIELD_NAMES_VI
from src.data.text_utils import count_syllables

DOCS = Path("data/interim/docs.jsonl")
OUT = Path("data/processed/chunks.jsonl")
META = Path("data/processed/chunks_meta.json")
SENT_SPLIT = re.compile(r"(?<=[.;!?])\s+(?=\S)")


def load_segmenter(name):
    if name == "none":
        return (lambda s: s), "none"
    if name == "underthesea":
        import underthesea
        from underthesea import word_tokenize
        return (lambda s: word_tokenize(s, format="text")), f"underthesea=={underthesea.__version__}"
    if name == "pyvi":
        from pyvi import ViTokenizer
        import pyvi
        return ViTokenizer.tokenize, f"pyvi=={getattr(pyvi, '__version__', '?')}"
    raise ValueError(f"segmenter không hỗ trợ: {name}")


def to_units(text, seg, max_tokens):
    """Đơn vị cắt = dòng; dòng quá dài thì tách thành câu."""
    units = []
    for line in text.split("\n"):
        if len(seg(line).split()) <= max_tokens // 2:
            units.append(line)
        else:
            units += [s for s in SENT_SPLIT.split(line) if s.strip()]
    return units


def pack(units, seg, max_tokens, prefix_tokens, overlap):
    """Gom đơn vị thành đoạn ≤ max_tokens (tính cả tiền tố), chồng lấn `overlap` đơn vị."""
    budget = max_tokens - prefix_tokens
    lens = [len(seg(u).split()) for u in units]
    chunks, cur, cur_len, i = [], [], 0, 0
    while i < len(units):
        u, n = units[i], lens[i]
        if n > budget:                      # 1 câu dài hơn cả ngưỡng: cắt cứng theo âm tiết
            if cur:
                chunks.append(cur)
                cur, cur_len = [], 0
            words = u.split()
            step = max(1, int(len(words) * budget * 0.9 / n))
            chunks += [[" ".join(words[j:j + step])] for j in range(0, len(words), step)]
            i += 1
            continue
        if cur_len + n > budget and cur:
            chunks.append(cur)
            keep = cur[-overlap:] if overlap else []
            keep_len = sum(len(seg(x).split()) for x in keep)
            if keep_len + n > budget:
                keep, keep_len = [], 0
            cur, cur_len = list(keep), keep_len
        cur.append(u)
        cur_len += n
        i += 1
    if cur:
        chunks.append(cur)
    return ["\n".join(c) for c in chunks]


def build_chunks(docs, seg, cfg):
    max_tokens = int(cfg.get("max_tokens", 256))
    overlap = int(cfg.get("overlap_sentences", 1))
    add_prefix = bool(cfg.get("add_context_prefix", True))
    fmt = cfg.get("chunk_id_format", "{doc_id}__{field}__{index}")
    out = []
    for doc in sorted(docs, key=lambda d: d["doc_id"]):
        for field in FIELD_LABELS:              # thứ tự cố định → chunk_id ổn định
            text = doc["fields"].get(field)
            if not text:
                continue
            prefix = f"{doc['title']} | {FIELD_NAMES_VI[field]}: " if add_prefix else ""
            prefix_tokens = len(seg(prefix).split()) if prefix else 0
            pieces = pack(to_units(text, seg, max_tokens), seg, max_tokens, prefix_tokens, overlap)
            for i, piece in enumerate(pieces):
                chunk_text = prefix + piece
                text_seg = seg(chunk_text)
                out.append({
                    "chunk_id": fmt.format(doc_id=doc["doc_id"], field=field, index=i),
                    "doc_id": doc["doc_id"],
                    "title": doc["title"],
                    "field": field,
                    "field_name": FIELD_NAMES_VI[field],
                    "part": i,
                    "n_parts": len(pieces),
                    "chunk_text": chunk_text,
                    "display_text": piece,
                    "text_seg": text_seg,
                    "n_tokens": len(text_seg.split()),
                    "n_syllables": count_syllables(chunk_text),
                    "url": doc["url"],
                    "accessed_at": doc["accessed_at"],
                })
    return out


def check(chunks, docs, max_tokens):
    """Assertion của hướng dẫn TV1 mục 6.2. Trả về list lỗi (rỗng = đạt)."""
    errors = []
    ids = [c["chunk_id"] for c in chunks]
    if len(ids) != len(set(ids)):
        errors.append("chunk_id bị trùng")
    if any(not c["chunk_text"].strip() or not c["text_seg"].strip() for c in chunks):
        errors.append("có chunk rỗng")
    covered = {c["doc_id"] for c in chunks}
    miss = [d["doc_id"] for d in docs if d["doc_id"] not in covered]
    if miss:
        errors.append(f"thủ tục không có chunk nào: {miss}")
    over = [c["chunk_id"] for c in chunks if c["n_tokens"] > max_tokens]
    if over:
        errors.append(f"{len(over)} chunk vượt {max_tokens} token: {over[:5]}")
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/chunking.yaml")
    ap.add_argument("--preprocessing", default="configs/preprocessing.yaml")
    ap.add_argument("--segmenter", help="ghi đè segmenter trong preprocessing.yaml (underthesea|pyvi|none)")
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config, encoding="utf-8"))
    pre = yaml.safe_load(open(args.preprocessing, encoding="utf-8"))
    seg, seg_version = load_segmenter(args.segmenter or pre["segmenter"]["name"])
    seg = functools.lru_cache(maxsize=None)(seg)    # cùng 1 câu được tách từ nhiều lần khi gom đoạn

    docs = [json.loads(l) for l in open(DOCS, encoding="utf-8") if l.strip()]
    chunks = build_chunks(docs, seg, cfg)
    errors = check(chunks, docs, int(cfg.get("max_tokens", 256)))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    meta = {
        "n_docs": len(docs), "n_chunks": len(chunks), "segmenter": seg_version,
        "chunking": cfg, "docs_sha256": hashlib.sha256(DOCS.read_bytes()).hexdigest(),
        "chunks_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(), "check_errors": errors,
    }
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(chunks)} chunk từ {len(docs)} thủ tục → {OUT} (segmenter {seg_version})")
    print("Kiểm tra: ĐẠT" if not errors else "Kiểm tra: CHƯA ĐẠT\n- " + "\n- ".join(errors))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
