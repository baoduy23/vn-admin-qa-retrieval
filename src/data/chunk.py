"""Chia đoạn (D03): units_current.jsonl → chunks.jsonl, kho dùng chung cho mọi mô hình truy hồi.

Đầu vào : data/processed/units_current.jsonl (từ apply_amendments)
          data/raw/source_list.csv, data/raw/amendments.yaml, configs/chunking.yaml
Đầu ra  : data/processed/chunks.jsonl, mỗi dòng 1 đoạn

Quy tắc (docs/huong-dan-thanh-vien-1.md mục 6):
  1 Điều = 1 đoạn. Điều dài quá max_tokens (đếm sau tách từ) thì tách theo Khoản;
  Khoản vẫn dài thì gom các Điểm thành từng phần (__P1, __P2...).
  Unit đã bị bãi bỏ (status = repealed) không vào kho.

Chạy từ gốc repo:  python -m src.data.chunk
"""
import re
import json
import hashlib
from functools import lru_cache

import pandas as pd
import yaml
from underthesea import word_tokenize

from src.data.parse_law import ROOT, RE_KHOAN, RE_DIEM, RE_PL_MUC

ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10}


# ---------- 1. Tách từ và đếm token ----------
@lru_cache(maxsize=8192)                   # có giới hạn: app gọi segment cho mọi câu hỏi người dùng gõ
def segment(text):
    """Tách từ bằng underthesea: "đăng ký khai sinh" → "đăng_ký khai_sinh".
    Tách riêng từng phần quanh " | " của tiền tố, không thì underthesea nối dấu | với chữ sau ("|_Khoản")."""
    return " | ".join(word_tokenize(part, format="text") for part in text.split(" | "))


def n_tokens(text):
    return len(segment(text).split())


# ---------- 2. Tên ngắn của văn bản (dùng trong tiền tố) ----------
def short_name(doc_id):
    """60.2014.QH13 → Luật Hộ tịch 60/2014/QH13; 123.2015.ND-CP → Nghị định 123/2015/NĐ-CP."""
    so, nam, loai = doc_id.split(".", 2)
    if loai.startswith("QH"):
        return f"Luật Hộ tịch {so}/{nam}/{loai}"
    ten = {"ND-CP": "Nghị định", "TT-BTP": "Thông tư"}[loai]
    return f"{ten} {so}/{nam}/{loai.replace('ND-', 'NĐ-')}"


# ---------- 3. Gom unit thành nhóm (1 nhóm = 1 Điều hoặc 1 mục Phụ lục) ----------
def wanted(rule, dieu, khoan):
    """Unit (dieu, khoan) có nằm trong phần được chunk của văn bản không."""
    if rule == "all":
        return True
    if dieu in rule.get("dieu", []):
        return True
    return khoan is not None and khoan in rule.get("khoan", {}).get(dieu, [])


def is_partial(rule, dieu):
    """Điều chỉ giữ vài Khoản → luôn chunk theo Khoản để chunk_id không giả vờ là cả Điều."""
    return rule != "all" and dieu not in rule.get("dieu", []) and dieu in rule.get("khoan", {})


def new_group(doc_id, key, dieu, title, u, partial=False):
    return dict(doc_id=doc_id, key=key, dieu=dieu, title=title, partial=partial,
                chuong=u.get("chuong"), chuong_ten=u.get("chuong_ten"),
                muc=u.get("muc"), muc_ten=u.get("muc_ten"),
                intro=[], khoans={}, ops=[], eff=[])


def add_meta(g, u):
    g["ops"] += u.get("amended_by") or []
    if u.get("effective_from"):
        g["eff"].append(u["effective_from"])


