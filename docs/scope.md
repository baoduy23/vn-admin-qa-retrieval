# Phạm vi dữ liệu

> Nhóm điền và chốt file này ở task S01. Sửa phạm vi sau khi đã freeze Dataset v1 phải làm lại nhãn.

**Lĩnh vực đã chọn:** Hộ tịch 

**Lý do:** người dân hỏi nhiều (khai sinh, kết hôn, khai tử, cải chính...). Quy định chia tầng rõ: Luật nêu nguyên tắc, Nghị định và Thông tư hướng dẫn chi tiết, nên có câu hỏi cần ghép nhiều văn bản. Có nhiều Điều nội dung gần giống nhau (ví dụ đăng ký khai sinh trong nước, có yếu tố nước ngoài, ở khu vực biên giới), phục vụ phân tích bắt buộc về tài liệu gần trùng.

**Ngoài phạm vi (dùng làm câu hỏi từ chối):** đất đai, cư trú, thuế, các lĩnh vực khác; quy định chưa có hiệu lực tại ngày chốt kho (ví dụ "Luật Hộ tịch mới năm 2027 có gì thay đổi?").

**Nguồn chính:** vbpl.vn | CSDL quốc gia về pháp luật (lọc lĩnh vực Hộ tịch); văn bản pháp luật về hộ tịch còn hiệu lực tại ngày tải. Văn bản nào trên vbpl.vn hoặc vanban.chinhphu.vn chỉ có PDF scan (không đọc được chữ) thì lấy toàn văn trên thuvienphapluat.vn và giữ file scan trong `data/raw/` để đối chiếu. Không cào web.

**Văn bản trong kho (Dataset v1): 10 văn bản**

Văn bản gốc (được tách và chunk):

| doc_id | Văn bản | Cơ quan ban hành | Vai trò | Bị sửa bởi |
|---|---|---|---|---|
| 60.2014.QH13 | Luật Hộ tịch 60/2014/QH13 | Quốc hội | Nguyên tắc, thẩm quyền, thủ tục chung | Không có văn bản sửa câu chữ |
| 123.2015.ND-CP | Nghị định 123/2015/NĐ-CP quy định chi tiết một số điều và biện pháp thi hành Luật Hộ tịch | Chính phủ | Chi tiết thủ tục, giấy tờ | 87/2020, 104/2022, 07/2025, 18/2026 |
| 04.2020.TT-BTP | Thông tư 04/2020/TT-BTP quy định chi tiết thi hành Luật Hộ tịch và Nghị định 123/2015/NĐ-CP | Bộ Tư pháp | Hồ sơ, biểu mẫu, cách làm từng trường hợp | 09/2022/TT-BTP, 04/2024/TT-BTP |
| 87.2020.ND-CP | Nghị định 87/2020/NĐ-CP về Cơ sở dữ liệu hộ tịch điện tử, đăng ký hộ tịch trực tuyến | Chính phủ | Đăng ký hộ tịch trực tuyến, bản sao trích lục | 07/2025 |

Văn bản sửa đổi (áp vào văn bản gốc qua `data/raw/amendments.yaml`, chỉ phần hộ tịch):

| doc_id | Văn bản | Phần dùng |
|---|---|---|
| 87.2020.ND-CP | (cũng là văn bản gốc ở trên) | Điều 25 khoản 2: bãi bỏ khoản 1, 2 Điều 12 NĐ 123 |
| 104.2022.ND-CP | Nghị định 104/2022/NĐ-CP sửa đổi các quy định liên quan việc nộp, xuất trình sổ hộ khẩu, sổ tạm trú | Điều 13 khoản 2: bỏ một cụm từ ở khoản 1 Điều 2 NĐ 123. Các Điều khác thuộc lĩnh vực khác |
| 09.2022.TT-BTP | Thông tư 09/2022/TT-BTP bãi bỏ một số nội dung tại các Thông tư về trợ giúp pháp lý, hộ tịch | Điều 2: bỏ "sổ hộ khẩu, sổ tạm trú" ở khoản 1 Điều 8 và điểm b khoản 3 Điều 9 TT 04/2020 |
| 04.2024.TT-BTP | Thông tư 04/2024/TT-BTP sửa đổi TT 02/2020 và TT 04/2020 | Điều 2: sửa TT 04/2020. Điều 1 (quốc tịch) ngoài phạm vi |
| 07.2025.ND-CP | Nghị định 07/2025/NĐ-CP sửa đổi các Nghị định về hộ tịch, quốc tịch, chứng thực | Điều 2 (sửa NĐ 123, thêm Điều 28a–28c) và Điều 3 (sửa NĐ 87). Điều 1, 4 ngoài phạm vi |
| 18.2026.ND-CP | Nghị định 18/2026/NĐ-CP sửa đổi một số nghị định để cắt giảm, đơn giản hóa thủ tục hành chính thuộc Bộ Tư pháp | Điều 13: sửa NĐ 123 (Điều 2, 22, 24, 26, 27). Các Điều khác ngoài phạm vi |

Văn bản ảnh hưởng hiệu lực nhưng không sửa câu chữ:

| doc_id | Văn bản | Phần dùng |
|---|---|---|
| 120.2025.ND-CP | Nghị định 120/2025/NĐ-CP quy định về phân định thẩm quyền của chính quyền địa phương 02 cấp trong lĩnh vực quản lý nhà nước của Bộ Tư pháp | Điều 4–8 và **mục I Phụ lục** (thời hạn mới, ví dụ kết hôn có yếu tố nước ngoài còn 05 ngày làm việc thay vì 15 ngày theo Luật) được chunk riêng; Điều 23 khoản 3: khi khác văn bản khác thì áp dụng NĐ 120. Hiệu lực 01/7/2025, hết hiệu lực từ 01/3/2027 |

Url, ngày hiệu lực, tình trạng hiệu lực và ngày tải từng văn bản ghi trong `data/raw/source_list.csv` (cột `amended_by`: văn bản sửa câu chữ; `affected_by`: văn bản chỉ ảnh hưởng hiệu lực).

Đã kiểm tra và **không đưa vào**: Nghị định 121/2025/NĐ-CP (phân quyền, phân cấp lĩnh vực Bộ Tư pháp) không có quy định về hộ tịch.

**Mốc hiệu lực của kho:** kho phản ánh quy định hộ tịch có hiệu lực tại ngày 09/10/2026, dùng được đến 28/02/2027. Luật Hộ tịch số 03/2026/QH16 có hiệu lực từ 01/3/2027 và thay thế toàn bộ Luật 60/2014, không được đưa vào vì chưa có hiệu lực. Đây là giới hạn của dữ liệu, cần ghi lại trong báo cáo. Danh sách văn bản sửa đổi đã đối chiếu với tab Lịch sử trên vbpl.vn ngày 09/10/2026.

**Ngày chốt:** 2026-10-06 (thêm Nghị định 123/2015 và Thông tư 04/2020 ngày 2026-10-08; thêm 07/2025/NĐ-CP, 04/2024/TT-BTP, 87/2020, 104/2022, 120/2025, cách hợp nhất bằng amendments.yaml và mốc hiệu lực ngày 2026-10-09; thêm 18/2026/NĐ-CP và 09/2022/TT-BTP sau khi đối chiếu vbpl.vn cùng ngày)

**Người duyệt:** Duy
