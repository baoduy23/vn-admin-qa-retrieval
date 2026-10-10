"""Tách văn bản luật (.docx trong data/interim) thành Chương → Mục → Điều → Khoản → Điểm.
 
Đầu vào : data/raw/source_list.csv (cột doc_id) + data/interim/<doc_id>.docx
Đầu ra  : data/processed/units.jsonl, mỗi dòng 1 đơn vị (Điều / Khoản / Điểm / Phụ lục)
 
Chạy từ gốc repo:  python -m src.data.parse_law
"""
import re
import json
from collections import Counter
from pathlib import Path

import docx
import pandas as pd

from src.data.text_utils import clean_lines, CleanLog

ROOT = Path(__file__).resolve().parents[2]


# Regex nhận diện cấp
RE_CHUONG = re.compile(r"^Chương\s+([IVXLC]+)\b\.?\s*(.*)$", re.I)
RE_MUC    = re.compile(r"^Mục\s+(\d+)\b\.?\s*(.*)$", re.I)
RE_DIEU   = re.compile(r"^Điều\s+(\d+[a-zđ]?)\s*\.\s*(.*)$")
RE_KHOAN  = re.compile(r"^(\d+)\.\s+(.*)$")
RE_DIEM   = re.compile(r"^([a-zđ])\)\s+(.*)$")
RE_PHULUC = re.compile(r"^PHỤ LỤC\b\s*([IVXLC]*)\s*(.*)$", re.I)
RE_PL_MUC = re.compile(r"^([IVXLC]+)\.\s+(.*)$")  # I II trong phu luc


def read_docx_lines(path):
    """Lấy text các đoạn văn theo thứ tự, BỎ bảng (bảng = header quốc hiệu + chữ ký)."""
    d = docx.Document(path)
    return [p.text for p in d.paragraphs]


RE_QUOTE_END = re.compile(r"”\s*[.;,]?$")  #dòng kết thúc đoạn trích: ..." ..." ...";


def update_in_quote(in_quote, line):
    """Đang trong đoạn trích hay không, SAU dòng này.
    Dùng cờ bật/tắt chứ không đếm ngoặc, vì văn bản gốc hay lệch ngoặc
    (mở 2 lần đóng 1 lần): cứ dòng nào kết thúc bằng ” là coi như hết trích"""
    if RE_QUOTE_END.search(line):
        return False
    if "“" in line and line.rfind("“") > line.rfind("”"):
        return True
    return in_quote


