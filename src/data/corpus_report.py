"""Báo cáo chất lượng kho văn bản (D02 EDA, mục 5.3 hướng dẫn TV1).

Đầu vào : data/processed/units.jsonl, units_current.jsonl, chunks.jsonl, configs/chunking.yaml
Đầu ra  : results/data_quality/corpus_report.md     (báo cáo đọc được, nộp cho nhóm)
          results/data_quality/dieu_table.csv       (bảng Điều: số khoản, số từ, bị sửa/bãi bỏ)
          results/data_quality/chunk_tokens.png     (phân bố độ dài chunk)

Chạy từ gốc repo (sau parse_law → apply_amendments → chunk):
    python -m src.data.corpus_report
"""
import re
import json
from collections import Counter

import matplotlib
matplotlib.use("Agg")                     # vẽ ra file, không cần màn hình
import matplotlib.pyplot as plt
import pandas as pd
import yaml

from src.data.parse_law import ROOT, EXPECTED
from src.data.chunk import n_tokens

OUT = ROOT / "results/data_quality"


def read_jsonl(path):
    return [json.loads(l) for l in open(path, encoding="utf-8")]


def dieu_table(units_cur):
    """1 dòng / Điều: số khoản, số từ (sau tách từ), bị sửa bao nhiêu unit, có bị bãi bỏ không."""
    rows = {}
    for u in units_cur:
        if u["level"] == "phu_luc" or u["dieu"] is None:
            continue
        key = (u["doc_id"], u["dieu"])
        r = rows.setdefault(key, dict(doc_id=u["doc_id"], dieu=u["dieu"], dieu_ten=u["dieu_ten"],
                                      chuong=u["chuong"], so_khoan=0, text=[], so_unit_sua=0,
                                      so_unit_bai_bo=0))
        if u["level"] == "khoan":
            r["so_khoan"] += 1
        if u["text"]:
            r["text"].append(u["text"])
        r["so_unit_sua"] += bool(u.get("amended_by"))
        r["so_unit_bai_bo"] += u.get("status") == "repealed"
    df = pd.DataFrame(rows.values())
    df["so_tu"] = [n_tokens("\n".join(t)) if t else 0 for t in df["text"]]
    return df.drop(columns="text")


def dieu_numbering_ok(dieus):
    """Số Điều liên tục 1..n (bỏ qua Điều chèn kiểu 28a)."""
    nums = sorted(int(d) for d in dieus if d.isdigit())
    return nums == list(range(1, len(nums) + 1))


def md_table(df):
    """DataFrame → bảng Markdown (không cần thư viện tabulate)."""
    cols = list(df.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in r) + " |")
    return "\n".join(lines)


