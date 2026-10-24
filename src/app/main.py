"""Web hỏi đáp hộ tịch (Quân, M6). Chạy từ gốc repo:

    streamlit run src/app/main.py
    ANSWER_PIPELINE=bm25 streamlit run src/app/main.py      # máy không có torch: chạy bản BM25

Đủ các chức năng đề bài yêu cầu:
  1. ô hỏi đáp                         4. câu hỏi tương tự            7. lịch sử truy vấn + thống kê chủ đề
  2. câu trả lời đề xuất (trích dẫn)   5. nút đánh giá câu trả lời
  3. nguồn + đoạn trích tô sáng        6. thông báo khi không đủ căn cứ
"""
from __future__ import annotations

import html
import inspect
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:                    # streamlit chỉ thêm src/app vào sys.path
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

st.set_page_config(page_title="Tra cứu Hộ tịch · Đề tài 10", page_icon="🪷", layout="wide",
                   initial_sidebar_state="collapsed")

from src.answer.answer import AnswerEngine, suggest_procedures  # noqa: E402
from src.answer.intent import TYPE_LABEL, chunk_topic, find_procedures  # noqa: E402
from src.app import db  # noqa: E402
from src.app import images  # noqa: E402
from src.app.style import css  # noqa: E402

TABS = [":material/home: Hỏi đáp", "Lịch sử truy vấn", "Thống kê", "Giới thiệu hệ thống"]
# st.tabs(on_change=...) chỉ có ở Streamlit mới; bản cũ hơn thì vẫn chạy, chỉ là vẽ cả 4 tab như trước.
LAZY_TABS = "on_change" in inspect.signature(st.tabs).parameters

QUICK = [
    ("Đăng ký khai sinh", "Đăng ký khai sinh cần những giấy tờ gì?"),
    ("Đăng ký kết hôn", "Đăng ký kết hôn cần giấy tờ gì và nộp ở đâu?"),
    ("Đăng ký khai tử", "Thời hạn đăng ký khai tử là bao lâu?"),
]
PROCS = [
    ("Khai sinh", ":material/child_care:", "Đăng ký khai sinh cho con ở đâu?"),
    ("Kết hôn", ":material/favorite:", "Thủ tục đăng ký kết hôn gồm những bước nào?"),
    ("Khai tử", ":material/local_florist:", "Ai có trách nhiệm đi đăng ký khai tử?"),
    ("Nhận cha, mẹ, con", ":material/family_restroom:", "Hồ sơ đăng ký nhận cha, mẹ, con gồm những gì?"),
    ("Giám hộ", ":material/shield_person:", "Đăng ký giám hộ cần giấy tờ gì?"),
    ("Thay đổi, cải chính hộ tịch", ":material/edit_document:", "Cải chính hộ tịch là gì, làm ở đâu?"),
    ("Xác nhận tình trạng hôn nhân", ":material/verified:", "Giấy xác nhận tình trạng hôn nhân có giá trị bao lâu?"),
    ("Trích lục, bản sao", ":material/description:", "Xin cấp bản sao trích lục hộ tịch ở đâu?"),
]


# ======================================================================= tài nguyên dùng chung
@st.cache_resource(show_spinner="Đang nạp mô hình và chỉ mục văn bản…")
def get_engine() -> AnswerEngine:
    return AnswerEngine()


def pipeline_desc(engine: AnswerEngine) -> dict:
    """Mô tả đúng pipeline đang chạy cho thẻ "Cách hệ thống trả lời", chân trang, trang giới thiệu.
    Trước đây ghi cứng "BM25 + SBERT + PhoRanker", kể cả khi web đã lùi về BM25 vì không nạp được model."""
    name = engine.retriever.name
    search = {"bm25": "BM25", "dense": "SBERT"}.get(name, "BM25 + SBERT")
    rerank = ""
    if name == "rerank":
        from src.retrieval.retrieve import load_spec
        r = load_spec().get("rerank", {})
        model = r.get("name", "cross-encoder").split("/")[-1]
        extra = f" (cộng tối đa {r['extra_bm25']} đoạn BM25 bỏ sót)" if r.get("extra_bm25") else ""
        rerank = f"{r.get('top_n', 20)} đoạn đầu{extra} bằng cross-encoder {model}"
    return dict(search=search, rerank=rerank, first="hybrid" if name in ("hybrid", "rerank") else name)