def group_units(units, include, drop_repealed=True):
    groups, by_key = [], {}
    for u in units:
        rule = include.get(u["doc_id"])
        if rule is None:
            continue
        if drop_repealed and u.get("status") == "repealed":
            continue

        if u["level"] == "phu_luc":                      # Phụ lục: mỗi unit là 1 mục La Mã
            lines = u["text"].split("\n")
            m = RE_PL_MUC.match(lines[0])
            if not m or rule == "all" or m.group(1) not in rule.get("phu_luc", []):
                continue
            so = ROMAN[m.group(1)]
            g = new_group(u["doc_id"], f"PL{so}", f"PL{so}", f"Phụ lục mục {m.group(1)}. {m.group(2)}", u)
            groups.append(g)
            add_meta(g, u)
            k = None
            for line in lines[1:]:
                if mk := RE_KHOAN.match(line):
                    k = mk.group(1)
                if k is None:
                    g["intro"].append(line)
                else:
                    g["khoans"].setdefault(k, []).append(line)
            continue

        if not wanted(rule, u["dieu"], u["khoan"]) and u["level"] != "dieu":
            continue
        gid = (u["doc_id"], u["dieu"])
        if gid not in by_key:
            title = f"Điều {u['dieu']}. {u['dieu_ten']}".strip()
            by_key[gid] = new_group(u["doc_id"], f"D{u['dieu']}", u["dieu"], title, u,
                                    partial=is_partial(rule, u["dieu"]))
            groups.append(by_key[gid])
        g = by_key[gid]
        if u["level"] == "dieu":
            if u["text"] and wanted(rule, u["dieu"], None):
                g["intro"].append(u["text"])
        else:
            g["khoans"].setdefault(u["khoan"], []).append(u["text"])
        add_meta(g, u)
    return [g for g in groups if g["intro"] or g["khoans"]]


# ---------- 4. Cắt nhóm thành đoạn ----------
def split_sentences(text):
    """Tách câu cho đoạn quá dài mà không có Điểm: cắt sau dấu . ; : (giữ dấu)."""
    return [s for s in re.split(r"(?<=[.;:])\s+", text) if s]


