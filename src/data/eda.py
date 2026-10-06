"""D02 (phần 2): EDA + báo cáo tiền xử lý.

Đọc docs.jsonl, chunks.jsonl và các log của bước parse, xuất:
    results/data_quality/corpus_report.md         báo cáo (đọc trên GitHub được)
    results/data_quality/figures/*.png            biểu đồ
    results/data_quality/near_duplicate_docs.csv  cặp thủ tục gần giống (cosine TF-IDF)
    results/data_quality/duplicate_chunk_texts.csv nội dung đoạn trùng giữa các thủ tục
    results/data_quality/issue_samples.csv        mọi vấn đề cần tra lại nguồn

Chạy:
    python -m src.data.eda
"""
import argparse
import csv
import hashlib
import json
import random
import re
from collections import Counter
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: E402
from sklearn.metrics.pairwise import cosine_similarity  # noqa: E402

from src.data.parse import FIELD_LABELS, FIELD_NAMES_VI, REQUIRED_FIELDS  # noqa: E402

DOCS = Path("data/interim/docs.jsonl")
CHUNKS = Path("data/processed/chunks.jsonl")
CHUNKS_META = Path("data/processed/chunks_meta.json")
MANIFEST = Path("data/raw/raw_manifest.csv")
QA = Path("results/data_quality")
FIG = QA / "figures"

# Bảng màu: 1 màu chính cho biểu đồ 1 chuỗi, thang xanh 1 màu cho heatmap.
BLUE = "#2a78d6"
ORANGE = "#eb6834"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e4e3df"
SURFACE = "#fcfcfb"
plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK_2, "xtick.color": INK_2, "ytick.color": INK_2,
    "axes.titlecolor": INK, "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.8, "axes.axisbelow": True, "font.size": 10, "font.family": "DejaVu Sans",
})

# Chỉ dùng để vẽ biểu đồ từ phổ biến, KHÔNG dùng để bỏ từ khi truy hồi.
DISPLAY_STOPWORDS = set("""và của các có được cho theo tại với trong là một những này đó khi
thì từ đến về do bởi hoặc người không phải nếu trường_hợp ngày đã sẽ để như trên số""".split())