@st.cache_data
def topic_questions(per_topic: int = 5) -> dict[str, list[str]]:
    """Câu hỏi mẫu theo từng việc hộ tịch, lấy từ bộ câu đã gán nhãn train + validation (không lấy test),
    mỗi nhóm câu hỏi 1 câu, ưu tiên câu gõ có dấu. Dùng cho mục "Chủ đề hữu ích" (kiểu Kho tri thức UEH)."""
    from src.retrieval.query import has_diacritics
    from src.retrieval.similar import question_bank
    out: dict[str, list[str]] = {label: [] for label, _, _ in PROCS}
    seen = set()
    for r in sorted(question_bank(), key=lambda r: (not has_diacritics(r["question"]), r["question_id"])):
        hits = [p for p in find_procedures(r["question"]) if p in out]
        if not hits or r["question_group_id"] in seen or len(out[hits[0]]) >= per_topic:
            continue
        seen.add(r["question_group_id"])
        out[hits[0]].append(r["question"].strip())
    return out


@st.cache_data
def source_list() -> pd.DataFrame:
    return pd.read_csv(ROOT / "data/raw/source_list.csv", encoding="utf-8-sig")


def ask(text: str) -> None:
    """Callback của các nút gợi ý: điền câu vào ô hỏi rồi chạy luôn."""
    st.session_state.q = text
    st.session_state.pending = True


def ask_again(text: str) -> None:
    """Nút "Hỏi lại" ở tab Lịch sử: như ask(), rồi chuyển luôn về tab Hỏi đáp để thấy kết quả."""
    ask(text)
    if LAZY_TABS:
        st.session_state.nav = TABS[0]


# ======================================================================= khung trang
def header() -> None:
    st.markdown(css(), unsafe_allow_html=True)
    st.markdown("""
<div class="site-header">
  <div>
    <div class="title"><span class="big">T</span>ra cứu <span class="big">H</span>ộ tịch</div>
    <div class="tagline">Hỏi đáp quy định hộ tịch, trả lời bằng trích dẫn nguyên văn và nguồn văn bản</div>
  </div>
  <div class="badges">
    <span class="badge-out">Đề tài 10 · Xử lý ngôn ngữ tự nhiên</span>
    <span class="badge-soft">Kho văn bản hiệu lực tại 09/10/2026</span>
  </div>
</div>""", unsafe_allow_html=True)


BIRDS = "<i></i>" * 12        # dải chim Lạc: thừa bao nhiêu con thì tự ẩn (xem .frieze trong style.py)


def footer(engine: AnswerEngine) -> None:
    d = pipeline_desc(engine)
    how = f"truy hồi {d['search']}" + (", xếp hạng lại bằng cross-encoder" if d["rerank"] else "")
    st.markdown(f"""
<div class="site-footer">
  <div class="frieze">{BIRDS}</div>
  <div class="cols">
    <div><h4>Tra cứu Hộ tịch</h4>Sản phẩm học tập của nhóm, Đề tài 10 môn Xử lý ngôn ngữ tự nhiên: {how},
      trả lời bằng trích dẫn nguyên văn.</div>
    <div><h4>Liên kết hữu ích</h4>
      <a href="https://dichvucong.gov.vn" target="_blank">Cổng Dịch vụ công quốc gia</a><br>
      <a href="https://vbpl.vn" target="_blank">Cơ sở dữ liệu quốc gia về văn bản pháp luật</a><br>
      <a href="https://thuvienphapluat.vn" target="_blank">Thư viện Pháp luật</a><br>
      <a href="https://github.com/baoduy23/vn-admin-qa-retrieval" target="_blank">Mã nguồn của nhóm (GitHub)</a></div>
    <div><h4>Lưu ý</h4>Đây không phải cổng thông tin của cơ quan nhà nước. Thông tin chỉ để tham khảo; thủ tục
      cụ thể xin liên hệ Ủy ban nhân dân cấp xã nơi cư trú.</div>
  </div>
  <div class="copy">Kho văn bản: 10 văn bản về hộ tịch có hiệu lực tại 09/10/2026, đã hợp nhất nội dung sửa đổi.</div>
</div>""", unsafe_allow_html=True)


