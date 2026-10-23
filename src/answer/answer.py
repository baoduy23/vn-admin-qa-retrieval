"""Hàm answer() (Quân, M6): câu hỏi → câu trả lời trích nguyên văn kèm nguồn, hoặc từ chối.

    from src.answer import answer
    r = answer("Đăng ký khai sinh cần giấy tờ gì?")
    r["answer"]      # 'Theo Luật Hộ tịch 60/2014/QH13, Điều 16 Khoản 1: "..."'
    r["sources"]     # top-k đoạn luật: tên văn bản, Điều/Khoản, link, điểm, đoạn trích tô sáng
    r["refused"]     # True khi không đủ căn cứ

Các bước:
  0. Câu hỏi về lĩnh vực khác (hộ chiếu, đất đai, thuế...) mà không nhắc việc hộ tịch nào → từ chối ngay
     (out_of_scope, intent.out_of_scope_topic), không truy hồi.
     Câu không có âm tiết nào xuất hiện trong kho ("hello world", gõ bừa) → từ chối ngay (no_overlap).
     Cần lớp này vì điểm rerank đã minmax trong tập ứng viên: hybrid và PhoRanker cùng chọn một đoạn
     là top-1 được 1.0, vượt τ dù đoạn đó chẳng liên quan gì.
  1. Tách câu nhiều ý (intent.split_multi_intent), mỗi ý truy hồi riêng bằng retrieve() của TV3.
  2. Mỗi ý: điểm top-1 < τ → từ chối (low_score). τ chọn trên validation (evaluate_answer.py).
  3. Câu hỏi đòi con số (tiền, phạt, tuổi, thời hạn) mà top evidence_k đoạn không có con số đó
     → từ chối (no_evidence), chống trả lời không có căn cứ cho câu unsupported.
  4. Còn lại: chọn khoản/điểm khớp nhất trong đoạn top-1, đưa vào mẫu
     Theo <tên văn bản>, Điều X Khoản Y: "<trích nguyên văn>".
  5. Kèm câu hỏi tương tự (similar_questions của TV3) và gợi ý khi câu thiếu thông tin.
Cả câu chỉ bị từ chối khi MỌI ý đều bị từ chối.
"""
from __future__ import annotations

from functools import lru_cache

import yaml

from src.answer.intent import (TYPE_LABEL, chunk_topic, evidence_pattern, expected_type, find_procedures, has_evidence,
                               is_underspecified, out_of_scope_topic, split_multi_intent,
                               topic_head)
from src.answer.line_scorer import load_line_scorer
from src.answer.retriever import Retriever, load_answer_config, load_retriever
from src.answer.template import best_quote, citation, format_answer, highlight_html
from src.answer.text import IDF, content_syllables
from src.retrieval.bm25 import tokenize
from src.data.split import ROOT
from src.retrieval.query import clean_query, strip_accents
from src.retrieval.retrieve import load_chunks, load_config, load_spec

SELECTED = ROOT / "configs/answer_selected.yaml"
AUTHORITY_NOTE_CHUNK = "120.2025.ND-CP__PL1__K2"      # cấp huyện → cấp xã (chính quyền 2 cấp)

REFUSAL_TEXT = {
    "empty": "Bạn chưa nhập câu hỏi.",
    "out_of_scope": ("Câu hỏi về {topic} nằm ngoài phạm vi kho văn bản hộ tịch (khai sinh, kết hôn, khai tử, "
                     "thay đổi, cải chính hộ tịch, nhận cha mẹ con, giám hộ, trích lục), nên hệ thống không trả lời."),
    "low_score": ("Hệ thống không tìm thấy quy định đủ liên quan trong kho văn bản hộ tịch để trả lời "
                  "câu hỏi này. Câu hỏi có thể nằm ngoài phạm vi kho (khai sinh, kết hôn, khai tử, "
                  "thay đổi, cải chính hộ tịch, nhận cha mẹ con, giám hộ, trích lục)."),
    "no_overlap": ("Câu hỏi không có từ nào xuất hiện trong kho văn bản hộ tịch (có thể là tiếng nước ngoài "
                   "hoặc gõ nhầm), nên hệ thống không trả lời."),
    "no_evidence": ("Các điều khoản tìm được không nêu {label} mà câu hỏi đòi hỏi. Hệ thống không đưa "
                    "ra con số khi không có căn cứ trong văn bản."),
}
REFUSAL_HINT = ("Bạn có thể hỏi lại cụ thể hơn, hoặc liên hệ Ủy ban nhân dân cấp xã nơi cư trú "
                "để được hướng dẫn chính thức.")


