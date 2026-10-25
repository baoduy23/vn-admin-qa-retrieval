# src/app/: web hỏi đáp (Quân)

Viết bằng Streamlit, gọi `AnswerEngine.answer()` trong `src/answer/`. Giao diện bắt chước Cổng Dịch vụ công quốc gia (đầu trang chữ có chân màu đỏ đất, thanh menu, nút vàng nghệ) và Kho tri thức UEH hotro.ueh.edu.vn (banner lớn, câu chào "Hãy để chúng tôi hỗ trợ bạn", ô tìm kiếm bo tròn có ảnh hoa sen bên trái, danh sách chủ đề hữu ích mở/đóng, chân trang nhiều cột), giữ tông cam đất. Ảnh mặc định lấy trên Wikimedia Commons: hoa sen, hoạ tiết chim Lạc, hoa văn mặt trống đồng Đông Sơn (phạm vi công cộng hoặc CC BY / CC BY-SA, tác giả và giấy phép từng ảnh ghi trong `images.py`). Không dùng quốc huy, và có ghi rõ đây không phải cổng của cơ quan nhà nước.

## Chạy

Từ gốc repo:

```bash
pip install -r requirements.txt                 # có streamlit
streamlit run src/app/main.py                   # dùng pipeline TV3 đã chốt (cần: pip install sentence-transformers torch)
```

Ảnh giao diện chỉ có 3 ảnh: `hoa_sen` (bên trái ô tìm kiếm), `chim_lac` (dải chim ở chân trang), `hoa_van_trong_dong` (nền mờ khu tìm kiếm). Muốn đổi ảnh thì chép ảnh vào `src/app/static/img/`, đặt đúng tên đó (đuôi .jpg/.png/.webp) rồi bấm Ctrl + F5. Thiếu ảnh nào thì web lấy ảnh mặc định trên Wikimedia Commons. Muốn tải sẵn ảnh mặc định về máy (không ghi đè ảnh đã có) thì chạy:

```bash
python -m src.app.images
```

Máy yếu hoặc chưa cài torch thì chạy bản BM25 (vẫn đủ 7 chức năng):

```bash
# Windows PowerShell
$env:ANSWER_PIPELINE="bm25"; streamlit run src/app/main.py
# macOS / Linux
ANSWER_PIPELINE=bm25 streamlit run src/app/main.py
```

Nếu nạp model bị lỗi (thiếu thư viện, không tải được từ Hugging Face) thì app tự chuyển về BM25 và hiện cảnh báo vàng dưới ô tìm kiếm.

Muốn trang Thống kê có số liệu lúc demo thì chạy `python -m src.app.demo_seed` (hỏi lần lượt các câu train + validation, không lấy test). Muốn xoá lịch sử thì xoá file `artifacts/app.db`.

## File

| File | Nội dung |
|---|---|
| `main.py` | App: đầu trang, thanh tab, dải tìm kiếm, 4 tab Hỏi đáp / Lịch sử truy vấn / Thống kê / Giới thiệu hệ thống |
| `db.py` | SQLite `artifacts/app.db` (đổi bằng biến `APP_DB`): `queries(id, time, question, refused, top_chunk_id, top_score, reason, n_parts, pipeline)`, `feedback(query_id, rating, comment, time)` |
| `style.py` | CSS, bảng màu |
| `images.py` | 3 ảnh giao diện: ưu tiên ảnh trong `static/img/`, không có thì dùng ảnh mặc định (Wikimedia); `python -m src.app.images` tải ảnh mặc định |
| `static/img/` | Ảnh giao diện (xem `README.txt` trong thư mục) (Streamlit phục vụ qua `app/static/...`, bật `enableStaticServing` trong `.streamlit/config.toml`) |
| `demo_seed.py` | Nạp lịch sử mẫu cho buổi demo |
| `requirements.txt` | Thư viện cho Streamlit Community Cloud (có torch CPU) |

`.streamlit/config.toml` ở gốc repo đặt theme sáng cùng tông màu.

## 7 chức năng theo đề bài

| Đề bài yêu cầu | Trên web |
|---|---|
| Giao diện hỏi đáp | Ô hỏi bo tròn, 3 nút vàng hỏi nhanh; mục "Tìm kiếm chủ đề hữu ích": 8 việc hộ tịch, mỗi việc 5 câu hỏi mẫu (lấy từ train + validation, không lấy test), bấm là hỏi |
| Câu trả lời đề xuất | Thẻ "Câu trả lời đề xuất": `Theo <văn bản>, Điều X Khoản Y: "<trích nguyên văn>"`; câu nhiều ý trả lời từng ý |
| Nguồn tài liệu và đoạn trích | Danh sách top-5 đoạn: tên văn bản, Điều/Khoản, link văn bản gốc, thanh điểm, đoạn trích có tô chữ trùng câu hỏi và tô nền dòng được trích |
| Câu hỏi tương tự | Cột phải, bấm vào là hỏi luôn (`similar_questions` của TV3, không lấy câu test) |
| Đánh giá câu trả lời | Nút Hữu ích / Chưa đúng (kèm ô góp ý), lưu bảng `feedback` |
| Thông báo khi không có căn cứ | Thẻ vàng "Chưa đủ căn cứ để trả lời" + lý do (điểm thấp hơn τ, hoặc văn bản không có con số câu hỏi đòi) + gợi ý liên hệ UBND cấp xã |
| Lịch sử và thống kê chủ đề | Tab Lịch sử (lọc, hỏi lại, tải CSV); tab Thống kê (tổng lượt, tỉ lệ trả lời/từ chối, % hữu ích, chủ đề hỏi nhiều, Điều được trích nhiều, lượt theo ngày, lý do từ chối) |

Ngoài ra còn có: gợi ý chọn việc cụ thể khi câu hỏi thiếu thông tin, lưu ý tự động khi đoạn trích còn ghi "cấp huyện" (Nghị định 120/2025/NĐ-CP đã chuyển về cấp xã) hoặc là Điều đã hợp nhất sửa đổi, và ô "Chi tiết kỹ thuật" hiện pipeline, τ, điểm từng ý cho tiện lúc thuyết trình.

## Deploy lên Streamlit Community Cloud

1. Đăng nhập https://share.streamlit.io bằng tài khoản GitHub có quyền đọc repo.
2. Bấm Create app, chọn repo `baoduy23/vn-admin-qa-retrieval`, nhánh `main`, file `src/app/main.py`.
3. Trong Advanced settings chọn Python 3.11. Ô Secrets để trống (bản đầy đủ). Nếu app bị khởi động lại vì thiếu RAM (2 model PhoBERT-base chạy CPU), thêm vào Secrets dòng `ANSWER_PIPELINE = "bm25"` để chạy bản nhẹ.
4. Deploy, lần đầu phải đợi tải model vài phút. Xong gửi link cho TV5 để đưa vào slide và kịch bản demo.

Lưu ý: ổ đĩa trên Cloud bị xoá mỗi lần app khởi động lại nên lịch sử và đánh giá chỉ giữ trong một lần chạy. Buổi demo nên chạy `demo_seed` trên máy hoặc quay video dự phòng.