def banner(engine: AnswerEngine) -> None:
    """Banner lớn kiểu UEH: nền cam đất chuyển màu, khối hình học vàng/cam."""
    n_docs = len(source_list())
    st.markdown(f"""
<div class="banner"><div class="inner">
  <div class="tri2"></div><div class="tri"></div>
  <div class="text">
    <span class="kicker">Hỏi đáp hộ tịch</span>
    <h1>Tra cứu quy định hộ tịch,<br>trả lời có trích dẫn</h1>
    <div class="sub">Khai sinh · Kết hôn · Khai tử · Thay đổi, cải chính · Nhận cha mẹ con · Giám hộ</div>
    <div class="stats"><span>{n_docs} văn bản</span><span>{len(engine.chunks)} điều, khoản</span>
      <span>Hiệu lực tại 09/10/2026</span></div>
  </div>
</div></div>""", unsafe_allow_html=True)


def search_form(compact: bool) -> bool:
    if not compact:
        st.markdown('<div class="hero-title">Hãy để chúng tôi <b>hỗ trợ bạn</b></div>'
                    '<div class="hero-sub">Hỏi về khai sinh, kết hôn, khai tử, hộ tịch.</div>',
                    unsafe_allow_html=True)
    with st.form("ask_form", border=False):
        c1, c2 = st.columns([5, 1.1], gap="small", vertical_alignment="bottom")
        c1.text_input("Câu hỏi", key="q", label_visibility="collapsed", max_chars=300,
                      placeholder="Thông tin bạn cần, ví dụ: làm giấy khai sinh cho con cần giấy tờ gì?")
        submitted = c2.form_submit_button("Tra cứu", icon=":material/search:", width="stretch")
    with st.container(key="quick"):
        cols = st.columns(3, gap="medium")
        for col, (label, q) in zip(cols, QUICK):
            col.button(label, key=f"quick_{label}", on_click=ask, args=(q,), width="stretch")
    return submitted


def hero(engine: AnswerEngine, compact: bool) -> bool:
    """Khu tìm kiếm kiểu UEH: câu chào, ô bo tròn, ảnh hoa sen bên trái, nền hoa văn trống đồng.
    compact=True (đang xem kết quả): bỏ ảnh cho gọn. Trả True nếu có câu cần trả lời."""
    with st.container(key="hero"):
        if compact:
            _, mid, _ = st.columns([0.35, 4, 0.35])
            with mid:
                submitted = search_form(True)
        else:
            left, mid, _ = st.columns([1.05, 3.6, 0.35], gap="large")
            left.markdown(f'<div class="side-photo" style="background-image:url(\'{images.url("hoa_sen")}\')"></div>',
                          unsafe_allow_html=True)
            with mid:
                submitted = search_form(False)
    if engine.warning:
        st.warning(engine.warning, icon=":material/info:")
    pending = st.session_state.pop("pending", False)
    return bool(submitted or pending)


# ======================================================================= hỏi đáp
def run_query(engine: AnswerEngine, question: str) -> None:
    t = time.perf_counter()
    result = engine.answer(question)
    result["elapsed_ms"] = round((time.perf_counter() - t) * 1000)
    st.session_state.result = result
    st.session_state.query_id = db.log_query(result) if result.get("question") else None


def chunk_meta(engine, result, chunk_id) -> dict:
    s = next((s for s in result["sources"] if s["chunk_id"] == chunk_id), None)
    if s:
        return s
    c = engine.by_id[chunk_id]
    return dict(doc_title=c["doc_title"], citation=c.get("dieu_title", ""), url=c.get("url", ""))