def pack(header, pieces, max_tokens):
    """Gom các mẩu liên tiếp thành phần, mỗi phần (cả tiền tố) không quá max_tokens."""
    parts, cur = [], []
    for p in pieces:
        if n_tokens(header + "\n" + p) > max_tokens:   # 1 mẩu đã quá dài → cắt theo câu
            if cur:
                parts.append(cur)
                cur = []
            sents = split_sentences(p)
            if len(sents) > 1:
                parts += pack(header, sents, max_tokens)
            else:                                        # 1 câu vẫn quá dài: cắt đôi theo âm tiết
                w = p.split()
                parts += pack(header, [" ".join(w[:len(w) // 2]), " ".join(w[len(w) // 2:])], max_tokens)
            continue
        if cur and n_tokens(header + "\n" + "\n".join(cur + [p])) > max_tokens:
            parts.append(cur)
            cur = []
        cur.append(p)
    if cur:
        parts.append(cur)
    return parts


def chunk_group(g, max_tokens):
    """Trả về list (suffix_id, khoan, phan, header, body)."""
    doc = short_name(g["doc_id"])
    head_dieu = f"{doc} | {g['title']}"
    all_lines = g["intro"] + [l for ls in g["khoans"].values() for l in ls]
    if not g["partial"] and n_tokens(head_dieu + "\n" + "\n".join(all_lines)) <= max_tokens:
        return [("", None, None, head_dieu, "\n".join(all_lines))]

    if not g["khoans"]:                                   # Điều dài nhưng không có Khoản
        parts = pack(head_dieu, split_sentences("\n".join(g["intro"])), max_tokens)
        return [(f"__P{i}", None, i, head_dieu, " ".join(p)) for i, p in enumerate(parts, 1)]

    out = []
    for n, (k, lines) in enumerate(g["khoans"].items()):
        if n == 0 and g["intro"] and not g["partial"]:   # đoạn dẫn trước khoản đầu tiên
            lines = g["intro"] + lines
        head = f"{head_dieu} | Khoản {k}"
        if n_tokens(head + "\n" + "\n".join(lines)) <= max_tokens:
            out.append((f"__K{k}", k, None, head, "\n".join(lines)))
            continue
        # Khoản dài: dòng dẫn của Khoản + từng Điểm là các mẩu để gom
        pieces, lead = [], []
        for l in lines:
            if RE_DIEM.match(l):
                pieces.append(l)
            elif pieces:
                pieces[-1] += "\n" + l
            else:
                lead.append(l)
        if lead:
            pieces.insert(0, "\n".join(lead))
        # tính cả chữ " (phần 9)" sẽ gắn vào tiền tố, kẻo phần nào cũng lố vài token
        for i, p in enumerate(pack(head + " (phần 9)", pieces, max_tokens), 1):
            out.append((f"__K{k}__P{i}", k, i, head + f" (phần {i})", "\n".join(p)))
    return out


# ---------- 5. Dựng chunks ----------
def load_ops_doc(path):
    """id op → văn bản sửa đổi (để amended_by ghi số hiệu văn bản chứ không phải id op)."""
    ops = yaml.safe_load(open(path, encoding="utf-8")) or []
    return {o["id"]: o["source"]["doc"] for o in ops}


def build_chunks(units, src, include, op_doc, max_tokens, drop_repealed=True):
    meta = src.set_index("doc_id")
    chunks = []
    for g in group_units(units, include, drop_repealed):
        m = meta.loc[g["doc_id"]]
        affected = [x for x in str(m.get("affected_by", "") or "").split(";") if x and x != "nan"]
        amended = sorted({op_doc.get(o, o) for o in g["ops"]})
        for suffix, khoan, phan, header, body in chunk_group(g, max_tokens):
            chunk_text = header + "\n" + body
            seg = segment(chunk_text)
            chunks.append(dict(
                chunk_id=f"{g['doc_id']}__{g['key']}{suffix}",
                doc_id=g["doc_id"], doc_title=short_name(g["doc_id"]),
                dieu=g["dieu"], dieu_title=g["title"], khoan=khoan, phan=phan,
                chuong=g["chuong"], chuong_ten=g["chuong_ten"], muc=g["muc"], muc_ten=g["muc_ten"],
                chunk_text=chunk_text, display_text=body, text_seg=seg, n_tokens=len(seg.split()),
                amended_by=amended, amendment_ops=sorted(set(g["ops"])), affected_by=affected,
                effective_from=max(g["eff"]) if g["eff"] else None,
                url=m["url"], accessed_at=m["accessed_at"],
            ))
    return chunks


# ---------- 6. Kiểm tra (mục 6.2 hướng dẫn TV1) ----------
def check_chunks(chunks, max_tokens):
    """Trả về list lỗi; rỗng = đạt."""
    errs = []
    ids = [c["chunk_id"] for c in chunks]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        errs.append(f"chunk_id trùng: {sorted(dup)[:5]}")
    for c in chunks:
        if not c["display_text"].strip() or not c["chunk_text"].strip() or not c["text_seg"].strip():
            errs.append(f"{c['chunk_id']}: rỗng")
        if c["n_tokens"] > max_tokens:
            errs.append(f"{c['chunk_id']}: {c['n_tokens']} token > {max_tokens}")
    texts = [c["display_text"] for c in chunks]
    same = {t for t in texts if texts.count(t) > 1}
    if same:
        errs.append(f"{len(same)} đoạn trùng nội dung, ví dụ: {next(iter(same))[:80]!r}")
    return errs


def sha256(path):
    # bỏ \r trước khi băm: Git trên Windows (autocrlf) checkout ra CRLF, máy nào băm cũng phải ra cùng 1 mã
    return hashlib.sha256(open(path, "rb").read().replace(b"\r\n", b"\n")).hexdigest()


def main():
    cfg = yaml.safe_load(open(ROOT / "configs/chunking.yaml", encoding="utf-8"))
    units = [json.loads(l) for l in open(ROOT / "data/processed/units_current.jsonl", encoding="utf-8")]
    src = pd.read_csv(ROOT / "data/raw/source_list.csv", dtype=str)
    op_doc = load_ops_doc(ROOT / "data/raw/amendments.yaml")

    chunks = build_chunks(units, src, cfg["include"], op_doc, cfg["max_tokens"], cfg.get("drop_repealed", True))
    errs = check_chunks(chunks, cfg["max_tokens"])
    for e in errs:
        print("LỖI:", e)
    assert not errs, f"{len(errs)} lỗi, xem ở trên"

    out = ROOT / "data/processed/chunks.jsonl"
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    df = pd.DataFrame(chunks)
    summary = df.groupby("doc_id").agg(so_chunk=("chunk_id", "size"),
                                       so_dieu=("dieu", "nunique"),
                                       token_tb=("n_tokens", "mean"),
                                       token_max=("n_tokens", "max")).round(1)
    print(summary.to_string())
    print(f"\n{len(chunks)} chunk → {out.relative_to(ROOT)}   sha256 = {sha256(out)[:16]}...")


if __name__ == "__main__":
    main()
