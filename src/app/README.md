# src/app/ — giao diện hỏi đáp (TV4)

Chưa có code. Dự kiến:

- Streamlit, gọi `answer(question)` → câu trả lời trích nguyên văn (`display_text`) kèm nguồn (`title`, `url`), hoặc thông báo từ chối khi điểm dưới ngưỡng.
- Đủ các chức năng đề bài yêu cầu: câu trả lời, nguồn + đoạn trích, câu hỏi tương tự, nút đánh giá, thông báo khi không có căn cứ, lịch sử và thống kê.
- SQLite: bảng `queries(id, time, question, refused, top_doc_id)` và `feedback(query_id, rating)`.
- Làm khung trên dữ liệu giả trước; khi TV3 có `retrieve()` thì ráp vào.

Chạy (khi có code): `streamlit run src/app/main.py`