def answer_card(engine, r: dict) -> None:
    if r["refused"]:
        msgs = [AnswerEngine.refusal_text(p) for p in r["parts"]] or [r["answer"].split("\n")[0]]
        body = "".join(f"<p>{html.escape(m)}</p>" for m in dict.fromkeys(msgs))
        label = {"out_of_scope": "Ngoài phạm vi hộ tịch", "no_overlap": "Ngoài phạm vi hộ tịch",
                 "empty": "Chưa có nội dung câu hỏi"}.get(r.get("reason"), "Chưa đủ căn cứ để trả lời")
        st.markdown(f"""
<div class="refuse-card">
  <div class="label">⚖ {label}</div>
  {body}
  <p>Bạn có thể hỏi lại cụ thể hơn, hoặc liên hệ <b>Ủy ban nhân dân cấp xã</b> nơi cư trú để được hướng dẫn chính thức.</p>
</div>""", unsafe_allow_html=True)
        return
    multi = len(r["parts"]) > 1
    blocks = []
    for i, p in enumerate(r["parts"], 1):
        head = f'<div class="part-q">Ý {i}: {html.escape(p["question"])}</div>' if multi else ""
        if p["refused"]:
            chip = "Ngoài phạm vi" if p["reason"] == "out_of_scope" else "Chưa đủ căn cứ"
            blocks.append(f'{head}<p><span class="chip muted">{chip}</span>'
                          f'{html.escape(AnswerEngine.refusal_text(p))}</p>')
            continue
        m = chunk_meta(engine, r, p["chunk_id"])
        quote = "<br>".join(html.escape(l) for l in p["quote_lines"])
        link = f'<span class="src-link"><a href="{m["url"]}" target="_blank">Xem văn bản gốc ↗</a></span>' if m.get("url") else ""
        blocks.append(f'{head}<div>Theo <b>{html.escape(m["doc_title"])}</b>, '
                      f'<span class="cite">{html.escape(m["citation"])}</span>:</div>'
                      f'<blockquote>“{quote}”</blockquote>{link}')
    notes = ""
    for n in r.get("notes", []):
        title = "Lưu ý về thẩm quyền" if n["kind"] == "authority" else "Văn bản đã hợp nhất"
        notes += f'<div class="note"><b>{title}:</b> {html.escape(n["text"])}</div>'
    st.markdown(f"""
<div class="answer-card">
  <div class="label">Câu trả lời đề xuất</div>
  {''.join(blocks)}
  {notes}
</div>""", unsafe_allow_html=True)


def clarify(r: dict) -> None:
    if not r.get("underspecified") or r["refused"]:
        return
    st.info("Câu hỏi chưa nói rõ việc hộ tịch nào, nên kết quả có thể chưa sát. Bạn đang hỏi về việc nào?",
            icon=":material/help:")
    with st.container(key="clarify"):
        cols = st.columns(3)
        for i, proc in enumerate(suggest_procedures(r["question"])):
            cols[i % 3].button(proc, key=f"clar_{i}", on_click=ask,
                               args=(f"{proc}: {r['question']}",), width="stretch")


def feedback_box(qid: int | None) -> None:
    if not qid:
        return
    st.markdown('<div class="sec-title left" style="font-size:18px;margin-top:6px">Đánh giá câu trả lời</div>',
                unsafe_allow_html=True)
    done = st.session_state.setdefault("rated", {})
    if qid in done:
        st.success("Cảm ơn bạn đã đánh giá!" if done[qid] == 1 else "Cảm ơn góp ý, nhóm sẽ dùng để phân tích lỗi.",
                   icon=":material/check_circle:")
        return
    with st.container(key="feedback"):
        c1, c2 = st.columns(2)
        if c1.button("Hữu ích", icon=":material/thumb_up:", key=f"up_{qid}", width="stretch"):
            db.save_feedback(qid, 1)
            done[qid] = 1
            st.rerun()
        if c2.button("Chưa đúng", icon=":material/thumb_down:", key=f"down_{qid}", width="stretch"):
            st.session_state[f"want_comment_{qid}"] = True
        if st.session_state.get(f"want_comment_{qid}"):
            note = st.text_area("Sai ở đâu? (không bắt buộc)", key=f"cmt_{qid}", height=80,
                                placeholder="Ví dụ: trích sai điều, câu trả lời thiếu ý thứ hai…")
            if st.button("Gửi góp ý", key=f"send_{qid}", type="primary"):
                db.save_feedback(qid, -1, note)
                done[qid] = -1
                st.rerun()


