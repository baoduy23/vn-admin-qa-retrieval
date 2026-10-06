"""D02 (phần 1): trích xuất theo mục + làm sạch, HTML → data/interim/docs.jsonl.

Không phụ thuộc class/id CSS của trang (dễ đổi khi cổng cập nhật giao diện).
Thay vào đó: chuyển trang thành các dòng văn bản, rồi cắt theo NHÃN MỤC
("Trình tự thực hiện:", "Thành phần hồ sơ:", ...). Trang lưu tay bằng Ctrl+S
cũng parse được y như trang crawl.

Chạy:
    python -m src.data.parse
    python -m src.data.parse --only 1.001193 --show   # in kết quả 1 thủ tục để soi
"""
import argparse
import csv
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

from src.data.text_utils import CleanLog, clean_lines

HTML_DIR = Path("data/raw/html")
SOURCE_LIST = Path("data/raw/source_list.csv")
MANIFEST = Path("data/raw/raw_manifest.csv")
OUT = Path("data/interim/docs.jsonl")
QA_DIR = Path("results/data_quality")

# Nhãn thông tin chung ở đầu trang.
META_LABELS = {
    "ma_thu_tuc": ["Mã thủ tục"],
    "so_quyet_dinh": ["Số quyết định"],
    "ten_thu_tuc": ["Tên thủ tục"],
    "cap_thuc_hien": ["Cấp thực hiện"],
    "loai_thu_tuc": ["Loại thủ tục"],
    "linh_vuc": ["Lĩnh vực"],
}
# Các mục nội dung. Thứ tự key = thứ tự hiển thị trong báo cáo.
FIELD_LABELS = {
    "trinh_tu": ["Trình tự thực hiện"],
    "cach_thuc": ["Cách thức thực hiện"],
    "thanh_phan_ho_so": ["Thành phần hồ sơ"],
    "thoi_han": ["Thời hạn giải quyết"],
    "le_phi": ["Phí, lệ phí"],
    "doi_tuong": ["Đối tượng thực hiện"],
    "co_quan": ["Cơ quan thực hiện", "Cơ quan có thẩm quyền", "Địa chỉ tiếp nhận HS",
                "Địa chỉ tiếp nhận hồ sơ", "Cơ quan được ủy quyền", "Cơ quan phối hợp"],
    "ket_qua": ["Kết quả thực hiện"],
    "yeu_cau_dieu_kien": ["Yêu cầu, điều kiện thực hiện", "Yêu cầu, điều kiện"],
    "can_cu_phap_ly": ["Căn cứ pháp lý"],
}
FIELD_NAMES_VI = {
    "trinh_tu": "Trình tự thực hiện", "cach_thuc": "Cách thức thực hiện",
    "thanh_phan_ho_so": "Thành phần hồ sơ", "thoi_han": "Thời hạn giải quyết",
    "le_phi": "Phí, lệ phí", "doi_tuong": "Đối tượng thực hiện", "co_quan": "Cơ quan thực hiện",
    "ket_qua": "Kết quả thực hiện", "yeu_cau_dieu_kien": "Yêu cầu, điều kiện",
    "can_cu_phap_ly": "Căn cứ pháp lý",
}
# Gặp các nhãn này thì dừng mục hiện tại và bỏ phần sau (menu, chân trang...).
STOP_LABELS = ["Từ khóa", "Mô tả", "Thủ tục hành chính liên quan", "Bản quyền",
               "Cơ quan chủ quản", "Đánh giá thủ tục"]
REQUIRED_FIELDS = ["thanh_phan_ho_so", "thoi_han", "co_quan"]   # hướng dẫn TV1, mục 5.3

BLOCK_TAGS = ["p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6",
              "table", "ul", "ol", "section", "article", "dt", "dd", "label"]


def _label_regex():
    entries = []
    for kind, mapping in (("meta", META_LABELS), ("field", FIELD_LABELS)):
        for key, labels in mapping.items():
            entries += [(lab, kind, key) for lab in labels]
    entries += [(lab, "stop", None) for lab in STOP_LABELS]
    entries.sort(key=lambda e: -len(e[0]))       # nhãn dài khớp trước
    lookup = {e[0].lower(): e for e in entries}
    alt = "|".join(re.escape(e[0]) for e in entries)
    # Nhãn phải đứng đầu dòng VÀ (có dấu ":" hoặc đứng một mình cả dòng),
    # để câu kiểu "Lệ phí đăng ký là..." trong nội dung không bị nhận nhầm.
    return re.compile(rf"^({alt})\s*(?::\s*(.*)|$)", re.IGNORECASE), lookup


LABEL_RE, LABEL_LOOKUP = _label_regex()


