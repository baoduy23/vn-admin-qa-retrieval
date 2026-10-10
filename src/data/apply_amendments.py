"""Áp các sửa đổi trong data/raw/amendments.yaml lên units.jsonl → bản "đang có hiệu lực".

Đầu vào : data/processed/units.jsonl (từ parse_law) + data/raw/amendments.yaml
Đầu ra  : data/processed/units_current.jsonl  (thêm 3 cột: status, amended_by, effective_from)
          data/processed/amendments_log.csv   (mỗi op 1 dòng: áp được không, đụng mấy unit)

5 loại op (giải thích ở đầu amendments.yaml): replace, insert, repeal, remove_phrase, rename.
Op áp theo thứ tự ngày hiệu lực; op nào lỗi thì ghi vào log và dừng, không ghi units_current.
Unit bị bãi bỏ vẫn giữ trong file (status=repealed), bước chunk mới bỏ ra.

Chạy từ gốc repo:  python -m src.data.apply_amendments
"""
import re
import json
import unicodedata

import pandas as pd
import yaml

from src.data.parse_law import ROOT, RE_MUC, RE_DIEU, RE_KHOAN, RE_DIEM, RE_QUOTE_END


# ---------- 1. Đọc dữ liệu ----------
def load_units(path):
    """Đọc units.jsonl của parse_law, thêm 3 cột theo dõi hiệu lực."""
    units = [json.loads(l) for l in open(path, encoding="utf-8")]
    for u in units:
        u["status"] = "active"          # active | repealed
        u["amended_by"] = []            # danh sách id op đã đụng vào unit này
        u["effective_from"] = None      # ngày hiệu lực của lần sửa gần nhất (None = bản gốc)
    return units


def load_ops(path):
    """Đọc amendments.yaml, sắp theo ngày hiệu lực (07/2025 phải áp trước 18/2026)."""
    ops = yaml.safe_load(open(path, encoding="utf-8"))
    # sort theo ngày hiệu lực; sorted() giữ nguyên thứ tự trong file khi trùng ngày
    return sorted(ops, key=lambda o: str(o["effective_date"]))


# ---------- 2. Tìm unit ----------
def same(u, doc, dieu, khoan=None, diem=None):
    """Unit u có đúng địa chỉ (văn bản, Điều, Khoản, Điểm) không. khoan/diem = None nghĩa là cấp Điều/Khoản."""
    return (u["doc_id"] == doc and u["dieu"] == dieu
            and u["khoan"] == khoan and u["diem"] == diem)


def find_one(units, ref):
    """Vị trí đúng 1 unit (doc, dieu, khoan, diem). Không có → None."""
    hits = [i for i, u in enumerate(units)
            if same(u, ref["doc"], ref["dieu"], ref.get("khoan"), ref.get("diem"))]
    return hits[0] if hits else None


def span(units, doc, dieu, khoan=None):
    """Các vị trí liền nhau thuộc 1 Điều (hoặc 1 Khoản và các Điểm con của nó)."""
    idx = [i for i, u in enumerate(units)
           if u["doc_id"] == doc and u["dieu"] == dieu
           and (khoan is None or u["khoan"] == khoan)]
    return idx


# ---------- 3. Lấy đoạn trích “...” trong unit nguồn ----------
def quoted_lines(text):
    """Các dòng nằm trong ngoặc kép, đã bỏ “ ở đầu và ” ở cuối."""
    out, inside = [], False
    for line in text.split("\n"):
        s = line.strip()
        if not inside and s.startswith("“"):
            inside = True
        if inside:
            end = bool(RE_QUOTE_END.search(s))
            s = s.lstrip("“")
            s = re.sub(r"”\s*[.;,]?$", "", s).strip()
            if s:
                out.append(s)
            if end:
                inside = False
    return out


def pick_khoan(lines, khoan):
    """Đoạn trích có nhiều khoản ("1. ..." "2. ...") → chỉ lấy khoản trùng target.
    Đoạn trích chỉ có 1 khoản hoặc không đánh số → trả nguyên."""
    starts = [i for i, l in enumerate(lines) if RE_KHOAN.match(l)]
    if khoan is None or len(starts) <= 1:
        return lines
    for n, i in enumerate(starts):
        if RE_KHOAN.match(lines[i]).group(1) == khoan:
            j = starts[n + 1] if n + 1 < len(starts) else len(lines)
            return lines[i:j]
    raise ValueError(f"không thấy khoản {khoan} trong đoạn trích")