def load_thresholds() -> dict:
    """τ theo từng loại pipeline: ưu tiên bản Quân chọn trên validation (answer_selected.yaml),
    chưa có thì dùng ngưỡng TV3 đã chọn cho bước truy hồi (retrieval_selected.yaml)."""
    th = dict(load_spec().get("thresholds", {}))
    if SELECTED.exists():
        th.update(yaml.safe_load(open(SELECTED, encoding="utf-8")).get("thresholds", {}))
    return th


def load_evidence_check(pipeline: str, default: bool) -> bool:
    """Bật / tắt kiểm tra căn cứ con số theo từng pipeline, như đã chọn trên validation."""
    if not default or not SELECTED.exists():
        return default
    ev = yaml.safe_load(open(SELECTED, encoding="utf-8")).get("evidence_check", default)
    return bool(ev.get(pipeline, default) if isinstance(ev, dict) else ev)


class AnswerEngine:
    def __init__(self, cfg: dict | None = None, retriever: Retriever | None = None,
                 chunks: list[dict] | None = None, similar=None, threshold: float | None = None,
                 line_scorer=None):
        """Tham số retriever / similar / threshold / line_scorer dùng khi đánh giá hoặc test (truyền hàm giả).
        Truyền retriever mà không truyền line_scorer thì chọn dòng bằng IDF (evaluate_answer không cần model)."""
        self.cfg = cfg or load_answer_config()
        self.chunks = chunks if chunks is not None else load_chunks()
        self.by_id = {c["chunk_id"]: c for c in self.chunks}
        self.retriever = retriever or load_retriever(self.cfg, self.chunks)
        self.threshold = threshold if threshold is not None else load_thresholds().get(self.retriever.name, 0.0)
        self.evidence_check = load_evidence_check(self.retriever.name, self.cfg.get("evidence_check", True))
        self.idf = IDF([l for c in self.chunks for l in c.get("display_text", "").split("\n")])
        # âm tiết bỏ dấu của cả kho: câu gõ có dấu hay không dấu đều so được
        self.vocab = {t for c in self.chunks for t in tokenize(strip_accents(c.get("chunk_text") or c.get("display_text", "")))}
        self._similar = similar
        self.warning = self.retriever.warning
        if line_scorer is None and retriever is None and not self.warning:
            line_scorer = load_line_scorer(self.cfg)
        self.line_scorer = line_scorer

    # ------------------------------------------------------------ câu hỏi tương tự
    def similar(self, question: str) -> list[dict]:
        if self._similar is None:
            self._similar = self._load_similar()
        try:
            return self._similar(question, self.cfg.get("similar", {}).get("k", 3))
        except Exception:
            return []

    def _load_similar(self):
        """Pipeline có bi-encoder thì dùng similar_questions của TV3 (cosine); bản BM25 thì Dice âm tiết."""
        from src.retrieval import similar as sim
        if self.retriever.name in ("dense", "hybrid", "rerank") and not self.retriever.warning:
            return lambda q, k: sim.similar_questions(q, k=k)
        idx = sim.SimilarIndex(sim.question_bank(), None)
        min_score = load_config()["similar_questions"]["min_score_lexical"]

        def lexical(q, k):
            # Dice tính cả hư từ ("mất bao lâu") nên lọc thêm: phải chung ≥ 2 âm tiết nội dung
            mine = set(content_syllables(q))
            hits = idx.search(q, k=3 * k, min_score=min_score)
            return [h for h in hits if len(mine & set(content_syllables(h["question"]))) >= 2][:k]
        return lexical

    # ------------------------------------------------------------ một ý
    def answer_part(self, question: str, k: int) -> dict:
        hits = self.retriever.search(question, max(k, self.cfg.get("evidence_k", 3)))
        top_score = hits[0][1] if hits else 0.0
        part = dict(question=question, hits=hits, top_score=top_score, refused=False, reason=None,
                    answer="", quote_lines=[], chunk_id=None, expected_type=expected_type(question))
        if not hits or top_score < self.threshold:
            part.update(refused=True, reason="low_score")
            return part
        ev_texts = [self.by_id[c]["display_text"] for c, _ in hits[: self.cfg.get("evidence_k", 3)] if c in self.by_id]
        if self.evidence_check and not has_evidence(part["expected_type"], ev_texts):
            part.update(refused=True, reason="no_evidence")
            return part
        chunk = self.by_id[hits[0][0]]
        quote = best_quote(question, chunk, self.idf, evidence_pattern(part["expected_type"]), self.line_scorer)
        part.update(chunk_id=chunk["chunk_id"], quote_lines=quote, answer=format_answer(chunk, quote))
        return part

    def in_corpus(self, question: str) -> bool:
        """Có ít nhất một âm tiết của câu hỏi xuất hiện trong kho (so bản bỏ dấu), tức BM25 top-1 > 0."""
        return any(t in self.vocab for t in tokenize(strip_accents(question)))

    def out_of_scope_part(self, question: str, head: str = "") -> dict | None:
        """Lọc phạm vi cho từng ý của câu nhiều ý: "Khai tử cho bố cần giấy gì? Sổ đỏ sang tên thế nào?" qua được
        bước lọc cả câu (có "khai tử") nhưng ý 2 hỏi đất đai, nên từ chối riêng ý đó thay vì trích luật hộ tịch.
        Chỉ xét chữ của chính ý đó, bỏ phần chủ đề (head) split_multi_intent ghép từ vế đầu: "Chồng tôi quốc tịch
        Úc, nộp gì" có "quốc tịch" là do ghép, ý thật là "nộp gì" (hồ sơ khai tử)."""
        own = question[len(head):].strip() if head and question.startswith(head + " ") else question
        topic = out_of_scope_topic(own) if self.cfg.get("out_of_scope_filter", True) else None
        if not topic:
            return None
        # hiện đúng chữ người dùng gõ cho ý này, không kèm chủ đề ghép ("Khai tử cho bố Sổ đỏ ...")
        return dict(question=own, hits=[], top_score=0.0, refused=True, reason="out_of_scope",
                    answer="", quote_lines=[], chunk_id=None, expected_type=None, out_of_scope_topic=topic)

    @staticmethod
    def refusal_text(part: dict) -> str:
        label = TYPE_LABEL.get(part.get("expected_type") or "", "thông tin")
        return REFUSAL_TEXT[part["reason"]].format(label=label, topic=part.get("out_of_scope_topic") or "")

    # ------------------------------------------------------------ cả câu
    def answer(self, question: str, k: int | None = None) -> dict:
        k = k or self.cfg.get("top_k", 5)
        q = clean_query(question).strip()
        base = dict(question=q, pipeline=self.retriever.name, threshold=self.threshold, warning=self.warning)
        if not q:
            return dict(base, refused=True, reason="empty", answer=REFUSAL_TEXT["empty"], parts=[],
                        sources=[], similar_questions=[], underspecified=False, notes=[], scores={})

        topic = out_of_scope_topic(q) if self.cfg.get("out_of_scope_filter", True) else None
        if topic:
            return dict(base, refused=True, reason="out_of_scope",
                        answer=f'{REFUSAL_TEXT["out_of_scope"].format(topic=topic)}\n{REFUSAL_HINT}',
                        parts=[], sources=[], similar_questions=[], underspecified=False, notes=[],
                        scores={"top1": 0.0, "threshold": self.threshold}, out_of_scope_topic=topic)
        if self.cfg.get("no_overlap_filter", True) and not self.in_corpus(q):
            return dict(base, refused=True, reason="no_overlap", answer=f'{REFUSAL_TEXT["no_overlap"]}\n{REFUSAL_HINT}',
                        parts=[], sources=[], similar_questions=[], underspecified=False, notes=[],
                        scores={"top1": 0.0, "threshold": self.threshold})

        split = self.cfg.get("multi_intent", {}).get("split", True)
        sub_questions = split_multi_intent(q) if split else [q]
        head = topic_head(sub_questions[0]) if len(sub_questions) > 1 else ""
        parts = [self.out_of_scope_part(s, head if i else "") or self.answer_part(s, k)
                 for i, s in enumerate(sub_questions)]
        refused = all(p["refused"] for p in parts)

        # câu trả lời: một ý → 1 đoạn; nhiều ý → đánh số từng ý
        if len(parts) == 1:
            p = parts[0]
            text = self.refusal_text(p) if p["refused"] else p["answer"]
        else:
            lines = [f"Câu hỏi gồm {len(parts)} ý:"]
            for i, p in enumerate(parts, 1):
                body = self.refusal_text(p) if p["refused"] else p["answer"]
                lines.append(f"{i}. {p['question']}: {body}")
            text = "\n".join(lines)
        if refused:
            text = f"{text}\n{REFUSAL_HINT}"

        sources = self.collect_sources(parts, k, q)
        under = is_underspecified(q, self.cfg.get("underspecified", {}).get("max_content_syllables", 5))
        return dict(
            base, refused=refused, answer=text, parts=[self._public(p) for p in parts],
            reason=parts[0]["reason"] if refused else None,
            sources=sources,
            similar_questions=self.similar(q),
            underspecified=under,
            notes=self.notes(parts, sources),
            scores={"top1": round(max(p["top_score"] for p in parts), 4), "threshold": self.threshold},
        )

    def collect_sources(self, parts: list[dict], k: int, question: str) -> list[dict]:
        """Ghép top-k của các ý xen kẽ nhau (ý 1 hạng 1, ý 2 hạng 1, ý 1 hạng 2, ...), bỏ trùng."""
        quote_of = {p["chunk_id"]: p["quote_lines"] for p in parts if p["chunk_id"]}
        seen, out = set(), []
        for rank in range(max(len(p["hits"]) for p in parts)):
            for pi, p in enumerate(parts):
                if rank >= len(p["hits"]) or len(out) >= k:
                    continue
                cid, score = p["hits"][rank]
                if cid in seen or cid not in self.by_id:
                    continue
                seen.add(cid)
                c = self.by_id[cid]
                quote = quote_of.get(cid, [])
                out.append(dict(
                    rank=len(out) + 1, part=pi + 1, chunk_id=cid, score=round(float(score), 4),
                    doc_id=c["doc_id"], doc_title=c["doc_title"], dieu_title=c.get("dieu_title") or "",
                    citation=citation(c, quote or None), url=c.get("url", ""),
                    excerpt=c.get("display_text", ""), quote_lines=quote,
                    excerpt_html=highlight_html(c.get("display_text", ""), p["question"], quote),
                    topic=chunk_topic(c), amended_by=c.get("amended_by") or [],
                    used_in_answer=cid in quote_of and not p["refused"],
                ))
        return out

    def notes(self, parts: list[dict], sources: list[dict]) -> list[dict]:
        """Lưu ý pháp lý tự động: đoạn trích còn ghi "cấp huyện" thì dẫn Nghị định 120/2025/NĐ-CP
        (chuyển nhiệm vụ cấp huyện về cấp xã), trích nguyên văn câu đầu của khoản đó."""
        out = []
        used = [s for s in sources if s["used_in_answer"]]
        if any("cap huyen" in strip_accents(" ".join(s["quote_lines"])) for s in used):
            c = self.by_id.get(AUTHORITY_NOTE_CHUNK)
            if c:
                first = c["display_text"].split(";")[0].strip()
                out.append(dict(kind="authority", text=f'Theo {c["doc_title"]}, Phụ lục mục I Khoản 2: "{first}; …"',
                                url=c.get("url", "")))
        for s in used:
            if s["amended_by"]:
                out.append(dict(kind="amended", text=f"{s['doc_title']}, {s['citation']} đã được hợp nhất nội dung "
                                f"sửa đổi bởi: {', '.join(s['amended_by'])}.", url=""))
        return out

    @staticmethod
    def _public(p: dict) -> dict:
        return {k: v for k, v in p.items() if k != "hits"} | {"top_chunks": [c for c, _ in p["hits"][:5]]}


@lru_cache(maxsize=1)
def get_engine() -> AnswerEngine:
    return AnswerEngine()


def answer(question: str, k: int | None = None) -> dict:
    """{question, answer, refused, reason, parts[], sources[], similar_questions[], underspecified,
    notes[], scores, pipeline}. Xem docstring đầu file."""
    return get_engine().answer(question, k)


def suggest_procedures(question: str) -> list[str]:
    """Gợi ý việc hộ tịch để người dùng hỏi rõ hơn (dùng khi underspecified)."""
    from src.answer.intent import PROCEDURE_NAMES
    have = set(find_procedures(question))
    return [p for p in PROCEDURE_NAMES if p not in have][:6]