def html_to_lines(html):
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg", "nav", "footer", "button"]):
        tag.decompose()
    # Bảng → mỗi hàng một dòng "ô 1 | ô 2 | ...". Xử lý bảng con trước.
    for table in reversed(soup.find_all("table")):
        rows = []
        for tr in table.find_all("tr"):
            cells = [" ".join(c.get_text(" ", strip=True).split()) for c in tr.find_all(["td", "th"], recursive=False)]
            if any(cells):
                rows.append(" | ".join(cells))
        block = soup.new_tag("div")
        for r in rows:
            p = soup.new_tag("p")
            p.string = r
            block.append(p)
        table.replace_with(block)
    for li in soup.find_all("li"):
        li.insert(0, "- ")
    for tag in soup.find_all(BLOCK_TAGS):
        tag.insert_before("\n")
        tag.insert_after("\n")
    root = _main_container(soup)
    return root.get_text("").splitlines()


def _main_container(soup):
    """Phần tử nhỏ nhất chứa đủ các nhãn chính = vùng nội dung thủ tục."""
    must = ["Trình tự thực hiện", "Thành phần hồ sơ", "Căn cứ pháp lý"]
    best = soup.body or soup
    best_len = len(best.get_text())
    for el in soup.find_all(["div", "section", "article", "main", "td"]):
        text = el.get_text()
        if len(text) < best_len and all(m in text for m in must):
            best, best_len = el, len(text)
    return best


def split_sections(lines):
    meta, fields, current = {}, {}, None
    for line in lines:
        s = line.strip()
        if not s:
            continue
        m = LABEL_RE.match(s)
        if m:
            _, kind, key = LABEL_LOOKUP[m.group(1).lower()]
            rest = (m.group(2) or "").strip()
            if kind == "stop":
                current = None
                continue
            if kind == "meta":
                if rest:
                    meta.setdefault(key, rest)
                    current = None
                else:
                    current = ("meta", key)      # giá trị nằm ở dòng kế tiếp
                continue
            current = ("field", key)
            fields.setdefault(key, [])
            if rest:
                fields[key].append(rest)
            continue
        if current is None:
            continue
        kind, key = current
        if kind == "meta":
            meta.setdefault(key, s)
            current = None
        else:
            fields[key].append(s)
    return meta, fields


def split_cach_thuc_table(lines):
    """Bảng "Cách thức thực hiện" của cổng gộp hình thức nộp + thời hạn + phí.

    Tách ra thành 3 mục riêng để không có 2 đoạn trùng thông tin.
    Trả về (cach_thuc, thoi_han, le_phi) dạng list dòng.
    """
    header_idx = next((i for i, l in enumerate(lines) if "|" in l and "Thời hạn" in l), None)
    if header_idx is None:
        return lines, [], []
    header = [h.strip().lower() for h in lines[header_idx].split("|")]

    def col(*keys):
        return next((i for i, h in enumerate(header) if any(k in h for k in keys)), None)

    c_form, c_time, c_fee, c_desc = col("hình thức"), col("thời hạn"), col("phí"), col("mô tả")
    cach, han, phi = list(lines[:header_idx]), [], []
    for l in lines[header_idx + 1:]:
        cells = [c.strip() for c in l.split("|")]
        if len(cells) != len(header):
            cach.append(l)
            continue
        form = cells[c_form] if c_form is not None else ""
        if c_desc is not None and cells[c_desc]:
            cach.append(f"{form}: {cells[c_desc]}" if form else cells[c_desc])
        elif form:
            cach.append(form)
        if c_time is not None and cells[c_time]:
            han.append(f"{form}: {cells[c_time]}" if form else cells[c_time])
        if c_fee is not None and cells[c_fee]:
            phi.append(f"{form}: {cells[c_fee]}" if form else cells[c_fee])
    return cach, han, phi


def _table(lines, must_header):
    """Tìm bảng (dòng "a | b | c") có header chứa must_header. Trả về (trước, header, hàng, sau)."""
    idx = next((i for i, l in enumerate(lines) if "|" in l and must_header in l.lower()), None)
    if idx is None:
        return None
    header = [h.strip().lower() for h in lines[idx].split("|")]
    rows, rest = [], []
    for l in lines[idx + 1:]:
        cells = [c.strip() for c in l.split("|")]
        (rows if len(cells) == len(header) else rest).append(cells if len(cells) == len(header) else l)
    return lines[:idx], header, rows, rest


def tidy_ho_so(lines):
    """Bảng hồ sơ → "- <tên giấy tờ> (Bản chính: 1, Bản sao: 0)". Bỏ cột tên file mẫu."""
    t = _table(lines, "tên giấy tờ")
    if not t:
        return lines
    before, header, rows, rest = t
    c_qty = next((i for i, h in enumerate(header) if "số lượng" in h), None)
    out = list(before)
    for cells in rows:
        qty = cells[c_qty].replace(" Bản sao", ", Bản sao") if c_qty is not None and cells[c_qty] else ""
        out.append(f"- {cells[0]}" + (f" ({qty})" if qty else ""))
    return out + rest