# ---------- 4. Tách đoạn trích thành unit (giống parse_law nhưng gọn) ----------
def split_block(lines, base):
    """lines = đoạn trích; base = unit mẫu để lấy chương/mục/điều.
    Trả về list unit mới theo đúng cấu trúc của units.jsonl."""
    ctx = {k: base.get(k) for k in ("doc_id", "chuong", "chuong_ten", "muc", "muc_ten",
                                    "dieu", "dieu_ten", "khoan", "diem")}
    ctx["phu_luc"] = None
    out, cur, expect_muc_ten = [], None, False

    def new(level, text):
        u = dict(ctx, level=level, text=text)
        out.append(u)
        return u

    for s in lines:
        if expect_muc_ten:                       # dòng sau "Mục 5" là tên mục
            ctx["muc_ten"] = s
            expect_muc_ten = False
            continue
        if m := RE_MUC.match(s):
            ctx["muc"], ctx["muc_ten"] = m.group(1), m.group(2) or None
            expect_muc_ten = not m.group(2)
            continue
        if m := RE_DIEU.match(s):
            ctx.update(dieu=m.group(1), dieu_ten=m.group(2), khoan=None, diem=None)
            cur = new("dieu", "")
        elif m := RE_KHOAN.match(s):
            ctx.update(khoan=m.group(1), diem=None)
            cur = new("khoan", s)
        elif (m := RE_DIEM.match(s)) and ctx["khoan"]:
            ctx["diem"] = m.group(1)
            cur = new("diem", s)
        elif cur is None:                        # đoạn trích không mở bằng số khoản
            cur = new("khoan" if ctx["khoan"] else "dieu", s)
        else:
            cur["text"] = (cur["text"] + "\n" + s).strip()
    return out


# ---------- 5. Các thao tác ----------
def norm(s):
    """NFC để cụm từ trong yaml khớp với text trong docx (docx có thể dùng dấu tổ hợp)."""
    return unicodedata.normalize("NFC", s)


def stamp(u, op):
    """Ghi dấu op lên unit: thêm id op vào amended_by, cập nhật ngày hiệu lực."""
    u["amended_by"] = u["amended_by"] + [op["id"]]
    u["effective_from"] = str(op["effective_date"])
    return u


def new_units(lines, base, op, history=()):
    """history = các op đã sửa unit cũ trước đó, giữ lại để biết unit bị sửa mấy lần."""
    out = split_block(lines, base)
    for u in out:
        u.update(status="active", amended_by=list(history), effective_from=None)
        stamp(u, op)
    return out


def must_find(units, ref):
    """find_one nhưng báo lỗi rõ ràng khi không có (thay vì lỗi TypeError khó hiểu)."""
    i = find_one(units, ref)
    if i is None:
        raise ValueError(f"không thấy unit đích {ref}")
    return i


def do_replace(units, op, src_lines):
    """Thay 1 Điểm (chỉ đổi text), 1 Khoản hoặc cả Điều (tách đoạn trích thành unit mới)."""
    t = op["target"]
    if t.get("diem"):                            # thay 1 điểm: chỉ đổi text
        i = must_find(units, t)
        units[i]["text"] = "\n".join(src_lines)
        stamp(units[i], op)
        return units, 1
    idx = span(units, t["doc"], t["dieu"], t.get("khoan"))
    lines = pick_khoan(src_lines, t.get("khoan"))
    new = new_units(lines, units[idx[0]], op, units[idx[0]]["amended_by"])
    if t.get("khoan") is None:                   # thay cả Điều: giữ chương/mục cũ
        for u in new:
            u["dieu"] = t["dieu"]
    return units[:idx[0]] + new + units[idx[-1] + 1:], len(new)


def do_insert(units, op, src_lines):
    """Chèn Khoản mới sau after_khoan, hoặc Điều mới (vd. 28a) sau after_dieu."""
    t = op["target"]
    if "after_khoan" in t:
        idx = span(units, t["doc"], t["dieu"], t["after_khoan"])
        base = dict(units[idx[0]], khoan=t["khoan"])
        lines = pick_khoan(src_lines, t["khoan"])
    else:
        idx = span(units, t["doc"], t["after_dieu"])
        base = units[idx[0]]
        lines = src_lines
    new = new_units(lines, base, op)
    pos = idx[-1] + 1
    return units[:pos] + new + units[pos:], len(new)


