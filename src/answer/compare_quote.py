"""So 2 cách chọn khoản để trích: IDF (cách cũ) và PhoRanker (line_scorer.py).

    python -m src.answer.compare_quote          # chạy trên train + validation, cần torch và model của TV3

Mỗi câu chỉ truy hồi 1 lần bằng pipeline đã chốt (retrieve() của TV3), rồi chọn dòng bằng 2 cách trên
cùng một đoạn top-1. Không đụng tập test, chỉ tính câu hợp lệ mà không bị từ chối.
F1 so với answer_text chỉ là con số tham khảo vì answer_text là câu tóm tắt, nên file CSV có thêm cột
`dung_hon` để chấm tay: idf / rerank / nhu_nhau / ca_hai_sai.

Ghi ra results/answer/quote_compare.csv và in tóm tắt ra màn hình.
"""
from __future__ import annotations

from src.answer.answer import AnswerEngine
from src.answer.evaluate_answer import NO_ANSWER, OUT, load_qrels, load_questions, token_f1, write_csv
from src.answer.line_scorer import load_line_scorer
from src.answer.retriever import Retriever, load_answer_config, load_retriever
from src.retrieval.retrieve import load_chunks


def cached(r: Retriever) -> Retriever:
    memo = {}

    def search(q, k):
        if (q, k) not in memo:
            memo[(q, k)] = r.search(q, k)
        return memo[(q, k)]
    return Retriever(r.name, search, r.warning)


def main() -> None:
    cfg = load_answer_config()
    chunks, qrels = load_chunks(), load_qrels()
    retr = load_retriever(cfg, chunks)
    scorer = load_line_scorer(dict(cfg, quote={"scorer": "rerank"}))
    if retr.warning or scorer is None:
        raise SystemExit("Không nạp được pipeline TV3 / PhoRanker (cần torch + sentence-transformers). "
                         + retr.warning)
    retr = cached(retr)
    base = dict(cfg, multi_intent={"split": False})
    eng = {name: AnswerEngine(base, retriever=retr, chunks=chunks, similar=lambda q, k: [], line_scorer=ls)
           for name, ls in (("idf", None), ("rerank", scorer))}

    rows = []
    for q in load_questions({"train", "validation"}):
        if q["type"] in NO_ANSWER:
            continue
        res = {name: e.answer(q["question"])["parts"][0] for name, e in eng.items()}
        if res["idf"]["refused"]:
            continue
        quote = {name: " ".join(p["quote_lines"]) for name, p in res.items()}
        cid = res["idf"]["chunk_id"]
        rows.append(dict(
            question_id=q["question_id"], split=q["split"], type=q["type"], question=q["question"],
            chunk_id=cid, relevance=qrels.get(q["question_id"], {}).get(cid, 0),
            changed=quote["idf"] != quote["rerank"],
            f1_idf=round(token_f1(quote["idf"], q["answer_text"]), 4),
            f1_rerank=round(token_f1(quote["rerank"], q["answer_text"]), 4),
            quote_idf=quote["idf"], quote_rerank=quote["rerank"], answer_text=q["answer_text"], dung_hon="",
        ))
    write_csv(OUT / "quote_compare.csv", rows)

    n = len(rows)
    ch = [r for r in rows if r["changed"]]
    mean = lambda xs: sum(xs) / len(xs) if xs else float("nan")   # noqa: E731
    print(f"{n} câu được trả lời (train + validation), {len(ch)} câu đổi khoản trích")
    print(f"F1 trung bình: idf {mean([r['f1_idf'] for r in rows]):.3f}  rerank {mean([r['f1_rerank'] for r in rows]):.3f}")
    print(f"Trên câu đổi khoản: rerank tốt hơn {sum(r['f1_rerank'] > r['f1_idf'] for r in ch)}, "
          f"kém hơn {sum(r['f1_rerank'] < r['f1_idf'] for r in ch)}, bằng {sum(r['f1_rerank'] == r['f1_idf'] for r in ch)}")
    print(f"→ {(OUT / 'quote_compare.csv')} (cột dung_hon để chấm tay các câu changed=True)")


if __name__ == "__main__":
    main()