# Parser
def parse_doc(path, log=None):
    lines = clean_lines(read_docx_lines(path), log)
    units = []                       # mỗi phần tử = 1 đơn vị lá (Điều / Khoản / Điểm / Phụ lục)
    ctx = dict(chuong=None, chuong_ten=None, muc=None, muc_ten=None,
               dieu=None, dieu_ten=None, khoan=None, diem=None, phu_luc=None)
    cur = None                       # đơn vị đang gom text
    in_quote = False                 # True = đang ở đoạn trích nguyên văn của văn bản khác
    started = False                  # bỏ phần mở đầu (quốc hiệu, tên VB, Căn cứ...)
    expect_title = None              # dòng sau "Chương I" / "PHỤ LỤC" là tên
 
    def new_unit(level):
        nonlocal cur
        cur = dict(level=level, **{k: ctx[k] for k in ctx}, lines=[])
        units.append(cur)
 
    for s in lines:
        quoted = in_quote or s.startswith("“")
        in_quote = update_in_quote(in_quote, s)
 
        if quoted:                            # đoạn trích: KHÔNG tách cấp, gom vào đơn vị hiện tại
            if cur is not None:
                cur["lines"].append(s)
            continue
 
        if expect_title:                      # tên Chương / Phụ lục nằm ở dòng kế
            if s.isupper():
                ctx[expect_title] = s
                if cur is not None and cur["level"] == "phu_luc":
                    cur["phu_luc_ten"] = s
                expect_title = None
                continue
            expect_title = None
 
        if m := RE_PHULUC.match(s):
            started = True
            ctx.update(phu_luc=("PHỤ LỤC " + m.group(1)).strip(), dieu=None, dieu_ten=None,
                       khoan=None, diem=None, chuong=None, chuong_ten=None, muc=None, muc_ten=None)
            new_unit("phu_luc")
            cur["lines"].append(s)
            expect_title = "phu_luc_ten" if not m.group(2) else None
            continue
 
        if ctx["phu_luc"]:                    # trong Phụ lục: tách theo I. II. III.
            if m := RE_PL_MUC.match(s):
                ctx.update(khoan=m.group(1))
                new_unit("phu_luc")
                cur["muc_pl_ten"] = m.group(2)
            if cur is not None:
                cur["lines"].append(s)
            continue
 
        if m := RE_CHUONG.match(s):
            started = True
            ctx.update(chuong=m.group(1).upper(), chuong_ten=m.group(2) or None,
                       muc=None, muc_ten=None)
            expect_title = None if m.group(2) else "chuong_ten"
            continue
        if started and (m := RE_MUC.match(s)):
            ctx.update(muc=m.group(1), muc_ten=m.group(2) or None)
            continue
        if m := RE_DIEU.match(s):
            started = True
            ctx.update(dieu=m.group(1), dieu_ten=m.group(2), khoan=None, diem=None)
            new_unit("dieu")
            continue
        if not started or ctx["dieu"] is None:
            continue                          # phần mở đầu
        if m := RE_KHOAN.match(s):
            ctx.update(khoan=m.group(1), diem=None)
            new_unit("khoan")
            cur["lines"].append(s)
            continue
        if ctx["khoan"] and (m := RE_DIEM.match(s)):
            ctx.update(diem=m.group(1))
            new_unit("diem")
            cur["lines"].append(s)
            continue
        cur["lines"].append(s)                # dòng thường: nối vào đơn vị đang mở
 
    # bỏ đơn vị rỗng (vd. Điều chỉ có tiêu đề, nội dung nằm ở các Khoản), ghép text
    out = []
    for u in units:
        u["text"] = "\n".join(u.pop("lines"))
        if u["text"] or u["level"] == "dieu":
            out.append(u)
    return out
 
 
#3 chay ca kho theo source list csv
EXPECTED = {"60.2014.QH13": 77, "123.2015.ND-CP": 45, "87.2020.ND-CP": 25,
            "04.2020.TT-BTP": 39, "104.2022.ND-CP": 15, "09.2022.TT-BTP": 4,
            "04.2024.TT-BTP": 4, "07.2025.ND-CP": 5, "120.2025.ND-CP": 24,
            "18.2026.ND-CP": 18}
 
 
def main():
    src = pd.read_csv(ROOT / "data/raw/source_list.csv", dtype=str)
    log, rows, summary = CleanLog(), [], []
    for doc_id in src["doc_id"]:
        units = parse_doc(ROOT / f"data/interim/{doc_id}.docx", log)
        for u in units:
            u["doc_id"] = doc_id
        rows += units
        dieus = [u["dieu"] for u in units if u["level"] == "dieu"]
        summary.append(dict(doc_id=doc_id, so_dieu=len(dieus), dung=EXPECTED.get(doc_id),
                            so_don_vi=len(units),
                            phu_luc=sum(u["level"] == "phu_luc" for u in units),
                            dieu_trung=[k for k, v in Counter(dieus).items() if v > 1]))
    summary = pd.DataFrame(summary)
    print(summary.to_string(index=False))
    bad = summary[summary.so_dieu != summary.dung]
    assert bad.empty, f"Lệch số Điều:\n{bad}"
 
    out = ROOT / "data/processed/units.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Ghi {len(rows)} đơn vị → {out}")
    print(pd.DataFrame(log.as_rows()))
 
 
if __name__ == "__main__":
    main()

