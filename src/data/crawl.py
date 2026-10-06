"""D01: tải trang chi tiết thủ tục về data/raw/html/<doc_id>.html.

Đọc data/raw/source_list.csv (các dòng in_scope = yes), mở từng URL bằng
trình duyệt headless (Playwright) vì trang Dịch vụ công tải nội dung bằng
JavaScript, lưu nguyên HTML đã render và ghi một dòng vào raw_manifest.csv.

Chạy:
    python -m src.data.crawl                     # tải các thủ tục chưa có
    python -m src.data.crawl --only 1.001193     # tải 1 thủ tục để thử
    python -m src.data.crawl --force             # tải lại (ghi sha256 mới)
    python -m src.data.crawl --headed            # mở trình duyệt thật để xem
    python -m src.data.crawl --register-manual   # đăng ký file m tự Ctrl+S

Nguyên tắc: không sửa file trong data/raw/html, mỗi lần tải là một dòng mới
trong manifest, nghỉ vài giây giữa các request.
"""
import argparse
import csv
import hashlib
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

RAW_DIR = Path("data/raw")
HTML_DIR = RAW_DIR / "html"
FAILED_DIR = HTML_DIR / "_failed"
SOURCE_LIST = RAW_DIR / "source_list.csv"
MANIFEST = RAW_DIR / "raw_manifest.csv"
MANIFEST_COLS = ["doc_id", "url", "file_path", "sha256", "bytes", "http_status",
                 "accessed_at", "method", "note"]

# Trang chỉ được coi là tải đúng khi có đủ các nhãn này trong nội dung.
MUST_HAVE = ["Trình tự thực hiện", "Thành phần hồ sơ"]
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/130.0 Safari/537.36 (student NLP project)")


