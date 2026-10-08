# Phạm vi dữ liệu

> Nhóm điền và chốt file này ở task S01. Sửa phạm vi sau khi đã freeze Dataset v1 phải làm lại nhãn.

**Lĩnh vực đã chọn:** Hộ tịch 

**Lý do:** nhiều câu hỏi thực tế, có sẵn các thủ tục gần giống nhau (khai sinh, kết hôn, khai tử, cải chính...) phục vụ phân tích bắt buộc.

**Ngoài phạm vi (dùng làm câu hỏi từ chối):** đất đai, cư trú, thuế, các lĩnh vực khác.

**Nguồn chính:** vbpl.vn | CSDL quốc gia về pháp luật (lọc lĩnh vực Hộ tịch); văn bản pháp luật về hộ tịch còn hiệu lực tại ngày tải. Văn bản nào trên vbpl.vn hoặc vanban.chinhphu.vn chỉ có PDF scan (không đọc được chữ) thì lấy toàn văn trên thuvienphapluat.vn và giữ file scan trong `data/raw/` để đối chiếu. Không cào web.

**Văn bản trong kho (Dataset v1):**

| doc_id | Văn bản | Cơ quan ban hành | Vai trò |
|---|---|---|---|
| 60.2014.QH13 | Luật Hộ tịch 60/2014/QH13 | Quốc hội | Nguyên tắc, thẩm quyền, thủ tục chung |
| 123.2015.ND-CP | Nghị định 123/2015/NĐ-CP quy định chi tiết một số điều và biện pháp thi hành Luật Hộ tịch | Chính phủ | Chi tiết thủ tục, giấy tờ |
| 04.2020.TT-BTP | Thông tư 04/2020/TT-BTP quy định chi tiết thi hành Luật Hộ tịch và Nghị định 123/2015/NĐ-CP | Bộ Tư pháp | Hồ sơ, biểu mẫu, cách làm từng trường hợp |

Url và ngày tải từng văn bản ghi trong `data/raw/source_list.csv`.

**Ngày chốt:** 2026-10-06 (thêm Nghị định 123/2015 và Thông tư 04/2020 ngày 2026-10-08)

**Người duyệt:** Duy