def do_repeal(units, op):
    """Đánh dấu repealed (không xóa dòng, không đánh số lại Khoản)."""
    t = op["target"]
    if t.get("diem"):
        idx = [must_find(units, t)]
    else:
        idx = span(units, t["doc"], t["dieu"], t.get("khoan"))
    for i in idx:
        units[i]["status"] = "repealed"
        stamp(units[i], op)
    return units, len(idx)


def do_remove_phrase(units, op):
    """Bỏ 1 cụm từ; khớp không phân biệt hoa thường, khoảng trắng giữa các chữ co giãn được."""
    i = must_find(units, op["target"])
    pattern = r"\s*".join(re.escape(w) for w in norm(op["phrase"]).split())
    text, n = re.subn(pattern, "", norm(units[i]["text"]), flags=re.I)
    if n == 0:
        raise ValueError("không thấy cụm từ cần bỏ")
    lines = [re.sub(r"[ \t]{2,}", " ", l).strip() for l in text.split("\n")]
    units[i]["text"] = "\n".join(l for l in lines if l)
    stamp(units[i], op)
    return units, 1


def do_rename(units, op):
    """Đổi tên Điều trên mọi unit của Điều đó."""
    t = op["target"]
    idx = span(units, t["doc"], t["dieu"])
    for i in idx:
        units[i]["dieu_ten"] = op["new_title"]
    stamp(units[idx[0]], op)
    return units, len(idx)


def apply_op(units, op):
    """Kiểm nguồn/đích tồn tại rồi gọi hàm theo loại op. Trả (units mới, số unit bị đụng)."""
    t = op["target"]
    if op["op"] in ("replace", "insert"):
        si = find_one(units, op["source"])
        if si is None:
            raise ValueError("không thấy unit nguồn")
        src_lines = quoted_lines(units[si]["text"])
        if not src_lines:
            raise ValueError("unit nguồn không có đoạn trích “...”")
    if op["op"] != "insert" and not span(units, t["doc"], t["dieu"], t.get("khoan")):
        raise ValueError("không thấy unit đích")

    if op["op"] == "replace":
        return do_replace(units, op, src_lines)
    if op["op"] == "insert":
        if find_one(units, t) is not None:
            raise ValueError("unit đích đã có, không insert được")
        return do_insert(units, op, src_lines)
    if op["op"] == "repeal":
        return do_repeal(units, op)
    if op["op"] == "remove_phrase":
        return do_remove_phrase(units, op)
    if op["op"] == "rename":
        return do_rename(units, op)
    raise ValueError(f"op lạ: {op['op']}")


# ---------- 6. Chạy ----------
def main():
    units = load_units(ROOT / "data/processed/units.jsonl")
    ops = load_ops(ROOT / "data/raw/amendments.yaml")
    n_before = len(units)

    log = []
    for op in ops:
        try:
            units, n = apply_op(units, op)
            log.append(dict(id=op["id"], op=op["op"], ngay=str(op["effective_date"]), ok=True, so_unit=n, loi=""))
        except Exception as e:
            log.append(dict(id=op["id"], op=op["op"], ngay=str(op["effective_date"]), ok=False, so_unit=0, loi=str(e)))

    log = pd.DataFrame(log)
    log.to_csv(ROOT / "data/processed/amendments_log.csv", index=False, encoding="utf-8-sig")
    print(log.to_string(index=False))

    bad = log[~log["ok"]]
    assert bad.empty, f"{len(bad)} op lỗi, xem cột 'loi' ở trên"

    out = ROOT / "data/processed/units_current.jsonl"
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        for u in units:
            f.write(json.dumps(u, ensure_ascii=False) + "\n")

    st = pd.Series([u["status"] for u in units]).value_counts()
    print(f"\n{n_before} unit gốc → {len(units)} unit sau sửa đổi "
          f"({st.get('active', 0)} active, {st.get('repealed', 0)} repealed)")
    print(f"{sum(bool(u['amended_by']) for u in units)} unit bị sửa → {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
