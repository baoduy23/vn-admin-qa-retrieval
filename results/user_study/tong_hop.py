"""Tổng hợp phiếu đánh giá người dùng ra ket_qua.md.

Chạy từ gốc repo: python results/user_study/tong_hop.py
Đọc phieu_khao_sat.csv (phiếu Google Form, đã bỏ cột thời gian) và nhom_cham.csv (nhóm chấm lại từng câu).
"""
import csv
import statistics as st
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
EXCLUDE: set[str] = set()  # mã phiếu không tính (vd phiếu điền thử), để trống là tính hết
MOI_CAU = 7        # mỗi câu hỏi trên phiếu có 7 cột


def sus(r):
    v = [int(r[f"SUS [{i}. " + ten + "]"]) for i, ten in SUS_ROWS]
    return 2.5 * sum((x - 1) if i % 2 == 0 else (5 - x) for i, x in enumerate(v))


def diem(s):
    return int(s[0]) if s[:1].isdigit() else None


def tom_tat(vals):
    vals = [v for v in vals if v is not None]
    return f"{st.median(vals):g} / {st.mean(vals):.2f} (n={len(vals)})" if vals else "—"


phieu = [r for r in csv.DictReader(open(HERE / "phieu_khao_sat.csv", encoding="utf-8"))
         if r["1. Mã người tham gia (do nhóm đưa, vd P01)"] not in EXCLUDE]
cot = list(phieu[0].keys())
SUS_ROWS = [(int(c[5:].split(".")[0]), c[5:].split(". ", 1)[1][:-1]) for c in cot if c.startswith("SUS [")]

cau = []
for r in phieu:
    for i in range(1, 6):
        q = r[f"Câu {i}: dán lại đúng câu bạn đã hỏi trên app"].strip()
        if q:
            g = {k.split(": ", 1)[1]: v for k, v in r.items() if k.startswith(f"Câu {i}: ")}
            cau.append(g)

cham = [r for r in csv.DictReader(open(HERE / "nhom_cham.csv", encoding="utf-8")) if r["participant"] not in EXCLUDE]
tra_loi = [g for g in cau if g["app đã làm gì?"] == "Trả lời"]
s = [sus(r) for r in phieu]

out = ["# Kết quả đánh giá người dùng", "",
       f"Số người: {len(phieu)}" + (f" (loại {', '.join(sorted(EXCLUDE))})" if EXCLUDE else "") + f"; số câu hỏi: {len(cau)}.", "",
       "## Người dùng tự chấm", "",
       "| Chỉ số | Kết quả |", "|---|---|"]
act = Counter(g["app đã làm gì?"] for g in cau)
out.append("| App làm gì | " + "; ".join(f"{k}: {v}" for k, v in act.most_common()) + " |")
dung = Counter(g["câu trả lời có đúng ý bạn hỏi không?"] for g in tra_loi)
out.append(f"| Đúng ý (trên {len(tra_loi)} câu app trả lời) | " + "; ".join(f"{k}: {v}" for k, v in dung.most_common()) + " |")
for ten, k in [("Nguồn liên quan", "nguồn trích dẫn (điều, khoản, văn bản) có liên quan đến câu hỏi không?"),
               ("Dễ hiểu", "câu trả lời dễ hiểu không?"), ("Hữu ích", "câu trả lời giúp ích cho bạn đến mức nào?")]:
    out.append(f"| {ten}, câu app trả lời (trung vị / TB, thang 1–5) | {tom_tat([diem(g[k]) for g in tra_loi])} |")
out.append(f"| SUS trung bình (min–max) | {st.mean(s):.1f} ({min(s):g}–{max(s):g}) |")
out.append("| SUS từng người | " + ", ".join(f"{r['1. Mã người tham gia (do nhóm đưa, vd P01)']} {x:g}" for r, x in zip(phieu, s)) + " |")

out += ["", "## Nhóm chấm lại", "", "| Phạm vi | Số câu | App trả lời | App từ chối | Quyết định đúng |", "|---|---|---|---|---|"]
for pv in ["in_scope", "unsupported", "out_of_scope"]:
    g = [r for r in cham if r["pham_vi"] == pv]
    if g:
        out.append(f"| {pv} | {len(g)} | {sum(r['app_lam'] == 'tra_loi' for r in g)} | "
                   f"{sum(r['app_lam'] == 'tu_choi' for r in g)} | {sum(r['quyet_dinh_dung'] == 'Đúng' for r in g)}/{len(g)} |")
sai = [r for r in cham if r["quyet_dinh_dung"] == "Sai"]
out += ["", "Câu app quyết định sai:", ""] + [f"- {r['participant']}: \"{r['question']}\". {r['ghi_chu']}" for r in sai]
nguon = [r["nguon_top1_dung"] for r in cham if r["app_lam"] == "tra_loi"]
out += ["", f"Nguồn top-1 đã chấm: {sum(bool(x) for x in nguon)}/{len(nguon)} câu app trả lời "
        f"({Counter(x for x in nguon if x)})." if any(nguon) else
        f"Nguồn top-1 chưa chấm ({len(nguon)} câu app trả lời).", ""]

(HERE / "ket_qua.md").write_text("\n".join(out), encoding="utf-8")
print("\n".join(out))
