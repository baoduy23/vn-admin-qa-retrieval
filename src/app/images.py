"""Ảnh trên giao diện web: chỉ 3 ảnh.

    hoa_sen              ảnh bên trái ô tìm kiếm (trang đầu)
    chim_lac             dải chim Lạc ở chân trang (hoạ tiết, chỉ dùng hình dáng, màu do CSS tô)
    hoa_van_trong_dong   hoa văn mặt trống đồng mờ làm nền khu tìm kiếm

DÙNG ẢNH CỦA MÌNH: chép ảnh vào src/app/static/img/ và đặt tên trùng tên ở trên, đuôi .jpg, .jpeg,
.png hoặc .webp (ví dụ src/app/static/img/hoa_sen.jpg). Web ưu tiên ảnh trong thư mục đó; không có
thì lấy ảnh mặc định từ Wikimedia Commons (cần mạng). Đổi ảnh xong bấm Ctrl + F5 trên trình duyệt.

    python -m src.app.images        # tải ảnh mặc định về src/app/static/img/ (không ghi đè ảnh đã có)
"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

STATIC = Path(__file__).resolve().parent / "static" / "img"
EXTS = (".jpg", ".jpeg", ".png", ".webp")
WIKI = "https://thumb.wikimedia.org/wikipedia/commons/thumb/"

# tên: (đuôi file khi tải mặc định, URL ảnh mặc định, mô tả, tác giả, giấy phép, trang gốc trên Commons)
IMAGES = {
    "hoa_sen": (
        ".jpg",
        WIKI + "0/0d/Nelumbo_nucifera_01.JPG/960px-Nelumbo_nucifera_01.JPG",
        "Hoa sen hồng", "Prenn", "CC BY-SA 3.0",
        "https://commons.wikimedia.org/wiki/File:Nelumbo_nucifera_01.JPG"),
    "chim_lac": (
        ".png",
        "https://upload.wikimedia.org/wikipedia/commons/d/da/Chim_Trong_Dong.PNG",
        "Hoạ tiết chim Lạc trên mặt trống đồng Hoàng Hạ", "Lưu Ly (Wikipedia tiếng Việt)", "Public domain",
        "https://commons.wikimedia.org/wiki/File:Chim_Trong_Dong.PNG"),
    "hoa_van_trong_dong": (
        ".png",
        WIKI + "1/16/Tr%E1%BB%91ng_%C4%91%E1%BB%93ng_%C4%90%C3%B4ng_S%C6%A1n.svg/"
               "960px-Tr%E1%BB%91ng_%C4%91%E1%BB%93ng_%C4%90%C3%B4ng_S%C6%A1n.svg.png",
        "Hoa văn mặt trống đồng Đông Sơn (nét vẽ)", "Tom Mai", "Public domain",
        "https://commons.wikimedia.org/wiki/File:Tr%E1%BB%91ng_%C4%91%E1%BB%93ng_%C4%90%C3%B4ng_S%C6%A1n.svg"),
}


def local_file(name: str) -> Path | None:
    """Ảnh của nhóm trong static/img/ (tên trùng, đuôi bất kỳ trong EXTS), hoặc None."""
    for ext in EXTS:
        for f in (STATIC / f"{name}{ext}", STATIC / f"{name}{ext.upper()}"):
            if f.exists():
                return f
    return None


def url(name: str) -> str:
    """Đường dẫn ảnh cho HTML/CSS. Ảnh trong máy kèm ?v=<thời điểm sửa> để trình duyệt không giữ ảnh cũ."""
    f = local_file(name)
    if f:
        return f"app/static/img/{f.name}?v={int(f.stat().st_mtime)}"
    return IMAGES[name][1]


def credits() -> list[dict]:
    return [dict(name=k, desc=d, author=a, license=l, page=p) for k, (_, _, d, a, l, p) in IMAGES.items()]


def download(force: bool = False) -> None:
    STATIC.mkdir(parents=True, exist_ok=True)
    # Wikimedia từ chối request không có User-Agent riêng
    headers = {"User-Agent": "vn-admin-qa-retrieval/1.0 (student NLP project; github.com/baoduy23/vn-admin-qa-retrieval)"}
    for name, (ext, remote, *_rest) in IMAGES.items():
        have = local_file(name)
        if have and not force:
            print(f"đã có  {have.name}  (giữ nguyên)")
            continue
        out = STATIC / f"{name}{ext}"
        with urllib.request.urlopen(urllib.request.Request(remote, headers=headers), timeout=60) as r:
            out.write_bytes(r.read())
        print(f"tải    {out.name}  ({out.stat().st_size // 1024} KB)")
    print(f"Xong → {STATIC}")


if __name__ == "__main__":
    download(force="--force" in sys.argv)