def sources(r: dict) -> None:
    title = "Các đoạn gần nhất (chưa đủ căn cứ)" if r["refused"] else "Nguồn văn bản và đoạn trích"
    st.markdown(f'<div class="sec-title left">{title}</div>', unsafe_allow_html=True)
    if not r["sources"]:
        st.caption("Không có đoạn nào.")
        return
    top = max(s["score"] for s in r["sources"]) or 1
    lo = min(s["score"] for s in r["sources"])
    multi = len(r["parts"]) > 1
    for s in r["sources"]:
        label = f"{s['rank']}. {s['doc_title']}, {s['citation'] or s['dieu_title']}"
        with st.expander(label, expanded=(s["rank"] == 1 and not r["refused"])):
            chips = ""
            if s["used_in_answer"]:
                chips += '<span class="chip ok">Dùng để trả lời</span>'
            if multi:
                chips += f'<span class="chip part">Ý {s["part"]}</span>'
            chips += f'<span class="chip muted">{html.escape(s["topic"])}</span>'
            width = 100 if top == lo else round(15 + 85 * (s["score"] - lo) / (top - lo))
            link = f' · <a href="{s["url"]}" target="_blank">văn bản gốc ↗</a>' if s["url"] else ""
            st.markdown(f"""
<div class="src-head"><b>{html.escape(s['dieu_title'])}</b>{link}<br>{chips}
  <span style="float:right">điểm {s['score']:.3f}</span></div>
<div class="scorebar"><span style="width:{width}%"></span></div>
<div class="excerpt">{s['excerpt_html']}</div>""", unsafe_allow_html=True)


def similar_box(r: dict) -> None:
    st.markdown('<div class="sec-title left" style="font-size:18px">Câu hỏi tương tự</div>', unsafe_allow_html=True)
    sims = r.get("similar_questions") or []
    if not sims:
        st.caption("Chưa có câu hỏi đủ giống trong kho câu hỏi mẫu.")
        return
    with st.container(key="similar"):
        for i, s in enumerate(sims):
            st.button(s["question"], key=f"sim_{i}_{s['question_id']}", on_click=ask, args=(s["question"],),
                      icon=":material/subdirectory_arrow_right:", width="stretch")


def tech_box(r: dict) -> None:
    with st.expander("Chi tiết kỹ thuật", icon=":material/tune:"):
        rows = [("Pipeline", r["pipeline"]), ("Ngưỡng từ chối τ", f"{r['threshold']:.4f}"),
                ("Điểm top-1", f"{r['scores'].get('top1', 0):.4f}"), ("Số ý", len(r["parts"])),
                ("Thời gian", f"{r.get('elapsed_ms', 0)} ms")]
        for i, p in enumerate(r["parts"], 1):
            et = TYPE_LABEL.get(p.get("expected_type") or "", "không")
            rows.append((f"Ý {i}", f"{p['question']} · điểm {p['top_score']:.3f} · hỏi con số: {et}"
                         + (f" · từ chối ({p['reason']})" if p["refused"] else "")))
        st.markdown("\n".join(f"- **{k}:** {v}" for k, v in rows))