def tidy_can_cu(lines):
    """Bảng căn cứ → "- 60/2014/QH13: Luật Hộ tịch (ban hành 20-11-2014, Quốc Hội)"."""
    t = _table(lines, "số ký hiệu")
    if not t:
        return lines
    before, header, rows, rest = t

    def col(key):
        return next((i for i, h in enumerate(header) if key in h), None)

    c_no, c_name, c_date, c_org = col("số ký hiệu"), col("trích yếu"), col("ngày"), col("cơ quan")
    out = list(before)
    for cells in rows:
        extra = ", ".join(x for x in [f"ban hành {cells[c_date]}" if c_date is not None and cells[c_date] else "",
                                      cells[c_org] if c_org is not None else ""] if x)
        out.append(f"- {cells[c_no]}: {cells[c_name]}" + (f" ({extra})" if extra else ""))
    return out + rest


def latest_manifest():
    if not MANIFEST.exists():
        return {}
    with open(MANIFEST, encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if "_failed" not in r["file_path"]]
    return {r["doc_id"]: r for r in rows}     # dòng sau ghi đè dòng trước = lần tải mới nhất


def parse_doc(doc_id, html, source, man, log):
    lines = html_to_lines(html)
    meta, raw_fields = split_sections(lines)
    if "cach_thuc" in raw_fields:
        cach, han, phi = split_cach_thuc_table(raw_fields["cach_thuc"])
        raw_fields["cach_thuc"] = cach
        if han and not raw_fields.get("thoi_han"):
            raw_fields["thoi_han"] = han
        if phi and not raw_fields.get("le_phi"):
            raw_fields["le_phi"] = phi
    if "thanh_phan_ho_so" in raw_fields:
        raw_fields["thanh_phan_ho_so"] = tidy_ho_so(raw_fields["thanh_phan_ho_so"])
    if "can_cu_phap_ly" in raw_fields:
        raw_fields["can_cu_phap_ly"] = tidy_can_cu(raw_fields["can_cu_phap_ly"])

    fields, raw_chars, clean_chars = {}, {}, {}
    for key in FIELD_LABELS:
        if key not in raw_fields:
            continue
        raw = raw_fields[key]
        cleaned = clean_lines(raw, log)
        if cleaned:
            fields[key] = "\n".join(cleaned)
            raw_chars[key] = len("\n".join(raw))
            clean_chars[key] = len(fields[key])

    meta = {k: " ".join(clean_lines([v], log)) for k, v in meta.items()}
    issues = []
    if meta.get("ma_thu_tuc") and meta["ma_thu_tuc"] != doc_id:
        issues.append(f"mã trên trang ({meta['ma_thu_tuc']}) khác doc_id")
    for f in REQUIRED_FIELDS:
        if f not in fields:
            issues.append(f"thiếu mục bắt buộc: {f}")
    if not fields:
        issues.append("không trích được mục nào (sai trang? trang lỗi?)")

    doc = {
        "doc_id": doc_id,
        "title": meta.get("ten_thu_tuc") or source.get("title", "").strip(),
        "ma_thu_tuc_tren_trang": meta.get("ma_thu_tuc", ""),
        "linh_vuc": meta.get("linh_vuc", ""),
        "cap_thuc_hien": meta.get("cap_thuc_hien", "") or source.get("issuing_level", ""),
        "so_quyet_dinh": meta.get("so_quyet_dinh", ""),
        "url": source.get("url", "").strip() or man.get("url", ""),
        "accessed_at": man.get("accessed_at", "") or source.get("accessed_at", ""),
        "raw_sha256": man.get("sha256", ""),
        "fields": fields,
        "stats": {"raw_chars": raw_chars, "clean_chars": clean_chars},
    }
    return doc, issues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--show", action="store_true", help="in JSON từng thủ tục ra màn hình")
    args = ap.parse_args()

    with open(SOURCE_LIST, encoding="utf-8-sig", newline="") as f:
        sources = {r["doc_id"].strip(): r for r in csv.DictReader(f)}
    man = latest_manifest()
    files = sorted(HTML_DIR.glob("*.html"))
    if args.only:
        files = [p for p in files if p.stem in set(args.only)]
    if not files:
        raise SystemExit(f"Không có file nào trong {HTML_DIR}. Chạy crawl trước.")

    log = CleanLog()
    docs, issue_rows = [], []
    for path in files:
        doc_id = path.stem
        if doc_id not in sources:
            issue_rows.append({"doc_id": doc_id, "issue": "có file HTML nhưng không có trong source_list"})
            continue
        doc, issues = parse_doc(doc_id, path.read_text(encoding="utf-8", errors="replace"),
                                sources[doc_id], man.get(doc_id, {}), log)
        docs.append(doc)
        issue_rows += [{"doc_id": doc_id, "issue": i} for i in issues]
        if args.show:
            print(json.dumps(doc, ensure_ascii=False, indent=2))

    if args.only:
        print("Chế độ --only chỉ để soi, không ghi đè docs.jsonl và log.")
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    QA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        for d in docs:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    with open(QA_DIR / "cleaning_log.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["rule", "hits"])
        w.writeheader()
        w.writerows(log.as_rows())
    with open(QA_DIR / "parse_issues.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["doc_id", "issue"])
        w.writeheader()
        w.writerows(issue_rows)
    print(f"{len(docs)} thủ tục → {OUT}; {len(issue_rows)} vấn đề → {QA_DIR / 'parse_issues.csv'}")


if __name__ == "__main__":
    main()
