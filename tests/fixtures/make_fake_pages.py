"""Sinh trang HTML GIẢ mô phỏng bố cục trang chi tiết thủ tục trên Cổng DVC.

CHỈ để test pipeline (crawl → parse → chunk → eda) khi chưa có dữ liệu thật.
Nội dung viết lại cho có cấu trúc giống thật, KHÔNG phải văn bản chính thức.

    python tests/fixtures/make_fake_pages.py <thư_mục_ra>
"""
import sys
from pathlib import Path

PAGE = """<!DOCTYPE html><html lang="vi"><head><meta charset="utf-8"><title>{ten}</title>
<style>.x{{color:red}}</style><script>var tracking = 1;</script></head><body>
<nav><a>Trang chủ</a><a>Thủ tục hành chính</a><a>Đăng nhập</a></nav>
<div class="layout"><div class="sidebar"><p>Thủ tục hành chính liên quan</p><ul><li>Thủ tục khác</li></ul></div>
<div class="main"><h1>{ten}</h1>
<div class="info">
<p><b>Mã thủ tục:</b> {ma}</p>
<p><b>Số quyết định:</b> 1234/QĐ-BTP</p>
<p><b>Tên thủ tục:</b> {ten}</p>
<p><b>Cấp thực hiện:</b> Cấp Xã</p>
<p><b>Loại thủ tục:</b> TTHC được luật giao quy định chi tiết</p>
<p><b>Lĩnh vực:</b> Hộ tịch</p>
<p><b>Trình tự thực hiện:</b></p><div>{trinh_tu}</div>
<p><b>Cách thức thực hiện:</b></p>
<table><tr><th>Hình thức nộp</th><th>Thời hạn giải quyết</th><th>Phí, lệ phí</th><th>Mô tả</th></tr>
{cach_thuc}</table>
<p><b>Thành phần hồ sơ:</b></p>
<table><tr><th>Tên giấy tờ</th><th>Mẫu đơn, tờ khai</th><th>Số lượng</th></tr>{ho_so}</table>
<p><b>Đối tượng thực hiện:</b> {doi_tuong}</p>
<p><b>Cơ quan thực hiện:</b> Ủy ban nhân dân cấp xã</p>
<p><b>Cơ quan có thẩm quyền:</b> Không có thông tin</p>
<p><b>Kết quả thực hiện:</b> {ket_qua}</p>
<p><b>Căn cứ pháp lý:</b></p>
<table><tr><th>Số ký hiệu</th><th>Trích yếu</th><th>Ngày ban hành</th><th>Cơ quan ban hành</th></tr>
<tr><td>60/2014/QH13</td><td>Luật Hộ tịch</td><td>20-11-2014</td><td>Quốc Hội</td></tr>
<tr><td>123/2015/NĐ-CP</td><td>Nghị định quy định chi tiết một số điều và biện pháp thi hành Luật Hộ tịch</td><td>15-11-2015</td><td>Chính phủ</td></tr>
</table>
<p><b>Yêu cầu, điều kiện thực hiện:</b></p><div>{dieu_kien}</div>
<p><b>Từ khóa:</b> hộ tịch</p><p><b>Mô tả:</b> Không có thông tin</p>
<p>Tải về</p><p>Tải về</p>
</div></div></div>
<footer>Bản quyền thuộc Văn phòng Chính phủ. Cổng Dịch vụ công Quốc gia.</footer></body></html>"""


def steps(*xs):
    return "".join(f"<p>{x}</p>" for x in xs)


def ways(rows):
    return "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td><td>{d}</td></tr>" for a, b, c, d in rows)


def papers(*xs):
    return "".join(f"<tr><td>{x}</td><td>{'Tờ khai.docx' if 'Tờ khai' in x else ''}</td><td>Bản chính: 1<br/>Bản sao: 0</td></tr>" for x in xs)


COMMON_STEP = ("Bước 1: Người yêu cầu nộp hồ sơ tại Bộ phận một cửa của Ủy ban nhân dân cấp xã hoặc nộp trực tuyến.",
               "Bước 2: Công chức tư pháp - hộ tịch tiếp nhận, kiểm tra hồ sơ;   nếu hồ sơ chưa đầy đủ thì hướng dẫn bổ sung.")