def home_empty(engine: AnswerEngine) -> None:
    """Trang đầu: chủ đề hữu ích (accordion kiểu Kho tri thức UEH) + thẻ "Cách hệ thống trả lời"."""
    left, right = st.columns([1.6, 1], gap="large")
    topics = topic_questions()
    with left:
        st.markdown('<div class="sec-title left">Tìm kiếm chủ đề hữu ích</div>', unsafe_allow_html=True)
        with st.container(key="topics"):
            for i, (label, icon, sample) in enumerate(PROCS):
                qs = topics.get(label) or [sample]
                with st.expander(label, icon=icon, expanded=(i == 0)):
                    st.markdown(f'<div class="topic-meta">{len(qs)} câu hỏi mẫu, bấm để hỏi</div>', unsafe_allow_html=True)
                    for j, q in enumerate(qs):
                        st.button(q, key=f"topic_{i}_{j}", on_click=ask, args=(q,),
                                  icon=":material/chevron_right:", width="stretch")
    with right:
        st.markdown('<div class="sec-title left">Cách hệ thống trả lời</div>', unsafe_allow_html=True)
        d = pipeline_desc(engine)
        steps = [f"<b>Tìm</b> các điều, khoản liên quan trong 10 văn bản hộ tịch ({d['search']})."]
        if d["rerank"]:
            steps.append(f"<b>Xếp hạng lại</b> {d['rerank']}.")
        steps += ["<b>Trích nguyên văn</b> khoản khớp nhất, ghi rõ văn bản, Điều, Khoản và đường dẫn văn bản gốc.",
                  "<b>Từ chối</b> câu ngoài lĩnh vực hộ tịch, câu có điểm thấp hơn ngưỡng, hoặc khi văn bản "
                  "không có con số câu hỏi đòi, thay vì đoán."]
        body = "<br>".join(f"{i}. {t}" for i, t in enumerate(steps, 1))
        st.markdown(f'<div class="how-card"><div class="bd">{body}</div></div>', unsafe_allow_html=True)


def go_home() -> None:
    st.session_state.result = None
    st.session_state.q = ""


def tab_home(engine: AnswerEngine) -> None:
    r = st.session_state.get("result")
    if not r:
        banner(engine)
    if hero(engine, compact=bool(r)):
        q = st.session_state.get("q", "").strip()
        if q:
            with st.spinner("Đang tra cứu văn bản…"):
                run_query(engine, q)
        else:
            st.session_state.result = None
        st.rerun()                                  # vẽ lại ở dạng gọn (không banner) cùng kết quả mới
    if not r:
        home_empty(engine)
        return
    st.write("")
    left, right = st.columns([2.2, 1], gap="large")
    with left:
        answer_card(engine, r)
        clarify(r)
        sources(r)
    with right:
        st.button("Về trang đầu", icon=":material/arrow_back:", on_click=go_home, key="go_home")
        similar_box(r)
        feedback_box(st.session_state.get("query_id"))
        tech_box(r)


# ======================================================================= lịch sử
def topic_of(engine, chunk_id) -> str:
    c = engine.by_id.get(chunk_id or "")
    return chunk_topic(c) if c else "–"


def cite_of(engine, chunk_id) -> str:
    c = engine.by_id.get(chunk_id or "")
    if not c:
        return ""
    k = f" Khoản {c['khoan']}" if c.get("khoan") else ""
    return f"{c['doc_title']}, Điều {c['dieu']}{k}"


def tab_history(engine: AnswerEngine) -> None:
    st.markdown('<div class="sec-title">Lịch sử truy vấn</div>', unsafe_allow_html=True)
    rows = db.history()
    if not rows:
        st.info("Chưa có câu hỏi nào. Hãy hỏi thử ở trang Hỏi đáp.", icon=":material/history:")
        return
    df = pd.DataFrame(rows)
    df["Thời gian"] = pd.to_datetime(df["time"]).dt.strftime("%d/%m/%Y %H:%M")
    df["Kết quả"] = df["refused"].map({0: "Trả lời", 1: "Từ chối"})
    df["Nguồn top-1"] = df["top_chunk_id"].map(lambda c: cite_of(engine, c))
    df["Chủ đề"] = df["top_chunk_id"].map(lambda c: topic_of(engine, c))
    df["Đánh giá"] = df["rating"].map({1: "👍", -1: "👎"}).fillna("")
    kw = st.text_input("Lọc theo từ khóa", placeholder="ví dụ: khai sinh", key="hist_kw")
    if kw:
        df = df[df["question"].str.contains(kw, case=False, na=False)]
    show = df.rename(columns={"question": "Câu hỏi", "top_score": "Điểm", "comment": "Góp ý"})
    st.dataframe(show[["Thời gian", "Câu hỏi", "Kết quả", "Nguồn top-1", "Chủ đề", "Điểm", "Đánh giá", "Góp ý"]],
                 hide_index=True, width="stretch", height=min(560, 38 + 35 * len(show)),
                 column_config={"Điểm": st.column_config.NumberColumn(format="%.3f")})
    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
    pick = c1.selectbox("Hỏi lại một câu", list(dict.fromkeys(df["question"])), index=None,
                        placeholder="Chọn câu hỏi trong lịch sử…")
    c2.button("Hỏi lại", icon=":material/replay:", disabled=pick is None, width="stretch",
              on_click=ask_again, args=(pick,), help="Điền câu vào ô hỏi rồi chuyển về tab Hỏi đáp")
    st.download_button("Tải lịch sử (CSV)", df.drop(columns=["rating"]).to_csv(index=False).encode("utf-8-sig"),
                       "lich_su_truy_van.csv", "text/csv", icon=":material/download:")