def main():
    units = read_jsonl(ROOT / "data/processed/units.jsonl")
    units_cur = read_jsonl(ROOT / "data/processed/units_current.jsonl")
    chunks = pd.DataFrame(read_jsonl(ROOT / "data/processed/chunks.jsonl"))
    cfg = yaml.safe_load(open(ROOT / "configs/chunking.yaml", encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)

    dt = dieu_table(units_cur)
    dt.to_csv(OUT / "dieu_table.csv", index=False, encoding="utf-8-sig")

    # 1. Số Điều mỗi văn bản (bản gốc, trước khi áp sửa đổi)
    goc = Counter(u["doc_id"] for u in units if u["level"] == "dieu")
    t1 = pd.DataFrame([dict(doc_id=d, so_dieu_tach=goc[d], so_dieu_ban_goc=n, khop=goc[d] == n,
                            danh_so_lien_tuc=dieu_numbering_ok({u["dieu"] for u in units
                                                                if u["doc_id"] == d and u["level"] == "dieu"}))
                       for d, n in EXPECTED.items()])

    # 2. Phân bổ Điều theo Chương (4 văn bản gốc)
    base = ["60.2014.QH13", "123.2015.ND-CP", "04.2020.TT-BTP", "87.2020.ND-CP"]
    t2 = (dt[dt.doc_id.isin(base)].groupby(["doc_id", "chuong"]).size()
          .unstack(fill_value=0).reindex(base))
    t2.columns = [f"Ch.{c}" for c in t2.columns]
    t2 = t2.reset_index()

    # 3. Độ dài mỗi Điều (số từ sau tách từ)
    t3 = (dt.groupby("doc_id")["so_tu"].describe(percentiles=[.5])[["min", "50%", "max"]]
          .astype(int).rename(columns={"50%": "median"}).reset_index())
    long_dieu = dt[dt.doc_id.isin(base) & (dt.so_tu > cfg["max_tokens"])].sort_values("so_tu", ascending=False)

    # 4. Rỗng, trùng
    empty = dt[dt.so_tu == 0]
    texts = Counter(u["text"] for u in units_cur if u["text"] and u.get("status") != "repealed")
    dup_units = {t: n for t, n in texts.items() if n > 1 and len(t) > 30}

    # 5. Hiệu lực: unit bị sửa / bãi bỏ
    t5 = pd.DataFrame([dict(doc_id=d,
                            unit_bi_sua=sum(bool(u.get("amended_by")) and u.get("status") != "repealed"
                                            for u in units_cur if u["doc_id"] == d),
                            unit_bai_bo=sum(u.get("status") == "repealed" for u in units_cur if u["doc_id"] == d))
                       for d in base])
    repealed = [f"{u['doc_id']} Điều {u['dieu']} khoản {u['khoan']}" for u in units_cur
                if u.get("status") == "repealed" and u["level"] == "khoan"]

    # 6. Chunk
    t6 = (chunks.groupby("doc_id").agg(so_chunk=("chunk_id", "size"), so_dieu=("dieu", "nunique"),
                                       token_min=("n_tokens", "min"), token_median=("n_tokens", "median"),
                                       token_max=("n_tokens", "max"))
          .reset_index())
    kind = chunks.chunk_id.map(lambda i: "phần của Khoản / Điều" if re.search(r"__P\d+$", i)
                               else ("1 Khoản" if re.search(r"__K[^_]+$", i) else "cả Điều"))
    t7 = kind.value_counts().rename_axis("kieu_chunk").reset_index(name="so_chunk")
    dup_chunks = chunks[chunks.display_text.duplicated(keep=False)]

    plt.figure(figsize=(7, 3.5))
    plt.hist(chunks.n_tokens, bins=30, color="#3b6ea5")
    plt.axvline(cfg["max_tokens"], color="#c0392b", linestyle="--", label=f"ngưỡng {cfg['max_tokens']}")
    plt.xlabel("Số từ / chunk (sau tách từ, gồm tiền tố)")
    plt.ylabel("Số chunk")
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT / "chunk_tokens.png", dpi=120)

    inc = "\n".join(f"- `{d}`: {r if r == 'all' else json.dumps(r, ensure_ascii=False)}"
                    for d, r in cfg["include"].items())

    md = f"""# Báo cáo chất lượng kho văn bản hộ tịch

Sinh tự động bởi `python -m src.data.corpus_report`. Đừng sửa tay, chạy lại script khi dữ liệu đổi.

**Tổng quan:** {len(goc)} văn bản, {sum(goc.values())} Điều, {len(units)} đơn vị (Điều/Khoản/Điểm/Phụ lục) ở bản gốc;
sau áp `amendments.yaml` còn {len(units_cur)} đơn vị; kho cuối có **{len(chunks)} chunk** từ {chunks.doc_id.nunique()} văn bản.

## 1. Số Điều

{md_table(t1)}

## 2. Phân bổ Điều theo Chương (văn bản gốc, sau sửa đổi)

{md_table(t2)}

## 3. Độ dài mỗi Điều (số từ sau tách từ underthesea)

{md_table(t3)}

Ở 4 văn bản gốc có {len(long_dieu)} Điều dài hơn ngưỡng {cfg['max_tokens']} từ nên bị tách theo Khoản ở bước chunk.
Dài nhất: {", ".join(f"{r.doc_id} Điều {r.dieu} ({r.so_tu})" for r in long_dieu.head(5).itertuples())}.

## 4. Rỗng và trùng nội dung

- Điều rỗng (không có chữ nào sau khi bỏ khoản bị bãi bỏ): {len(empty)}{"" if empty.empty else " → " + ", ".join(f"{r.doc_id} Điều {r.dieu}" for r in empty.itertuples())}
- Đơn vị trùng nội dung (dài hơn 30 ký tự, còn hiệu lực): {len(dup_units)}{"" if not dup_units else " → ví dụ: " + repr(next(iter(dup_units))[:80])}
- Chunk trùng nội dung: {len(dup_chunks)}

## 5. Hiệu lực (sau khi áp `data/raw/amendments.yaml`)

{md_table(t5)}

Khoản bị bãi bỏ (không vào kho, không đánh số lại): {"; ".join(repealed)}.

Văn bản ảnh hưởng hiệu lực nhưng không sửa câu chữ (NĐ 120/2025) được ghi ở cột `affected_by` của chunk.

## 6. Chunk

{md_table(t6)}

{md_table(t7)}

![Phân bố độ dài chunk](chunk_tokens.png)

## 7. Phần được chunk của từng văn bản (`configs/chunking.yaml`)

{inc}

Văn bản sửa đổi chỉ giữ phần có nội dung tự thân (chuyển tiếp, khai thác thông tin cư trú, thẩm quyền
theo chính quyền 2 cấp, Phụ lục I NĐ 120); phần "sửa Điều X thành..." đã nằm trong bản hợp nhất.
"""
    (OUT / "corpus_report.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