PROCS = [
    dict(ma="1.001193", ten="Đăng ký khai sinh",
         trinh_tu=steps(*COMMON_STEP, "Bước 3: Nếu thông tin khai sinh đầy đủ, phù hợp, công chức ghi nội dung khai sinh vào Sổ hộ tịch, cập nhật vào Cơ sở dữ liệu hộ tịch điện tử và lấy Số định danh cá nhân.", "Bước 4: Chủ tịch Ủy ban nhân dân cấp xã cấp Giấy khai sinh cho người được đăng ký khai sinh."),
         cach_thuc=ways([("Trực tiếp", "Ngay trong ngày tiếp nhận hồ sơ; trường hợp nhận hồ sơ sau 15 giờ thì trả kết quả trong ngày làm việc tiếp theo.", "Lệ phí : 0 Đồng (Miễn lệ phí đăng ký khai sinh đúng hạn)", "Nộp tại Bộ phận một cửa."), ("Trực tuyến", "Ngay trong ngày tiếp nhận hồ sơ.", "Lệ phí : 0 Đồng", "Nộp qua Cổng Dịch vụ công.")]),
         ho_so=papers("Tờ khai đăng ký khai sinh theo mẫu", "Giấy chứng sinh hoặc văn bản của người làm chứng xác nhận về việc sinh", "Giấy tờ tùy thân của người đi đăng ký"),
         doi_tuong="Công dân Việt Nam", ket_qua="Giấy khai sinh (bản chính)",
         dieu_kien=steps("Người đi đăng ký là cha, mẹ hoặc ông, bà, người thân thích khác.", "Thời hạn đăng ký là 60 ngày kể từ ngày sinh.")),
    dict(ma="1.000894", ten="Đăng ký kết hôn",
         trinh_tu=steps(*COMMON_STEP, "Bước 3: Nếu thấy đủ điều kiện kết hôn, công chức ghi việc kết hôn vào Sổ hộ tịch, hai bên nam, nữ cùng ký tên vào Sổ hộ tịch.", "Bước 4: Hai bên nam, nữ cùng ký vào Giấy chứng nhận kết hôn; Chủ tịch Ủy ban nhân dân cấp xã trao Giấy chứng nhận kết hôn."),
         cach_thuc=ways([("Trực tiếp", "Ngay sau khi nhận đủ giấy tờ; trường hợp cần xác minh thì không quá 05 ngày làm việc.", "Lệ phí : 0 Đồng (Miễn lệ phí)", "Hai bên nam, nữ phải có mặt."), ("Trực tuyến", "Ngay sau khi nhận đủ giấy tờ.", "Lệ phí : 0 Đồng", "Nộp hồ sơ trực tuyến, có mặt khi nhận kết quả.")]),
         ho_so=papers("Tờ khai đăng ký kết hôn theo mẫu", "Giấy xác nhận tình trạng hôn nhân (trường hợp đăng ký thường trú ở nơi khác)", "Giấy tờ tùy thân của hai bên"),
         doi_tuong="Công dân Việt Nam", ket_qua="Giấy chứng nhận kết hôn",
         dieu_kien=steps("Nam từ đủ 20 tuổi trở lên, nữ từ đủ 18 tuổi trở lên.", "Việc kết hôn do nam và nữ tự nguyện quyết định.", "Không bị mất năng lực hành vi dân sự.")),
    dict(ma="1.000656", ten="Đăng ký khai tử",
         trinh_tu=steps(*COMMON_STEP, "Bước 3: Công chức ghi nội dung khai tử vào Sổ hộ tịch, cùng người đi khai tử ký vào Sổ.", "Bước 4: Chủ tịch Ủy ban nhân dân cấp xã cấp Trích lục khai tử cho người đi khai tử."),
         cach_thuc=ways([("Trực tiếp", "Ngay trong ngày tiếp nhận hồ sơ; cần xác minh thì không quá 03 ngày làm việc.", "Lệ phí : 0 Đồng (Miễn lệ phí đăng ký khai tử đúng hạn)", ""), ("Trực tuyến", "Ngay trong ngày tiếp nhận hồ sơ.", "Lệ phí : 0 Đồng", "")]),
         ho_so=papers("Tờ khai đăng ký khai tử theo mẫu", "Giấy báo tử hoặc giấy tờ thay thế Giấy báo tử"),
         doi_tuong="Công dân Việt Nam", ket_qua="Trích lục khai tử (bản chính)",
         dieu_kien=steps("Trong thời hạn 15 ngày kể từ ngày có người chết, vợ, chồng hoặc con, cha, mẹ hoặc người thân thích khác có trách nhiệm đi khai tử.")),
    dict(ma="1.004746", ten="Đăng ký lại khai sinh",
         trinh_tu=steps(*COMMON_STEP, "Bước 3: Trong thời hạn 05 ngày làm việc, công chức kiểm tra, xác minh hồ sơ.", "Bước 4: Nếu việc đăng ký lại khai sinh là đúng, Chủ tịch Ủy ban nhân dân cấp xã cấp Giấy khai sinh."),
         cach_thuc=ways([("Trực tiếp", "05 Ngày làm việc", "Lệ phí : theo quy định của Hội đồng nhân dân cấp tỉnh", ""), ("Trực tuyến", "05 Ngày làm việc", "Lệ phí : theo quy định của Hội đồng nhân dân cấp tỉnh", "")]),
         ho_so=papers("Tờ khai đăng ký lại khai sinh theo mẫu", "Bản sao toàn bộ hồ sơ, giấy tờ của người yêu cầu có các thông tin liên quan đến nội dung khai sinh", "Giấy tờ tùy thân của người đi đăng ký"),
         doi_tuong="Công dân Việt Nam", ket_qua="Giấy khai sinh (bản chính)",
         dieu_kien=steps("Việc khai sinh đã được đăng ký tại cơ quan có thẩm quyền của Việt Nam trước ngày 01/01/2016 nhưng Sổ hộ tịch và bản chính giấy tờ hộ tịch đều bị mất.")),
    dict(ma="1.004837", ten="Đăng ký khai sinh kết hợp nhận cha, mẹ, con",
         trinh_tu=steps(*COMMON_STEP, "Bước 3: Nếu thông tin khai sinh và việc nhận cha, mẹ, con là đúng, công chức ghi vào Sổ hộ tịch.", "Bước 4: Chủ tịch Ủy ban nhân dân cấp xã cấp Giấy khai sinh và Trích lục đăng ký nhận cha, mẹ, con."),
         cach_thuc=ways([("Trực tiếp", "Ngay trong ngày tiếp nhận hồ sơ; cần xác minh thì không quá 05 ngày làm việc.", "Lệ phí : 0 Đồng (Miễn lệ phí phần khai sinh đúng hạn)", "")]),
         ho_so=papers("Tờ khai đăng ký khai sinh theo mẫu", "Tờ khai đăng ký nhận cha, mẹ, con theo mẫu", "Giấy chứng sinh", "Chứng cứ chứng minh quan hệ cha, mẹ, con"),
         doi_tuong="Công dân Việt Nam", ket_qua="Giấy khai sinh; Trích lục đăng ký nhận cha, mẹ, con",
         dieu_kien=steps("Các bên còn sống vào thời điểm đăng ký và không có tranh chấp.")),
    dict(ma="2.000635", ten="Cấp bản sao Trích lục hộ tịch",
         trinh_tu=steps("Bước 1: Người yêu cầu nộp tờ khai tại Ủy ban nhân dân cấp xã nơi đã đăng ký hộ tịch.", "Bước 2: Công chức kiểm tra, nếu yêu cầu phù hợp thì trình Chủ tịch ký cấp bản sao trích lục."),
         cach_thuc=ways([("Trực tiếp", "Ngay trong ngày tiếp nhận yêu cầu", "Phí : 8000 Đồng (một bản sao trích lục)", ""), ("Trực tuyến", "Ngay trong ngày tiếp nhận yêu cầu", "Phí : 8000 Đồng", "")]),
         ho_so=papers("Tờ khai cấp bản sao trích lục hộ tịch theo mẫu", "Văn bản ủy quyền (nếu nộp thay)"),
         doi_tuong="Cá nhân có yêu cầu", ket_qua="Bản sao trích lục hộ tịch",
         dieu_kien=steps("Không")),
]


def main(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for p in PROCS:
        (out / f"{p['ma']}.html").write_text(PAGE.format(**p), encoding="utf-8")
    return [p["ma"] for p in PROCS], {p["ma"]: p["ten"] for p in PROCS}


if __name__ == "__main__":
    print(main(sys.argv[1] if len(sys.argv) > 1 else "fake_pages"))