# ======================================================================= thống kê
def bar(df: pd.DataFrame, x: str, y: str, color: str = "#C9653F", height: int = 300):
    import altair as alt
    return (alt.Chart(df).mark_bar(color=color, cornerRadiusEnd=3)
            .encode(x=alt.X(f"{x}:Q", title=None), y=alt.Y(f"{y}:N", sort="-x", title=None,
                                                            axis=alt.Axis(labelLimit=320)),
                    tooltip=[y, x]).properties(height=height))


def tab_stats(engine: AnswerEngine) -> None:
    st.markdown('<div class="sec-title">Thống kê truy vấn</div>', unsafe_allow_html=True)
    rows = db.history(limit=100000)
    if not rows:
        st.info("Chưa có dữ liệu thống kê.", icon=":material/bar_chart:")
        return
    df = pd.DataFrame(rows)
    s = db.summary()
    rated = s["up"] + s["down"]
    c = st.columns(4)
    c[0].metric("Tổng lượt hỏi", f"{s['n']:,}".replace(",", "."))
    c[1].metric("Tỉ lệ trả lời", f"{1 - s['refused'] / s['n']:.0%}")
    c[2].metric("Tỉ lệ từ chối", f"{s['refused'] / s['n']:.0%}")
    c[3].metric("Đánh giá hữu ích", f"{s['up'] / rated:.0%}" if rated else "–", help=f"{rated} lượt đánh giá")

    df["topic"] = df["top_chunk_id"].map(lambda x: topic_of(engine, x))
    ans = df[df["refused"] == 0]
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("**Chủ đề được hỏi nhiều** (theo đoạn luật dùng để trả lời)")
        t = ans["topic"].value_counts().rename_axis("Chủ đề").reset_index(name="Số lượt")
        if len(t):
            st.altair_chart(bar(t, "Số lượt", "Chủ đề"), width="stretch")
        else:
            st.caption("Chưa có.")
    with right:
        st.markdown("**Điều luật được trích nhiều nhất**")
        d = ans["top_chunk_id"].map(lambda x: cite_of(engine, x)).value_counts().head(10)
        d = d.rename_axis("Điều").reset_index(name="Số lượt")
        if len(d):
            st.altair_chart(bar(d, "Số lượt", "Điều", color="#D9A33A"), width="stretch")
        else:
            st.caption("Chưa có.")
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("**Lượt hỏi theo ngày**")
        day = (pd.to_datetime(df["time"]).dt.date.value_counts().sort_index()
               .rename_axis("Ngày").reset_index(name="Số lượt"))
        st.bar_chart(day, x="Ngày", y="Số lượt", color="#C9653F", height=260)
    with right:
        st.markdown("**Lý do từ chối**")
        reasons = {"out_of_scope": "Câu hỏi thuộc lĩnh vực khác (lọc trước truy hồi)",
                   "no_overlap": "Không có từ nào trong kho (tiếng nước ngoài, gõ bừa)",
                   "low_score": "Điểm thấp hơn ngưỡng τ (có thể ngoài phạm vi)",
                   "no_evidence": "Văn bản không có con số câu hỏi đòi"}
        rr = df[df["refused"] == 1]["reason"].map(reasons).value_counts()
        if len(rr):
            st.dataframe(rr.rename_axis("Lý do").reset_index(name="Số lượt"), hide_index=True, width="stretch")
        else:
            st.caption("Chưa có câu nào bị từ chối.")


