# results/user_study/: đánh giá với người dùng

Người ngoài nhóm dùng thử bản web (https://hoidap-hotich.streamlit.app) đêm 28 rạng sáng 29/10/2026. Mỗi người tự đặt 3–5 câu hỏi, không dùng câu có sẵn trong bộ dữ liệu, gồm ít nhất 1 câu gõ không dấu và 1 câu ngoài hộ tịch. Sau mỗi câu, người dùng bấm Hữu ích / Chưa đúng trên web rồi điền phiếu Google Form. Cuối buổi điền thang SUS (Brooke, 1996) 10 câu, bản tiếng Việt do nhóm tự dịch, chưa kiểm định.

Người dùng không có chuyên môn pháp lý, nên ô "đúng ý" trên phiếu chỉ là cảm nhận của họ. Ví dụ có người chấm "sai" cho câu hỏi thời tiết dù app đã từ chối đúng. Vì vậy nhóm chấm lại từng câu theo [hướng dẫn gán nhãn](../../data/labels/annotation_guideline.md): câu thuộc phạm vi nào (in_scope / unsupported / out_of_scope), và app quyết định trả lời hay từ chối có đúng không.

Các câu hỏi ở đây không được thêm vào `questions.csv`, `qrels.csv` hay tập test.

| File | Nội dung |
|---|---|
| `phieu_khao_sat.csv` | Phiếu Google Form, đã bỏ cột thời gian, không thu email |
| `nhom_cham.csv` | Nhóm chấm lại từng câu: phạm vi, quyết định đúng/sai, nguồn top-1 (để trống là chưa chấm) |
| `tong_hop.py` | Tính các bảng trong `ket_qua.md`. `EXCLUDE` là danh sách phiếu không tính, hiện để trống |
| `ket_qua.md` | Kết quả |

```bash
python results/user_study/tong_hop.py
```

Giới hạn: số người ít và chọn theo kiểu thuận tiện (người quen của nhóm), nên kết quả chỉ để mô tả và tìm lỗi, không dùng để kết luận thống kê.