def load_jsonl(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(FIG / name, dpi=150)
    plt.close(fig)
    return f"figures/{name}"


def short(s, n=38):
    return s if len(s) <= n else s[: n - 1] + "…"


def n_words(text):
    return len(re.findall(r"\w+", text))


# ---------------------------------------------------------------- biểu đồ
def fig_field_coverage(docs):
    n = len(docs)
    pct = [100 * sum(f in d["fields"] for d in docs) / n for f in FIELD_LABELS]
    labels = [FIELD_NAMES_VI[f] + (" *" if f in REQUIRED_FIELDS else "") for f in FIELD_LABELS]
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    y = np.arange(len(labels))[::-1]
    colors = [ORANGE if p < 100 and f in REQUIRED_FIELDS else BLUE for p, f in zip(pct, FIELD_LABELS)]
    ax.barh(y, pct, color=colors, height=0.6)
    for yi, p in zip(y, pct):
        ax.text(min(p, 100) + 1, yi, f"{p:.0f}%", va="center", color=INK_2, fontsize=9)
    ax.set_yticks(y, labels)
    ax.set_xlim(0, 112)
    ax.set_xlabel("% thủ tục có mục này\n(* mục bắt buộc; màu cam = mục bắt buộc còn thiếu ở một số thủ tục)")
    ax.set_title("Độ phủ các mục sau khi trích xuất")
    ax.grid(axis="y", visible=False)
    return save(fig, "01_field_coverage.png")


def fig_field_length(docs):
    data, labels = [], []
    for f in FIELD_LABELS:
        vals = [n_words(d["fields"][f]) for d in docs if f in d["fields"]]
        if vals:
            data.append(vals)
            labels.append(FIELD_NAMES_VI[f])
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    mpl_ver = tuple(int(x) for x in matplotlib.__version__.split(".")[:2])
    horiz = {"orientation": "horizontal"} if mpl_ver >= (3, 10) else {"vert": False}
    bp = ax.boxplot(data[::-1], **horiz, widths=0.5, patch_artist=True,
                    medianprops={"color": INK, "linewidth": 1.5},
                    whiskerprops={"color": INK_2}, capprops={"color": INK_2},
                    flierprops={"marker": "o", "markersize": 4, "markerfacecolor": BLUE, "markeredgecolor": SURFACE})
    for b in bp["boxes"]:
        b.set(facecolor="#b7d3f6", edgecolor=BLUE)
    ax.set_yticks(range(1, len(labels) + 1), labels[::-1])
    ax.set_xscale("log")
    ax.set_xlabel("Số âm tiết trong mục (thang log)")
    ax.set_title("Độ dài từng mục")
    ax.grid(axis="y", visible=False)
    return save(fig, "02_field_length.png")


def fig_chunk_hist(chunks, max_tokens):
    vals = [c["n_tokens"] for c in chunks]
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    ax.hist(vals, bins=min(40, max(10, len(vals) // 5)), color=BLUE, edgecolor=SURFACE, linewidth=1)
    ax.axvline(max_tokens, color=ORANGE, linewidth=2, linestyle="--")
    ax.text(max_tokens, ax.get_ylim()[1] * 0.92, f" ngưỡng {max_tokens}", color=INK_2, fontsize=9)
    med = float(np.median(vals))
    ax.axvline(med, color=INK_2, linewidth=1)
    ax.text(med, ax.get_ylim()[1] * 0.80, f" trung vị {med:.0f}", color=INK_2, fontsize=9)
    ax.set_xlabel("Số từ sau tách từ (gồm tiền tố)")
    ax.set_ylabel("Số chunk")
    ax.set_title("Phân bố độ dài chunk")
    ax.grid(axis="x", visible=False)
    return save(fig, "03_chunk_length.png")


def fig_chunks_per_doc(chunks, docs):
    cnt = Counter(c["doc_id"] for c in chunks)
    title = {d["doc_id"]: d["title"] for d in docs}
    items = sorted(cnt.items(), key=lambda kv: kv[1])
    h = max(3.0, 0.24 * len(items) + 1)
    fig, ax = plt.subplots(figsize=(7.5, h))
    y = np.arange(len(items))
    ax.barh(y, [v for _, v in items], color=BLUE, height=0.65)
    ax.set_yticks(y, [short(title.get(k, k)) for k, _ in items], fontsize=8)
    ax.set_xlabel("Số chunk")
    ax.set_title("Số chunk trên mỗi thủ tục")
    ax.grid(axis="y", visible=False)
    return save(fig, "04_chunks_per_doc.png")


def fig_similarity(docs, sim):
    n = len(docs)
    size = min(14, max(6, 0.25 * n + 3))
    fig, ax = plt.subplots(figsize=(size + 2.5, size))
    m = sim.copy()
    np.fill_diagonal(m, np.nan)
    im = ax.imshow(m, cmap="Blues", vmin=0, vmax=1)
    ticks = [d["doc_id"] for d in docs]
    fs = 7 if n > 20 else 8
    ax.set_xticks(range(n), ticks, rotation=90, fontsize=fs)
    ax.set_yticks(range(n), [short(d["title"], 30) for d in docs], fontsize=fs)
    ax.grid(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.04)
    cb.set_label("cosine TF-IDF", color=INK_2)
    ax.set_title("Độ giống nhau giữa các thủ tục")
    return save(fig, "05_doc_similarity.png")


def fig_top_terms(chunks, k=20):
    cnt = Counter()
    for c in chunks:
        for t in c["text_seg"].lower().split():
            if re.fullmatch(r"[\w_]+", t) and not t.isdigit() and len(t) > 1 and t not in DISPLAY_STOPWORDS:
                cnt[t] += 1
    top = cnt.most_common(k)[::-1]
    fig, ax = plt.subplots(figsize=(7.5, 5))
    y = np.arange(len(top))
    ax.barh(y, [v for _, v in top], color=BLUE, height=0.65)
    ax.set_yticks(y, [t.replace("_", " ") for t, _ in top])
    ax.set_xlabel("Số lần xuất hiện")
    ax.set_title(f"{k} từ xuất hiện nhiều nhất (sau tách từ, tính cả tiền tố)")
    ax.grid(axis="y", visible=False)
    return save(fig, "06_top_terms.png"), top[::-1]


def fig_cleaning(rules, raw_chars, clean_chars):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 3.6), gridspec_kw={"width_ratios": [2, 1]})
    if rules:
        r = rules[::-1]
        y = np.arange(len(r))
        a1.barh(y, [x["hits"] for x in r], color=BLUE, height=0.6)
        a1.set_yticks(y, [x["rule"] for x in r], fontsize=8)
    a1.set_xlabel("Số lần tác động")
    a1.set_title("Rule làm sạch")
    a1.grid(axis="y", visible=False)
    a2.bar([0, 1], [raw_chars, clean_chars], color=[GRID, BLUE], width=0.6)
    a2.set_xticks([0, 1], ["Trước", "Sau"])
    for x, v in enumerate([raw_chars, clean_chars]):
        a2.text(x, v, f"{v:,}".replace(",", "."), ha="center", va="bottom", fontsize=9, color=INK_2)
    a2.set_title("Tổng ký tự")
    a2.grid(axis="x", visible=False)
    return save(fig, "07_cleaning.png")


# ---------------------------------------------------------------- báo cáo
def md_table(df):
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "\\|").replace("\n", " ") for c in cols) + " |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--near-dup", type=float, default=0.8, help="ngưỡng cosine coi là gần giống")
    ap.add_argument("--samples", type=int, default=10, help="số chunk ngẫu nhiên in ra để đọc tay")
    args = ap.parse_args()

    docs = sorted(load_jsonl(DOCS), key=lambda d: d["doc_id"])
    chunks = load_jsonl(CHUNKS)
    cmeta = json.loads(CHUNKS_META.read_text(encoding="utf-8")) if CHUNKS_META.exists() else {}
    max_tokens = int(cmeta.get("chunking", {}).get("max_tokens", 200))
    rules = list(csv.DictReader(open(QA / "cleaning_log.csv", encoding="utf-8")))
    for r in rules:
        r["hits"] = int(r["hits"])
    parse_issues = list(csv.DictReader(open(QA / "parse_issues.csv", encoding="utf-8")))
    manifest = list(csv.DictReader(open(MANIFEST, encoding="utf-8"))) if MANIFEST.exists() else []

    issues = [{"doc_id": r["doc_id"], "stage": "parse", "issue": r["issue"]} for r in parse_issues]

    # Trùng y hệt và gần giống
    full = [" ".join(d["fields"].values()) for d in docs]
    hashes = Counter(hashlib.sha256(t.encode()).hexdigest() for t in full)
    exact_dup = sum(v - 1 for v in hashes.values() if v > 1)
    sim = cosine_similarity(TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True).fit_transform(full)) \
        if len(docs) > 1 else np.ones((1, 1))
    pairs = []
    for i in range(len(docs)):
        for j in range(i + 1, len(docs)):
            if sim[i, j] >= args.near_dup:
                pairs.append({"doc_id_a": docs[i]["doc_id"], "title_a": docs[i]["title"],
                              "doc_id_b": docs[j]["doc_id"], "title_b": docs[j]["title"],
                              "cosine": round(float(sim[i, j]), 3)})
    pairs.sort(key=lambda p: -p["cosine"])
    pd.DataFrame(pairs, columns=["doc_id_a", "title_a", "doc_id_b", "title_b", "cosine"]).to_csv(
        QA / "near_duplicate_docs.csv", index=False, encoding="utf-8")

    # Đoạn có nội dung y hệt ở nhiều thủ tục (vd "Lệ phí: Miễn") → tiền tố là thứ phân biệt chúng
    by_text = {}
    for c in chunks:
        by_text.setdefault(c["display_text"].strip().lower(), []).append(c)
    dup_texts = [{"display_text": cs[0]["display_text"][:120], "n": len(cs), "chunk_ids": " ".join(c["chunk_id"] for c in cs)}
                 for cs in by_text.values() if len({c["doc_id"] for c in cs}) > 1]
    dup_texts.sort(key=lambda r: -r["n"])
    pd.DataFrame(dup_texts, columns=["display_text", "n", "chunk_ids"]).to_csv(
        QA / "duplicate_chunk_texts.csv", index=False, encoding="utf-8")

    short_chunks = [c for c in chunks if n_words(c["display_text"]) < 3]
    for c in short_chunks:
        issues.append({"doc_id": c["doc_id"], "stage": "chunk", "issue": f"chunk quá ngắn: {c['chunk_id']}"})
    for d in docs:
        if not d["url"] or not d["accessed_at"]:
            issues.append({"doc_id": d["doc_id"], "stage": "source", "issue": "thiếu url hoặc accessed_at"})
    pd.DataFrame(issues, columns=["doc_id", "stage", "issue"]).to_csv(QA / "issue_samples.csv", index=False, encoding="utf-8")

    raw_chars = sum(sum(d["stats"]["raw_chars"].values()) for d in docs)
    clean_chars = sum(sum(d["stats"]["clean_chars"].values()) for d in docs)

    figs = {
        "coverage": fig_field_coverage(docs),
        "field_len": fig_field_length(docs),
        "chunk_len": fig_chunk_hist(chunks, max_tokens),
        "per_doc": fig_chunks_per_doc(chunks, docs),
        "sim": fig_similarity(docs, sim),
        "cleaning": fig_cleaning(rules, raw_chars, clean_chars),
    }
    figs["terms"], _ = fig_top_terms(chunks)

    # Bảng theo mục
    rows = []
    for f in FIELD_LABELS:
        lens = [n_words(d["fields"][f]) for d in docs if f in d["fields"]]
        fc = [c for c in chunks if c["field"] == f]
        rows.append({
            "Mục": FIELD_NAMES_VI[f] + (" (bắt buộc)" if f in REQUIRED_FIELDS else ""),
            "Số thủ tục có": f"{len(lens)}/{len(docs)}",
            "Âm tiết min / trung vị / max": f"{min(lens)} / {int(np.median(lens))} / {max(lens)}" if lens else "-",
            "Số chunk": len(fc),
            "Bị cắt nhỏ (>1 chunk)": len({c["doc_id"] for c in fc if c["n_parts"] > 1}),
        })
    field_df = pd.DataFrame(rows)

    tok = np.array([c["n_tokens"] for c in chunks])
    dates = sorted(d["accessed_at"][:10] for d in docs if d["accessed_at"])
    missing_req = sum(1 for d in docs for f in REQUIRED_FIELDS if f not in d["fields"])

    def status(ok, warn=False):
        return "Đạt" if ok else ("Cần xem" if warn else "Chưa đạt")

    checks = pd.DataFrame([
        {"Kiểm tra": "doc_id duy nhất", "Kết quả": f"{len(docs)} thủ tục, {len(docs) - len({d['doc_id'] for d in docs})} trùng",
         "Trạng thái": status(len(docs) == len({d['doc_id'] for d in docs}))},
        {"Kiểm tra": "Đủ mục bắt buộc (hồ sơ, thời hạn, cơ quan)", "Kết quả": f"thiếu {missing_req} lượt",
         "Trạng thái": status(missing_req == 0)},
        {"Kiểm tra": "Lỗi khi trích xuất", "Kết quả": f"{len(parse_issues)} vấn đề (parse_issues.csv)",
         "Trạng thái": status(not parse_issues, warn=True)},
        {"Kiểm tra": "Thủ tục trùng y hệt", "Kết quả": str(exact_dup), "Trạng thái": status(exact_dup == 0)},
        {"Kiểm tra": f"Cặp gần giống (cosine ≥ {args.near_dup})", "Kết quả": f"{len(pairs)} cặp (giữ cả hai, dùng cho phân tích)",
         "Trạng thái": "Ghi nhận"},
        {"Kiểm tra": "chunk_id duy nhất, không rỗng, phủ mọi thủ tục, ≤ ngưỡng",
         "Kết quả": "; ".join(cmeta.get("check_errors", [])) or "không lỗi",
         "Trạng thái": status(not cmeta.get("check_errors"))},
        {"Kiểm tra": "Chunk quá ngắn (< 3 từ nội dung)", "Kết quả": str(len(short_chunks)),
         "Trạng thái": status(not short_chunks, warn=True)},
        {"Kiểm tra": "Có url và ngày tải", "Kết quả": f"thiếu {sum(1 for d in docs if not d['url'] or not d['accessed_at'])}",
         "Trạng thái": status(all(d["url"] and d["accessed_at"] for d in docs))},
        {"Kiểm tra": "Căn cứ pháp lý còn hiệu lực", "Kết quả": "kiểm tra tay trên vbpl.vn / thuvienphapluat",
         "Trạng thái": "Làm tay"},
    ])

    rnd = random.Random(42)
    samples = rnd.sample(chunks, min(args.samples, len(chunks)))

    demo = any(d["url"].startswith(("http://127.0.0.1", "http://localhost", "file:")) for d in docs)
    L = []
    if demo:
        L += ["> **DỮ LIỆU GIẢ ĐỂ TEST PIPELINE.** Báo cáo này chạy trên trang mẫu tự tạo, "
              "không phải dữ liệu thật từ Cổng Dịch vụ công. Không dùng số liệu này trong báo cáo nhóm.", ""]
    L += [
        "# Báo cáo tiền xử lý kho tài liệu (D02–D03)", "",
        f"Tạo tự động bởi `python -m src.data.eda` ngày {date.today().isoformat()}.", "",
        "## 1. Tổng quan", "",
        md_table(pd.DataFrame([
            {"Chỉ số": "Số thủ tục", "Giá trị": len(docs)},
            {"Chỉ số": "Số lần tải trong raw_manifest", "Giá trị": len(manifest)},
            {"Chỉ số": "Ngày tải", "Giá trị": f"{dates[0]} → {dates[-1]}" if dates else "-"},
            {"Chỉ số": "Số chunk", "Giá trị": len(chunks)},
            {"Chỉ số": "Chunk / thủ tục (trung bình)", "Giá trị": f"{len(chunks) / max(1, len(docs)):.1f}"},
            {"Chỉ số": "Độ dài chunk min / trung vị / p95 / max (từ)",
             "Giá trị": f"{tok.min()} / {int(np.median(tok))} / {int(np.percentile(tok, 95))} / {tok.max()}" if len(tok) else "-"},
            {"Chỉ số": "Ngưỡng chunk", "Giá trị": f"{max_tokens} từ, chồng lấn {cmeta.get('chunking', {}).get('overlap_sentences', '?')} câu"},
            {"Chỉ số": "Công cụ tách từ", "Giá trị": cmeta.get("segmenter", "?")},
            {"Chỉ số": "sha256 chunks.jsonl", "Giá trị": f"`{cmeta.get('chunks_sha256', '')[:16]}…`"},
        ])), "",
        "## 2. Kiểm tra chất lượng", "",
        md_table(checks), "",
        "Chi tiết từng vấn đề: `issue_samples.csv`.", "",
        "## 3. Làm sạch", "",
        f"Tổng ký tự trong các mục: {raw_chars:,} → {clean_chars:,} "
        f"(bỏ {100 * (1 - clean_chars / raw_chars):.1f}%).".replace(",", ".") if raw_chars else "",
        "Không lowercase, không bỏ dấu, không bỏ stopword ở bước này (để dành cho cấu hình từng mô hình).", "",
        md_table(pd.DataFrame(rules)) if rules else "_Không rule nào tác động._", "",
        f"![Làm sạch]({figs['cleaning']})", "",
        "## 4. Các mục của thủ tục", "",
        md_table(field_df), "",
        f"![Độ phủ]({figs['coverage']})", "",
        f"![Độ dài mục]({figs['field_len']})", "",
        "## 5. Chunk", "",
        f"![Độ dài chunk]({figs['chunk_len']})", "",
        f"![Chunk mỗi thủ tục]({figs['per_doc']})", "",
        f"Có {len(dup_texts)} nội dung đoạn xuất hiện y hệt ở nhiều thủ tục (`duplicate_chunk_texts.csv`). "
        "Tiền tố \"tên thủ tục | mục\" là thứ duy nhất phân biệt chúng, nên đừng bỏ tiền tố khi index.", "",
        "## 6. Thủ tục gần giống nhau", "",
        "Dùng cho phân tích bắt buộc \"nhiều tài liệu có nội dung gần giống\" và để TV2 viết câu hỏi loại near-duplicate.", "",
        md_table(pd.DataFrame(pairs[:15])[["title_a", "title_b", "cosine"]]) if pairs else "_Không có cặp nào vượt ngưỡng._", "",
        f"![Độ giống nhau]({figs['sim']})", "",
        "## 7. Từ vựng", "",
        f"![Từ phổ biến]({figs['terms']})", "",
        f"## 8. {len(samples)} chunk ngẫu nhiên để đọc tay (seed 42)", "",
        "Đọc từng đoạn: có bị cắt giữa câu không, có rác giao diện không, tiền tố có đúng thủ tục không.", "",
    ]
    for c in samples:
        L += [f"**{c['chunk_id']}** ({c['n_tokens']} từ)", "", "> " + c["chunk_text"].replace("\n", "\n> "), ""]
    L += ["## 9. Nhận xét của TV1", "", "_Điền tay: vấn đề phát hiện được, cách xử lý, việc còn tồn._", ""]
    (QA / "corpus_report.md").write_text("\n".join(L), encoding="utf-8")
    print(f"Báo cáo → {QA / 'corpus_report.md'}; {len(figs)} biểu đồ → {FIG}/")


if __name__ == "__main__":
    main()