# ======================================================================= giới thiệu
def tab_about(engine: AnswerEngine) -> None:
    st.markdown('<div class="sec-title">Giới thiệu hệ thống</div>', unsafe_allow_html=True)
    d = pipeline_desc(engine)
    steps = [("Tiền xử lý", "làm sạch, chuẩn hóa dấu"), ("Chia đoạn", "1 Điều / Khoản = 1 đoạn"),
             ("Lập chỉ mục", d["search"]), ("Truy hồi", d["first"] + (", top-20" if d["rerank"] else ""))]
    if d["rerank"]:
        steps.append(("Xếp hạng lại", "cross-encoder"))
    steps.append(("Trả lời", "trích nguyên văn hoặc từ chối"))
    flow = '<span class="arrow">→</span>'.join(f'<span class="step">{a}<small>{b}</small></span>' for a, b in steps)
    st.markdown(f'<div class="pipeline">{flow}</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1], gap="large")
    with c1:
        st.markdown("**Cấu hình đang chạy**")
        st.markdown(f"""
- Pipeline truy hồi: **{engine.retriever.name}** (đọc từ `configs/retrieval_selected.yaml`)
- Ngưỡng từ chối τ trên điểm top-1: **{engine.threshold:.4f}**, chọn trên tập validation
- Kiểm tra căn cứ con số (tiền, phạt, tuổi, thời hạn): **{'bật' if engine.evidence_check else 'tắt'}**
- Tách câu nhiều ý: **{'bật' if engine.cfg.get('multi_intent', {}).get('split', True) else 'tắt'}**
- Kho: **{len(engine.chunks)}** đoạn trích từ **{len({c['doc_id'] for c in engine.chunks})}** văn bản có điều khoản riêng
  (văn bản còn lại chỉ sửa đổi văn bản khác, đã hợp nhất vào bản gốc)
""")
    with c2:
        st.markdown("**Giới hạn**")
        st.markdown("""
- Chỉ trả lời trong phạm vi hộ tịch; câu về cư trú, đất đai, thuế… sẽ bị từ chối.
- Kho phản ánh quy định có hiệu lực tại 09/10/2026; văn bản mới hơn chưa có.
- Câu trả lời là trích dẫn để tham khảo, không thay cho hướng dẫn của cơ quan có thẩm quyền.
""")
    st.markdown("**Văn bản trong kho**")
    sl = source_list()[["doc_id", "title", "issuing_level", "effective_date", "status", "url"]]
    st.dataframe(sl.rename(columns={"doc_id": "Số hiệu", "title": "Tên văn bản", "issuing_level": "Cơ quan ban hành",
                                    "effective_date": "Hiệu lực từ", "status": "Tình trạng", "url": "Nguồn"}),
                 hide_index=True, width="stretch",
                 column_config={"Nguồn": st.column_config.LinkColumn(display_text="mở ↗")})


# ======================================================================= main
def main() -> None:
    header()
    engine = get_engine()
    # Chỉ chạy tab đang mở: trước đây mỗi lần hỏi cả 4 tab đều chạy lại (đọc SQLite, vẽ biểu đồ thống kê) dù
    # người dùng chỉ thấy 1 tab. key="nav" để nút "Hỏi lại" chuyển tab được (ask_again).
    tabs = st.tabs(TABS, key="nav", on_change="rerun") if LAZY_TABS else st.tabs(TABS)
    for tab, draw in zip(tabs, (tab_home, tab_history, tab_stats, tab_about)):
        if getattr(tab, "open", None) is False:     # None: Streamlit cũ không biết tab nào đang mở, vẽ hết như cũ
            continue
        with tab:
            draw(engine)
    footer(engine)


main()