def read_sources(only=None):
    with open(SOURCE_LIST, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    ids = [r["doc_id"].strip() for r in rows]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        sys.exit(f"doc_id bị trùng trong source_list.csv: {sorted(dup)}")
    rows = [r for r in rows if r.get("in_scope", "").strip().lower() in {"yes", "y", "1", "true"}]
    if only:
        rows = [r for r in rows if r["doc_id"].strip() in set(only)]
    missing_url = [r["doc_id"] for r in rows if not r.get("url", "").strip()]
    if missing_url:
        sys.exit(f"Thiếu url cho: {missing_url}")
    return rows


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def append_manifest(row):
    new = not MANIFEST.exists()
    with open(MANIFEST, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_COLS)
        if new:
            w.writeheader()
        w.writerow(row)


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def save(doc_id, url, html, status, method, note=""):
    data = html.encode("utf-8")
    ok = all(label in html for label in MUST_HAVE)
    path = (HTML_DIR if ok else FAILED_DIR) / f"{doc_id}.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    if ok and path.exists():
        # --force: giữ bản cũ thay vì ghi đè, đổi tên theo hash của nó.
        old = path.read_bytes()
        archive = HTML_DIR / "_old" / f"{doc_id}.{sha256_bytes(old)[:8]}.html"
        archive.parent.mkdir(parents=True, exist_ok=True)
        path.replace(archive)
    path.write_bytes(data)
    append_manifest({
        "doc_id": doc_id, "url": url, "file_path": path.as_posix(),
        "sha256": sha256_bytes(data), "bytes": len(data), "http_status": status,
        "accessed_at": now_iso(), "method": method,
        "note": note if ok else (note + " thiếu nhãn mục, xem _failed/").strip(),
    })
    return ok


def crawl_playwright(rows, headed, delay, timeout_s):
    from playwright.sync_api import TimeoutError as PwTimeout
    from playwright.sync_api import sync_playwright

    n_ok = 0
    with sync_playwright() as p:
        # CHROMIUM_PATH: dùng Chrome/Chromium có sẵn thay vì bản Playwright tải về (không bắt buộc).
        browser = p.chromium.launch(headless=not headed, executable_path=os.environ.get("CHROMIUM_PATH") or None)
        ctx = browser.new_context(user_agent=USER_AGENT, locale="vi-VN")
        page = ctx.new_page()
        for i, r in enumerate(rows, 1):
            doc_id, url = r["doc_id"].strip(), r["url"].strip()
            status, html, note = None, "", ""
            for attempt in range(3):
                try:
                    resp = page.goto(url, wait_until="domcontentloaded", timeout=timeout_s * 1000)
                    status = resp.status if resp else None
                    # Đợi JS đổ nội dung: chờ tới khi thấy nhãn mục đầu tiên.
                    page.wait_for_function(
                        "t => document.body && document.body.innerText.includes(t)",
                        arg=MUST_HAVE[0], timeout=timeout_s * 1000)
                    page.wait_for_load_state("networkidle", timeout=timeout_s * 1000)
                    html = page.content()
                    note = ""
                    break
                except PwTimeout:
                    html = page.content()
                    note = f"timeout lần {attempt + 1}"
                    time.sleep(5 * (attempt + 1))
            ok = save(doc_id, url, html, status, "playwright", note)
            n_ok += ok
            print(f"[{i}/{len(rows)}] {doc_id} {'OK' if ok else 'LỖI'} ({status}) {note}")
            time.sleep(random.uniform(*delay))
        browser.close()
    return n_ok


def crawl_requests(rows, delay, timeout_s):
    import requests

    n_ok = 0
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    for i, r in enumerate(rows, 1):
        doc_id, url = r["doc_id"].strip(), r["url"].strip()
        resp = s.get(url, timeout=timeout_s)
        resp.encoding = resp.apparent_encoding or "utf-8"
        ok = save(doc_id, url, resp.text, resp.status_code, "requests")
        n_ok += ok
        print(f"[{i}/{len(rows)}] {doc_id} {'OK' if ok else 'LỖI'} ({resp.status_code})")
        time.sleep(random.uniform(*delay))
    return n_ok


def register_manual(rows):
    """Đăng ký các file HTML m tự lưu bằng Ctrl+S vào data/raw/html/<doc_id>.html."""
    logged = set()
    if MANIFEST.exists():
        with open(MANIFEST, encoding="utf-8") as f:
            logged = {(r["doc_id"], r["sha256"]) for r in csv.DictReader(f)}
    n = 0
    for r in rows:
        doc_id = r["doc_id"].strip()
        path = HTML_DIR / f"{doc_id}.html"
        if not path.exists():
            continue
        data = path.read_bytes()
        if (doc_id, sha256_bytes(data)) in logged:
            continue
        append_manifest({
            "doc_id": doc_id, "url": r["url"].strip(), "file_path": path.as_posix(),
            "sha256": sha256_bytes(data), "bytes": len(data), "http_status": "",
            "accessed_at": now_iso(), "method": "manual_save", "note": "lưu tay bằng trình duyệt",
        })
        n += 1
    print(f"Đã đăng ký {n} file lưu tay vào {MANIFEST}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="*", help="chỉ tải các doc_id này")
    ap.add_argument("--force", action="store_true", help="tải lại cả file đã có")
    ap.add_argument("--engine", choices=["playwright", "requests"], default="playwright")
    ap.add_argument("--headed", action="store_true", help="hiện cửa sổ trình duyệt")
    ap.add_argument("--delay", type=float, nargs=2, default=(3.0, 6.0), metavar=("MIN", "MAX"))
    ap.add_argument("--timeout", type=int, default=45, help="giây cho mỗi trang")
    ap.add_argument("--register-manual", action="store_true")
    args = ap.parse_args()

    rows = read_sources(args.only)
    if args.register_manual:
        return register_manual(rows)
    if not args.force:
        rows = [r for r in rows if not (HTML_DIR / f"{r['doc_id'].strip()}.html").exists()]
    if not rows:
        print("Không còn thủ tục nào cần tải (dùng --force để tải lại).")
        return
    print(f"Sẽ tải {len(rows)} thủ tục bằng {args.engine} ...")
    if args.engine == "playwright":
        n_ok = crawl_playwright(rows, args.headed, args.delay, args.timeout)
    else:
        n_ok = crawl_requests(rows, args.delay, args.timeout)
    print(f"Xong: {n_ok}/{len(rows)} trang đúng nội dung. Trang lỗi nằm ở {FAILED_DIR}/")


if __name__ == "__main__":
    main()
