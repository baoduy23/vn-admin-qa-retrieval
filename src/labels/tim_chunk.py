"""Tìm chunk để gán qrels: gõ câu hỏi, in top-k chunk theo BM25.

Chạy:  python -m src.labels.tim_chunk "giấy khai sinh ghi sai ngày sinh"
       python -m src.labels.tim_chunk "cải chính hộ tịch" -k 10
Câu hỏi không dấu sẽ khớp kém (kho có dấu), nên gõ có dấu khi tìm.
"""
import argparse
import json
from pathlib import Path

from src.retrieval.bm25 import BM25

ROOT = Path(__file__).resolve().parents[2]
CHUNKS = ROOT / "data/processed/chunks.jsonl"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("-k", type=int, default=5)
    ap.add_argument("--chars", type=int, default=400, help="số ký tự in ra mỗi chunk")
    args = ap.parse_args()

    chunks = [json.loads(line) for line in open(CHUNKS, encoding="utf-8")]
    bm25 = BM25([c["chunk_text"] for c in chunks], [c["chunk_id"] for c in chunks])
    by_id = {c["chunk_id"]: c for c in chunks}

    for rank, (cid, score) in enumerate(bm25.search(args.query, k=args.k), 1):
        text = by_id[cid]["chunk_text"].replace("\n", " ")
        print(f"#{rank}  {cid}  (score {score:.2f})")
        print(f"    {text[:args.chars]}")
        print()


if __name__ == "__main__":
    main()
